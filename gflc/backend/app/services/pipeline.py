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
                        stats: dict | None = None, on_progress=None) -> int:
    """解析并入库；stats 为可选出参，带回 OCR 页数/失败页等元信息。

    on_progress(done, total, stage) 为可选的进度回调（用于任务进度条「不卡在某个值」）：
    - stage="ocr"：扫描件逐页识别，done/total 为已完成页数/总页数；
    - stage="text"：文字层解析完成，进入分块前给一次；
    - stage="chunk"：分块与入库阶段给一次。
    回调异常只记日志，不允许影响解析主链路。
    """
    def _emit(done: int, total: int, stage: str) -> None:
        if not on_progress:
            return
        try:
            on_progress(int(done), int(total), stage)
        except Exception:  # noqa: BLE001 进度回调失败不能拖垮解析
            _log.warning("解析进度回调失败（document_id=%s）", doc.id, exc_info=True)

    from app.services.parse import parser_for
    ext = os.path.splitext(str(local_path))[1].lower()
    # PDF 走可配置引擎（mineru 可选）；Word/MD/TXT 走各自解析器
    parser = get_parser(settings.PDF_ENGINE) if ext == ".pdf" else parser_for(local_path)
    try:
        pages = parser.parse(local_path)
        if stats is not None:
            stats["parse_mode"] = "text"
        # 文字层有效性检查：扫描版 PDF 常带一层「只有水印」的文字层
        # （实测某教材 20 页共 284 字，全是「公众号 XX 免费分享」），
        # 这类不抛 NoTextLayerError 就会被当有效文本，chunk 全为水印、卡片必然 0 产出。
        if ext == ".pdf" and pages:
            # pages 是 [(页码, 文本)] 结构（见 parse.py），取元组第二项；
            # 兼容万一传入纯字符串列表的调用方。
            def _page_text(p) -> str:
                return (p[1] if isinstance(p, tuple) and len(p) >= 2 else p) or ""

            avg_chars = sum(len(_page_text(p)) for p in pages) / max(1, len(pages))
            min_chars = int(os.getenv("OCR_MIN_PAGE_CHARS", "80"))
            if avg_chars < min_chars:
                _log.info("文字层平均每页仅 %.0f 字（阈值 %d），判定为无有效文字层，切视觉 OCR"
                          "（document_id=%s）", avg_chars, min_chars, doc.id)
                if stats is not None:
                    stats["text_layer_avg_chars"] = round(avg_chars, 1)
                from app.core.errors import ErrCode
                raise NoTextLayerError(
                    ErrCode.PARSE_002,
                    f"文字层内容过少（平均每页约 {avg_chars:.0f} 字），按扫描件处理")
        _emit(1, 1, "text")
    except NoTextLayerError as e:
        # 扫描件无文字层：自动切视觉 OCR，识别文本回灌同一分块/入库链路。
        # OCR_ENABLED=0 时保留原 PARSE-002 失败契约；非 PDF 不会走这条路。
        if ext != ".pdf" or os.getenv("OCR_ENABLED", "1").strip().lower() not in ("1", "true", "yes"):
            raise
        _log.info("PDF 无文字层，切换视觉 OCR 兜底（document_id=%s）：%s", doc.id, e.message)
        from app.services.question_vision import ocr_pdf_to_pages
        pages = asyncio.run(ocr_pdf_to_pages(
            str(local_path), document_id=doc.id, stats=stats,
            on_progress=(lambda done, total: _emit(done, total, "ocr")) if on_progress else None,
            # 视觉 OCR 记账：按文档归属用户写入 cost_ledger（token/花费统计才有源）
            user_id=doc.user_id,
        ))
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
    _emit(1, 1, "chunk")

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
