# -*- coding: utf-8 -*-
"""题库：两步生成（先上传落盘 → 再后台视觉识别成题库），另保留一步到位的 /import。"""
import hashlib
import os
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Document, Question, QuestionBank
from app.routers.deps import get_current_user
from app.schemas.schemas import QuestionOut
from app.services.storage import get_storage
from app.worker import runner

router = APIRouter(prefix="/questions", tags=["questions"])
_ALLOWED = {".pdf", ".xlsx", ".xlsm", ".docx", ".txt", ".md"}
_EXT_HINT = "pdf/xlsx/xlsm/docx/txt/md"


def _pdf_pages(data: bytes, ext: str) -> int:
    """只读页数，不解析内容；非 PDF 或失败给 0。"""
    if ext != ".pdf":
        return 0
    try:
        import pymupdf
        doc = pymupdf.open(stream=data, filetype="pdf")
        try:
            return int(doc.page_count)
        finally:
            doc.close()
    except Exception:  # noqa: BLE001
        return 0


def _owned_document(db: Session, document_id: int, user_id: int) -> Document:
    """带租户过滤取文档；别人的文档 403，不存在 404。"""
    doc = crud.get_document(db, document_id, user_id)
    if doc is not None:
        return doc
    if db.get(Document, document_id) is not None:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    raise APIError(ErrCode.COMMON_404, "文档不存在", 404)


async def _read_upload(file: UploadFile) -> tuple[bytes, str, str]:
    name = file.filename or "题库"
    ext = os.path.splitext(name)[1].lower()
    if ext not in _ALLOWED:
        raise APIError(ErrCode.FILE_002, f"题库仅支持 {_EXT_HINT}，收到 {ext}")
    data = await file.read()
    if not data:
        raise APIError(ErrCode.FILE_002, "文件为空，请重新选择")
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise APIError(ErrCode.FILE_001, "文件过大")
    return data, name, ext


@router.post("/upload")
async def upload_question_file(file: UploadFile = File(...), user=Depends(get_current_user),
                               db: Session = Depends(get_db)):
    """第一步：只落盘 + 建文档（status=uploaded），不解析题目。"""
    data, name, ext = await _read_upload(file)
    pages = _pdf_pages(data, ext)
    h = hashlib.sha256(data).hexdigest()

    old = crud.find_by_hash(db, user.id, h)
    if old is not None and old.source_type == "question_bank":
        return {"ok": True, "data": {"document_id": old.id, "filename": old.title,
                                     "size": old.size or len(data), "pages": pages,
                                     "dedup": True}}

    key = f"{user.id}/qb_{uuid.uuid4().hex[:12]}_{name}"
    get_storage().save(key, data)
    doc = crud.create_document(db, user_id=user.id, title=name, source_type="question_bank",
                               content_hash=h, storage_key=key, size=len(data),
                               mime=file.content_type or "")
    doc.status = "uploaded"
    db.commit()
    return {"ok": True, "data": {"document_id": doc.id, "filename": name, "size": len(data),
                                 "pages": pages, "dedup": False}}


