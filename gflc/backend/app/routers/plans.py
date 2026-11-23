# -*- coding: utf-8 -*-
"""学习计划：目标 → LLM 拆解逐日任务 → 勾选完成。"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Plan, PlanTask
from app.routers.deps import get_current_user
from app.schemas.schemas import PlanIn
from app.worker import runner

router = APIRouter(prefix="/plans", tags=["plans"])


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite 读回的时间可能无时区，统一补 UTC 以便跨来源排序。"""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def plan_task_due(plan: Plan, task: PlanTask) -> datetime | None:
    """D10：任务到期时间。优先用显式 due；历史数据按 plan 创建日 + day_index 派生。"""
    if task.due is not None:
        return _aware(task.due)
    if plan.created_at is None:
        return None
    return _aware(plan.created_at) + timedelta(days=max(1, task.day_index or 1) - 1)


@router.post("")
async def create_plan(body: PlanIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    days = max(1, min(body.days, 60))
    t = runner.create_task(db, user.id, "plan_generate")
    runner.submit(t.id, "plan_generate", {"goal": body.goal, "days": days})
    return {"ok": True, "data": {"task_id": t.id}}


@router.get("")
async def list_plans(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Plan).where(Plan.user_id == user.id).order_by(Plan.id.desc()).limit(30)))
    return {"ok": True, "data": [{"id": p.id, "goal": p.goal, "days": p.days} for p in rows]}


@router.get("/{plan_id}")
async def get_plan(plan_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.scalar(select(Plan).where(Plan.id == plan_id, Plan.user_id == user.id))
    if not p:
        raise APIError(ErrCode.AUTH_403, "无权访问该计划", 403)
    tasks = list(db.scalars(select(PlanTask).where(PlanTask.plan_id == p.id).order_by(PlanTask.day_index, PlanTask.id)))
    by_day: dict[int, list] = {}
    for t in tasks:
        due = plan_task_due(p, t)
        # only-add：原有字段不变，新增 due 供「今日待办」与前端消费
        by_day.setdefault(t.day_index, []).append({
            "id": t.id, "title": t.title, "detail": t.detail, "done": bool(t.done),
            "due": due.isoformat() if due else None,
        })
    return {"ok": True, "data": {"id": p.id, "goal": p.goal, "days": p.days,
                                 "tasks": [{"day": d, "items": v} for d, v in sorted(by_day.items())]}}


@router.post("/tasks/{task_id}/toggle")
async def toggle(task_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    t = db.get(PlanTask, task_id)
    if not t:
        raise APIError(ErrCode.COMMON_400, "任务不存在")
    p = db.get(Plan, t.plan_id)
    if not p or p.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权操作", 403)
    t.done = 0 if t.done else 1
    db.commit()
    return {"ok": True, "data": {"id": t.id, "done": bool(t.done)}}
