# -*- coding: utf-8 -*-
"""通知（阶段 C）：实时计算，不落库。

三类通知：
- due_cards：到期卡片数（reps>0 且 due_at<=now）
- parse_done：最近 24h 完成的解析任务
- streak：连续打卡达标（≥7 天）

前端顶栏铃铛抽屉消费。已读状态存 localStorage（前端），本接口只供数据。
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Attempt, Card, ReviewLog, Task, User
from app.routers.deps import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _streak(db: Session, uid: int) -> int:
    """连续打卡天数（复用 achievements 口径）。"""
    r_days = {d for (d,) in db.execute(
        select(func.date(ReviewLog.created_at)).where(ReviewLog.user_id == uid)).all()}
    a_days = {d for (d,) in db.execute(
        select(func.date(Attempt.created_at)).where(Attempt.user_id == uid)).all()}
    day_set = r_days | a_days
    d = datetime.now(timezone.utc).date()
    streak = 0
    while d.isoformat() in day_set:
        streak += 1
        d -= timedelta(days=1)
    return streak


@router.get("")
async def list_notifications(user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    uid = user.id
    now = datetime.now(timezone.utc)
    items = []

    # 1) 到期卡片
    due = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == uid, Card.reps > 0,
        or_(Card.due_at.is_(None), Card.due_at <= now))) or 0
    if due > 0:
        items.append({"type": "due_cards", "title": f"{due} 张卡片到期",
                      "body": "现在开始复习，保持记忆曲线", "at": now.isoformat()})

    # 2) 解析完成（最近 24h）
    done = list(db.scalars(select(Task).where(
        Task.user_id == uid, Task.status == "ready",
        Task.updated_at >= now - timedelta(hours=24))
        .order_by(Task.updated_at.desc()).limit(5)))
    for t in done:
        items.append({"type": "parse_done", "title": f"解析完成 · {t.type}",
                      "body": f"任务 #{t.id} 已完成",
                      "at": t.updated_at.isoformat() if t.updated_at else now.isoformat()})

    # 3) 连续达标
    streak = _streak(db, uid)
    if streak >= 7 and streak % 7 == 0:
        items.append({"type": "streak", "title": f"连续打卡 {streak} 天",
                      "body": "坚持就是胜利，继续加油", "at": now.isoformat()})

    return {"ok": True, "data": items}


@router.post("/{notify_id}/read")
async def mark_read(notify_id: str, user: User = Depends(get_current_user)):
    """已读状态由前端 localStorage 管理，此接口为契约占位（幂等）。"""
    return {"ok": True, "data": {"read": notify_id}}
