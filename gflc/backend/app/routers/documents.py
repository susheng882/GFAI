# -*- coding: utf-8 -*-
"""文档：上传（直传或预签名）→ 建档 → 解析切块 → 生成卡片 → 列表/详情。
P0 解析同步；P1 改 Redis 队列 + Worker（接口不变）。"""
import hashlib
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Card, CardDeck, Chunk, Document, Note
from app.routers.deps import get_current_user
from app.schemas.schemas import DocumentOut, NoteIn, NoteOut, PresignIn
from app.services.storage import get_storage, presign_put, stat_size
from app.worker import runner

router = APIRouter(prefix="/documents", tags=["documents"])

_ALLOWED = {".pdf"}


def _check_name(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED:
        raise APIError(ErrCode.FILE_002, f"暂不支持的文件类型：{ext}（P0 仅 PDF）")
    return ext


@router.post("/upload")
async def upload_direct(file: UploadFile = File(...), user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """前端一步上传（本地/MinIO 通用）。真实内容哈希去重。"""
    _check_name(file.filename or "x.pdf")
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise APIError(ErrCode.FILE_001, f"超过单文件上限 {settings.MAX_UPLOAD_MB} MB")
    h = hashlib.sha256(data).hexdigest()
    exist = crud.find_by_hash(db, user.id, h)
    if exist:
        return {"ok": True, "data": {"document": DocumentOut.model_validate(exist).model_dump(), "dedup": True}}
    key = f"{user.id}/{h[:16]}_{file.filename}"
    get_storage().save(key, data)
    doc = crud.create_document(db, user_id=user.id, title=file.filename, source_type="pdf",
                               content_hash=h, storage_key=key, size=len(data),
                               mime=file.content_type or "application/pdf")
    return {"ok": True, "data": {"document": DocumentOut.model_validate(doc).model_dump(), "dedup": False}}


@router.post("/presign")
async def presign(body: PresignIn, user=Depends(get_current_user)):
    _check_name(body.filename)
    if body.size and body.size > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise APIError(ErrCode.FILE_001, f"超过单文件上限 {settings.MAX_UPLOAD_MB} MB")
    key = f"{user.id}/{uuid.uuid4().hex}_{body.filename}"
    url = presign_put(key, body.content_type)
    return {"ok": True, "data": {"upload_url": url, "storage_key": key, "method": "PUT"}}


@router.post("")
async def create_document(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    key = body.get("storage_key", "")
    title = body.get("title") or os.path.basename(key)
    if not key:
        raise APIError(ErrCode.COMMON_400, "缺少 storage_key")
    # S1 越权防护：storage_key 必须属于当前用户目录，且不得含路径穿越字符。
    # presign 下发的 key 形如 "{user.id}/{uuid}_{filename}"，其它前缀一律拒绝。
    prefix = f"{user.id}/"
    if not key.startswith(prefix) or key == prefix or ".." in key or "\\" in key or key.startswith("/"):
        raise APIError(ErrCode.AUTH_403, "storage_key 不属于当前用户或格式非法", 403)
    try:
        real_size = stat_size(key)
    except Exception as e:
        raise APIError(ErrCode.FILE_001, f"存储端未找到文件：{e}") from e
    h = hashlib.sha256(f"{key}:{real_size}".encode()).hexdigest()
    exist = crud.find_by_hash(db, user.id, h)
    if exist:
        return {"ok": True, "data": {"document": DocumentOut.model_validate(exist).model_dump(), "dedup": True}}
    doc = crud.create_document(db, user_id=user.id, title=title, source_type="pdf", content_hash=h,
                               storage_key=key, size=real_size, mime=body.get("mime", "application/pdf"))
    return {"ok": True, "data": {"document": DocumentOut.model_validate(doc).model_dump(), "dedup": False}}


@router.get("")
async def list_documents(user=Depends(get_current_user), db: Session = Depends(get_db)):
    # 题库文件在「题库」页管理，不在资料列表里重复出现
    docs = [d for d in crud.list_documents(db, user.id) if d.source_type != "question_bank"]
    return {"ok": True, "data": [DocumentOut.model_validate(d).model_dump() for d in docs]}


@router.get("/{doc_id}")
async def get_document(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    return {"ok": True, "data": DocumentOut.model_validate(doc).model_dump()}


@router.post("/{doc_id}/parse")
async def parse_document(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    t = runner.create_task(db, user.id, "pdf_parse", doc.id)
    runner.submit(t.id, "pdf_parse", {"document_id": doc.id})
    return {"ok": True, "data": {"task_id": t.id}}


@router.post("/{doc_id}/cards")
async def make_cards(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    t = runner.create_task(db, user.id, "card_generate", doc.id)
    runner.submit(t.id, "card_generate", {"document_id": doc.id})
    return {"ok": True, "data": {"task_id": t.id}}


@router.get("/{doc_id}/cards")
async def list_cards(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    rows = list(db.scalars(select(Card).where(Card.document_id == doc.id).order_by(Card.id)))
    return {"ok": True, "data": [
        {"id": c.id, "deck_id": c.deck_id, "question": c.question, "answer": c.answer,
         "tag": c.tag, "page": c.page,
         "due_at": c.due_at.isoformat() if c.due_at else None, "reps": c.reps} for c in rows
    ]}


@router.patch("/{doc_id}")
async def rename_document(doc_id: int, body: dict, user=Depends(get_current_user),
                          db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    title = (body.get("title") or "").strip()
    if not title:
        raise APIError(ErrCode.COMMON_400, "标题不能为空")
    doc.title = title[:512]
    db.commit()
    return {"ok": True, "data": DocumentOut.model_validate(doc).model_dump()}


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """删除文档及其知识块、卡片、笔记、卡包；题库集一并清理。"""
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    n_cards = db.query(Card).filter(Card.document_id == doc.id).delete(synchronize_session=False)
    n_chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).delete(synchronize_session=False)
    n_notes = db.query(Note).filter(Note.document_id == doc.id).delete(synchronize_session=False)
    n_decks = db.query(CardDeck).filter(CardDeck.document_id == doc.id).delete(synchronize_session=False)
    db.delete(doc)
    db.commit()
    return {"ok": True, "data": {"deleted": True, "cards": n_cards, "chunks": n_chunks,
                                "notes": n_notes, "decks": n_decks}}


# ---------- 笔记 CRUD ----------
@router.get("/{doc_id}/notes")
async def list_notes(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    rows = list(db.scalars(select(Note).where(Note.document_id == doc.id).order_by(Note.id.desc())))
    return {"ok": True, "data": [NoteOut.model_validate(n).model_dump() for n in rows]}


@router.post("/{doc_id}/notes")
async def create_note(doc_id: int, body: NoteIn, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    n = Note(user_id=user.id, document_id=doc.id, title=body.title or doc.title,
             summary=body.summary, points=body.points)
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"ok": True, "data": NoteOut.model_validate(n).model_dump()}
