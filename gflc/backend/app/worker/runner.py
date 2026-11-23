# -*- coding: utf-8 -*-
"""后台任务执行器：单线程串行消费，重活不再阻塞事件循环。
handler 签名：fn(db, task, payload, update) -> dict
    update(progress: int, message: str | None = None)

P1 稳定性补强：
- 进度看门狗：独立守护线程每 15s 扫描，无进度超过阶段阈值判定卡死 → 标 failed(TASK-TIMEOUT)
- worker 线程疑似死亡/长时间卡住 → 重新拉起线程（旧线程阻塞调用返回后自然退出）
- 进程重启恢复：running 超 5 分钟标 failed(TASK-INTERRUPTED)，pending 重新入队
- 提交任务时把 payload 落进 checkpoint，重试接口才能还原参数

V2/D2/A6/S8 补强（本轮）：
- 队列后端由 queue.py 决定：memory（进程内，默认）/ redis（RQ 独立 Worker）/ auto（探测回落）
- API 在 redis 模式只 enqueue，不启动本地 worker 线程；执行入口 execute_task 供 RQ Worker 复用
- 任务态显式包含 queued：看门狗只对 running 计时；queued 用独立 TASK_QUEUE_TIMEOUT
- running 阶段按阶段阈值计时（由 update(message) 推断阶段，或 update.stage(name) 显式指定），
  默认阈值来自 settings.TASK_TIMEOUT / TASK_TIMEOUT
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
from app.worker import queue as queue_mod

log = logging.getLogger("gflc.worker")

# 任务态：queued 为显式一等状态（D2/A6），不进 running 看门狗计时
STATUS_PENDING = "pending"
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_READY = "ready"
STATUS_FAILED = "failed"

# 可读错误码：任何降级/超时/入队失败都通过 error_code 暴露，禁止静默
ERR_TASK_TIMEOUT = "TASK-TIMEOUT"
ERR_QUEUE_TIMEOUT = "TASK-QUEUE-TIMEOUT"
ERR_ENQUEUE_FAILED = "TASK-ENQUEUE-FAILED"

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


def _read_queue_timeout() -> int:
    """排队超时独立阈值（D2）：默认 600s，避免排队任务被 running 看门狗误杀。"""
    raw = os.getenv("TASK_QUEUE_TIMEOUT")
    if raw not in (None, ""):
        try:
            v = int(float(raw))
            if v > 0:
                return v
            log.error("TASK-QUEUE-TIMEOUT-CONFIG-INVALID: TASK_QUEUE_TIMEOUT=%r 非正数，使用默认 600", raw)
        except (TypeError, ValueError):
            log.error("TASK-QUEUE-TIMEOUT-CONFIG-INVALID: TASK_QUEUE_TIMEOUT=%r 非法，使用默认 600", raw)
    return 600


QUEUE_TIMEOUT_SECONDS = _read_queue_timeout()

# running 阶段阈值：默认沿用 settings.TASK_TIMEOUT（见 _read_timeout）；
# 可用 TASK_STAGE_TIMEOUT_<STAGE> 覆盖，例如 TASK_STAGE_TIMEOUT_TRANSCRIBE=3600。
# 阶段名由 update(p, message) 的中文 message 推断，或 update.stage(name) 显式指定。
_STAGE_RULES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("语音转写", "抽取音频"), "transcribe"),
    (("识别关键帧文字", "识别拼图文字", "逐页视觉识别", "视觉识别", "识别题目"), "ocr"),
    (("提取关键帧", "提取关键帧拼图", "抽帧", "关键帧"), "frames"),
    (("下载文件", "解析链接", "下载完成", "字幕取材", "取材完成"), "io"),
    (("解析 PDF", "读取文件", "读取真实数据", "准备生成"), "parse"),
    (("生成图文笔记", "生成", "拆解任务", "设计布局"), "generate"),
    (("写入", "保存布局", "整理结果"), "finish"),
)
_STAGE_NAMES = tuple(dict((s, 1) for _, s in _STAGE_RULES))  # 去重后的阶段名，供 health 展示


def infer_stage(message: str | None) -> str | None:
    """从 handler 的进度文案推断当前阶段；推断不出返回 None（走全局默认阈值）。"""
    if not message:
        return None
    for keywords, stage in _STAGE_RULES:
        if any(k in message for k in keywords):
            return stage
    return None


def stage_timeout(stage: str | None) -> int:
    """返回阶段超时秒数；默认来自 TASK_TIMEOUT / settings.TASK_TIMEOUT。"""
    default = TASK_TIMEOUT_SECONDS
    if not stage:
        return default
    raw = os.getenv(f"TASK_STAGE_TIMEOUT_{str(stage).upper()}")
    if raw in (None, ""):
        return default
    try:
        v = int(float(raw))
    except (TypeError, ValueError):
        log.error("STAGE-TIMEOUT-CONFIG-INVALID: TASK_STAGE_TIMEOUT_%s=%r 非法，使用默认 %ss",
                  str(stage).upper(), raw, default)
        return default
    if v <= 0:
        log.error("STAGE-TIMEOUT-CONFIG-INVALID: TASK_STAGE_TIMEOUT_%s=%r 非正数，使用默认 %ss",
                  str(stage).upper(), raw, default)
        return default
    return v


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
# 视频任务独立并发池：视频是「下载 + 云转写 + LLM」的 IO 等待型任务，
# 单线程会把整季 16P 排成一小时；而 PDF/题库等仍走单线程，避免 SQLite 写锁打架。
VIDEO_TASK_TYPES = {"video_url", "video_upload"}
_vq: "queue.Queue" = queue.Queue()
_vthreads: list["threading.Thread"] = []
# 看门狗判定超时后通知主循环：不要再回写 ready
_cancel: set[int] = set()


def register(task_type: str, fn):
    _handlers[task_type] = fn


def _record_timeline(db, task, p: int, message: str) -> None:
    """把阶段切换时间点写进 checkpoint.stage_timeline，供性能定位用。

    只记「文案变化」的那一次，避免同一阶段的高频 update 刷爆 checkpoint；
    写失败只 WARNING，绝不影响主流程（与 _cp_save 同一策略）。
    """
    try:
        # JSON 列必须换新对象，原地改 dict 不会触发 SQLAlchemy UPDATE（踩过一次）
        cp = dict(task.checkpoint) if isinstance(task.checkpoint, dict) else {}
        tl = list(cp.get("stage_timeline") or [])
        label = str(message)[:40]
        if tl and tl[-1].get("m") == label:
            return
        t0 = task.created_at
        if t0 is None:
            el = 0.0
        else:
            base = t0 if t0.tzinfo else t0.replace(tzinfo=timezone.utc)
            el = round(max(0.0, (datetime.now(timezone.utc) - base).total_seconds()), 1)
        tl.append({"t": el, "p": int(p), "m": label})
        cp["stage_timeline"] = tl[-40:]
        task.checkpoint = cp
        db.commit()
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:
            pass
        log.warning("stage_timeline 写入失败（task=%s）：%s", getattr(task, "id", "?"), e)


def submit(task_id: int, task_type: str, payload: dict | None = None):
    """提交任务。memory 路径与改前完全一致；redis 路径只入队、不执行。"""
    payload = payload or {}
    _remember_payload(task_id, payload)
    dispatch(task_id, task_type, payload)


def dispatch(task_id: int, task_type: str, payload: dict) -> bool:
    """按当前后端分派入队。redis 入队失败显式标 failed 并打 ERROR，不静默假装成功。"""
    backend, _init_error = queue_mod.current_backend()
    if backend == "memory":
        return _enqueue(task_id, task_type, payload)

    res = queue_mod.enqueue(task_id, task_type, payload, timeout=TASK_TIMEOUT_SECONDS)
    if res.ok:
        _mark_queued(task_id, res.job_id)
        return True
    # 不静默：DB 落 failed + 可读错误码 + ERROR 日志
    _fail(task_id, ERR_ENQUEUE_FAILED,
          f"{res.error_code or 'QUEUE-ENQUEUE-FAILED'}: {res.error_message}")
    log.error("QUEUE-ENQUEUE-FAILED: 任务 %s（%s）未入队，已标 failed（%s）",
              task_id, task_type, res.error_code)
    return False


def _mark_queued(task_id: int, job_id: str | None):
    """RQ 入队成功后落显式 queued 态 + 排队时间戳（排队超时独立计）。"""
    db = SessionLocal()
    try:
        t = db.get(Task, task_id)
        if t is None:
            return
        cp = dict(t.checkpoint or {})
        cp["queued_at"] = time.time()
        if job_id:
            cp["rq_job_id"] = job_id
        t.checkpoint = cp
        t.status = STATUS_QUEUED
        t.progress = 0
        t.error_code = None
        t.error_message = None
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        # 入队已成功，Worker 仍会推进任务；但 DB 状态滞后必须显式告警，不静默吞掉
        log.error("任务 %s 标记 queued 失败：RQ 任务已入队但 DB 状态可能滞后", task_id, exc_info=True)
    finally:
        db.close()


def _enqueue(task_id: int, task_type: str, payload: dict) -> bool:
    with _state:
        if task_id in _queued:
            return False
        _queued.add(task_id)
    if task_type in VIDEO_TASK_TYPES:
        _vq.put((task_id, task_type, payload))
    else:
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


def _loop(gen: int, q: "queue.Queue | None" = None):
    q = q or _q
    while True:
        with _state:
            if gen != _generation:
                return  # 已被看门狗重启，旧线程收工
        task_id, task_type, payload = q.get()
        try:
            _run_task(gen, task_id, task_type, payload)
        except Exception:  # noqa: BLE001
            log.exception("worker 执行任务 %s 时发生未捕获异常", task_id)
        finally:
            q.task_done()


def _run_task(gen: int, task_id: int, task_type: str, payload: dict):
    db = SessionLocal()
    task = None
    try:
        task = db.get(Task, task_id)
        if not task:
            return
        # 跨进程放弃（RQ 模式 API 与 Worker 不同进程，_cancel 不共享）：
        # DB 已是 failed/ready 说明用户已放弃或任务已完成，绝不覆盖重跑。
        if task.status in (STATUS_FAILED, STATUS_READY):
            log.warning("任务 %s 当前状态=%s，跳过执行（可能已放弃或已完成）", task_id, task.status)
            return
        with _state:
            if task_id in _cancel:
                _cancel.discard(task_id)
                log.warning("任务 %s 在开跑前已被取消，跳过", task_id)
                return
            _meta[task_id] = {"gen": gen, "started": time.time(), "progress": time.time(),
                              "stage": None, "task_type": task_type}

        # 原子领取：5 路并发下必须用条件 UPDATE 抢占，否则同一任务可能被两个线程跑
        from sqlalchemy import update as sa_update
        claimed = db.execute(
            sa_update(Task)
            .where(Task.id == task_id, Task.status.in_((STATUS_PENDING, STATUS_QUEUED)))
            .values(status=STATUS_RUNNING, progress=1, error_code=None, error_message=None)
        ).rowcount
        db.commit()
        if not claimed:
            log.warning("任务 %s 已被其他 worker 领取或状态已变，跳过", task_id)
            return
        db.refresh(task)

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
                    stage = infer_stage(message)
                    if stage:
                        m["stage"] = stage
            if message:
                _record_timeline(db, task, p, message)

        # 显式阶段标注：handler 可调 update.stage("transcribe") 指定阶段阈值，
        # 未调用时由 update(p, message) 的中文文案自动推断（对现有 handler 零改动）。
        def set_stage(name: str):
            with _state:
                m = _meta.get(task_id)
                if m is not None:
                    m["stage"] = str(name)

        # 心跳：长阶段（如 ffmpeg 抽帧）无法回写百分比时，用它刷新看门狗时间戳，
        # 避免「任务正常执行中却被判 TASK-TIMEOUT」。只刷新内存时间戳，不写 DB。
        def beat():
            with _state:
                m = _meta.get(task_id)
                if m is not None:
                    m["progress"] = time.time()
        update.beat = beat
        update.stage = set_stage

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


def execute_task(task_id: int, task_type: str, payload: dict | None = None) -> dict:
    """RQ Worker 的任务执行入口（queue.run_rq_job 调用）。

    与内存队列共用 _run_task 核心，确保 handler 分派、状态机、心跳语义完全一致；
    API 进程永不调用本函数（redis 模式下不启动本地 worker）。
    """
    payload = payload or {}
    _run_task(0, task_id, task_type, payload)
    return {"task_id": task_id, "type": task_type}


def start_watchdog_only():
    """RQ Worker 进程专用：只启动任务级看门狗，不启动本地内存消费线程。"""
    global _started
    with _state:
        _started = True
    _ensure_watchdog()


def _fail(task_id: int, code: str, message: str) -> bool:
    db = SessionLocal()
    try:
        t = db.get(Task, task_id)
        if t is None or t.status not in (STATUS_PENDING, STATUS_QUEUED, STATUS_RUNNING):
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
    # V2：redis 模式禁止 API 进程本地执行任务，只入队（Worker 在独立进程）
    if queue_mod.current_backend()[0] == "redis":
        log.error("QUEUE-POLICY-VIOLATION: redis 模式下拒绝在 API 进程启动本地 worker 线程；"
                  "请用 python -m app.worker.queue_worker 启动 Worker")
        return
    global _thread, _vthreads, _generation
    with _state:
        if not force and _thread is not None and _thread.is_alive():
            return
        _generation += 1
        gen = _generation
        th = threading.Thread(target=_loop, args=(gen,), daemon=True, name=f"gflc-worker-{gen}")
        _thread = th
        # 视频并发池：默认 5（VIDEO_CONCURRENCY 可调），整季 16P 才不会排成一小时
        n = max(1, int(getattr(settings, "VIDEO_CONCURRENCY", 5) or 5))
        _vthreads = [threading.Thread(target=_loop, args=(gen, _vq), daemon=True,
                                      name=f"gflc-vworker-{gen}-{i}") for i in range(n)]
    th.start()
    for v in _vthreads:
        v.start()
    log.info("worker 线程已启动：%s；视频并发池 %s 个：%s", th.name, len(_vthreads),
             [v.name for v in _vthreads])


def _restart(reason: str):
    global _thread, _vthreads, _generation
    with _state:
        _generation += 1
        gen = _generation
        _meta.clear()  # 旧线程的进度记录不再可信；_cancel 保留，防止迟到结果覆盖 failed
        th = threading.Thread(target=_loop, args=(gen,), daemon=True, name=f"gflc-worker-{gen}")
        _thread = th
        n = max(1, int(getattr(settings, "VIDEO_CONCURRENCY", 5) or 5))
        _vthreads = [threading.Thread(target=_loop, args=(gen, _vq), daemon=True,
                                      name=f"gflc-vworker-{gen}-{i}") for i in range(n)]
    th.start()
    for v in _vthreads:
        v.start()
    log.error("worker 线程重启（%s），新线程 %s + 视频池 %s", reason, th.name, len(_vthreads))


def _scan_queue_timeouts(now: float) -> int:
    """D2：queued 态独立排队超时；只对 running 计时的看门狗不碰这些任务。

    仅 redis 模式 DB 会落 queued 态；memory 模式任务仍是 pending，行为与改前一致。
    """
    if queue_mod.current_backend()[0] != "redis":
        return 0
    db = SessionLocal()
    timed_out: list[tuple[int, str]] = []
    try:
        rows = list(db.scalars(select(Task).where(Task.status == STATUS_QUEUED)))
        for t in rows:
            cp = t.checkpoint if isinstance(t.checkpoint, dict) else {}
            raw = cp.get("queued_at")
            try:
                qa = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                qa = None
            if qa is None:
                # 不静默：缺时间戳也要显式告警并按 created_at 兜底计时
                created = _as_aware(t.created_at)
                qa = created.timestamp() if created is not None else None
                log.error("QUEUE-TIMESTAMP-MISSING: 任务 %s 缺少 queued_at，按 created_at 兜底计时", t.id)
            if qa is not None and now - qa > QUEUE_TIMEOUT_SECONDS:
                timed_out.append((t.id, t.type))
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("queued 排队超时扫描失败")
        return 0
    finally:
        db.close()

    for tid, ttype in timed_out:
        if _fail(tid, ERR_QUEUE_TIMEOUT,
                 f"任务排队超过 {QUEUE_TIMEOUT_SECONDS}s 未被 Worker 领取，判定排队超时（类型 {ttype}）"):
            log.error("QUEUE-TIMEOUT: 任务 %s（%s）排队超时 %ss，已标 failed(%s)",
                      tid, ttype, QUEUE_TIMEOUT_SECONDS, ERR_QUEUE_TIMEOUT)
    return len(timed_out)


def _scan():
    """看门狗单次扫描：running 按阶段阈值、queued 按排队阈值；线程自愈仅内存模式。"""
    now = time.time()
    # 1) running 态：_meta 只在任务开跑时写入，排队任务天然不进这里（D2）
    with _state:
        snap = [(tid, dict(m)) for tid, m in _meta.items()]
    for tid, m in snap:
        stage = m.get("stage")
        limit = stage_timeout(stage)
        if now - m["progress"] > limit:
            if _fail(tid, ERR_TASK_TIMEOUT,
                     f"任务阶段 {stage or 'default'} 超过 {limit}s 无进度，判定卡死并终止等待，可重试"):
                with _state:
                    _cancel.add(tid)
                    cur = _meta.get(tid)
                    if cur is not None:
                        cur["progress"] = time.time()  # 避免重复告警

    # 2) queued 态：独立排队阈值，与 running 看门狗解耦
    _scan_queue_timeouts(now)

    # 3) 线程自愈：redis 模式任务由独立 RQ Worker 执行，不在此拉本地线程（V2）
    if queue_mod.current_backend()[0] != "memory":
        return
    with _state:
        alive = _thread is not None and _thread.is_alive()
        v_alive = [t for t in _vthreads if t.is_alive()]
        stuck = [(tid, dict(m)) for tid, m in _meta.items()
                 if now - m["started"] > TASK_TIMEOUT_SECONDS * 2]
    if v_alive and len(v_alive) < len(_vthreads):
        log.warning("视频 worker 线程有退出：存活 %s/%s", len(v_alive), len(_vthreads))
    if not alive:
        log.error("worker 线程不存在或已退出，重新拉起")
        _restart("线程已死亡")
        return
    if stuck:
        for tid, _m in stuck:
            _fail(tid, ERR_TASK_TIMEOUT,
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
    # redis 模式：running/queued 由独立 RQ Worker 与 RQ 注册表负责恢复，
    # API 进程不做 recover，避免把 Worker 正在执行的任务误判为僵尸并重跑（V2）
    if queue_mod.current_backend()[0] == "redis":
        log.warning("RECOVER-SKIPPED: redis 模式下任务恢复交由 RQ Worker 处理，runner.recover 不抢跑")
        return {"failed": 0, "requeued": 0, "skipped": 0}
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
        dispatch(task_id, task_type, payload)
    if failed or requeued or skipped:
        log.warning("任务恢复完成：僵尸 failed=%s，重新入队=%s，跳过=%s", failed, requeued, skipped)
    return {"failed": failed, "requeued": requeued, "skipped": skipped}


def wake():
    """外部触发一次恢复扫描并确保 worker 存活（redis 模式只保看门狗，不本地执行）。"""
    backend, _ = queue_mod.current_backend()
    if backend == "redis":
        _ensure_watchdog()
        return
    try:
        recover()
    except Exception:  # noqa: BLE001
        log.exception("wake 恢复扫描失败")
    _ensure_worker()
    _ensure_watchdog()


def health() -> dict:
    """健康检查。原有字段语义保持不变，新增字段均为可选（API 契约只增不删）。"""
    backend, init_error = queue_mod.current_backend()
    with _state:
        items = list(_meta.items())
        th = _thread
    if backend == "redis":
        # 实时探测，避免启动后 Redis 挂掉却一直回报 alive=true（禁止静默失败）
        ok, reason = queue_mod.probe_redis()
        if not ok:
            log.error("REDIS-UNAVAILABLE: health 探测失败（%s）", reason)
        alive = ok
        queue_size = queue_mod.queue_size() if ok else 0
        worker_name = f"rq:{queue_mod.QUEUE_NAME}"
    else:
        alive = bool(th is not None and th.is_alive())
        queue_size = _q.qsize()
        worker_name = th.name if th is not None else None
    current, elapsed = None, 0.0
    if items:
        cur_id, m = max(items, key=lambda kv: kv[1]["started"])
        current = cur_id
        elapsed = round(max(0.0, time.time() - m["started"]), 1)
    out = {
        "alive": alive,
        "queue_size": queue_size,
        "current_task": current,
        "current_elapsed": elapsed,
        "timeout_seconds": TASK_TIMEOUT_SECONDS,
        "worker": worker_name,
        # 新增（向后兼容）
        "queue_backend": backend,
        "queue_timeout_seconds": QUEUE_TIMEOUT_SECONDS,
        "stage_timeouts": {s: stage_timeout(s) for s in _STAGE_NAMES},
        # 视频并发池状态（新增，向后兼容）
        "video_queue_size": _vq.qsize(),
        "video_workers": len([t for t in _vthreads if t.is_alive()]),
    }
    if init_error:
        out["queue_init_error"] = init_error
    return out


def start():
    global _started
    with _state:
        already = _started
        _started = True
    backend, init_error = queue_mod.current_backend()
    if backend == "redis":
        # V2：API 只 enqueue，不 recover（避免抢跑独立 Worker）、不启动本地消费线程。
        # 看门狗仍保留：扫 queued 排队超时（D2），不执行任务。
        if init_error:
            log.error("REDIS-UNAVAILABLE: API 启动于 redis 模式但 %s；后续入队将显式失败", init_error)
        else:
            log.info("API 启动于 redis 模式：仅入队（队列 %s）；Worker 请用 "
                     "python -m app.worker.queue_worker 启动", queue_mod.QUEUE_NAME)
        _ensure_watchdog()
        return
    if not already:
        try:
            recover()
        except Exception:  # noqa: BLE001
            log.exception("启动时任务恢复失败")
    _ensure_worker()
    _ensure_watchdog()
