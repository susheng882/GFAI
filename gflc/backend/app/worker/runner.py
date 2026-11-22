# -*- coding: utf-8 -*-
"""后台任务执行器：单线程串行消费，重活不再阻塞事件循环。
handler 签名：fn(db, task, payload, update) -> dict
    update(progress: int, message: str | None = None)

P1 稳定性补强：
- 进度看门狗：独立守护线程每 15s 扫描，无进度超过 TASK_TIMEOUT 判定卡死 → 标 failed(TASK-TIMEOUT)
- worker 线程疑似死亡/长时间卡住 → 重新拉起线程（旧线程阻塞调用返回后自然退出）
- 进程重启恢复：running 超 5 分钟标 failed(TASK-INTERRUPTED)，pending 重新入队
- 提交任务时把 payload 落进 checkpoint，重试接口才能还原参数
"""
import logging
import os
import queue
import threading
import time
import traceback
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.budget import set_current_user_id
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import Task

log = logging.getLogger("gflc.worker")

# 可重放的 payload 需要能还原；提交时落 checkpoint（见 _remember_payload）
_REPLAY_BY_DOC = ("pdf_parse", "card_generate")


def _read_timeout() -> int:
    """优先环境变量 TASK_TIMEOUT，其次 settings，最后 600s。"""
    for raw in (os.getenv("TASK_TIMEOUT"), os.getenv("TASK_TIMEOUT_SECONDS"),
                getattr(settings, "TASK_TIMEOUT", None)):
        if raw is None or raw == "":
            continue
        try:
            v = int(float(raw))
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return 600


TASK_TIMEOUT_SECONDS = _read_timeout()
WATCH_INTERVAL_SECONDS = float(os.getenv("TASK_WATCH_INTERVAL") or 15)
INTERRUPT_GRACE_SECONDS = 300  # 重启后 running 超过 5 分钟即视为僵尸任务

_q: "queue.Queue[tuple[int, str, dict]]" = queue.Queue()
_handlers: dict[str, callable] = {}

_state = threading.Lock()
_started = False
_generation = 0
_thread: "threading.Thread | None" = None
_watchdog_thread: "threading.Thread | None" = None
_boot_done = False  # 启动期恢复只做一次，避免 wake() 抢跑运行中的任务
# task_id -> {"gen": int, "started": float, "progress": float}
_meta: dict[int, dict] = {}
# 已入队 / 正在执行的任务 id（避免 recover 重复入队）
_queued: set[int] = set()
# 看门狗判定超时后通知主循环：不要再回写 ready
_cancel: set[int] = set()


def register(task_type: str, fn):
    _handlers[task_type] = fn


def submit(task_id: int, task_type: str, payload: dict | None = None):
    payload = payload or {}
    _remember_payload(task_id, payload)
    _enqueue(task_id, task_type, payload)


def _enqueue(task_id: int, task_type: str, payload: dict) -> bool:
    with _state:
        if task_id in _queued:
            return False
        _queued.add(task_id)
    _q.put((task_id, task_type, payload))
    return True


def _remember_payload(task_id: int, payload: dict):
    """把 payload 落到 checkpoint，进程重启/重试时据此还原参数。失败不影响主流程。"""
    db = SessionLocal()
    try:
        task = db.get(Task, task_id)
        if task is None:
            return
        cp = dict(task.checkpoint or {})
        cp["payload"] = payload
        task.checkpoint = cp
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        log.warning("任务 %s 的 payload 落库失败，重试能力受限", task_id, exc_info=True)
    finally:
        db.close()


def create_task(db, user_id: int, task_type: str, document_id: int | None = None) -> Task:
    t = Task(user_id=user_id, type=task_type, document_id=document_id, status="pending", progress=0)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def _loop(gen: int):
    while True:
        with _state:
            if gen != _generation:
                return  # 已被看门狗重启，旧线程收工
        task_id, task_type, payload = _q.get()
        try:
            _run_task(gen, task_id, task_type, payload)
        except Exception:  # noqa: BLE001
            log.exception("worker 执行任务 %s 时发生未捕获异常", task_id)
        finally:
            _q.task_done()


