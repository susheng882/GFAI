# -*- coding: utf-8 -*-
"""检索（P0）：jieba 分词 + BM25 关键词召回 + sqlite-vec 向量召回，双路合并统一重排。

提速与质量改造（2026-11-22）：
- 进程内缓存 BM25 索引，同一批语料只分词/建模一次，指纹变化自动失效；
- retrieve_multi：一次建索引、多查询打分，按 chunk_key 去重合并；
- V1/Q1：向量 Top20 + BM25 Top20 双路召回，按 chunk_key 合并去重后统一重排；
  VECTOR_ENABLED=false 时退化为纯 BM25，行为与加向量前一致；
- D7：笔记正文切块写入 chunks 表（source_type='note'），与文档块共用同一份检索语料
  与同一张 vec 表，一次 retrieve_multi 完成统一召回/重排；
- D3/Q3：BM25 归一化 + 向量相似度 + 关键词覆盖率融合为单一 0~1 置信度。

任何向量相关失败都只告警并降级为 BM25，绝不导致问答整体失败。
"""
import hashlib
import logging
import math
import os
from types import SimpleNamespace

import jieba
from rank_bm25 import BM25Plus
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Chunk, Document, Note
from app.services import embedding, vector_index
from app.services.chunking import chunk_text

jieba.setLogLevel(20)
log = logging.getLogger(__name__)

# 进程内索引缓存：key=(user_id, document_id or 0[, "combined"]) -> (fingerprint, bm25)
_INDEX_CACHE: dict[tuple, tuple] = {}
_INDEX_CACHE_MAX = 64
# 笔记切块缓存：user_id -> (fingerprint, hits)
_NOTE_CACHE: dict[int, tuple] = {}
# 笔记物理入库指纹：user_id -> fingerprint，避免每次问答都 delete/insert
_NOTE_PERSIST_CACHE: dict[int, tuple] = {}


def tokenize(text: str) -> list[str]:
    return [w.strip() for w in jieba.cut(text or "") if w.strip()]


def _chunk_stmt(user_id: int, document_id: int | None):
    # D6：上限来自 config，不再硬编码；多取一条用于检测"是否触顶"。
    stmt = select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user_id)
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
    return stmt.limit(settings.RETRIEVAL_MAX_CHUNKS + 1)


def _fingerprint(chunks: list) -> tuple:
    """语料指纹：块数 + 最小/最大 id + 内容哈希异或和，覆盖新增/删除/内容替换。"""
    if not chunks:
        return (0, 0, 0, 0)
    h = 0
    for c in chunks:
        h ^= hash(c.content_hash or c.id)
    return (len(chunks), min(c.id for c in chunks), max(c.id for c in chunks), h)


def _get_index(db: Session, user_id: int, document_id: int | None):
    """返回 (chunks, bm25)；索引按指纹缓存，语料未变则零分词、零建模。"""
    rows = list(db.scalars(_chunk_stmt(user_id, document_id)))
    if not rows:
        return [], None
    # D6：触顶只告警（带用户/文档维度），检索行为保持不变。
    cap = settings.RETRIEVAL_MAX_CHUNKS
    if len(rows) > cap:
        log.warning(
            "retrieval corpus truncated: user=%s doc=%s has >%s chunks; "
            "only the first %s are searchable. Reduce material or raise RETRIEVAL_MAX_CHUNKS.",
            user_id, document_id, cap, cap)
    chunks = rows[:cap]
    key = (user_id, document_id or 0)
    fp = _fingerprint(chunks)
    cached = _INDEX_CACHE.get(key)
    if cached and cached[0] == fp:
        return chunks, cached[1]
    corpus = [tokenize(c.content) for c in chunks]
    bm25 = BM25Plus(corpus)
    if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
        _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
    _INDEX_CACHE[key] = (fp, bm25)
    return chunks, bm25


def _hash_text(text: str) -> str:
    return hashlib.md5((text or "").encode("utf-8", "ignore")).hexdigest()


def _notes_fingerprint(rows: list) -> tuple:
    if not rows:
        return (0, 0, 0)
    stamps = [getattr(n, "updated_at", None) for n in rows]
    latest = max((s.timestamp() if hasattr(s, "timestamp") else 0) for s in stamps if s) if any(stamps) else 0
    return (len(rows), max(n.id for n in rows), round(latest, 3))


