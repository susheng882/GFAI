# -*- coding: utf-8 -*-
"""仪表盘：真实统计 / AI 生成（月周日粒度）/ 自由布局缩放 / 单卡编辑。"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Attempt, Card, CardDeck, Chunk, DashboardLayout, Document, Question
from app.routers.deps import get_current_user
from app.schemas.schemas import DashCardPatchIn, DashGenIn, DashOrderIn
from app.worker import runner

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _own_layout(db: Session, layout_id: int, user_id: int) -> DashboardLayout:
    row = db.scalar(select(DashboardLayout).where(DashboardLayout.id == layout_id,
                                                  DashboardLayout.user_id == user_id))
    if not row:
        raise APIError(ErrCode.AUTH_403, "无权访问该仪表盘", 403)
    return row


@router.get("/stats")
async def stats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    uid = user.id
    now = datetime.now(timezone.utc)
    docs = db.scalar(select(func.count()).select_from(Document).where(Document.user_id == uid)) or 0
    chunks = db.scalar(select(func.count()).select_from(Chunk).join(
        Document, Chunk.document_id == Document.id).where(Document.user_id == uid)) or 0
    cards = db.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid)) or 0
    due = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == uid, or_(Card.reps == 0, Card.due_at.is_(None), Card.due_at <= now))) or 0
    reviewed = db.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid, Card.reps > 0)) or 0
    questions = db.scalar(select(func.count()).select_from(Question).where(Question.user_id == uid)) or 0
    attempts = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == uid)) or 0
    correct = db.scalar(select(func.count()).select_from(Attempt).where(
        Attempt.user_id == uid, Attempt.correct == 1)) or 0

    # 最近 7 天作答量（真实数据，前端折线用）
    week = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        n = db.scalar(select(func.count()).select_from(Attempt).where(
            Attempt.user_id == uid, func.date(Attempt.created_at) == day.isoformat())) or 0
        week.append({"label": day.strftime("%m-%d"), "value": int(n)})

    decks = db.execute(
        select(CardDeck.name, func.count(Card.id))
        .join(Card, Card.deck_id == CardDeck.id)
        .where(CardDeck.user_id == uid, CardDeck.kind == "chapter")
        .group_by(CardDeck.name).order_by(func.count(Card.id).desc()).limit(6)
    ).all()

    return {"ok": True, "data": {
        "documents": docs, "chunks": chunks, "cards": cards, "due": due, "reviewed": reviewed,
        "questions": questions, "attempts": attempts,
        "accuracy": round(correct / attempts * 100, 1) if attempts else 0,
        "week": week,
        "chapters": [{"name": n, "cards": int(c)} for n, c in decks],
    }}


@router.post("/generate")
async def generate(body: DashGenIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """按主题 + 时间粒度生成仪表盘（会带上用户真实学习数据）。"""
    theme = (body.theme or "").strip()
    if not theme:
        raise APIError(ErrCode.COMMON_400, "请填写仪表盘主题")
    t = runner.create_task(db, user.id, "dashboard_generate")
    runner.submit(t.id, "dashboard_generate", {"theme": theme, "scope": body.scope})
    return {"ok": True, "data": {"task_id": t.id}}


@router.get("/latest")
async def latest(scope: str | None = None, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    stmt = select(DashboardLayout).where(DashboardLayout.user_id == user.id)
    if scope:
        stmt = stmt.where(DashboardLayout.scope == scope)
    row = db.scalar(stmt.order_by(DashboardLayout.is_default.desc(), DashboardLayout.id.desc()).limit(1))
    if not row:
        return {"ok": True, "data": None}
    return {"ok": True, "data": {
        "id": row.id, "theme": row.theme, "config": row.config, "order": row.order,
        "positions": row.positions or {}, "scope": row.scope or "week",
        "is_default": bool(row.is_default),
    }}


@router.get("/list")
async def list_layouts(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(DashboardLayout).where(DashboardLayout.user_id == user.id)
                           .order_by(DashboardLayout.is_default.desc(), DashboardLayout.id.desc()).limit(20)))
    return {"ok": True, "data": [{"id": r.id, "theme": r.theme, "scope": r.scope or "week",
                                  "is_default": bool(r.is_default)} for r in rows]}


@router.put("/{layout_id}/order")
async def save_order(layout_id: int, body: DashOrderIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    row.order = body.order
    if body.positions:
        row.positions = body.positions
    if body.scope in ("month", "week", "day"):
        row.scope = body.scope
    db.commit()
    return {"ok": True, "data": {"id": row.id, "order": row.order,
                                 "positions": row.positions, "scope": row.scope}}


@router.patch("/{layout_id}/card")
async def patch_card(layout_id: int, body: DashCardPatchIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """编辑单张卡片内容（标题/数值/清单/图表数据）。"""
    row = _own_layout(db, layout_id, user.id)
    cfg = dict(row.config or {})
    cards = [dict(c) for c in cfg.get("cards", [])]
    hit = None
    for c in cards:
        if c.get("id") == body.card_id:
            hit = c
            break
    if hit is None:
        raise APIError(ErrCode.COMMON_404, "卡片不存在", 404)
    for field in ("title", "value", "unit", "hint"):
        v = getattr(body, field)
        if v is not None:
            hit[field] = v
    if body.items is not None:
        hit["items"] = body.items
    if body.data is not None:
        hit["data"] = body.data
    cfg["cards"] = cards
    row.config = cfg
    db.commit()
    return {"ok": True, "data": {"card": hit}}


@router.post("/{layout_id}/default")
async def set_default(layout_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    db.query(DashboardLayout).filter(DashboardLayout.user_id == user.id).update(
        {"is_default": 0}, synchronize_session=False)
    row.is_default = 1
    db.commit()
    return {"ok": True, "data": {"id": row.id, "is_default": True}}


@router.delete("/{layout_id}")
async def delete_layout(layout_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    db.delete(row)
    db.commit()
    return {"ok": True, "data": {"deleted": True}}
