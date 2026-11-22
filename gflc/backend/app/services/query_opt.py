# -*- coding: utf-8 -*-
"""检索查询优化：查询改写（含领域限定）+ 语义重排。

设计原则：
- 每个函数都自带兜底，失败绝不抛异常，主流程降级即可；
- 批量一次调用（n 个片段拼进一个 prompt），不逐条调模型；
- 同问题 10 分钟内复用改写结果（进程内缓存）。
"""
import asyncio
import logging
import re
import time

from app.ai.deepseek import chat, extract_json
from app.ai.prompts import (QUERY_REWRITE_SYSTEM, RERANK_SYSTEM, query_rewrite_user,
                            rerank_user)
from app.core.config import settings

log = logging.getLogger(__name__)

RELEVANT_SCORE = 3.0      # 重排得分 >= 3 视为相关
_REWRITE_TIMEOUT = 8.0    # 改写超过 8s 直接放弃
_RERANK_TIMEOUT = 6.5    # 重排超时放弃（返回全 0）
_TTL = 600                # 改写结果 10 分钟内复用
_CACHE_MAX = 256
_MAX_QUERIES = 3

_cache: dict[str, tuple[float, list[str]]] = {}
_STOP = re.compile(r"(有什么|是什么|为什么|怎么样|怎么|如何|请问|能不能|可以吗|哪些|哪几种|吗|呢|嘛|\?|？|。|，|,)")
# 模型可能因为「why」写得过长把 JSON 截断，这里做一次宽松兜底解析
_SCORE_PAIR = re.compile(r'"i"\s*:\s*(\d+)\s*,\s*"score"\s*:\s*(-?\d+(?:\.\d+)?)')
_JSON_STR = re.compile(r'"([^"\\]{2,80})"')


def _cache_get(key: str) -> list[str] | None:
    item = _cache.get(key)
    if not item:
        return None
    ts, val = item
    if time.time() - ts > _TTL:
        _cache.pop(key, None)
        return None
    return val


def _cache_put(key: str, val: list[str]) -> None:
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()
    _cache[key] = (time.time(), val)


def _rule_rewrite(question: str, domain_words: list[str] | None = None) -> list[str]:
    """零成本的规则改写：去疑问词 + 拼领域词，作为模型改写失败时的兜底。"""
    q = (question or "").strip()
    if not q:
        return []
    out: list[str] = [q]
    core = re.sub(r"\s+", " ", _STOP.sub(" ", q)).strip()
    if core and core != q and len(core) >= 2:
        out.append(core)
    words = [w.strip() for w in (domain_words or []) if w and w.strip()][:3]
    if words:
        out.append(f"{out[-1]} {' '.join(words)}")
    return out[:_MAX_QUERIES]


def rewrite_with_domain(question: str, domain_words: list[str] | None = None) -> list[str]:
    """规则化改写（同步、零模型调用），保留给不需要消歧的场景。"""
    return _rule_rewrite(question, domain_words)


async def rewrite(question: str, domain_words: list[str] | None = None) -> list[str]:
    """把口语问题改写成 2–3 条带领域限定的检索查询（模型改写 + 规则兜底）。

    失败/超时（>8s）返回规则改写结果；永远不抛异常。
    """
    q = (question or "").strip()
    if not q:
        return []

    key = q + "|" + ",".join((domain_words or [])[:2])
    cached = _cache_get(key)
    if cached:
        return list(cached)

    user_text = query_rewrite_user(q)
    words = [w for w in (domain_words or []) if w and w.strip()][:3]
    if words:
        user_text += f"\n本用户资料所属领域（可用于限定）：{' '.join(words)}"

    try:
        res = await asyncio.wait_for(
            chat(settings.LLM_LIGHT_MODEL,
                 [{"role": "system", "content": QUERY_REWRITE_SYSTEM},
                  {"role": "user", "content": user_text}],
                 temperature=0.1, max_tokens=700, json_mode=True),
            timeout=_REWRITE_TIMEOUT)
        text = res.text or ""
        try:
            raw = extract_json(text).get("queries")
            items = [str(x).strip() for x in raw if isinstance(x, str)] if isinstance(raw, list) else []
        except Exception:
            items = [s.strip() for s in _JSON_STR.findall(text) if s.strip() != "queries"]
        out: list[str] = []
        for s in items:
            if 2 <= len(s) <= 80 and s not in out:
                out.append(s)
        if not out:
            return _rule_rewrite(q, domain_words)
        out = out[:2]           # 留一个位置给原问题，总数不超过 3
        if q not in out:
            out.append(q)
        out = out[:_MAX_QUERIES]
        _cache_put(key, out)
        return out
    except Exception as e:  # 超时 / 解析失败 / 模型不可用
        log.warning("query rewrite failed, fallback to rule rewrite: %s", e)
        return _rule_rewrite(q, domain_words)


async def rerank(question: str, snippets: list[str]) -> list[float]:
    """批量给片段打 0–5 相关性分，返回与 snippets 等长的数组。

    解析失败一律返回 ``[0]*n``，绝不抛异常。
    """
    n = len(snippets)
    if n == 0:
        return []
    trimmed = [(s or "")[:400] for s in snippets]
    # 每个片段要输出 i/score/why，给足 token，否则 JSON 会被截断
    max_tokens = min(2400, 200 + 140 * n)
    try:
        res = await asyncio.wait_for(
            chat(settings.LLM_LIGHT_MODEL,
                 [{"role": "system", "content": RERANK_SYSTEM},
                  {"role": "user", "content": rerank_user(question, trimmed)}],
                 temperature=0.0, max_tokens=max_tokens, json_mode=True),
            timeout=_RERANK_TIMEOUT)
        text = res.text or ""
        scores = [0.0] * n
        try:
            got = extract_json(text).get("scores") or []
            pairs = [(int(it.get("i")), float(it.get("score"))) for it in got
                     if isinstance(it, dict) and str(it.get("i", "")).isdigit()
                     and isinstance(it.get("score"), (int, float))]
        except Exception:
            pairs = [(int(a), float(b)) for a, b in _SCORE_PAIR.findall(text)]
        for idx, score in pairs:
            if 1 <= idx <= n:
                scores[idx - 1] = max(0.0, min(5.0, score))
        return scores
    except Exception as e:
        log.warning("rerank failed, treat all as irrelevant: %s", e)
        return [0.0] * n


def is_relevant(score: float) -> bool:
    return score >= RELEVANT_SCORE
