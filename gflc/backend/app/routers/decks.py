# -*- coding: utf-8 -*-
"""卡包 / 卡片 CRUD：一份文档 = 一个 root 大卡包，PDF 大纲 = 章节子卡包。"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Card, CardDeck, Document
from app.routers.deps import get_current_user
from app.schemas.schemas import CardIn, CardPatchIn, DeckIn, DeckPatchIn

router = APIRouter(tags=["decks"])

_MAX_LIMIT = 500


def _deck_or_403(db: Session, deck_id: int, user_id: int) -> CardDeck:
    d = db.scalar(select(CardDeck).where(CardDeck.id == deck_id, CardDeck.user_id == user_id))
    if not d:
        raise APIError(ErrCode.AUTH_403, "无权访问该卡包", 403)
    return d


def _card_or_403(db: Session, card_id: int, user_id: int) -> Card:
    c = db.scalar(select(Card).where(Card.id == card_id, Card.user_id == user_id))
    if not c:
        raise APIError(ErrCode.AUTH_403, "无权访问该卡片", 403)
    return c


def _child_ids(db: Session, deck_id: int, user_id: int) -> list[int]:
    return list(db.scalars(select(CardDeck.id)
                           .where(CardDeck.user_id == user_id, CardDeck.parent_id == deck_id)))


def _scope_ids(db: Session, deck_id: int, user_id: int) -> list[int]:
    """卡包自身 + 其章节子包（root 的统计/取卡都覆盖子包）。"""
    return [deck_id] + _child_ids(db, deck_id, user_id)


def _deck_base(d: CardDeck) -> dict:
    return {"id": d.id, "document_id": d.document_id, "parent_id": d.parent_id,
            "name": d.name, "kind": d.kind or "root", "sort": d.sort or 0}


def _card_out(c: Card) -> dict:
    return {"id": c.id, "deck_id": c.deck_id, "document_id": c.document_id,
            "question": c.question, "answer": c.answer, "tag": c.tag or "",
            "difficulty": c.difficulty or "mid", "page": c.page or 0,
            "due_at": c.due_at.isoformat() if c.due_at else None,
            "reps": c.reps or 0, "lapses": c.lapses or 0}


def _stats(db: Session, user_id: int, deck_ids: list[int], now: datetime) -> dict[int, tuple[int, int, int]]:
    """一次性 group by 出每个卡的 total / due / done，避免循环计数。"""
    out: dict[int, tuple[int, int, int]] = {i: (0, 0, 0) for i in deck_ids}
    if not deck_ids:
        return out
    due_cond = or_(Card.due_at.is_(None), Card.due_at <= now)
    rows = db.execute(
        select(Card.deck_id, func.count(Card.id),
               func.sum(case((due_cond, 1), else_=0)),
               func.sum(case((Card.reps > 0, 1), else_=0)))
        .where(Card.user_id == user_id, Card.deck_id.in_(deck_ids))
        .group_by(Card.deck_id)
    ).all()
    for deck_id, total, due, done in rows:
        out[deck_id] = (int(total or 0), int(due or 0), int(done or 0))
    return out


# ---------- 卡包 ----------
@router.get("/decks")
async def list_decks(user=Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    decks = list(db.scalars(select(CardDeck).where(CardDeck.user_id == user.id)
                            .order_by(CardDeck.sort, CardDeck.id)))
    stats = _stats(db, user.id, [d.id for d in decks], now)
    ids = {d.id for d in decks}

    children: dict[int, list[CardDeck]] = {}
    tops: list[CardDeck] = []
    for d in decks:
        if not d.parent_id or d.parent_id not in ids:
            tops.append(d)
        else:
            children.setdefault(d.parent_id, []).append(d)

    data = []
    for d in tops:
        t, due, done = stats.get(d.id, (0, 0, 0))
        kids = []
        for k in children.get(d.id, []):
            kt, kdue, kdone = stats.get(k.id, (0, 0, 0))
            t += kt
            due += kdue
            done += kdone
            kids.append({**_deck_base(k), "total": kt, "due": kdue, "done": kdone, "children": []})
        data.append({**_deck_base(d), "total": t, "due": due, "done": done, "children": kids})
    return {"ok": True, "data": data}


@router.post("/decks")
async def create_deck(body: DeckIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    document_id = body.document_id
    parent = None
    if body.parent_id is not None:
        parent = _deck_or_403(db, body.parent_id, user.id)
        if document_id is None:
            document_id = parent.document_id
    if document_id is not None:
        doc = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user.id))
        if not doc:
            raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)

    deck = CardDeck(user_id=user.id, document_id=document_id, parent_id=body.parent_id,
                    name=body.name.strip(), kind="chapter" if parent else "root", sort=0)
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return {"ok": True, "data": {**_deck_base(deck), "total": 0, "due": 0, "done": 0}}


@router.patch("/decks/{deck_id}")
async def rename_deck(deck_id: int, body: DeckPatchIn, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    deck = _deck_or_403(db, deck_id, user.id)
    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise APIError(ErrCode.COMMON_400, "卡包名不能为空")
        deck.name = name
        db.commit()
        db.refresh(deck)
    return {"ok": True, "data": _deck_base(deck)}


@router.delete("/decks/{deck_id}")
async def delete_deck(deck_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    deck = _deck_or_403(db, deck_id, user.id)
    ids = _scope_ids(db, deck_id, user.id)
    # 卡片只解绑，不删学习数据
    kept = db.execute(update(Card)
                      .where(Card.user_id == user.id, Card.deck_id.in_(ids))
                      .values(deck_id=None)).rowcount or 0
    # 先删子包再删父包
    deleted = 0
    for did in sorted(ids, reverse=True):
        deleted += db.execute(delete(CardDeck).where(CardDeck.id == did,
                                                      CardDeck.user_id == user.id)).rowcount or 0
    db.commit()
    return {"ok": True, "data": {"deleted": deleted, "cards_kept": kept}}


@router.get("/decks/{deck_id}/cards")
async def deck_cards(deck_id: int, limit: int = 200, offset: int = 0,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    deck = _deck_or_403(db, deck_id, user.id)
    ids = _scope_ids(db, deck.id, user.id)
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    rows = list(db.scalars(
        select(Card).where(Card.user_id == user.id, Card.deck_id.in_(ids))
        .order_by(Card.due_at, Card.id).limit(limit).offset(offset)
    ))
    return {"ok": True, "data": [_card_out(c) for c in rows]}


# ---------- 卡片 ----------
@router.get("/cards")
async def list_cards(q: str = "", deck_id: int | None = None, limit: int = 200,
                     offset: int = 0, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    stmt = select(Card).where(Card.user_id == user.id)
    if deck_id is not None:
        deck = _deck_or_403(db, deck_id, user.id)
        stmt = stmt.where(Card.deck_id.in_(_scope_ids(db, deck.id, user.id)))
    kw = q.strip()
    if kw:
        like = f"%{kw}%"
        stmt = stmt.where(or_(Card.question.ilike(like), Card.answer.ilike(like)))
    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    rows = list(db.scalars(stmt.order_by(Card.due_at, Card.id).limit(limit).offset(offset)))
    return {"ok": True, "data": [_card_out(c) for c in rows]}


@router.post("/cards")
async def create_card(body: CardIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if body.deck_id is None:
        raise APIError(ErrCode.COMMON_400, "请先选择卡包")
    deck = _deck_or_403(db, body.deck_id, user.id)
    if deck.document_id is None:
        raise APIError(ErrCode.COMMON_400, "该卡包未关联文档，无法新建卡片")
    card = Card(user_id=user.id, document_id=deck.document_id, deck_id=deck.id,
                question=body.question, answer=body.answer, tag=body.tag or "",
                difficulty=body.difficulty or "mid", page=body.page or 0,
                due_at=datetime.now(timezone.utc), reps=0, lapses=0)
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"ok": True, "data": _card_out(card)}


@router.get("/cards/{card_id}")
async def get_card(card_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {"ok": True, "data": _card_out(_card_or_403(db, card_id, user.id))}


@router.patch("/cards/{card_id}")
async def patch_card(card_id: int, body: CardPatchIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    card = _card_or_403(db, card_id, user.id)
    if body.deck_id is not None:
        deck = _deck_or_403(db, body.deck_id, user.id)
        card.deck_id = deck.id
        if deck.document_id is not None:
            card.document_id = deck.document_id
    for field in ("question", "answer", "tag", "difficulty"):
        val = getattr(body, field)
        if val is not None:
            setattr(card, field, val)
    db.commit()
    db.refresh(card)
    return {"ok": True, "data": _card_out(card)}


@router.delete("/cards/{card_id}")
async def delete_card(card_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    card = _card_or_403(db, card_id, user.id)
    db.delete(card)
    db.commit()
    return {"ok": True, "data": {"deleted": 1}}
