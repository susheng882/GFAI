# -*- coding: utf-8 -*-
"""实体一致性校验（S3/Q2，幻觉治理第三层）。

从答案里抽取「数值 / 专有名词」，与所引 chunk 原文比对：
- 不一致时记录「不一致实体」日志，并在响应里新增 suspect_entities 字段 + 标注存疑；
- QA_ENTITY_STRICT=true 时直接改为拒答（默认关闭，避免误伤，保证既有行为稳定）。

本模块是纯函数集合，不依赖数据库与模型，便于独立自测。
"""
import logging
import os
import re

log = logging.getLogger(__name__)

# 只抽取「带量纲/小数/大数」的数值，跳过「1、2、3」这类枚举序号噪声
_NUMBER = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?\s*(?:[%％‰]|年|月|日|小时|分钟|秒|次|倍|元|万|亿|"
    r"章|节|页|分|度|℃|kg|km|cm|mm|m|s|W))", re.I)
_BRACKET_TERM = re.compile(r"[《「『【\"“]([^》」』】\"”\n]{2,40})[》」』】\"”]")
_EN_TERM = re.compile(r"\b[A-Z][A-Za-z][A-Za-z0-9_-]{1,30}\b|\b[A-Z]{2,10}\b")
_EN_STOP = {"The", "This", "That", "These", "Those", "However", "Therefore",
            "Moreover", "And", "But", "For", "From", "With", "Hence", "Thus"}


def strict_mode() -> bool:
    return os.getenv("QA_ENTITY_STRICT", "false").strip().lower() in ("1", "true", "yes", "on")


def extract(answer: str | None) -> dict[str, list[str]]:
    """抽取答案中的数值与专名（去重，保持出现顺序）。"""
    text = answer or ""
    numbers: list[str] = []
    for m in _NUMBER.finditer(text):
        v = re.sub(r"\s+", "", m.group(1))
        if v not in numbers:
            numbers.append(v)
    terms: list[str] = []
    for m in _BRACKET_TERM.finditer(text):
        v = m.group(1).strip()
        if len(v) >= 2 and v not in terms:
            terms.append(v)
    for m in _EN_TERM.finditer(text):
        v = m.group(0)
        if v in _EN_STOP or v in terms:
            continue
        terms.append(v)
    return {"numbers": numbers, "terms": terms}


def check(answer: str | None, source_texts: list[str], question: str = "") -> list[dict]:
    """比对答案实体与引用原文，返回不一致实体列表。

    每个元素形如 {"type": "number"/"term", "value": "..."}。
    问题里本身出现的实体不视为幻觉（用户提供的条件）。
    """
    entities = extract(answer)
    src = "\n".join(t or "" for t in (source_texts or []))
    q = question or ""
    suspects: list[dict] = []
    for kind, values in entities.items():
        for v in values:
            if v in src or v in q:
                continue
            suspects.append({"type": kind, "value": v})
    return suspects


def apply(answer: str, hits: list, question: str = "",
          user_id: int | None = None) -> tuple[str, list[dict], bool]:
    """把实体校验结果应用到答案：返回 (answer_out, suspects, refused)。

    hits 为带 .content 属性的检索块（Chunk 或 SimpleNamespace 均可）。
    """
    sources = [getattr(h, "content", "") or "" for h in (hits or [])]
    suspects = check(answer, sources, question)
    if not suspects:
        return answer, [], False

    values = "、".join(s["value"] for s in suspects[:8])
    log.warning("不一致实体: user=%s count=%s values=%s", user_id, len(suspects), values[:200])

    if strict_mode():
        return ("模型答案中的部分数值/专名未见于引用资料，已拒绝回答并标记为存疑，请核对原文或换用联网检索。",
                suspects, True)

    mark = ("（存疑：以下数值/专名未在引用资料中找到，请核对来源：%s）\n" % values)
    return mark + answer, suspects, False


def describe(suspects: list[dict]) -> str:
    """给前端展示用的可读文案。"""
    if not suspects:
        return ""
    return "检测到 %d 处不一致实体：%s" % (
        len(suspects), "、".join(s["value"] for s in suspects[:8]))
