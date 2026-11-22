# -*- coding: utf-8 -*-
"""检索（P0）：jieba 分词 + BM25 关键词召回，限定当前用户/文档。

提速改造（2026-11-22）：
- 进程内缓存「BM25 索引」，同一批语料只分词/建模一次，指纹变化自动失效；
- 新增 retrieve_multi：一次建索引、多条改写查询分别打分后按块去重合并，
  替代原来「每条查询各建一次全量索引」的 O(3N) 浪费。
向量检索接口预留：后续可在此加 pgvector/本地 embedding。
"""
import jieba
from rank_bm25 import BM25Plus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Chunk, Document

jieba.setLogLevel(20)

# 进程内索引缓存：key=(user_id, document_id or 0) -> (fingerprint, bm25)
_INDEX_CACHE: dict[tuple, tuple] = {}
_INDEX_CACHE_MAX = 64


def tokenize(text: str) -> list[str]:
    return [w.strip() for w in jieba.cut(text or "") if w.strip()]


def _chunk_stmt(user_id: int, document_id: int | None):
    stmt = select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user_id)
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
    return stmt.limit(800)


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
    chunks = list(db.scalars(_chunk_stmt(user_id, document_id)))
    if not chunks:
        return [], None
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


def retrieve(db: Session, user_id: int, question: str, document_id: int | None = None,
             top_k: int = 5) -> list[tuple[Chunk, float]]:
    """单查询召回（保留兼容）。索引已缓存，重复调用几乎零成本。"""
    chunks, bm25 = _get_index(db, user_id, document_id)
    if not chunks:
        return []
    scores = bm25.get_scores(tokenize(question))
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [(chunks[i], float(scores[i])) for i in order if scores[i] > 0]


def retrieve_multi(db: Session, user_id: int, queries: list[str],
                   document_id: int | None = None, top_k: int = 5) -> list[tuple[Chunk, float]]:
    """多查询召回：只建一次索引，逐条 query 打分后按块 id 取最高分去重合并。"""
    chunks, bm25 = _get_index(db, user_id, document_id)
    if not chunks:
        return []
    merged: dict[int, tuple[Chunk, float]] = {}
    for q in queries[:3]:
        scores = bm25.get_scores(tokenize(q))
        order = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
        for i in order:
            s = float(scores[i])
            if s <= 0:
                continue
            cid = chunks[i].id
            if cid not in merged or s > merged[cid][1]:
                merged[cid] = (chunks[i], s)
    return [v for _, v in sorted(merged.items(), key=lambda kv: -kv[1][1])[:top_k]]