def _run_task(gen: int, task_id: int, task_type: str, payload: dict):
    db = SessionLocal()
    task = None
    try:
        task = db.get(Task, task_id)
        if not task:
            return
        with _state:
            if task_id in _cancel:
                _cancel.discard(task_id)
                log.warning("任务 %s 在开跑前已被取消，跳过", task_id)
                return
            _meta[task_id] = {"gen": gen, "started": time.time(), "progress": time.time()}

        task.status = "running"
        task.progress = 1
        task.error_code = None
        task.error_message = None
        db.commit()

        # S3：后台任务也要把用户写入 ContextVar，否则 ai 层读不到归属、
        # 预算拦截被跳过或记到别的请求名下。asyncio.run 会继承当前 context。
        set_current_user_id(task.user_id)

        def update(p: int, message: str | None = None):
            task.progress = max(1, min(99, int(p)))
            db.commit()
            with _state:
                m = _meta.get(task_id)
                if m is not None:
                    m["progress"] = time.time()

        # 心跳：长阶段（如 ffmpeg 抽帧）无法回写百分比时，用它刷新看门狗时间戳，
        # 避免「任务正常执行中却被判 TASK-TIMEOUT」。只刷新内存时间戳，不写 DB。
        def beat():
            with _state:
                m = _meta.get(task_id)
                if m is not None:
                    m["progress"] = time.time()
        update.beat = beat

        fn = _handlers.get(task_type)
        if not fn:
            raise RuntimeError(f"未知任务类型：{task_type}")
        result = fn(db, task, payload, update) or {}

        with _state:
            canceled = task_id in _cancel
            _cancel.discard(task_id)
        if canceled:
            log.warning("任务 %s 已被判定超时，丢弃迟到的执行结果", task_id)
            return
        try:
            db.refresh(task)  # 看门狗可能在别的 session 里把状态改成了 failed
        except Exception:  # noqa: BLE001
            pass
        if task.status == "failed":
            log.warning("任务 %s 已失败（可能超时），不覆盖为 ready", task_id)
            return
        task.status = "ready"
        task.progress = 100
        task.result = result
        db.commit()
    except Exception as e:  # noqa: BLE001
        try:
            with _state:
                canceled = task_id in _cancel
                _cancel.discard(task_id)
            if task is not None and not canceled:
                db.rollback()
                db.refresh(task)
                if task.status != "failed":
                    task.status = "failed"
                    task.error_code = "TASK-500"
                    task.error_message = str(e)[:500]
                    db.commit()
            traceback.print_exc()
        except Exception:  # noqa: BLE001
            pass
    finally:
        set_current_user_id(None)  # 清除任务身份，避免下一个任务继承
        with _state:
            _meta.pop(task_id, None)
            _queued.discard(task_id)
        db.close()


def _fail(task_id: int, code: str, message: str) -> bool:
    db = SessionLocal()
    try:
        t = db.get(Task, task_id)
        if t is None or t.status not in ("pending", "running"):
            return False
        t.status = "failed"
        t.error_code = code
        t.error_message = message[:500]
        db.commit()
        log.error("任务 %s 标记失败：%s（%s）", task_id, code, message)
        return True
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("标记任务 %s 失败时出错", task_id)
        return False
    finally:
        db.close()


def abort(task_id: int) -> bool:
    """用户主动放弃任务：DB 标 failed(TASK-ABORTED)，并加入 _cancel 让迟到结果作废。

    队列里的任务不移除（queue 无法随机删除），由 _run_task 开跑前检查 _cancel 跳过。
    """
    with _state:
        _cancel.add(task_id)
    ok = _fail(task_id, "TASK-ABORTED", "用户已放弃该任务")
    if not ok:
        with _state:
            _cancel.discard(task_id)
        return False
    with _state:
        _meta.pop(task_id, None)
    return True


def _ensure_worker(force: bool = False):
    global _thread, _generation
    with _state:
        if not force and _thread is not None and _thread.is_alive():
            return
        _generation += 1
        gen = _generation
        th = threading.Thread(target=_loop, args=(gen,), daemon=True, name=f"gflc-worker-{gen}")
        _thread = th
    th.start()
    log.info("worker 线程已启动：%s", th.name)


def _restart(reason: str):
    global _thread, _generation
    with _state:
        _generation += 1
        gen = _generation
        _meta.clear()  # 旧线程的进度记录不再可信；_cancel 保留，防止迟到结果覆盖 failed
        th = threading.Thread(target=_loop, args=(gen,), daemon=True, name=f"gflc-worker-{gen}")
        _thread = th
    th.start()
    log.error("worker 线程重启（%s），新线程 %s", reason, th.name)


def _scan():
    """看门狗单次扫描：超时标记 + 线程自愈。"""
    now = time.time()
    with _state:
        snap = [(tid, dict(m)) for tid, m in _meta.items()]
    for tid, m in snap:
        if now - m["progress"] > TASK_TIMEOUT_SECONDS:
            if _fail(tid, "TASK-TIMEOUT",
                     f"任务超过 {TASK_TIMEOUT_SECONDS}s 无进度，判定卡死并终止等待，可重试"):
                with _state:
                    _cancel.add(tid)
                    cur = _meta.get(tid)
                    if cur is not None:
                        cur["progress"] = time.time()  # 避免重复告警

    with _state:
        alive = _thread is not None and _thread.is_alive()
        stuck = [(tid, dict(m)) for tid, m in _meta.items()
                 if now - m["started"] > TASK_TIMEOUT_SECONDS * 2]
    if not alive:
        log.error("worker 线程不存在或已退出，重新拉起")
        _restart("线程已死亡")
        return
    if stuck:
        for tid, _m in stuck:
            _fail(tid, "TASK-TIMEOUT",
                  f"任务执行超过 {TASK_TIMEOUT_SECONDS * 2}s，worker 线程疑似卡死，已重启执行器")
            with _state:
                _cancel.add(tid)
        _restart(f"任务 {stuck[-1][0]} 运行超过 {TASK_TIMEOUT_SECONDS * 2}s")