@router.post("/{document_id}/generate")
async def generate_bank(document_id: int, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """第二步：把已上传的题库文件入队生成题目（后台视觉识别）。"""
    doc = _owned_document(db, document_id, user.id)
    if doc.source_type != "question_bank":
        raise APIError(ErrCode.COMMON_400, "该文档不是题库文件，无法生成题库")
    if not doc.storage_key:
        raise APIError(ErrCode.COMMON_400, "题库文件已清理，请重新上传")
    doc.status = "parsing"
    db.commit()

    t = runner.create_task(db, user.id, "question_import", document_id=doc.id)
    runner.submit(t.id, "question_import", {"document_id": doc.id, "storage_key": doc.storage_key,
                                            "filename": doc.title, "size": doc.size or 0,
                                            "mime": doc.mime or ""})
    return {"ok": True, "data": {"task_id": t.id, "document_id": doc.id}}


@router.post("/import")
async def import_questions(file: UploadFile = File(...), user=Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """一步到位（兼容旧前端）：建文档 → 直接入队生成。"""
    data, name, ext = await _read_upload(file)
    key = f"{user.id}/qb_{uuid.uuid4().hex[:12]}_{name}"
    get_storage().save(key, data)
    doc = crud.create_document(db, user_id=user.id, title=name, source_type="question_bank",
                               content_hash=hashlib.sha256(data).hexdigest(), storage_key=key,
                               size=len(data), mime=file.content_type or "")
    doc.status = "uploaded"
    db.commit()

    tmp = os.path.join(tempfile.gettempdir(), f"gflc_qb_{uuid.uuid4().hex}{ext}")
    with open(tmp, "wb") as f:
        f.write(data)

    t = runner.create_task(db, user.id, "question_import", document_id=doc.id)
    runner.submit(t.id, "question_import", {"path": tmp, "document_id": doc.id, "filename": name,
                                            "storage_key": key, "size": len(data),
                                            "mime": file.content_type or ""})
    return {"ok": True, "data": {"task_id": t.id, "document_id": doc.id}}


@router.get("/banks")
async def list_banks(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """题库集列表：含题数、章节分布、科目。"""
    banks = list(db.scalars(select(QuestionBank).where(QuestionBank.user_id == user.id)
                            .order_by(QuestionBank.id.desc()).limit(50)))
    out = []
    for b in banks:
        rows = list(db.execute(
            select(Question.chapter, func.count()).where(Question.bank_id == b.id)
            .group_by(Question.chapter)).all())
        chapters = [{"chapter": (r[0] or "未分类"), "count": r[1]} for r in rows]
        total = sum(c["count"] for c in chapters)
        out.append({"id": b.id, "name": b.name, "subject": b.subject,
                    "total": total, "chapters": chapters,
                    "created_at": b.created_at.isoformat() if b.created_at else None})

    # 兜底：历史数据可能没有题库集归属，聚成「未归类题目」，不要让题目在黑箱里消失
    loose = list(db.execute(
        select(Question.chapter, func.count()).where(Question.user_id == user.id,
                                                     Question.bank_id.is_(None))
        .group_by(Question.chapter)).all())
    if loose:
        chapters = [{"chapter": (r[0] or "未分类"), "count": r[1]} for r in loose]
        out.append({"id": None, "name": "未归类题目", "subject": "",
                    "total": sum(c["count"] for c in chapters), "chapters": chapters,
                    "created_at": None})
    return {"ok": True, "data": out}


@router.delete("/banks/{bank_id}")
async def delete_bank(bank_id: int, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """删除题库集及其全部题目（独立题库页用）。

    幂等：不存在或不属于当前用户，返回 0 个删除，不报错。
    删除顺序：先清 attempts（引用题目）、再清题目、再清题库集本身。
    """
    bank = db.scalar(select(QuestionBank).where(
        QuestionBank.id == bank_id, QuestionBank.user_id == user.id))
    if not bank:
        return {"ok": True, "data": {"deleted": 0}}
    # attempts 通过 question_id 外键引用题目，先删
    db.execute(text(
        "DELETE FROM attempts WHERE question_id IN "
        "(SELECT id FROM questions WHERE bank_id = :b)"), {"b": bank_id})
    n_q = db.execute(text("DELETE FROM questions WHERE bank_id = :b"), {"b": bank_id}).rowcount
    db.execute(text("DELETE FROM question_banks WHERE id = :b"), {"b": bank_id})
    db.commit()
    return {"ok": True, "data": {"deleted": n_q or 0}}


@router.get("")
async def list_questions(bank_id: int | None = None, document_id: int | None = None,
                         chapter: str | None = None, user=Depends(get_current_user),
                         db: Session = Depends(get_db)):
    stmt = select(Question).where(Question.user_id == user.id)
    if bank_id:
        stmt = stmt.where(Question.bank_id == bank_id)
    if document_id:
        stmt = stmt.where(Question.document_id == document_id)
    if chapter:
        stmt = stmt.where(Question.chapter == chapter)
    rows = list(db.scalars(stmt.order_by(Question.id).limit(300)))
    return {"ok": True, "data": [QuestionOut.model_validate(q).model_dump() for q in rows]}
