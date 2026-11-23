# -*- coding: utf-8 -*-
"""DeepSeek（OpenAI 兼容）客户端。所有模型经此适配器，换供应商只改配置。"""
import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import APIError, ErrCode

_log = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


async def chat(model: str, messages: list[dict], *, temperature: float = 0.3,
               max_tokens: int | None = None, json_mode: bool = True,
               effort: str | None = None) -> LLMResult:
    if not settings.LLM_API_KEY:
        raise APIError(ErrCode.AI_001, "未配置 LLM_API_KEY（请在 .env 填入 DeepSeek Key）")

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or settings.MAX_TASK_TOKENS,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if effort:
        payload["reasoning_effort"] = effort

    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
    url = settings.LLM_API_BASE.rstrip("/") + "/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as e:
        raise APIError(ErrCode.AI_001, "模型调用超时") from e
    except httpx.HTTPError as e:
        raise APIError(ErrCode.AI_001, f"模型调用失败：{e}") from e

    if resp.status_code >= 400:
        # 强档模型可能不支持 json_object，去掉重试一次
        if json_mode and resp.status_code in (400, 422):
            payload.pop("response_format", None)
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise APIError(ErrCode.AI_001, f"模型返回 {resp.status_code}：{resp.text[:200]}")

    data = resp.json()
    try:
        text = data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as e:
        raise APIError(ErrCode.AI_003, "模型响应结构异常") from e
    usage = data.get("usage", {}) or {}
    return LLMResult(text=text,
                     prompt_tokens=int(usage.get("prompt_tokens", 0)),
                     completion_tokens=int(usage.get("completion_tokens", 0)))


def _repair_json(text: str) -> str:
    """修常见的模型 JSON 污染：字符串内裸换行/制表符、被截断的尾部。

    实测 deepseek-flash 写长中文笔记时会把换行直接塞进字符串（json 报
    "Invalid control character"）或漏转义引号导致 "Unterminated string"，
    以前这种就必须换 strong 档重跑一次（图文笔记多花 100s+）。这里做确定性修复，
    修复后仍必须通过 Pydantic 校验才算数，不会把坏数据放进去。
    """
    out: list[str] = []
    in_string = False
    escaped = False
    for ch in text:
        if in_string:
            if escaped:
                out.append(ch)
                escaped = False
            elif ch == "\\":
                out.append(ch)
                escaped = True
            elif ch == '"':
                out.append(ch)
                in_string = False
            elif ch == "\n":
                out.append("\\n")
            elif ch == "\r":
                out.append("\\r")
            elif ch == "\t":
                out.append("\\t")
            else:
                out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)
    if in_string:  # 尾部被截断：先闭合字符串
        out.append('"')

    s = "".join(out).rstrip()
    # 按括号栈补齐未闭合的数组/对象（截断场景）
    stack: list[str] = []
    in_string = False
    escaped = False
    for ch in s:
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()
    # 去掉悬空的 , "key": 之类残尾，再补闭合符
    while s and s[-1] in ", \n\r\t":
        s = s[:-1]
    for ch in reversed(stack):
        s += "}" if ch == "{" else "]"
    return s


def extract_json(text: str) -> dict:
    """容错从模型输出中提取 JSON 对象。"""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    for candidate in (text,):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass
    start = text.find("{")
    if start != -1:
        try:
            fixed = _repair_json(text[start:])
            data = json.loads(fixed)
            _log.warning("模型 JSON 经修复后可用（len=%s）", len(text))
            return data
        except json.JSONDecodeError:
            pass
    raise APIError(ErrCode.AI_003, "模型输出不是合法 JSON")

async def chat_stream(model: str, messages: list[dict], *, temperature: float = 0.3,
                      max_tokens: int | None = None, effort: str | None = None):
    """流式对话：逐段 yield 文本增量。用于问答首字秒出。"""
    if not settings.LLM_API_KEY:
        raise APIError(ErrCode.AI_001, "未配置 LLM_API_KEY")
    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or settings.MAX_TASK_TOKENS,
        "stream": True,
    }
    if effort:
        payload["reasoning_effort"] = effort
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}
    url = settings.LLM_API_BASE.rstrip("/") + "/chat/completions"
    try:
        async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", "ignore")[:200]
                    raise APIError(ErrCode.AI_001, f"模型返回 {resp.status_code}：{body}")
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                        delta = obj["choices"][0].get("delta", {})
                        piece = delta.get("content") or ""
                    except (KeyError, IndexError, json.JSONDecodeError):
                        continue
                    if piece:
                        yield piece
    except httpx.TimeoutException as e:
        raise APIError(ErrCode.AI_001, "模型调用超时") from e
    except httpx.HTTPError as e:
        raise APIError(ErrCode.AI_001, f"模型网络错误：{e}") from e
