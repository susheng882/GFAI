# -*- coding: utf-8 -*-
"""语义切片：按标题/段落切，目标块长 300 字、重叠 100、单段超 800 触发二次切。
纯函数，便于单测；不做任何模型调用。"""
import os
import re

from app.core.config import settings

# 章节标题（中文常见写法）
_HEADING_RE = re.compile(r"^\s*(第[一二三四五六七八九十百零\d]+[章节讲部分]|[一二三四五六七八九十]+[、.]|\d+(\.\d+)*[ 、.])\s*\S+")
_SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])\s*")

# 公式原子化（28 号报告 Q10）：$...$ 作为不可拆单元。
# 分句时先把公式替换成占位符，避免 LaTeX 中的分号/句号把公式切断；还原后再打包。
_FORMULA_RE = re.compile(r"\$[^$\n]*\$")
_SLOT_RE = re.compile(r"\ue000(\d+)\ue001")


def _split_sentences(text: str) -> list[str]:
    slots: list[str] = []

    def _stash(m: re.Match) -> str:
        slots.append(m.group(0))
        return "\ue000%d\ue001" % (len(slots) - 1)

    masked = _FORMULA_RE.sub(_stash, text)

    def _restore(part: str) -> str:
        return _SLOT_RE.sub(lambda m: slots[int(m.group(1))], part)

    parts = [_restore(p.strip()) for p in _SENT_SPLIT.split(masked) if p.strip()]
    return parts or [text.strip()]


def _safe_tail(text: str, overlap: int) -> str:
    """取末尾 overlap 字作重叠；切点若落在 $...$ 公式内部则前移到公式起点，保证公式原子。"""
    if overlap <= 0:
        return ""
    start = max(0, len(text) - overlap)
    for m in _FORMULA_RE.finditer(text):
        if m.start() < start < m.end():
            start = m.start()  # 把整条公式纳入下一块的头部（重叠略大于 overlap，可接受）
            break
    return text[start:]


def _pack(units: list[str], size: int, overlap: int) -> list[str]:
    """把句子/段落跨段打包成约 size 字的块，块间保留 overlap 字重叠。

    units 整体append、不从中途切断；重叠尾巴经 _safe_tail 保护，避免 $...$ 被切两半。
    """
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for u in units:
        if cur and cur_len + len(u) > size:
            text = "\n".join(cur).strip()
            chunks.append(text)
            tail = _safe_tail(text, overlap)
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
    """按页切块，返回带页码溯源的块列表。

    OCR_CHUNK_SIZE>0 时，对含公式（$...$）的页临时放大块长，进一步降低公式被跨块切开的风险；
    0 表示沿用 CHUNK_SIZE。注：若需严格按「OCR 来源」而非「含公式」判定，
    需要 pipeline.py 在调用 chunk_pages 时传入 parse_mode（本轮不在本 Agent 文件所有权内）。
    """
    out: list[dict] = []
    idx = 0
    ocr_size = int(os.getenv("OCR_CHUNK_SIZE", "0") or 0)
    for page_no, text in pages:
        page_size = ocr_size if ocr_size > 0 and "$" in text else size
        for c in chunk_text(text, size=page_size, overlap=overlap):
            out.append({"content": c, "page": page_no, "chunk_index": idx, "heading_path": ""})
            idx += 1
    return out
