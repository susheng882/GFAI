# -*- coding: utf-8 -*-
"""DeepSeek（OpenAI 兼容）客户端。所有模型经此适配器，换供应商只改配置。"""
import json
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.core.errors import APIError, ErrCode


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


def extract_json(text: str) -> dict:
    """容错从模型输出中提取 JSON 对象。"""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start:end + 1])
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
