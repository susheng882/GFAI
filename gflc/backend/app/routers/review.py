# -*- coding: utf-8 -*-
"""复习排期：基于 py-fsrs（FSRS-6）。新卡立即可复习，评分后按 FSRS 排下一次。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fsrs import Card as FSRSCard
from fsrs import Rating, Scheduler
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Card
from app.routers.deps import get_current_user

router = APIRouter(prefix="/review", tags=["review"])
_scheduler = Scheduler()

_RATING = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}


class ReviewIn(BaseModel):
    rating: int  # 1 Again / 2 Hard / 3 Good / 4 Easy


def _out(c: Card) -> dict:
    return {"id": c.id, "question": c.question, "answer": c.answer, "tag": c.tag, "page": c.page,
            "reps": c.reps, "due_at": c.due_at.isoformat() if c.due_at else None}


@router.get("/due")
async def due(limit: int = 20, user=Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    rows = list(db.scalars(
        select(Card).where(Card.user_id == user.id,
                           or_(Card.reps == 0, Card.due_at.is_(None), Card.due_at <= now))
        .order_by(Card.due_at, Card.id).limit(limit)
    ))
    return {"ok": True, "data": {"count": len(rows), "cards": [_out(c) for c in rows]}}


@router.post("/{card_id}")
async def review(card_id: int, body: ReviewIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.scalar(select(Card).where(Card.id == card_id, Card.user_id == user.id))
    if not c:
        raise APIError(ErrCode.AUTH_403, "无权复习该卡片", 403)
    if body.rating not in _RATING:
        raise APIError(ErrCode.COMMON_400, "rating 必须为 1–4")
    fsrs_card = FSRSCard.from_dict(c.fsrs_state) if c.fsrs_state else FSRSCard()
    fsrs_card, _log = _scheduler.review_card(fsrs_card, _RATING[body.rating])
    c.fsrs_state = fsrs_card.to_dict()
    c.due_at = fsrs_card.due
    c.reps = (c.reps or 0) + 1
    if body.rating == 1:
        c.lapses = (c.lapses or 0) + 1
    db.commit()
    return {"ok": True, "data": _out(c)}
