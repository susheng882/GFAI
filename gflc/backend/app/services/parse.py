# -*- coding: utf-8 -*-
"""PDF 解析适配器：PyMuPDF 为主（轻、快），MinerU 为可选（质量优先，重）。
统一返回 [(页码, 文本)]，供切片使用。"""
import re
from pathlib import Path

from app.core.errors import APIError, ErrCode

# 一页抽取文本低于该字数，视为疑似扫描页；全文都低于阈值即判定「无文字层」
_MIN_TEXT_PER_PAGE = 20


class NoTextLayerError(APIError):
    """PDF 无文字层（扫描件）专用信号。

    继承 APIError 保证未启用 OCR 兜底时仍是原有 PARSE-002 契约；
    解析管线捕获后自动切换视觉 OCR，识别文本回灌同一分块/入库链路。
    """

    pass


class ParserAdapter:
    name = "base"

    def parse(self, path: str | Path) -> list[tuple[int, str]]:  # pragma: no cover - 接口
        raise NotImplementedError


class PyMuPDFParser(ParserAdapter):
    name = "pymupdf"

    def parse(self, path: str | Path) -> list[tuple[int, str]]:
        try:
            import pymupdf as fitz  # PyMuPDF ≥1.24 推荐入口
        except ImportError:
            try:
                import fitz  # 旧版兼容
            except ImportError as e:
                raise APIError(ErrCode.PARSE_001, "未安装 PyMuPDF，请 pip install pymupdf") from e
        pages: list[tuple[int, str]] = []
        try:
            doc = fitz.open(str(path))
            try:
                if doc.page_count == 0:
                    raise APIError(ErrCode.PARSE_002, "PDF 为空（0 页），无可解析内容")
                for i, page in enumerate(doc, start=1):
                    pages.append((i, (page.get_text("text") or "").strip()))
            finally:
                doc.close()
        except APIError:
            raise
        except Exception as e:
            raise APIError(ErrCode.PARSE_001, f"PDF 无法读取：{e}") from e
        if not any(len(t) >= _MIN_TEXT_PER_PAGE for _, t in pages):
            raise NoTextLayerError(
                ErrCode.PARSE_002,
                f"PDF 无文字层（{len(pages)} 页，疑似扫描件），已切换视觉 OCR 兜底",
            )
        return pages


class MinerUParser(ParserAdapter):
    """调用 mineru CLI：mineru -p input.pdf -o outdir -b pipeline，读回 markdown。"""
    name = "mineru"

    def parse(self, path: str | Path) -> list[tuple[int, str]]:  # pragma: no cover - 需外部依赖
        import subprocess
        import tempfile

        src = Path(path)
        outdir = Path(tempfile.mkdtemp(prefix="mineru_"))
        try:
            subprocess.run(["mineru", "-p", str(src), "-o", str(outdir), "-b", "pipeline"],
                           check=True, capture_output=True, timeout=600)
        except FileNotFoundError as e:
            raise APIError(ErrCode.PARSE_001, "未安装 mineru，可改用 PyMuPDF 引擎") from e
        except subprocess.CalledProcessError as e:
            raise APIError(ErrCode.PARSE_003, f"MinerU 解析失败：{e.stderr[-300:] if e.stderr else ''}") from e
        md_files = list(outdir.rglob("*.md"))
        if not md_files:
            raise APIError(ErrCode.PARSE_003, "MinerU 未产出 markdown")
        text = md_files[0].read_text(encoding="utf-8", errors="ignore")
        # MinerU 输出整篇 markdown，按页号不可得时统一记第 1 页的连续文本
        return [(1, text)]


def get_parser(engine: str | None = None) -> ParserAdapter:
    engine = (engine or "pymupdf").lower()
    if engine == "mineru":
        return MinerUParser()
    return PyMuPDFParser()

