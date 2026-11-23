# -*- coding: utf-8 -*-
"""队列后端抽象（V2 / S8）：memory（进程内）| redis（RQ 独立 Worker）| auto（探测回落）。

设计约定：
1. 本模块顶层不 import runner，避免循环依赖；RQ job 入口 run_rq_job 内部延迟导入。
2. redis 模式下 API 进程只负责 enqueue，绝不执行任务；执行统一交给 queue_worker.py 独立进程。
3. 任何降级 / 不可用 / 入队失败都打 WARNING/ERROR 并返回可读错误码，禁止静默假装成功。

新增环境变量（由集成方回填 config / .env.example）：
- QUEUE_BACKEND：auto|memory|redis，默认 memory（保证 dev 与 95/95 回归行为不变）。
- RQ_QUEUE_NAME：RQ 队列名，默认 gflc。
REDIS_URL 沿用 config.py 既有字段（读取同名环境变量），不引入新开关。
"""
import logging
import os
from dataclasses import dataclass

from app.core.config import settings

log = logging.getLogger("gflc.queue")

# 队列名：RQ Worker 与 API 必须一致
QUEUE_NAME = (os.getenv("RQ_QUEUE_NAME") or "gflc").strip() or "gflc"

# 可读错误码（API 侧任务会落 error_code，前端可见）
ERR_REDIS_UNAVAILABLE = "REDIS-UNAVAILABLE"
ERR_REDIS_VERSION = "REDIS-VERSION-UNSUPPORTED"
ERR_QUEUE_FALLBACK = "QUEUE-FALLBACK-MEMORY"
ERR_CONFIG_INVALID = "QUEUE-CONFIG-INVALID"
ERR_ENQUEUE_FAILED = "QUEUE-ENQUEUE-FAILED"

# 后端状态：首次 resolve_backend() 时确定，force=True 可重探（Worker 进程用）
_backend: str | None = None
_redis_ok: bool = False
_init_error: str | None = None


@dataclass
class EnqueueResult:
    """入队结果。ok=False 时 error_code/error_message 必有值，调用方必须显式失败。"""
    ok: bool
    backend: str
    job_id: str | None = None
    error_code: str | None = None
    error_message: str = ""


def _redis_url() -> str:
    # settings.REDIS_URL 已在 config.py 读取 REDIS_URL 环境变量；这里允许运行期覆盖（自测用）。
    return os.getenv("REDIS_URL") or settings.REDIS_URL


def get_connection():
    """建立 Redis 连接（延迟导入 redis-py：memory 模式零依赖）。"""
    import redis  # noqa: PLC0415

    return redis.Redis.from_url(
        _redis_url(),
        socket_connect_timeout=2,
        socket_timeout=2,
        health_check_interval=30,
        decode_responses=False,
        # 本机 Redis 版本较老（不支持 HELLO/RESP3），redis-py 8.x 默认 protocol=3 会握手失败；
        # 显式用 RESP2，rq 3.0 完全兼容。生产若用新 Redis 亦无副作用。
        protocol=2,
    )


def probe_redis() -> tuple[bool, str]:
    """探测 Redis 可用性与版本。rq 3.0 要求 Redis >= 4.0（多字段 HSET）。

    失败时返回 (False, 原因)，由调用方按模式决定告警级别；不静默降级。
    """
    try:
        conn = get_connection()
        conn.ping()
        try:
            ver = str(conn.info("server").get("redis_version", ""))
            major = int(ver.split(".")[0]) if ver else 0
            if major and major < 4:
                return False, (f"{ERR_REDIS_VERSION}: Redis {ver} 过低，"
                               "rq 3.0 要求 >= 4.0（多字段 HSET）")
        except Exception:  # noqa: BLE001
            # INFO 在部分托管 Redis 被禁用；PING 通即视为可用，跳过版本校验
            log.warning("REDIS-VERSION-CHECK-SKIPPED: INFO server 不可用，仅按 PING 判定")
        return True, ""
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def resolve_backend(force: bool = False) -> str:
    """解析队列后端。

    - memory：强制进程内队列，不探测 Redis（dev / 95/95 回归路径，行为与改前一致）。
    - redis ：强制 RQ；Redis 不可用时**不回落内存**，保留 redis 标识并在入队时显式失败。
    - auto  ：探测 Redis，可用走 RQ，不可用回落 memory 并打 WARNING（不静默）。
    """
    global _backend, _redis_ok, _init_error
    if _backend is not None and not force:
        return _backend

    mode = (os.getenv("QUEUE_BACKEND") or "memory").strip().lower()
    if mode not in ("auto", "memory", "redis"):
        log.error("%s: QUEUE_BACKEND=%r 非法（允许 auto|memory|redis），按 memory 处理",
                  ERR_CONFIG_INVALID, mode)
        mode = "memory"

    if mode == "memory":
        _backend, _redis_ok, _init_error = "memory", False, None
        log.info("队列后端=memory（进程内队列，行为与历史一致）")
        return _backend

    ok, reason = probe_redis()
    _redis_ok = ok

    if mode == "redis":
        if ok:
            _backend, _init_error = "redis", None
            log.info("队列后端=redis（RQ 队列=%s）；API 仅入队，请启动独立 Worker", QUEUE_NAME)
        else:
            # 强制 redis 模式不可用：不回落内存，失败在 enqueue 处显式暴露
            _backend = "redis"
            _init_error = f"{ERR_REDIS_UNAVAILABLE}: {reason}"
            log.error("REDIS-UNAVAILABLE: 指定 QUEUE_BACKEND=redis 但 Redis 不可用（%s）；"
                      "不回落内存队列，后续入队将显式失败", reason)
    else:  # auto
        if ok:
            _backend, _init_error = "redis", None
            log.info("QUEUE-AUTO: 探测到 Redis，启用 RQ 队列=%s", QUEUE_NAME)
        else:
            _backend, _init_error = "memory", None
            log.warning("%s: auto 模式探测 Redis 失败（%s），回落内存队列；"
                        "任务不会进入 Redis，请检查 REDIS_URL", ERR_QUEUE_FALLBACK, reason)
    return _backend


