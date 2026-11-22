# -*- coding: utf-8 -*-
"""检索（P0）：jieba 分词 + BM25 关键词召回，限定当前用户/文档。
向量检索接口预留：后续可在此加 pgvector/本地 embedding。"""
import jieba
from rank_bm25 import BM25Plus
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Chunk, Document

jieba.setLogLevel(20)


def tokenize(text: str) -> list[str]:
    return [w.strip() for w in jieba.cut(text or "") if w.strip()]


def retrieve(db: Session, user_id: int, question: str, document_id: int | None = None,
             top_k: int = 5) -> list[tuple[Chunk, float]]:
    stmt = select(Chunk).join(Document, Chunk.document_id == Document.id).where(Document.user_id == user_id)
    if document_id:
        stmt = stmt.where(Chunk.document_id == document_id)
    chunks = list(db.scalars(stmt.limit(800)))
    if not chunks:
        return []
    corpus = [tokenize(c.content) for c in chunks]
    bm25 = BM25Plus(corpus)
    scores = bm25.get_scores(tokenize(question))
    order = sorted(range(len(chunks)), key=lambda i: -scores[i])[:top_k]
    return [(chunks[i], float(scores[i])) for i in order if scores[i] > 0]
