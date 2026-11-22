# -*- coding: utf-8 -*-
"""题库解析：抽取文本 → 分批交强档模型结构化（题干/选项/答案/五段解析）。"""
import os

from app.ai.prompts import QUESTION_BATCH_SYSTEM, question_batch_user
from app.ai.router import generate_json
from app.core.errors import APIError, ErrCode
from app.schemas.schemas import QuestionBatch

_BATCH_CHARS = 3000


def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        from app.services.parse import PyMuPDFParser
        return "\n".join(t for _, t in PyMuPDFParser().parse(path))
    if ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
                if cells:
                    lines.append(" | ".join(cells))
        wb.close()
        return "\n".join(lines)
    if ext == ".docx":
        import docx
        d = docx.Document(path)
        parts = [p.text.strip() for p in d.paragraphs if p.text.strip()]
        for tb in d.tables:
            for row in tb.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)
    if ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    raise APIError(ErrCode.FILE_002, f"题库暂不支持 {ext}（支持 pdf/xlsx/docx/txt）")


async def parse_questions(text: str, max_questions: int = 20, on_progress=None) -> list:
    text = (text or "").strip()
    if not text:
        raise APIError(ErrCode.PARSE_002, "题库文本为空")
    batches = [text[i:i + _BATCH_CHARS] for i in range(0, len(text), _BATCH_CHARS)][:6]
    out = []
    for bi, b in enumerate(batches):
        if on_progress:
            on_progress(int(40 + 50 * (bi + 1) / max(1, len(batches))))
        try:
            obj, _ = await generate_json("strong", QUESTION_BATCH_SYSTEM, question_batch_user(b), QuestionBatch)
        except APIError:
            continue
        out.extend(obj.questions)
        if len(out) >= max_questions:
            break
    return out[:max_questions]