class DocxParser(ParserAdapter):
    """Word 解析：按段落读，Heading 样式进 heading_path，页码用「段序」近似。"""
    name = "docx"

    def parse(self, path):
        try:
            import docx
        except ImportError as e:
            raise APIError(ErrCode.PARSE_001, "未安装 python-docx") from e
        try:
            d = docx.Document(str(path))
        except Exception as e:
            raise APIError(ErrCode.PARSE_001, f"Word 无法读取：{e}") from e
        pages, buf, page = [], [], 1
        for p in d.paragraphs:
            text = (p.text or "").strip()
            if not text:
                continue
            style = (getattr(p.style, "name", "") or "").lower()
            if style.startswith("heading") or style.startswith("标题"):
                if buf:
                    pages.append((page, "\n".join(buf)))
                    buf, page = [], page + 1
                buf.append(f"[{text}]")  # 标题用方括号标记，交给分块器识别层级
            else:
                buf.append(text)
        if buf:
            pages.append((page, "\n".join(buf)))
        if not pages:
            raise APIError(ErrCode.PARSE_002, "Word 文档没有可读文本")
        return pages


class MarkdownParser(ParserAdapter):
    """Markdown / TXT：按一级/二级标题切段，标题保留原样（带 #）。"""
    name = "markdown"

    def parse(self, path):
        try:
            with open(str(path), "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
        except OSError as e:
            raise APIError(ErrCode.PARSE_001, f"文件读取失败：{e}") from e
        if not raw.strip():
            raise APIError(ErrCode.PARSE_002, "文件内容为空")
        pages, buf, page = [], [], 1
        for line in raw.splitlines():
            if re.match(r"^#{1,3}\s+", line):
                if buf:
                    pages.append((page, "\n".join(buf)))
                    buf, page = [], page + 1
                buf.append(line.strip())
            else:
                buf.append(line)
        if buf:
            pages.append((page, "\n".join(buf)))
        return pages


_EXT_PARSERS = {
    ".pdf": PyMuPDFParser,
    ".docx": DocxParser,
    ".md": MarkdownParser,
    ".markdown": MarkdownParser,
    ".txt": MarkdownParser,
}


def parser_for(path) -> ParserAdapter:
    """按扩展名选解析器：PDF → PyMuPDF，Word → python-docx，MD/TXT → 标题切段。"""
    import os
    ext = os.path.splitext(str(path))[1].lower()
    cls = _EXT_PARSERS.get(ext)
    if cls is None:
        raise APIError(ErrCode.PARSE_001, f"不支持的格式：{ext or '未知'}")
    return cls()

# ---------- 去噪（B2）：页眉/页脚/页码/水印 ----------
_NOISE_LINE = re.compile(
    r"^\s*(?:[-—·•]?\s*\d{1,3}\s*[-—·•]?|第\s*\d+\s*(?:页|/\s*\d+)|"
    r"\d+\s*/\s*\d+|机密|内部资料|仅供.{0,6}使用|版权所有.{0,20}|confidential)\s*$",
    re.I)


def denoise_pages(pages: list[tuple[int, str]], *, repeat_ratio: float = 0.6) -> list[tuple[int, str]]:
    """去掉页眉页脚、页码、水印这类“每页重复的废话”。

    只看每页的**首尾各 2 行**作为页眉页脚候选（正文中间不会被误杀），
    归一化页码后统计重复次数；再按正则删纯页码/水印行。
    """
    if not pages:
        return pages
    total = len(pages)

    def _key(line: str) -> str:
        return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line)).strip()

    counter: dict[str, int] = {}
    for _, text in pages:
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        cand = set(lines[:2]) | set(lines[-2:]) if len(lines) > 2 else set(lines)
        for ln in {_key(x) for x in cand}:
            counter[ln] = counter.get(ln, 0) + 1

    threshold = max(3, int(total * repeat_ratio))
    repeated = {k for k, v in counter.items() if v >= threshold and len(k) < 40}

    out: list[tuple[int, str]] = []
    dropped = 0
    for page, text in pages:
        lines = [x for x in text.splitlines() if x.strip()]
        edge = set(range(min(2, len(lines)))) | set(range(max(0, len(lines) - 2), len(lines)))
        kept = []
        for i, ln in enumerate(lines):
            t = ln.strip()
            is_edge = i in edge
            if (is_edge and _key(t) in repeated) or _NOISE_LINE.match(t):
                dropped += 1
                continue
            kept.append(ln.rstrip())
        out.append((page, "\n".join(kept)))
    if dropped:
        import logging
        logging.getLogger(__name__).info("去噪：丢弃 %s 行页眉页脚/页码（%s 页）", dropped, total)
    return out
