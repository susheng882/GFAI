# -*- coding: utf-8 -*-
"""后台任务共享工具（T-3 拆分）：checkpoint 读写与时间格式化。

从原 app/worker/handlers.py 原样迁出，函数体逐字未改。
logger 名保持 "app.worker.handlers"，拆分后日志来源不变。
"""
import logging

_log = logging.getLogger("app.worker.handlers")


# ---------------------------------------------------------------------------
# A5：阶段化 checkpoint / 真断点续传（只写 task.checkpoint，不改状态机枚举）
# ---------------------------------------------------------------------------


def _cp_get(task) -> dict:
    cp = getattr(task, "checkpoint", None)
    return dict(cp) if isinstance(cp, dict) else {}


def _cp_save(db, task, **stages):
    """把已完成阶段写入 task.checkpoint；写失败 WARNING，不影响主流程。"""
    try:
        cp = _cp_get(task)
        data = dict(cp.get("video_stages") or {})
        data.update(stages)
        cp["video_stages"] = data
        task.checkpoint = cp
        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        _log.warning("视频任务 checkpoint 写入失败（task=%s）：%s", getattr(task, "id", "?"), e)


def _ts_mmss(sec: float) -> str:
    s = max(0, int(round(float(sec or 0))))
    return f"{s // 60:02d}:{s % 60:02d}"
