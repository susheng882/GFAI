# -*- coding: utf-8 -*-
"""解析管线：读文件 → 解析 → 切块 → 写 chunks → 标就绪。"""
import hashlib
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Chunk, Document
from app.services.chunking import chunk_pages
from app.services.parse import get_parser


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pdf_to_chunks(db: Session, doc: Document, local_path: str | Path) -> int:
    pages = get_parser(settings.PDF_ENGINE).parse(local_path)
    chunks = chunk_pages(pages)
    if not chunks:
        from app.core.errors import APIError, ErrCode
        raise APIError(ErrCode.PARSE_003, "切分结果为空")

    for c in chunks:
        db.add(Chunk(
            document_id=doc.id,
            content=c["content"],
            heading_path=c["heading_path"],
            page=c["page"],
            chunk_index=c["chunk_index"],
            content_hash=hashlib.sha256(c["content"].encode("utf-8")).hexdigest(),
        ))
    doc.status = "ready"
    db.commit()
    return len(chunks)
