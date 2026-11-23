# -*- coding: utf-8 -*-
"""V5 账号数据导出与注销清理。

- build_export：把用户全部业务数据打成机器可读 JSON 归档（敏感字段脱敏，绝不含密码哈希/凭据）。
- purge_user_data：级联清理 documents/chunks/notes/cards/attempts/plans/tasks/成本账本等，
  调用存储删除对象、清检索缓存，并写审计日志。
- 所有动作只存「动作 + IP 摘要 + 非敏感备注」到审计表，不落原文与凭据。

说明：storage.py 为只读引用（不在本 Agent 所有权内），其现有接口没有 delete；
本模块通过 get_storage() 取实例后按「delete 方法 → MinIO client().remove_object →
本地 base/_path」顺序防御式调用，缺能力时记 WARNING 并在返回结果里暴露失败数，不静默吞掉。
"""
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import (
    Attempt, AuditLog, Card, CardDeck, CostLedger, DashboardLayout, Document,
    Note, NoteFolder, Plan, PlanTask, Question, QuestionBank, Task, User, Chunk,
)

log = logging.getLogger(__name__)
EXPORT_SCHEMA_VERSION = "1.0"


# ---------------------------------------------------------------------------
# 审计
# ---------------------------------------------------------------------------
def ip_digest(request) -> str:
    """取 IP 的 sha256 前 16 位作为摘要；绝不落原文。"""
    raw = (request.client.host if getattr(request, "client", None) else "-") or "-"
    return hashlib.sha256(raw.encode("utf-8", "ignore")).hexdigest()[:16]


def write_audit(db: Session, user_id: int, action: str, request, detail: str = "") -> AuditLog:
    """写一条审计日志（调用方负责 commit）。只写动作/IP 摘要/非敏感备注。"""
    row = AuditLog(user_id=user_id, action=action, ip_hash=ip_digest(request),
                   detail=(detail or "")[:200])
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# 导出
# ---------------------------------------------------------------------------
def _mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    keep = local[:2] if len(local) > 2 else local[:1]
    return "{}***@{}".format(keep, domain)


def _jsonable(v: Any) -> Any:
    if isinstance(v, (datetime,)):
        return v.isoformat()
    if hasattr(v, "isoformat") and not isinstance(v, (str, bytes, int, float)):
        try:
            return v.isoformat()
        except Exception:
            pass
    return v


def _row(obj) -> dict:
    """把 ORM 行转成纯 dict（datetime→ISO 字符串），供 JSON 序列化。"""
    from sqlalchemy import inspect as sa_inspect
    out: dict = {}
    try:
        attrs = sa_inspect(obj).mapper.column_attrs
    except Exception:
        return {}
    for a in attrs:
        key = a.key
        if key == "password_hash":  # 凭据绝不导出
            continue
        out[key] = _jsonable(getattr(obj, key, None))
    return out


def _rows(objs) -> list[dict]:
    return [_row(o) for o in objs]


def build_export(db: Session, user_id: int) -> dict:
    """构建机器可读归档：用户全部业务数据；用户邮箱脱敏，不含密码_hash。"""
    user = db.get(User, user_id)
    doc_ids = select(Document.id).where(Document.user_id == user_id)
    plan_ids = select(Plan.id).where(Plan.user_id == user_id)

    data = {
        "documents": _rows(db.scalars(select(Document).where(Document.user_id == user_id))),
        "chunks": _rows(db.scalars(select(Chunk).where(Chunk.document_id.in_(doc_ids)))),
        "tasks": _rows(db.scalars(select(Task).where(Task.user_id == user_id))),
        "notes": _rows(db.scalars(select(Note).where(Note.user_id == user_id))),
        "note_folders": _rows(db.scalars(select(NoteFolder).where(NoteFolder.user_id == user_id))),
        "card_decks": _rows(db.scalars(select(CardDeck).where(CardDeck.user_id == user_id))),
        "cards": _rows(db.scalars(select(Card).where(Card.user_id == user_id))),
        "question_banks": _rows(db.scalars(select(QuestionBank).where(QuestionBank.user_id == user_id))),
        "questions": _rows(db.scalars(select(Question).where(Question.user_id == user_id))),
        "attempts": _rows(db.scalars(select(Attempt).where(Attempt.user_id == user_id))),
        "plans": _rows(db.scalars(select(Plan).where(Plan.user_id == user_id))),
        "plan_tasks": _rows(db.scalars(select(PlanTask).where(PlanTask.plan_id.in_(plan_ids)))),
        "cost_ledger": _rows(db.scalars(select(CostLedger).where(CostLedger.user_id == user_id))),
        "dashboard_layouts": _rows(db.scalars(select(DashboardLayout).where(DashboardLayout.user_id == user_id))),
    }
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": user_id,
            "email": _mask_email(user.email) if user else "***",
            "role": user.role if user else "",
            "status": user.status if user else "",
            "created_at": _jsonable(user.created_at) if user else None,
        },
        "data": data,
        "note": "本归档为用户个人数据副本；邮箱已脱敏，密码哈希与凭据未包含。",
    }


