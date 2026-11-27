# -*- coding: utf-8 -*-
"""AI 伴侣会话（0012）：会话列表/消息持久化；发送消息复用 /qa 流式引擎（异步落库）。

批次 3 的 agent-ai 会基于本模块做前端；这里先把接口契约定死。
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Conversation, ConversationMessage, User
from app.routers.deps import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConvIn(BaseModel):
    title: str | None = Field(default=None, max_length=120)


class MsgIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    context: dict | None = None   # { notes: [id], wrongs: [id], plans: [id] }


def _conv_or_404(db: Session, conv_id: int, uid: int) -> Conversation:
    conv = db.scalar(select(Conversation).where(
        Conversation.id == conv_id, Conversation.user_id == uid))
    if not conv:
        raise APIError(ErrCode.COMMON_404, "会话不存在或不属于当前用户", 404)
    return conv


def _conv_out(c: Conversation) -> dict:
    return {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat()}


@router.get("")
async def list_conversations(user: User = Depends(get_current_user),
                             db: Session = Depends(get_db)):
    """会话列表：按 updated_at 倒序，带未读数（本实现未读恒 0，前端展示用）。"""
    rows = list(db.scalars(select(Conversation).where(Conversation.user_id == user.id)
                           .order_by(Conversation.updated_at.desc()).limit(100)))
    out = []
    for c in rows:
        n = db.scalar(select(func.count()).select_from(ConversationMessage)
                      .where(ConversationMessage.conversation_id == c.id)) or 0
        o = _conv_out(c)
        o["messages"] = int(n)
        out.append(o)
    return {"ok": True, "data": out}


@router.post("")
async def create_conversation(body: ConvIn, user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    c = Conversation(user_id=user.id, title=(body.title or "新对话").strip()[:120] or "新对话",
                     created_at=datetime.now(timezone.utc),
                     updated_at=datetime.now(timezone.utc))
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"ok": True, "data": _conv_out(c)}


@router.get("/{conv_id}/messages")
async def list_messages(conv_id: int, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    _conv_or_404(db, conv_id, user.id)
    rows = list(db.scalars(select(ConversationMessage)
                           .where(ConversationMessage.conversation_id == conv_id)
                           .order_by(ConversationMessage.id).limit(500)))
    return {"ok": True, "data": [
        {"id": m.id, "role": m.role, "content": m.content,
         "sources": m.sources, "steps": m.steps,
         "created_at": m.created_at.isoformat() if m.created_at else None}
        for m in rows]}


@router.post("/{conv_id}/messages")
async def send_message(conv_id: int, body: MsgIn,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """发送消息（流式 NDJSON）。用户消息落库；AI 回复由 /qa 引擎流式产出并落库。

    事件协议与 /qa/stream 一致：status → sources → delta* → done。
    前端 agent-ai 会复用 streamQA 的解析逻辑。
    """
    conv = _conv_or_404(db, conv_id, user.id)
    db.add(ConversationMessage(conversation_id=conv_id, role="user", content=body.content,
                               created_at=datetime.now(timezone.utc)))
    db.commit()

    from app.routers.qa import _ask_core
    from app.schemas.schemas import QaIn

    async def gen():
        try:
            data = await _ask_core(QaIn(question=body.content), None, user, db,
                                   "auto", body.content)
            answer = (data.get("answer") or "").strip()
            sources = data.get("sources") or []
        except Exception as e:  # noqa: BLE001 引擎失败也要给前端可读错误
            yield json.dumps({"type": "error",
                              "message": getattr(e, "message", str(e))[:200]},
                             ensure_ascii=False) + "\n"
            return
        # AI 回复落库
        db.add(ConversationMessage(conversation_id=conv_id, role="assistant",
                                   content=answer, sources=sources, steps=None,
                                   created_at=datetime.now(timezone.utc)))
        conv.updated_at = datetime.now(timezone.utc)
        db.commit()
        # 流式回放：status → sources → delta（全文一次）→ done
        yield json.dumps({"type": "status", "status": "thinking",
                          "message": "检索资料与学科知识"}, ensure_ascii=False) + "\n"
        if sources:
            yield json.dumps({"type": "sources", "sources": sources},
                             ensure_ascii=False) + "\n"
        yield json.dumps({"type": "delta", "text": answer}, ensure_ascii=False) + "\n"
        yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@router.patch("/{conv_id}")
async def rename_conversation(conv_id: int, body: ConvIn,
                              user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    conv = _conv_or_404(db, conv_id, user.id)
    if body.title and body.title.strip():
        conv.title = body.title.strip()[:120]
        db.commit()
    return {"ok": True, "data": _conv_out(conv)}


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: int, user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    conv = _conv_or_404(db, conv_id, user.id)
    db.execute(ConversationMessage.__table__.delete()
               .where(ConversationMessage.conversation_id == conv_id))
    db.delete(conv)
    db.commit()
    return {"ok": True, "data": {"deleted": conv_id}}
