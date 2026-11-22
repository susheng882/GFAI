# -*- coding: utf-8 -*-
"""语义切片：按标题/段落切，目标块长 300 字、重叠 100、单段超 800 触发二次切。
纯函数，便于单测；不做任何模型调用。"""
import re

from app.core.config import settings

# 章节标题（中文常见写法）
_HEADING_RE = re.compile(r"^\s*(第[一二三四五六七八九十百零\d]+[章节讲部分]|[一二三四五六七八九十]+[、.]|\d+(\.\d+)*[ 、.])\s*\S+")
_SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])\s*")


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts or [text.strip()]


def _pack(units: list[str], size: int, overlap: int) -> list[str]:
    """把句子/段落跨段打包成约 size 字的块，块间保留 overlap 字重叠。"""
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for u in units:
        if cur and cur_len + len(u) > size:
            text = "\n".join(cur).strip()
            chunks.append(text)
            tail = text[-overlap:] if overlap > 0 else ""
            cur = [tail] if tail else []
            cur_len = len(tail)
        cur.append(u)
        cur_len += len(u)
    if cur:
        chunks.append("\n".join(cur).strip())
    return [c for c in chunks if c]


def chunk_text(text: str, *, size: int | None = None, overlap: int | None = None,
               paragraph_threshold: int | None = None) -> list[str]:
    """把一段文本切成检索单元。"""
    size = size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    threshold = paragraph_threshold or settings.PARAGRAPH_SPLIT_THRESHOLD

    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []

    chunks: list[str] = []
    # 先按空行/换行分段落，再统一跨段打包到目标块长（避免每段都碎成一块）
    paragraphs = [p.strip() for p in re.split(r"\n{1,}", text) if p.strip()]
    units: list[str] = []
    for para in paragraphs:
        if len(para) > threshold:
            units.extend(_split_sentences(para))
        else:
            units.append(para)
    chunks = _pack(units, size, overlap)
    return chunks


def chunk_pages(pages: list[tuple[int, str]], *, size: int | None = None,
                overlap: int | None = None) -> list[dict]:
    """按页切块，返回带页码溯源的块列表。"""
    out: list[dict] = []
    idx = 0
    for page_no, text in pages:
        for c in chunk_text(text, size=size, overlap=overlap):
            out.append({"content": c, "page": page_no, "chunk_index": idx, "heading_path": ""})
            idx += 1
    return out