def _ensure_note_columns(db: Session) -> bool:
    """幂等为 chunks 表补 source_type / note_user_id / note_key 列（仅 sqlite）。"""
    try:
        cols = {r[1] for r in db.execute(text("PRAGMA table_info(chunks)")).fetchall()}
        changed = False
        for col, ddl in (("source_type", "TEXT DEFAULT 'document'"),
                         ("note_user_id", "INTEGER"),
                         ("note_key", "TEXT")):
            if col not in cols:
                db.execute(text("ALTER TABLE chunks ADD COLUMN %s %s" % (col, ddl)))
                changed = True
        if changed:
            db.commit()
        return True
    except Exception as e:
        log.warning("笔记统一索引列准备失败，回退到内存笔记语料: %s", e)
        return False


def _persist_note_chunks(db: Session, user_id: int, rows: list) -> bool:
    """D7：笔记正文切块写入 chunks（source_type='note'）。按指纹增量更新，失败仅告警。"""
    fp = _notes_fingerprint(rows)
    if _NOTE_PERSIST_CACHE.get(user_id) == fp:
        return True
    if not _ensure_note_columns(db):
        return False
    try:
        db.execute(text("DELETE FROM chunks WHERE source_type='note' AND note_user_id=:u"),
                   {"u": user_id})
        for n in rows:
            body = (n.content or n.summary or "").strip()
            if not body:
                continue
            for idx, piece in enumerate(chunk_text(body)):
                content = "【笔记】%s\n%s" % (n.title or "", piece)
                db.execute(text(
                    "INSERT INTO chunks(document_id,content,heading_path,page,chunk_index,"
                    "content_hash,source_type,note_user_id,note_key) "
                    "VALUES(0,:c,'',0,:i,:h,'note',:u,:k)"),
                    {"c": content, "i": idx, "h": _hash_text(content),
                     "u": user_id, "k": "%s-%s" % (n.id, idx)})
        db.commit()
        _NOTE_PERSIST_CACHE[user_id] = fp
        return True
    except Exception as e:
        log.warning("笔记块写入 chunks 失败（检索仍可用内存语料）: %s", e)
        try:
            db.rollback()
        except Exception:
            pass
        return False


def _note_hits(db: Session, user_id: int) -> list:
    """把用户笔记正文切块成统一检索单元（带 source_type='note'）。"""
    try:
        rows = list(db.scalars(select(Note).where(Note.user_id == user_id)
                               .order_by(Note.updated_at.desc()).limit(200)))
    except Exception as e:
        log.warning("notes load failed: %s", e)
        return []
    if not rows:
        return []
    _persist_note_chunks(db, user_id, rows)  # 物理入 chunks 表；失败不影响本次检索
    fp = _notes_fingerprint(rows)
    cached = _NOTE_CACHE.get(user_id)
    if cached and cached[0] == fp:
        return cached[1]
    hits = []
    for n in rows:
        body = (n.content or n.summary or "").strip()
        if not body:
            continue
        for idx, piece in enumerate(chunk_text(body)):
            content = "【笔记】%s\n%s" % (n.title or "", piece)
            hits.append(SimpleNamespace(
                id="note:%s:%s" % (n.id, idx),
                chunk_id="note-%s-%s" % (n.id, idx),
                content=content, page=0, ts_start=None, document_id=None,
                content_hash=_hash_text(content), source_type="note",
                note_title=n.title or "", bm25_score=0.0, vec_score=0.0))
    if len(_NOTE_CACHE) >= _INDEX_CACHE_MAX:
        _NOTE_CACHE.pop(next(iter(_NOTE_CACHE)))
    _NOTE_CACHE[user_id] = (fp, hits)
    return hits


def _as_hit(c) -> SimpleNamespace:
    """把 ORM Chunk / 笔记块统一成带双路分数字段的轻量对象。"""
    return SimpleNamespace(
        id=getattr(c, "id", 0),
        chunk_id=getattr(c, "chunk_id", str(getattr(c, "id", ""))),
        content=getattr(c, "content", "") or "",
        page=getattr(c, "page", 0) or 0,
        ts_start=getattr(c, "ts_start", None),
        document_id=getattr(c, "document_id", None),
        content_hash=getattr(c, "content_hash", "") or "",
        source_type=getattr(c, "source_type", "document") or "document",
        note_title=getattr(c, "note_title", "") or "",
        bm25_score=float(getattr(c, "bm25_score", 0.0) or 0.0),
        vec_score=float(getattr(c, "vec_score", 0.0) or 0.0))


def _key_of(hit) -> str:
    return "%s:%s" % (hit.source_type, hit.chunk_id)