def current_backend() -> tuple[str, str | None]:
    """返回 (backend, init_error)。init_error 非空表示强制 redis 但初始化失败。"""
    return resolve_backend(), _init_error


def is_redis_available() -> bool:
    return _redis_ok


def get_queue():
    """构造 RQ Queue（每次新建连接，避免跨进程 fork 复用）。"""
    from rq import Queue  # noqa: PLC0415

    return Queue(QUEUE_NAME, connection=get_connection())


def enqueue(task_id: int, task_type: str, payload: dict, timeout: int | None = None) -> EnqueueResult:
    """仅入队，不执行。返回 EnqueueResult，失败时带可读错误码。"""
    backend = resolve_backend()
    if backend != "redis":
        return EnqueueResult(False, backend, error_code="QUEUE-WRONG-BACKEND",
                             error_message="memory 模式应由 runner._enqueue 处理，不应调用 queue.enqueue")
    if _init_error:
        log.error("QUEUE-ENQUEUE-FAILED: 任务 %s 入队前检测到 %s", task_id, _init_error)
        return EnqueueResult(False, backend, error_code=ERR_ENQUEUE_FAILED, error_message=_init_error)
    try:
        job = get_queue().enqueue(
            run_rq_job,
            task_id,
            task_type,
            payload or {},
            timeout=timeout or 1800,
            result_ttl=0,       # 结果落 DB，不在 Redis 堆积
            failure_ttl=86400,
            meta={"task_type": task_type, "task_id": task_id},
        )
        log.info("任务 %s 已入 RQ 队列 %s（job=%s，timeout=%ss）",
                 task_id, QUEUE_NAME, job.id, timeout or 1800)
        return EnqueueResult(True, backend, job_id=job.id)
    except Exception as e:  # noqa: BLE001
        msg = f"{type(e).__name__}: {e}"
        log.error("QUEUE-ENQUEUE-FAILED: 任务 %s 入队失败（%s）", task_id, msg, exc_info=True)
        return EnqueueResult(False, backend, error_code=ERR_ENQUEUE_FAILED, error_message=msg)


def create_worker():
    """构造 RQ Worker（延迟导入：仅 Worker 进程需要 rq）。"""
    from rq import Worker  # noqa: PLC0415

    return Worker([QUEUE_NAME], connection=get_connection())


def queue_size() -> int:
    """读取 RQ 队列长度；读取失败打 ERROR 而非静默返回 0。"""
    if resolve_backend() != "redis":
        return 0
    try:
        q = get_queue()
        return int(len(q))
    except Exception as e:  # noqa: BLE001
        log.error("REDIS-QUEUE-READ-FAILED: 读取队列 %s 长度失败（%s）", QUEUE_NAME, e)
        return 0


def run_rq_job(task_id: int, task_type: str, payload: dict) -> dict:
    """RQ job 入口（必须顶层可导入，供 Worker 反序列化）。

    延迟导入 runner 避免循环依赖；真正执行逻辑复用 runner.execute_task，
    与内存队列共用同一 handler 分派与状态机，确保两条路径语义一致。
    """
    from app.worker import runner  # noqa: PLC0415

    return runner.execute_task(task_id, task_type, payload)
