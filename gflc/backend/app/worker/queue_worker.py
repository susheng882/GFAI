# -*- coding: utf-8 -*-
"""RQ Worker 独立进程入口（V2 / S8）。

启动：
    cd gflc/backend
    QUEUE_BACKEND=redis python -m app.worker.queue_worker

一次性冒烟（处理完当前队列即退出，适合 compose / CI）：
    QUEUE_BACKEND=redis RQ_BURST=1 python -m app.worker.queue_worker

约束：
- 本进程只消费任务，不提供 HTTP 服务；API 进程仅 enqueue（见 queue.py）。
- 强制 redis 模式；若 QUEUE_BACKEND=memory/auto 或 Redis 不可用，打 ERROR 并以非零码退出，
  绝不静默降级成"假 Worker"。
- 任务执行复用 runner.execute_task → runner._run_task 与 handlers.register_all，
  与内存队列共用同一套 handler，避免两套执行语义。

新增环境变量：RQ_BURST（"1" 表示 burst 模式，处理完当前队列退出），默认 "0"（常驻）。
"""
import logging
import os
import sys

from app.worker import queue as queue_mod
from app.worker import runner
from app.worker.handlers import register_all

log = logging.getLogger("gflc.queue_worker")


def _setup_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> int:
    _setup_logging()

    # 1) 注册全部 handler（与 API lifespan 中的 register_all 完全一致）
    register_all()

    # 2) 强制 redis 后端：Worker 不允许以 memory 模式空跑
    mode = (os.getenv("QUEUE_BACKEND") or "memory").strip().lower()
    backend = queue_mod.resolve_backend(force=True)
    if mode != "redis" or backend != "redis":
        log.error("QUEUE-WORKER-NO-REDIS: Worker 需要 QUEUE_BACKEND=redis 且 Redis 可用"
                  "（当前 mode=%s, backend=%s）；拒绝以 memory 模式空跑", mode, backend)
        return 2
    if not queue_mod.is_redis_available():
        log.error("REDIS-UNAVAILABLE: Worker 无法连接 Redis（%s），退出", queue_mod._redis_url())
        return 2

    # 3) 只启动任务级看门狗（running 按阶段阈值 / queued 按排队阈值），不启动本地消费线程
    runner.start_watchdog_only()

    # 4) 构造 RQ Worker 并开始消费；与 API 共用 QUEUE_NAME
    try:
        worker = queue_mod.create_worker()
    except Exception as e:  # noqa: BLE001
        log.error("QUEUE-WORKER-INIT-FAILED: 创建 RQ Worker 失败（%s: %s）",
                  type(e).__name__, e, exc_info=True)
        return 3

    burst = os.getenv("RQ_BURST", "0").strip() == "1"
    log.info("RQ Worker 启动：queue=%s, redis=%s, burst=%s, pid=%s",
             queue_mod.QUEUE_NAME, queue_mod._redis_url(), burst, os.getpid())
    try:
        worker.work(burst=burst)
    except KeyboardInterrupt:
        log.info("RQ Worker 收到中断信号，正常退出")
    except Exception as e:  # noqa: BLE001
        log.error("QUEUE-WORKER-CRASH: Worker 异常退出（%s: %s）", type(e).__name__, e, exc_info=True)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
