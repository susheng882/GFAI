# -*- coding: utf-8 -*-
"""笔记 AI 协作：生成建议（只返回、不落库）与笔记转背诵卡片。"""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.mock import mock_cards
from app.ai.prompts import CARD_SYSTEM, NOTE_AI_SYSTEM, card_user, note_ai_user
from app.ai.router import estimate_cost, generate_json
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.models.models import Card, CostLedger, Note
from app.schemas.schemas import CardGenResult, NoteAiIn, NoteAiOut
from app.services.cards import _chapter_deck, _root_deck

_FALLBACK_TEXT = {
    "improve": "## 待润色\n\n- 模型暂不可用，可先手动调整段落顺序与措辞。\n- 建议每条要点只讲一个知识点。",
    "expand": "## 待补充\n\n- 模型暂不可用，可先手动补充要点、例子与易错点。\n- 建议按「定义 → 方法 → 例题 → 易错点」补全。",
    "summarize": "## 待提炼\n\n- 模型暂不可用，可先手动抄出 3–5 条关键结论。",
    "quiz": "## 待自测\n\n- 模型暂不可用，可先手动把要点改写成问答形式。",
}


def _fallback(body: NoteAiIn) -> NoteAiOut:
    return NoteAiOut(suggestion=_FALLBACK_TEXT.get(body.mode, _FALLBACK_TEXT["improve"]),
                     points=[], kind="qa" if body.mode == "quiz" else "note")


async def suggest(db: Session, user_id: int, body: NoteAiIn) -> NoteAiOut:
    """调中档模型生成建议；失败降级为本地提示，不抛 500。"""
    try:
        obj, res = await generate_json(
            "mid", NOTE_AI_SYSTEM,
            note_ai_user(body.title, body.content, body.instruction, body.mode), NoteAiOut)
    except APIError:
        return _fallback(body)

    if not (obj.suggestion or "").strip():
        return _fallback(body)

    db.add(CostLedger(user_id=user_id, task_type="note_ai", model=settings.LLM_MID_MODEL,
                      prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
                      cost_cny=estimate_cost(settings.LLM_MID_MODEL,
                                             res.prompt_tokens, res.completion_tokens)))
    db.commit()
    return obj


async def to_cards(db: Session, user_id: int, note: Note) -> tuple[int, int]:
    """把笔记正文转成卡片，归入「文档大卡包 → 以笔记标题命名的章节包」。"""
    content = (note.content or "").strip()
    if not content:
        raise APIError(ErrCode.COMMON_400, "笔记内容为空，无法生成卡片")

    root = _root_deck(db, user_id, note.document_id)
    deck = _chapter_deck(db, user_id, root, note.title or "笔记", 0)

    res = None
    try:
        obj, res = await generate_json(
            "light", CARD_SYSTEM, card_user(content, 3, 0, note.title or ""), CardGenResult)
        items = obj.cards
    except APIError:
        items = mock_cards(content, 3, 0).cards  # 模型不可用时用规则抽取兜底

    for item in items:
        db.add(Card(user_id=user_id, document_id=note.document_id, deck_id=deck.id,
                    question=item.question, answer=item.answer, tag=item.tag or "",
                    page=item.page or 0, due_at=datetime.now(timezone.utc)))

    if res is not None:
        db.add(CostLedger(user_id=user_id, task_type="note_to_cards", model=settings.LLM_LIGHT_MODEL,
                          prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
                          cost_cny=estimate_cost(settings.LLM_LIGHT_MODEL,
                                                 res.prompt_tokens, res.completion_tokens)))
    db.commit()
    return len(items), deck.id