# ---------------------------------------------------------------------------
# 存储对象清理（防御式，缺能力时告警而非静默）
# ---------------------------------------------------------------------------
def _delete_one_object(storage, key: str) -> bool:
    """删除单个存储对象。按既有接口能力依次尝试，返回是否成功。"""
    if not key:
        return False
    delete_fn = getattr(storage, "delete", None)
    if callable(delete_fn):
        delete_fn(key)
        return True
    client_fn = getattr(storage, "client", None)
    if callable(client_fn):
        # MinioStorage：复用既有 client()，无需新增依赖
        client_fn().remove_object(settings.MINIO_BUCKET, key)
        return True
    base = getattr(storage, "base", None)
    path_fn = getattr(storage, "_path", None)
    if base and callable(path_fn):
        # LocalStorage：复用既有 _path()（内含 commonpath 越权防护）
        p = path_fn(key)
        if os.path.isfile(p):
            os.remove(p)
        return True
    return False


def purge_storage_objects(keys: list[str], user_id: int) -> tuple[int, int]:
    """返回 (成功数, 失败数)。任一对象失败都记 WARNING，带 user_id。"""
    keys = [k for k in keys if k]
    if not keys:
        return 0, 0
    try:
        from app.services.storage import get_storage
        storage = get_storage()
    except Exception as e:  # pragma: no cover - 存储不可用时仍继续清 DB
        log.warning("账号注销存储清理不可用 user=%s err=%s", user_id, e)
        return 0, len(keys)
    purged = failed = 0
    for key in keys:
        try:
            if _delete_one_object(storage, key):
                purged += 1
            else:
                failed += 1
                log.warning("存储后端无删除能力，对象未清除 user=%s key=%s", user_id, key)
        except Exception as e:
            failed += 1
            log.warning("存储对象删除失败 user=%s key=%s err=%s", user_id, key, e)
    return purged, failed


def clear_search_cache(user_id: int) -> bool:
    """清理该用户的检索相关进程内缓存（rag/query_opt/answer_cache 均只读引用）。"""
    cleared = True
    try:
        from app.services import rag
        cache = getattr(rag, "_INDEX_CACHE", None)
        if isinstance(cache, dict):
            for k in [k for k in cache if isinstance(k, tuple) and k and k[0] == user_id]:
                cache.pop(k, None)
    except Exception as e:  # pragma: no cover
        cleared = False
        log.warning("清理 rag 索引缓存失败 user=%s err=%s", user_id, e)
    try:
        from app.services import query_opt
        cache = getattr(query_opt, "_cache", None)
        if isinstance(cache, dict):
            for k in [k for k in cache if str(user_id) in str(k)]:
                cache.pop(k, None)
    except Exception as e:  # pragma: no cover
        cleared = False
        log.warning("清理 query_opt 缓存失败 user=%s err=%s", user_id, e)
    try:
        from app.services import answer_cache  # 由 qa-retrieval Agent 提供，可能尚不存在
        for name in ("invalidate_user", "clear_user", "clear"):
            fn = getattr(answer_cache, name, None)
            if callable(fn):
                try:
                    fn(user_id)
                except TypeError:
                    fn()
                break
    except ImportError:
        pass
    except Exception as e:  # pragma: no cover
        cleared = False
        log.warning("清理 answer_cache 失败 user=%s err=%s", user_id, e)
    return cleared


# ---------------------------------------------------------------------------
# 注销：级联清理
# ---------------------------------------------------------------------------
def purge_user_data(db: Session, user_id: int, request) -> dict:
    """级联清理用户全部业务数据 + 存储对象 + 检索缓存，并写审计日志。"""
    doc_ids = select(Document.id).where(Document.user_id == user_id)
    plan_ids = select(Plan.id).where(Plan.user_id == user_id)
    q_ids = select(Question.id).where(Question.user_id == user_id)

    storage_keys = list(db.scalars(select(Document.storage_key).where(Document.user_id == user_id)))

    deleted: dict[str, int] = {}

    def _del(model, *conditions) -> None:
        res = db.execute(delete(model).where(*conditions))
        deleted[model.__tablename__] = deleted.get(model.__tablename__, 0) + int(res.rowcount or 0)

    # 先删依赖表，最后删父表（SQLite/PostgreSQL 均安全）
    _del(Attempt, (Attempt.user_id == user_id) | (Attempt.question_id.in_(q_ids)))
    _del(CostLedger, CostLedger.user_id == user_id)
    _del(Task, Task.user_id == user_id)
    _del(Chunk, Chunk.document_id.in_(doc_ids))
    _del(Note, (Note.user_id == user_id) | (Note.document_id.in_(doc_ids)))
    _del(NoteFolder, NoteFolder.user_id == user_id)
    _del(Card, (Card.user_id == user_id) | (Card.document_id.in_(doc_ids)))
    _del(CardDeck, (CardDeck.user_id == user_id) | (CardDeck.document_id.in_(doc_ids)))
    _del(QuestionBank, QuestionBank.user_id == user_id)
    _del(Question, (Question.user_id == user_id) | (Question.document_id.in_(doc_ids)))
    _del(PlanTask, PlanTask.plan_id.in_(plan_ids))
    _del(Plan, Plan.user_id == user_id)
    _del(DashboardLayout, DashboardLayout.user_id == user_id)
    _del(Document, Document.user_id == user_id)
    user_obj = db.get(User, user_id)
    if user_obj:
        db.delete(user_obj)
        deleted["users"] = 1

    purged, failed = purge_storage_objects(list(storage_keys), user_id)
    cache_cleared = clear_search_cache(user_id)

    # 审计在最后写：保留注销动作本身（审计表无外键，user 行删除后仍有效）
    write_audit(db, user_id, "delete", request,
                detail="cascade={}".format(sum(deleted.values())))
    db.commit()

    return {
        "deleted": deleted,
        "storage": {"objects": len(storage_keys), "purged": purged, "failed": failed},
        "cache_cleared": cache_cleared,
        "audit": "delete",
    }
