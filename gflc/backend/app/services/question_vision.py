# -*- coding: utf-8 -*-
"""试卷视觉解析：PDF 逐页渲染 → 多模态识别 → 结构化题目（含 LaTeX）。
解决「文本层公式丢失导致题目残破」的问题。"""
import base64

import pymupdf

from app.ai.deepseek import chat, extract_json
from app.core.config import settings

PROMPT = """这是考研试卷的一页。识别其中所有题目，数学公式用 LaTeX（$...$）。
输出 JSON：
{"paper_meta":{"subject":"考研数学/英语/政治/专业课等","title":""},
 "questions":[{"no":"1","section":"选择题|填空题|解答题","chapter":"高等数学|线性代数|概率论与数理统计|其他","stem":"","options":["A. ...","B. ...","C. ...","D. ..."],"answer":""}]}
要求：
- 题干完整，公式必须用 LaTeX 还原，不要丢失
- 选择题给 4 个选项；填空题/解答题 options 为空数组
- answer 只填试卷中明确印出的答案；没有就留空，禁止编造
- 卷首说明、分值表、答题提示不是题目，不要放进 questions
- chapter 按题目知识点判断（数学卷：高数/线代/概率）
只输出 JSON，不要解释。"""


def render_pages(path: str, dpi: int = 140) -> list[bytes]:
    doc = pymupdf.open(path)
    out = []
    for pg in doc:
        out.append(pg.get_pixmap(dpi=dpi).tobytes("png"))
    doc.close()
    return out


async def extract_page(png: bytes) -> dict:
    b64 = base64.b64encode(png).decode()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}},
    ]}]
    res = await chat(settings.LLM_LIGHT_MODEL, messages, temperature=0,
                     max_tokens=16000, json_mode=False, effort="low")
    return extract_json(res.text)


async def parse_paper(path: str, on_progress=None) -> dict:
    pages = render_pages(path)
    questions: list[dict] = []
    meta: dict = {}
    for i, png in enumerate(pages):
        if on_progress:
            on_progress(int(5 + 85 * (i + 1) / max(1, len(pages))))
        try:
            data = await extract_page(png)
        except Exception:
            continue
        if not meta and data.get("paper_meta"):
            meta = data.get("paper_meta") or {}
        for q in data.get("questions", []) or []:
            q["page"] = i + 1
            questions.append(q)
    return {"meta": meta, "questions": questions, "pages": len(pages)}
