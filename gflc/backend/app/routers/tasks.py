# -*- coding: utf-8 -*-
"""后台任务查询：列表 / 详情（前端轮询进度、任务管理页）+ 重试 / 清理 / 健康检查。"""
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Task
from app.routers.deps import get_current_user
from app.services.storage import get_storage
from app.worker import runner

router = APIRouter(prefix="/tasks", tags=["tasks"])

# 可重放：参数能从数据库（document_id / checkpoint）还原
REPLAYABLE = {"pdf_parse", "card_generate", "dashboard_generate",
              "plan_generate", "question_import", "video_url"}
# 不可重放：上传的临时文件已被删除
NEED_REUPLOAD = {"video_upload"}


def _elapsed(t: Task) -> float | None:
    if t.status != "running" or t.created_at is None:
        return None
    created = t.created_at if t.created_at.tzinfo else t.created_at.replace(tzinfo=timezone.utc)
    try:
        return round(max(0.0, (datetime.now(timezone.utc) - created).total_seconds()), 1)
    except TypeError:  # 极端情况下的 naive/aware 混用
        return None


def _build_payload(t: Task, materialize: bool = True) -> dict:
    """从 checkpoint / document_id 重建 payload；不可还原时抛 400（不抛 500）。"""
    cp = t.checkpoint if isinstance(t.checkpoint, dict) else {}
    p = cp.get("payload") if isinstance(cp.get("payload"), dict) else {}

    def pick(key, default=None):
        v = p.get(key)
        if v is None or v == "":
            v = cp.get(key)
        return default if v is None or v == "" else v

    if t.type in ("pdf_parse", "card_generate"):
        doc_id = t.document_id or pick("document_id")
        if not doc_id:
            raise APIError(ErrCode.COMMON_400, "原任务的文档信息已丢失，无法重试，请重新发起")
        return {"document_id": int(doc_id)}

    if t.type == "dashboard_generate":
        return {"theme": pick("theme", "学习计划"), "scope": pick("scope", "week")}

    if t.type == "plan_generate":
        goal = pick("goal")
        if not goal:
            raise APIError(ErrCode.COMMON_400, "原任务的学习目标已丢失，无法重试，请重新生成计划")
        try:
            days = int(pick("days", 7))
        except (TypeError, ValueError):
            days = 7
        return {"goal": goal, "days": max(1, min(days, 60))}

    if t.type == "video_url":
        url = pick("url")
        if not url:
            raise APIError(ErrCode.COMMON_400, "原任务的视频链接已丢失，无法重试，请重新提交链接")
        tpls = p.get("templates") or cp.get("templates") or ["summary"]
        if isinstance(tpls, str):
            tpls = [x.strip().lower() for x in tpls.replace("，", ",").split(",") if x.strip()]
        return {"url": url, "title": pick("title", "链接视频"), "templates": list(tpls) or ["summary"]}

    if t.type == "question_import":
        key = pick("storage_key")
        filename = pick("filename", "题库")
        if not key:
            raise APIError(ErrCode.COMMON_400, "原始题库文件已清理，无法重试，请重新上传文件")
        if not materialize:
            return {"storage_key": key, "filename": filename}
        ext = os.path.splitext(str(filename))[1].lower() or ".pdf"
        try:
            raw = get_storage().read(key)
        except Exception as e:  # noqa: BLE001
            raise APIError(ErrCode.COMMON_400, "原始题库文件已清理，无法重试，请重新上传文件") from e
        tmp = os.path.join(tempfile.gettempdir(), f"gflc_qb_{uuid.uuid4().hex}{ext}")
        with open(tmp, "wb") as f:
            f.write(raw)
        return {"path": tmp, "filename": filename, "storage_key": key,
                "size": len(raw), "mime": p.get("mime") or ""}

    if t.type in NEED_REUPLOAD:
        raise APIError(ErrCode.COMMON_400, "该任务使用了上传的临时文件（已清理），无法重试，请重新上传文件")
    raise APIError(ErrCode.COMMON_400, f"任务类型 {t.type} 不支持重试")


def _can_retry(t: Task) -> bool:
    if t.status != "failed" or t.type not in REPLAYABLE:
        return False
    try:
        _build_payload(t, materialize=False)
        return True
    except APIError:
        return False
    except Exception:  # noqa: BLE001
        return False


def _can_abort(t: Task) -> bool:
    return t.status in ("pending", "running")


def _out(t: Task) -> dict:
    return {
        "id": t.id, "type": t.type, "status": t.status, "progress": t.progress,
        "error_code": t.error_code, "error_message": t.error_message,
        "document_id": t.document_id, "result": t.result,
        "elapsed": _elapsed(t), "can_retry": _can_retry(t), "can_abort": _can_abort(t),
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


@router.get("")
async def list_tasks(limit: int = 20, user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Task).where(Task.user_id == user.id)
                           .order_by(Task.id.desc()).limit(max(1, min(limit, 100)))))
    return {"ok": True, "data": [_out(t) for t in rows]}


@router.get("/health")
async def worker_health(user=Depends(get_current_user)):
    return {"ok": True, "data": runner.health()}


@router.post("/cleanup")
async def cleanup_tasks(days: int = 3, user=Depends(get_current_user), db: Session = Depends(get_db)):
    days = max(1, min(days, 30))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    n = db.execute(delete(Task).where(Task.user_id == user.id, Task.status == "failed",
                                      Task.created_at < cutoff)).rowcount or 0
    db.commit()
    return {"ok": True, "data": {"deleted": int(n), "days": days}}


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not t:
        raise APIError(ErrCode.COMMON_404, "任务不存在", 404)
    if t.status != "failed":
        raise APIError(ErrCode.COMMON_400, f"只有失败的任务可以重试（当前状态：{t.status}）")
    if t.type in NEED_REUPLOAD:
        raise APIError(ErrCode.COMMON_400, "该任务使用了上传的临时文件（已清理），请重新上传文件")
    payload = _build_payload(t)
    nt = runner.create_task(db, user.id, t.type, t.document_id)
    runner.submit(nt.id, t.type, payload)
    runner.wake()
    return {"ok": True, "data": {"task_id": nt.id, "type": t.type, "status": "pending"}}


@router.post("/{task_id}/abort")
async def abort_task(task_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.scalar(select(Task).where(Task.id == task_id))
    if not t:
        raise APIError(ErrCode.COMMON_404, "任务不存在", 404)
    if t.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权操作该任务", 403)
    if t.status == "ready":
        raise APIError(ErrCode.COMMON_400, "任务已完成，无需放弃")
    if t.status == "failed":
        raise APIError(ErrCode.COMMON_400, "任务已失败，无需放弃")
    if t.status not in ("pending", "running"):
        raise APIError(ErrCode.COMMON_400, f"当前状态（{t.status}）不支持放弃任务")
    if not runner.abort(t.id):
        raise APIError(ErrCode.COMMON_400, "任务状态已变化，放弃失败，请刷新后重试")
    return {"ok": True, "data": {"aborted": True, "task_id": t.id}}


@router.get("/{task_id}")
async def get_task(task_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if not t:
        raise APIError(ErrCode.AUTH_403, "无权访问该任务", 403)
    return {"ok": True, "data": _out(t)}