def _fuse(hit) -> float:
    """双路分数融合：BM25 归一化(0~1) 与向量相似度(0~1) 等权。"""
    b = 1.0 - math.exp(-max(0.0, hit.bm25_score) / 3.0)
    v = max(0.0, min(1.0, hit.vec_score))
    return round(0.5 * b + 0.5 * v, 4)


def fused_confidence(hits: list, question: str) -> float:
    """D3/Q3：BM25 归一化 + 向量相似度 + 关键词覆盖率 → 单一 0~1 置信度。"""
    if not hits:
        return 0.0
    top_bm25 = max((h.bm25_score for h in hits), default=0.0)
    bm_norm = 1.0 - math.exp(-max(0.0, top_bm25) / 3.0)
    vec_sim = max((h.vec_score for h in hits), default=0.0)
    ctx = "\n".join(h.content for h in hits)
    toks = {t for t in tokenize(question) if len(t) >= 2}
    coverage = (sum(1 for t in toks if t in ctx) / len(toks)) if toks else 0.0
    conf = 0.35 * bm_norm + 0.35 * vec_sim + 0.30 * coverage
    return round(min(1.0, max(0.0, conf)), 2)


def retrieve(db: Session, user_id: int, question: str, document_id: int | None = None,
             top_k: int = 5) -> list[tuple]:
    """单查询召回（保留兼容）。索引已缓存，重复调用几乎零成本。"""
    chunks, bm25 = _get_index(db, user_id, document_id)
    if not chunks:
        return []
    scores = bm25.get_scores(tokenize(question))
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [(_as_hit(chunks[i]), float(scores[i])) for i in order if scores[i] > 0]


def retrieve_multi(db: Session, user_id: int, queries: list[str],
                   document_id: int | None = None, top_k: int = 5) -> list[tuple]:
    """BM25 Top20 + 向量 Top20 按 chunk_key 合并去重，统一重排后返回 top_k。

    VECTOR_ENABLED=false 时跳过向量路，退化为纯 BM25（行为与加向量前一致）。
    返回 (hit, fused_score)，hit 带 chunk_id/page/ts_start/source_type 等字段。
    """
    chunks, _ = _get_index(db, user_id, document_id)
    notes = [] if document_id else _note_hits(db, user_id)  # D7：限定文档时不掺笔记
    corpus = [_as_hit(c) for c in chunks] + notes
    cap = settings.RETRIEVAL_MAX_CHUNKS
    corpus = corpus[:cap]
    if not corpus:
        return []

    top = max(20, top_k * 2)
    # 合并语料的 BM25：无笔记时复用 _get_index 的进程内索引，有笔记时单独缓存一份
    if notes:
        key = (user_id, document_id or 0, "combined")
        fp = (len(corpus), _hash_text("|".join(h.content_hash for h in corpus)))
        cached = _INDEX_CACHE.get(key)
        if cached and cached[0] == fp:
            bm25 = cached[1]
        else:
            bm25 = BM25Plus([tokenize(h.content) for h in corpus])
            if len(_INDEX_CACHE) >= _INDEX_CACHE_MAX:
                _INDEX_CACHE.pop(next(iter(_INDEX_CACHE)))
            _INDEX_CACHE[key] = (fp, bm25)
    else:
        bm25 = _get_index(db, user_id, document_id)[1]

    merged: dict[str, object] = {}
    if bm25 is not None:
        for q in queries[:3]:
            scores = bm25.get_scores(tokenize(q))
            order = sorted(range(len(corpus)), key=lambda i: -scores[i])[:top]
            for i in order:
                s = float(scores[i])
                if s <= 0:
                    continue
                h = corpus[i]
                k = _key_of(h)
                prev = merged.get(k)
                if prev is None or s > prev.bm25_score:
                    nh = _as_hit(h)
                    nh.bm25_score = s
                    merged[k] = nh

    if vector_index.available():
        items = [{"key": _key_of(h), "text": h.content, "content_hash": h.content_hash,
                  "user_id": user_id, "document_id": h.document_id or 0,
                  "source_type": h.source_type} for h in corpus]
        vector_index.sync(items)  # 增量写入，content_hash 未变则跳过
        corpus_map = {_key_of(h): h for h in corpus}
        for q in queries[:2]:
            sims = vector_index.search(q, top, user_id, document_id)
            for k, sim in sims.items():
                base = merged.get(k) or corpus_map.get(k)
                if base is None:
                    continue
                nh = _as_hit(base)
                nh.vec_score = max(nh.vec_score, sim)
                merged[k] = nh

    ranked = sorted(merged.values(), key=lambda h: (_fuse(h), h.bm25_score), reverse=True)
    return [(h, _fuse(h)) for h in ranked[:top_k]]