def _watchdog():
    while True:
        time.sleep(WATCH_INTERVAL_SECONDS)
        try:
            _scan()
        except Exception:  # noqa: BLE001
            log.exception("看门狗扫描异常")


def _ensure_watchdog():
    global _watchdog_thread
    with _state:
        if _watchdog_thread is not None and _watchdog_thread.is_alive():
            return
        th = threading.Thread(target=_watchdog, daemon=True, name="gflc-watchdog")
        _watchdog_thread = th
    th.start()


def _as_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _payload_from_task(t: Task) -> dict | None:
    """从 checkpoint / document_id 还原 payload；还原不了返回 None。"""
    cp = t.checkpoint if isinstance(t.checkpoint, dict) else {}
    p = cp.get("payload")
    if isinstance(p, dict) and p:
        payload = dict(p)
        if t.document_id and not payload.get("document_id"):
            payload["document_id"] = t.document_id
        return payload
    if t.document_id and t.type in _REPLAY_BY_DOC:
        return {"document_id": t.document_id}
    return None


def recover(db=None, force: bool = False) -> dict:
    """进程重启后的任务恢复：僵尸 running 标失败，pending 重新入队。

    只有启动后第一次 recover（或 force=True）才会把"新近 running"退回 pending；
    之后的 wake() 只补入队，避免抢跑别的线程/进程正在执行的任务。
    """
    global _boot_done
    own = db is None
    db = db or SessionLocal()
    boot = force or not _boot_done
    failed = requeued = skipped = 0
    queue_items: list[tuple[int, str, dict]] = []
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=INTERRUPT_GRACE_SECONDS)
        rows = list(db.scalars(select(Task).where(Task.status.in_(("running", "pending")))
                               .order_by(Task.id)))
        with _state:
            inprocess = set(_meta) | set(_queued)
        for t in rows:
            if t.id in inprocess:
                continue
            if t.status == "running":
                if not boot:
                    skipped += 1  # 运行中但不在本进程，可能是别的实现/进程，不抢
                    continue
                created = _as_aware(t.created_at)
                if created is not None and created < cutoff:
                    t.status = "failed"
                    t.error_code = "TASK-INTERRUPTED"
                    t.error_message = "服务重启导致中断，可重试"
                    failed += 1
                    continue
                # 新近的 running：重启后无线程持有，退回 pending 重新跑
                t.status = "pending"
                t.progress = 0
            payload = _payload_from_task(t)
            if payload is None or t.type not in _handlers:
                skipped += 1
                log.warning("任务 %s（%s）缺少可还原参数，保持 pending 不自动重跑", t.id, t.type)
                continue
            queue_items.append((t.id, t.type, payload))
            requeued += 1
        db.commit()
        _boot_done = True
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("任务恢复失败")
    finally:
        if own:
            db.close()

    for task_id, task_type, payload in queue_items:
        _enqueue(task_id, task_type, payload)
    if failed or requeued or skipped:
        log.warning("任务恢复完成：僵尸 failed=%s，重新入队=%s，跳过=%s", failed, requeued, skipped)
    return {"failed": failed, "requeued": requeued, "skipped": skipped}


def wake():
    """外部触发一次恢复扫描并确保 worker 存活。"""
    try:
        recover()
    except Exception:  # noqa: BLE001
        log.exception("wake 恢复扫描失败")
    _ensure_worker()
    _ensure_watchdog()


def health() -> dict:
    with _state:
        items = list(_meta.items())
        th = _thread
    alive = bool(th is not None and th.is_alive())
    current, elapsed = None, 0.0
    if items:
        cur_id, m = max(items, key=lambda kv: kv[1]["started"])
        current = cur_id
        elapsed = round(max(0.0, time.time() - m["started"]), 1)
    return {
        "alive": alive,
        "queue_size": _q.qsize(),
        "current_task": current,
        "current_elapsed": elapsed,
        "timeout_seconds": TASK_TIMEOUT_SECONDS,
        "worker": th.name if th is not None else None,
    }


def start():
    global _started
    with _state:
        already = _started
        _started = True
    if not already:
        try:
            recover()
        except Exception:  # noqa: BLE001
            log.exception("启动时任务恢复失败")
    _ensure_worker()
    _ensure_watchdog()
