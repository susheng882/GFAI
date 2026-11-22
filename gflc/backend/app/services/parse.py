# -*- coding: utf-8 -*-
"""PDF 解析适配器：PyMuPDF 为主（轻、快），MinerU 为可选（质量优先，重）。
统一返回 [(页码, 文本)]，供切片使用。"""
from pathlib import Path

from app.core.errors import APIError, ErrCode

# 一页抽取文本低于该字数，视为疑似扫描页（P0 只标记，OCR 进 V1.5）
_MIN_TEXT_PER_PAGE = 20


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
            for i, page in enumerate(doc, start=1):
                pages.append((i, (page.get_text("text") or "").strip()))
            doc.close()
        except Exception as e:
            raise APIError(ErrCode.PARSE_001, f"PDF 无法读取：{e}") from e
        if not any(len(t) >= _MIN_TEXT_PER_PAGE for _, t in pages):
            raise APIError(ErrCode.PARSE_002, "PDF 暂无可抽取文本（疑似扫描件，OCR 属 V1.5）")
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
