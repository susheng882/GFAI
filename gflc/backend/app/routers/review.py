# -*- coding: utf-8 -*-
"""复习排期：基于 py-fsrs（FSRS-6）。新卡立即可复习，评分后按 FSRS 排下一次。"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fsrs import Card as FSRSCard
from fsrs import Rating, Scheduler
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Card, Note, ReviewLog
from app.routers.deps import get_current_user
from app.services.mastery import (
    card_mastery_after_rating,
    humanize_seconds,
    preview_card_schedule,
)

router = APIRouter(prefix="/review", tags=["review"])
_scheduler = Scheduler()

_RATING = {1: Rating.Again, 2: Rating.Hard, 3: Rating.Good, 4: Rating.Easy}
# 「标记掌握」后的排期间隔：足够远，不再出现在到期队列（用户可在卡片浏览器重置）
MASTERED_DAYS = 3650


class ReviewIn(BaseModel):
    rating: int  # 0 标记掌握（永久） / 1 Again / 2 Hard / 3 Good / 4 Easy


class PreviewIn(BaseModel):
    card_id: int


class DeferIn(BaseModel):
    """B10：延后复习入参。days 默认 1 天，允许 1–365 天。"""
    days: int = 1


def _out(c: Card, note_title: str | None = None) -> dict:
    return {"id": c.id, "question": c.question, "answer": c.answer, "tag": c.tag, "page": c.page,
            "reps": c.reps, "due_at": c.due_at.isoformat() if c.due_at else None,
            # 掌握度真值：前端据此判断是否显示「取消掌握」入口（只增字段，不影响旧解析）
            "mastery": round(float(c.mastery or 0.0), 4),
            # 同源卡来源信息：source_note_id 为卡片自带列，note_title 由调用方一次性批量补齐
            "source_note_id": c.source_note_id,
            "note_title": note_title}


@router.get("/due")
async def due(limit: int = 20, new_limit: int | None = None,
              user=Depends(get_current_user), db: Session = Depends(get_db)):
    """待复习队列：到期卡优先占名额，新卡按「复习压力」自动压缩。

    分区口径（两段 SQL 分别取，不捞全表）：
    - 到期卡：reps > 0 且（due_at 为空或已到期），最多 limit 张
    - 新卡：reps == 0，最多 min(new_limit 或自动配额, limit - 到期数) 张
    自动配额：到期 ≥ limit×0.8 → 新卡压到 1；到期 ≤ limit×0.5 → 新卡填满剩余；
    中间区间只给一半。返回结构只增不改（多一个 quota）。
    """
    limit = max(1, min(limit, 100))
    now = datetime.now(timezone.utc)
    due_cond = (Card.user_id == user.id, Card.reps > 0,
                or_(Card.due_at.is_(None), Card.due_at <= now))
    new_cond = (Card.user_id == user.id, Card.reps == 0)
    # 真实总数（不受 limit 影响）：前端队列条要显示「今天还有多少张」，不能被 limit 封顶
    total_due = int(db.scalar(select(func.count(Card.id)).where(*due_cond)) or 0)
    total_new = int(db.scalar(select(func.count(Card.id)).where(*new_cond)) or 0)

    rows = list(db.scalars(
        select(Card).where(*due_cond).order_by(Card.due_at, Card.id).limit(limit)
    ))
    due_count = len(rows)
    room = max(0, limit - due_count)

    if new_limit is None:
        if due_count * 5 >= limit * 4:        # 到期 ≥ 80%
            cap, rule = min(1, room), "heavy"
        elif due_count * 2 <= limit:          # 到期 ≤ 50%
            cap, rule = room, "light"
        else:                                  # 50%–80%
            cap, rule = room // 2, "balanced"
    else:
        cap, rule = max(0, min(new_limit, room)), "manual"

    if cap > 0:
        rows.extend(db.scalars(
            select(Card).where(Card.user_id == user.id, Card.reps == 0)
            .order_by(Card.due_at, Card.id).limit(cap)
        ))
    new_count = len(rows) - due_count

    # 来源笔记标题：只有存在 source_note_id 的卡片才查，且一次 in_ 批量取，避免逐卡 N+1
    note_ids = {c.source_note_id for c in rows if c.source_note_id}
    titles: dict[int, str] = {}
    if note_ids:
        titles = dict(db.execute(
            select(Note.id, Note.title).where(Note.id.in_(note_ids),
                                              or_(Note.user_id == user.id, Note.user_id.is_(None)))
        ).all())
    return {"ok": True, "data": {
        "count": len(rows),
        "cards": [_out(c, titles.get(c.source_note_id)) for c in rows],
        # 只增字段：旧调用方只读 cards/count，不受影响。
        # total_* 是不受 limit 影响的真实总数，供队列条显示「今天还有多少」，避免被 limit 封顶。
        "quota": {"due_count": due_count, "new_count": new_count,
                  "new_limit": cap, "rule": rule,
                  "total_due": total_due, "total_new": total_new},
    }}


@router.post("/preview")
async def preview(body: PreviewIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """B4：预览四档评分各自的下次复习间隔。只读，不改掌握度/FSRS 状态、不写库。"""
    c = db.scalar(select(Card).where(Card.id == body.card_id, Card.user_id == user.id))
    if not c:
        raise APIError(ErrCode.AUTH_403, "无权预览该卡片", 403)
    now = datetime.now(timezone.utc)
    intervals = []
    for rating in (1, 2, 3, 4):
        pv = preview_card_schedule(c.mastery, rating, now=now)
        # FSRS 旁列：与 POST /review/{id} 的实际排期同源，纯计算不落库，失败仅留空
        fsrs_due_at, fsrs_days, fsrs_hours, fsrs_secs = None, None, None, None
        try:
            fsrs_card = FSRSCard.from_dict(c.fsrs_state) if c.fsrs_state else FSRSCard()
            new_card, _log = _scheduler.review_card(fsrs_card, _RATING[rating])
            if new_card.due is not None:
                due = new_card.due
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                secs = max(0.0, (due - now).total_seconds())
                fsrs_secs = secs
                fsrs_hours = round(secs / 3600.0, 3)
                fsrs_days = round(secs / 86400.0, 4)
                fsrs_due_at = due.isoformat()
        except Exception:  # noqa: BLE001  旁列不影响四档主结果
            pass
        # 文案优先用 FSRS 分钟级间隔（与真实写库一致）；FSRS 不可用时回落 mastery 天级
        label = humanize_seconds(fsrs_secs) if fsrs_secs is not None else pv["label"]
        intervals.append({
            "rating": rating,
            "label": label,
            "days": pv["days"],
            "due_at": pv["due_at"].isoformat(),
            "mastery_after": round(pv["mastery_after"], 4),
            "fsrs_due_at": fsrs_due_at,
            "fsrs_days": fsrs_days,
            "fsrs_hours": fsrs_hours,
        })
    return {"ok": True, "data": {
        "card_id": c.id,
        "count": len(intervals),
        "intervals": intervals,
        "now": now.isoformat(),
        "source": "mastery.preview_card_schedule",
    }}


def _note_title(db: Session, c: Card, user_id: int) -> str | None:
    """单卡来源笔记标题（评分接口回包用；无来源笔记返回 None）。"""
    if not c.source_note_id:
        return None
    return db.scalar(select(Note.title).where(Note.id == c.source_note_id,
                                              or_(Note.user_id == user_id, Note.user_id.is_(None))))


@router.post("/{card_id}/defer")
async def defer(card_id: int, body: DeferIn | None = None,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    """B10：延后复习。只把 due_at 推到 now + days 天，不改 mastery / reps / fsrs_state。"""
    days = 1 if body is None else body.days
    if days < 1 or days > 365:
        raise APIError(ErrCode.COMMON_400, "延后天数必须为 1–365 之间的整数")
    c = db.scalar(select(Card).where(Card.id == card_id, Card.user_id == user.id))
    if not c:
        raise APIError(ErrCode.AUTH_403, "无权操作该卡片", 403)
    c.due_at = datetime.now(timezone.utc) + timedelta(days=days)
    # B14：延后也留痕（rating=-1），热力图统计时排除，不影响复习量
    db.add(ReviewLog(user_id=user.id, card_id=c.id, rating=-1))
    db.commit()
    return {"ok": True, "data": {"card_id": c.id, "due_at": c.due_at.isoformat(),
                                 "deferred_days": days}}


@router.post("/{card_id}")
async def review(card_id: int, body: ReviewIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.scalar(select(Card).where(Card.id == card_id, Card.user_id == user.id))
    if not c:
        raise APIError(ErrCode.AUTH_403, "无权复习该卡片", 403)
    # rating=0 为「标记掌握」：不参与 FSRS 排期，直接置 mastery=1 且 due 推到远期（用户显式出口）
    if body.rating == 0:
        c.mastery = 1.0
        c.due_at = datetime.now(timezone.utc) + timedelta(days=MASTERED_DAYS)
        c.reps = (c.reps or 0) + 1
        # B14：标记掌握同样记一条（rating=0），计入当日复习量
        db.add(ReviewLog(user_id=user.id, card_id=c.id, rating=0))
        db.commit()
        return {"ok": True, "data": {**_out(c, _note_title(db, c, user.id)), "mastered": True}}
    if body.rating not in _RATING:
        raise APIError(ErrCode.COMMON_400, "rating 必须为 0（标记掌握）或 1–4")
    fsrs_card = FSRSCard.from_dict(c.fsrs_state) if c.fsrs_state else FSRSCard()
    fsrs_card, _log = _scheduler.review_card(fsrs_card, _RATING[body.rating])
    c.fsrs_state = fsrs_card.to_dict()
    c.due_at = fsrs_card.due
    c.reps = (c.reps or 0) + 1
    if body.rating == 1:
        c.lapses = (c.lapses or 0) + 1
    # 同步掌握度，避免 due_at 与 mastery 两套口径长期分叉（mastery<0.35 会被判为到期）
    c.mastery = card_mastery_after_rating(c.mastery, body.rating)
    db.add(ReviewLog(user_id=user.id, card_id=c.id, rating=body.rating))
    db.commit()
    return {"ok": True, "data": _out(c, _note_title(db, c, user.id))}
