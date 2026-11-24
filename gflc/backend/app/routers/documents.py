# -*- coding: utf-8 -*-
"""文档：上传（直传或预签名）→ 建档 → 解析切块 → 生成卡片 → 列表/详情。
P0 解析同步；P1 改 Redis 队列 + Worker（接口不变）。"""
import hashlib
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select, union_all
from sqlalchemy.orm import Session

from app.ai.router import generate_json
from app.core.budget import budget
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Attempt, Card, CardDeck, Chunk, Document, Note, Question
from app.routers.deps import get_current_user
from app.schemas.schemas import DocumentOut, NoteIn, PresignIn
from app.services.storage import get_storage, presign_put, stat_size
from app.worker import runner

router = APIRouter(prefix="/documents", tags=["documents"])
log = logging.getLogger(__name__)

_ALLOWED = {".pdf", ".docx", ".md", ".markdown", ".txt"}


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
    doc = crud.create_document(db, user_id=user.id, title=file.filename, source_type="doc",
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
    doc = crud.create_document(db, user_id=user.id, title=title, source_type="doc", content_hash=h,
                               storage_key=key, size=real_size, mime=body.get("mime", "application/pdf"))
    return {"ok": True, "data": {"document": DocumentOut.model_validate(doc).model_dump(), "dedup": False}}


@router.get("")
async def list_documents(user=Depends(get_current_user), db: Session = Depends(get_db)):
    # 题库文件在「题库」页管理，不在资料列表里重复出现；
    # 问答沉淀用的容器资料（content_hash=qa-collection-*）是内部占位，同样不展示
    docs = [
        d for d in crud.list_documents(db, user.id)
        if d.source_type != "question_bank"
        and not str(d.content_hash or "").startswith("qa-collection-")
    ]
    return {"ok": True, "data": [DocumentOut.model_validate(d).model_dump() for d in docs]}


@router.get("/{doc_id}")
async def get_document(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    return {"ok": True, "data": DocumentOut.model_validate(doc).model_dump()}


@router.get("/{doc_id}/overview")
async def document_overview(doc_id: int, user=Depends(get_current_user),
                            db: Session = Depends(get_db)):
    """资料二级枢纽：一屏看清这份资料学到哪了。

    契约（只增接口，不改既有接口行为）：
      document / chunks / notes / cards / questions / mastery 六块。
    全部指标在 SQL 层聚合（count / sum(case) / avg），不把明细捞进 Python 再过滤。

    掌握度口径（S2 统一口径，卡片与题目各算一次观测）：
      score < 0.35 → 未开始；0.35 ≤ score ≤ 0.7 → 学习中；score > 0.7 → 已掌握。
      score = 该资料全部卡片与题目 mastery 的均值；无观测时为 0。
    """
    doc = db.scalar(select(Document).where(Document.id == doc_id))
    if doc is None:
        raise APIError(ErrCode.COMMON_404, "资料不存在", 404)
    if doc.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权访问该资料", 403)

    # SQLite 的时间列不带时区（CURRENT_TIMESTAMP 为 naive UTC），比较时要去掉 tzinfo；
    # PostgreSQL 的 timestamptz 保留 aware UTC，交给驱动转换。
    now = datetime.now(timezone.utc)
    if db.get_bind().dialect.name == "sqlite":
        now = now.replace(tzinfo=None)

    n_chunks = db.scalar(
        select(func.count()).select_from(Chunk).where(Chunk.document_id == doc.id)) or 0

    note_rows = db.execute(
        select(Note.id, Note.title, Note.source, Note.updated_at)
        .where(Note.document_id == doc.id)
        .order_by(Note.updated_at.desc(), Note.id.desc()).limit(5)
    ).all()

    cards_total, cards_mastered, cards_due, cards_avg = db.execute(
        select(
            func.count(Card.id),
            func.coalesce(func.sum(case((Card.mastery > 0.7, 1), else_=0)), 0),
            func.coalesce(func.sum(case(
                (and_(Card.due_at.is_not(None), Card.due_at <= now), 1), else_=0)), 0),
            func.coalesce(func.avg(Card.mastery), 0.0),
        ).where(Card.document_id == doc.id, Card.user_id == user.id)
    ).one()

    recent_cards = db.execute(
        select(Card.id, Card.question, Card.mastery, Card.due_at)
        .where(Card.document_id == doc.id, Card.user_id == user.id)
        .order_by(Card.id.desc()).limit(4)
    ).all()

    # 一次 JOIN 聚合出题目总数 / 已答数 / 作答次数 / 答对次数；
    # answered = 有过 attempt 的不同题目数（同一题刷多次不重复计）。
    q_total, q_answered, q_attempts, q_correct = db.execute(
        select(
            func.count(func.distinct(Question.id)),
            func.count(func.distinct(Attempt.question_id)),
            func.count(Attempt.id),
            func.coalesce(func.sum(case((Attempt.correct == 1, 1), else_=0)), 0),
        ).select_from(Question)
        .outerjoin(Attempt, and_(Attempt.question_id == Question.id,
                                 Attempt.user_id == user.id))
        .where(Question.document_id == doc.id, Question.user_id == user.id)
    ).one()

    # 卡片与题目的 mastery 合并为一张观测表，再一次聚合出均值与三档分布
    obs = union_all(
        select(Card.mastery.label("m")).where(
            Card.document_id == doc.id, Card.user_id == user.id),
        select(Question.mastery.label("m")).where(
            Question.document_id == doc.id, Question.user_id == user.id),
    ).subquery()
    m_score, m_new, m_learning, m_mastered = db.execute(
        select(
            func.coalesce(func.avg(obs.c.m), 0.0),
            func.coalesce(func.sum(case((obs.c.m < 0.35, 1), else_=0)), 0),
            func.coalesce(func.sum(case(
                (and_(obs.c.m >= 0.35, obs.c.m <= 0.7), 1), else_=0)), 0),
            func.coalesce(func.sum(case((obs.c.m > 0.7, 1), else_=0)), 0),
        )
    ).one()

    score = round(float(m_score or 0.0), 3)
    level = "not_started" if score < 0.35 else ("learning" if score <= 0.7 else "mastered")

    return {"ok": True, "data": {
        "document": {
            "id": doc.id,
            "title": doc.title,
            "source_type": doc.source_type,
            "status": doc.status,
            "size": doc.size,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
        },
        "chunks": int(n_chunks),
        "notes": [{
            "id": n.id,
            "title": n.title or "",
            "source": n.source or "manual",
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
        } for n in note_rows],
        "cards": {
            "total": int(cards_total or 0),
            "mastered": int(cards_mastered or 0),
            "due": int(cards_due or 0),
            "avg_mastery": round(float(cards_avg or 0.0), 3),
            "recent": [{
                "id": c.id,
                "question": c.question,
                "mastery": round(float(c.mastery or 0.0), 3),
                "due_at": c.due_at.isoformat() if c.due_at else None,
            } for c in recent_cards],
        },
        "questions": {
            "total": int(q_total or 0),
            "answered": int(q_answered or 0),
            "accuracy": round(q_correct / q_attempts * 100, 1) if q_attempts else 0.0,
        },
        "mastery": {
            "level": level,
            "score": score,
            "breakdown": {
                "未开始": int(m_new or 0),
                "学习中": int(m_learning or 0),
                "已掌握": int(m_mastered or 0),
            },
        },
    }}


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
# 资料 → 笔记：同步生成（前端显示 loading）。取前 N 段避免超长，N 可用运行时配置覆盖。
_NOTE_MAX_CHUNKS = 40       # 单次生成读取的最大块数
_NOTE_CHUNK_CHARS = 1200    # 单块截断长度：长块只取开头，保证总 prompt 可控
_NOTE_MAX_TOKENS = 4000     # mid 档默认 3000 会把长笔记截成半截 JSON，这里放宽

NOTE_GEN_SYSTEM = (
    "你是学习笔记整理助手。把给定的资料片段整理成一份能直接背诵的笔记：\n"
    "1) 先用 150 字以内概括核心内容（summary）；\n"
    "2) 正文用 Markdown 分节（## / ###）与列表组织，公式用 LaTeX（$...$）；\n"
    "3) 只能依据给定片段，不编造片段里没有的内容；片段未涉及的部分直说「资料未涉及」；\n"
    "4) 最后给 3–6 条要点或易错点（points，每条一句话）；\n"
    "5) 全文中文。只输出 JSON。"
)


class _NoteGenOut(BaseModel):
    """模型输出的结构化笔记契约（title/summary/points/content）。"""
    title: str = ""
    summary: str = ""
    points: list[str] = []
    content: str = ""


def _note_user(title: str, blocks: list[str]) -> str:
    return ('输出 JSON：{"title":"","summary":"","points":[""],"content":""}。\n'
            f"资料标题：{title}\n资料片段：\n" + "\n\n".join(blocks))


def _note_max_chunks(db: Session) -> int:
    """块数可配：运行时配置 doc_note_max_chunks 覆盖默认值（不改静态配置文件）。"""
    try:
        from app.services import settings_store
        raw = settings_store.get_runtime(db, "doc_note_max_chunks", str(_NOTE_MAX_CHUNKS))
        n = int(raw or _NOTE_MAX_CHUNKS)
        return n if 1 <= n <= 200 else _NOTE_MAX_CHUNKS
    except Exception:
        return _NOTE_MAX_CHUNKS


def _note_out(n: Note) -> dict:
    """按 NoteOut 契约出参。

    updated_at 在 schema 里是字符串，直接 model_validate(ORM) 会把 datetime 塞进 str 字段
    而校验失败（老 list_notes 就这么挂的），这里统一转 ISO 字符串。
    """
    return {
        "id": n.id,
        "document_id": n.document_id,
        "folder_id": n.folder_id,
        "title": n.title or "",
        "summary": n.summary or "",
        "content": n.content,
        "points": n.points,
        "source": n.source or "manual",
        "kind": n.kind or "note",
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("/{doc_id}/notes")
async def list_notes(doc_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    rows = list(db.scalars(select(Note).where(Note.document_id == doc.id).order_by(Note.id.desc())))
    return {"ok": True, "data": [_note_out(n) for n in rows]}


@router.post("/{doc_id}/notes")
async def create_note(doc_id: int, body: NoteIn, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """资料 → 笔记。两种语义：

    1) body.content 非空：旧语义，按用户显式给的内容直接落库（兼容历史前端）；
    2) body.content 为空：AI 生成 —— 读取该文档 chunks（按 chunk_index 排序取前 N 段）
       → mid 档模型生成结构化笔记 → 写入 Note（source='ai'）。
       失败一律抛中文可读错误，绝不静默返回空笔记。
    """
    doc = crud.get_document(db, doc_id, user.id)
    if not doc:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)

    explicit = (body.content or "").strip()
    if explicit:
        n = Note(user_id=user.id, document_id=doc.id,
                 title=(body.title or doc.title)[:256], summary=body.summary,
                 content=explicit, points=body.points,
                 source=body.source or "manual", kind=body.kind or "note")
        db.add(n)
        db.commit()
        db.refresh(n)
        return {"ok": True, "data": _note_out(n)}

    # ---- AI 生成路径 ----
    chunks = list(db.scalars(
        select(Chunk).where(Chunk.document_id == doc.id)
        .order_by(Chunk.chunk_index, Chunk.id).limit(_note_max_chunks(db))))
    if not chunks:
        raise APIError(ErrCode.COMMON_400, "该资料还未解析，请先解析后再生成笔记")

    blocks: list[str] = []
    for c in chunks:
        text = (c.content or "").strip()
        if not text:
            continue
        page = f"（第 {c.page} 页）" if c.page else ""
        blocks.append(f"片段 {c.chunk_index + 1}{page}：{text[:_NOTE_CHUNK_CHARS]}")
    if not blocks:
        raise APIError(ErrCode.COMMON_400, "该资料没有可用文本，请重新解析后再生成笔记")

    title = (body.title or "").strip() or doc.title
    try:
        obj, res = await generate_json("mid", NOTE_GEN_SYSTEM, _note_user(title, blocks),
                                       _NoteGenOut, max_tokens=_NOTE_MAX_TOKENS,
                                       user_id=user.id, task_type="doc_note")
    except APIError as e:
        # 配额类错误原样抛出（用户需要看到具体限额），其余转成可读中文
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        log.warning("资料生成笔记失败 doc=%s err=%s", doc.id, e)
        raise APIError(ErrCode.AI_003, f"笔记生成失败：{e.message}，请稍后重试") from e
    except Exception as e:  # 网络等非契约异常同样不静默
        log.warning("资料生成笔记异常 doc=%s err=%s", doc.id, e)
        raise APIError(ErrCode.AI_003, "笔记生成失败：模型调用异常，请稍后重试") from e

    content = (obj.content or "").strip()
    if not content:
        raise APIError(ErrCode.AI_003, "笔记生成失败：模型未返回正文，请重试")

    # 成本账本：generate_json 只做预算拦截，记账由业务层补一笔（与其它 AI 路径一致）
    try:
        budget.record(user.id, "doc_note", res.prompt_tokens, res.completion_tokens,
                      settings.LLM_MID_MODEL)
    except Exception as e:
        log.warning("笔记成本记账失败 doc=%s err=%s", doc.id, e)

    # 同一资料的 AI 笔记只保留一份：重复点「生成笔记」原地更新（note id 稳定、不堆同名条目），
    # 只动 source='ai' 的行，手工笔记一律不碰（与视频笔记只清 AI 产物的策略一致）。
    new_title = ((obj.title or "").strip() or f"{title} · AI 笔记")[:256]
    new_points = [p.strip() for p in (obj.points or []) if (p or "").strip()]
    old = db.scalar(select(Note).where(Note.document_id == doc.id, Note.source == "ai",
                                       Note.kind == "note").order_by(Note.id.desc()))
    if old is not None:
        old.title, old.summary = new_title, (obj.summary or "")[:1000]
        old.content, old.points = content, new_points
        n = old
        db.query(Note).filter(Note.document_id == doc.id, Note.source == "ai",
                              Note.kind == "note", Note.id != n.id).delete(
            synchronize_session=False)  # 历史重复行一并清掉
    else:
        n = Note(user_id=user.id, document_id=doc.id, title=new_title,
                 summary=(obj.summary or "")[:1000], content=content, points=new_points,
                 source="ai", kind="note")
        db.add(n)
    db.commit()
    db.refresh(n)
    return {"ok": True,
            "data": {**_note_out(n), "chunks_used": len(blocks)}}
