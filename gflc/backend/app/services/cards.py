# -*- coding: utf-8 -*-
"""卡片生成：无 Key 或 MOCK_AI 时走规则生成；否则逐块调轻档模型。
按 PDF 大纲把卡片归入「大卡包 → 章节卡包」，单块失败跳过、不卡整篇。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.mock import mock_cards
from app.ai.prompts import CARD_SYSTEM, card_user
from app.ai.router import estimate_cost, generate_json
from app.core.config import settings
from app.core.errors import APIError
from app.models.models import Card, CardDeck, Chunk, CostLedger, Document
from app.schemas.schemas import CardGenResult

_UNSORTED = "未分章"


def _root_deck(db: Session, user_id: int, document_id: int) -> CardDeck:
    deck = db.scalars(
        select(CardDeck).where(CardDeck.user_id == user_id,
                               CardDeck.document_id == document_id,
                               CardDeck.kind == "root")
    ).first()
    if deck:
        return deck
    doc = db.get(Document, document_id)
    title = (doc.title if doc else "") or "我的卡包"
    if title.lower().endswith(".pdf"):
        title = title[:-4]
    deck = CardDeck(user_id=user_id, document_id=document_id, parent_id=None,
                    name=title[:200], kind="root", sort=0)
    db.add(deck)
    db.flush()
    return deck


def _chapter_deck(db: Session, user_id: int, root: CardDeck, name: str, sort: int) -> CardDeck:
    """章节卡包按名称复用，避免重复建包。"""
    name = (name or "").strip()[:200] or _UNSORTED
    deck = db.scalars(
        select(CardDeck).where(CardDeck.user_id == user_id,
                               CardDeck.parent_id == root.id,
                               CardDeck.name == name)
    ).first()
    if deck:
        return deck
    deck = CardDeck(user_id=user_id, document_id=root.document_id, parent_id=root.id,
                    name=name, kind="chapter", sort=sort)
    db.add(deck)
    db.flush()
    return deck


def _chapter_name(ch_heading: str, item_chapter: str) -> str:
    """优先用模型判定的章节，其次用切块时的标题路径（取最末一级作为章节名）。"""
    c = (item_chapter or "").strip()
    if c:
        return c
    h = (ch_heading or "").strip()
    if h:
        parts = [p for p in h.replace(">", "/").split("/") if p.strip()]
        return parts[-1].strip() if parts else h
    return _UNSORTED


async def generate_cards(db: Session, user_id: int, document_id: int, max_chunks: int = 10,
                         on_progress=None) -> int:
    chunks = list(db.scalars(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index).limit(max_chunks)
    ))
    use_mock = settings.MOCK_AI or not settings.LLM_API_KEY
    root = _root_deck(db, user_id, document_id)
    total = 0
    for i, ch in enumerate(chunks):
        if on_progress:
            on_progress(int(8 + 84 * (i + 1) / max(1, len(chunks))))
        res = None
        if use_mock:
            items = mock_cards(ch.content, 3, ch.page).cards
        else:
            try:
                obj, res = await generate_json(
                    "light", CARD_SYSTEM, card_user(ch.content, 3, ch.page, ch.heading_path), CardGenResult)
            except APIError:
                continue  # 单块失败跳过
            items = obj.cards
        for item in items:
            deck = _chapter_deck(db, user_id, root, _chapter_name(ch.heading_path, item.chapter), i)
            db.add(Card(user_id=user_id, document_id=document_id, deck_id=deck.id, chunk_id=ch.id,
                        question=item.question, answer=item.answer, tag=item.tag,
                        page=item.page or ch.page, due_at=datetime.now(timezone.utc)))
        if res is not None:
            db.add(CostLedger(user_id=user_id, task_type="card_generate", model=settings.LLM_LIGHT_MODEL,
                              prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
                              cost_cny=estimate_cost(settings.LLM_LIGHT_MODEL,
                                                     res.prompt_tokens, res.completion_tokens)))
        total += len(items)
    db.commit()
    return total
