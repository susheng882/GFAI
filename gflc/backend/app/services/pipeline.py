# -*- coding: utf-8 -*-
"""解析管线：读文件 → 解析 → 切块 → 写 chunks → 标就绪。"""
import asyncio
import hashlib
import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import Chunk, Document
from app.services.chunking import chunk_pages
from app.services.parse import NoTextLayerError, get_parser

_log = logging.getLogger(__name__)


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_pdf_to_chunks(db: Session, doc: Document, local_path: str | Path,
                        stats: dict | None = None) -> int:
    """解析并入库；stats 为可选出参，带回 OCR 页数/失败页等元信息。"""
    from app.services.parse import parser_for
    ext = os.path.splitext(str(local_path))[1].lower()
    # PDF 走可配置引擎（mineru 可选）；Word/MD/TXT 走各自解析器
    parser = get_parser(settings.PDF_ENGINE) if ext == ".pdf" else parser_for(local_path)
    try:
        pages = parser.parse(local_path)
        if stats is not None:
            stats["parse_mode"] = "text"
    except NoTextLayerError as e:
        # 扫描件无文字层：自动切视觉 OCR，识别文本回灌同一分块/入库链路。
        # OCR_ENABLED=0 时保留原 PARSE-002 失败契约；非 PDF 不会走这条路。
        if ext != ".pdf" or os.getenv("OCR_ENABLED", "1").strip().lower() not in ("1", "true", "yes"):
            raise
        _log.info("PDF 无文字层，切换视觉 OCR 兜底（document_id=%s）：%s", doc.id, e.message)
        from app.services.question_vision import ocr_pdf_to_pages
        pages = asyncio.run(ocr_pdf_to_pages(str(local_path), document_id=doc.id, stats=stats))
        _log.info("视觉 OCR 兜底产出 %s 页（document_id=%s）", len(pages), doc.id)
    # B2 去噪：页眉页脚/页码/水印不进知识库（否则检索会召回一堆废话）
    if getattr(settings, "PARSE_DENOISE", True):
        from app.services.parse import denoise_pages
        pages = denoise_pages(pages)
    chunks = chunk_pages(pages)
    if not chunks:
        from app.core.errors import APIError, ErrCode
        _log.error("解析后切分结果为空（document_id=%s，%s 页无可入库文本），不写 ready",
                   doc.id, len(pages))
        raise APIError(ErrCode.PARSE_003,
                       f"切分结果为空（document_id={doc.id}，{len(pages)} 页无可入库文本）")

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
