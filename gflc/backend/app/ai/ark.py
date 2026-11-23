# -*- coding: utf-8 -*-
"""火山方舟（Ark）OpenAI 兼容通道。

与 deepseek.py 的区别：
1. 独立 endpoint / key（ARK_API_BASE / ARK_API_KEY），可独立开关；
2. 默认关闭推理模型的思考（thinking=disabled）——方舟这几个可用模型都是推理模型，
   不关的话 reasoning_content 会把 max_tokens 吃光，正文变空（README 里记过一次的坑）；
3. 失败时由调用方决定是否回落 DeepSeek 官方通道。

许可说明：接口形态与 OpenAI Chat Completions 一致，本文件为自研实现。
"""
import asyncio
import json
import logging

import httpx

from app.ai.deepseek import LLMResult, extract_json
from app.core.config import settings
from app.core.errors import APIError, ErrCode

_log = logging.getLogger(__name__)


def _cfg(purpose: str = "note") -> tuple[str, str]:
    """(base_url, api_key)：配置中心优先，未配置回落 .env。"""
    from app.services.settings_store import cached
    c = cached(purpose)
    if c and c[1]:
        return (c[0] or settings.ARK_API_BASE, c[1])
    return (settings.ARK_API_BASE, settings.ARK_API_KEY)


def available() -> bool:
    if not settings.ARK_ENABLED:
        return False
    from app.services.settings_store import cached
    c = cached("note") or cached("vision")
    return bool(settings.ARK_API_KEY or (c and c[1]))


# 按事件循环缓存信号量：每个任务用 asyncio.run 起独立 loop，跨 loop 复用会报错
_SEMS: dict[int, "asyncio.Semaphore"] = {}


def _sem() -> "asyncio.Semaphore":
    loop = asyncio.get_running_loop()
    key = id(loop)
    s = _SEMS.get(key)
    if s is None:
        s = asyncio.Semaphore(max(1, int(settings.ARK_MAX_CONCURRENCY)))
        _SEMS[key] = s
    return s


def _headers() -> dict:
    return {"Authorization": f"Bearer {_cfg()[1]}", "Content-Type": "application/json"}


async def chat(model: str, messages: list[dict], *, temperature: float = 0.3,
               max_tokens: int | None = None, json_mode: bool = False,
               effort: str | None = None) -> LLMResult:
    if not available():
        raise APIError(ErrCode.AI_001, "未配置方舟 ARK_API_KEY 或已关闭 ARK_ENABLED")

    payload: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens or settings.MAX_TASK_TOKENS,
        "stream": False,
    }
    if settings.ARK_DISABLE_THINKING:
        payload["thinking"] = {"type": "disabled"}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    if effort:
        payload["reasoning_effort"] = effort

    url = _cfg()[0].rstrip("/") + "/chat/completions"
    # 限流 + 429 退避：该账号 3 并发即 429，且会排队很久才返回，必须自己控并发
    timeout = int(getattr(settings, "ARK_TIMEOUT_SECONDS", 100) or 100)
    last_err: Exception | None = None
    resp = None
    for attempt in range(3):
        try:
            async with _sem():
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(url, headers=_headers(), json=payload)
        except httpx.TimeoutException as e:
            last_err = e
            _log.warning("方舟超时（第 %s 次，%ss）", attempt + 1, timeout)
        except httpx.HTTPError as e:
            raise APIError(ErrCode.AI_001, f"方舟调用失败：{e}") from e
        else:
            if resp.status_code == 429:
                wait = 2 * (attempt + 1) ** 2
                _log.warning("方舟限流 429（第 %s 次），%ss 后重试", attempt + 1, wait)
                await asyncio.sleep(wait)
                last_err = None
                continue
            if resp.status_code >= 500:
                await asyncio.sleep(2 * (attempt + 1))
                continue
            break
    if resp is None or resp.status_code == 429:
        raise APIError(ErrCode.AI_001,
                       f"方舟限流或超时（已重试 3 次，并发上限 {settings.ARK_MAX_CONCURRENCY}）") from last_err

    if resp.status_code >= 400:
        # 部分模型不支持 json_object / thinking 字段，去掉重试一次再放弃
        retry_payload = dict(payload)
        retry_payload.pop("response_format", None)
        retry_payload.pop("thinking", None)
        if retry_payload != payload and resp.status_code in (400, 422):
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, headers=_headers(), json=retry_payload)
        if resp.status_code >= 400:
            detail = resp.text[:200]
            if resp.status_code == 404 and "not activated" in detail:
                raise APIError(ErrCode.AI_001,
                               f"方舟模型 {model} 未开通（请到方舟控制台「开通管理」授权）") from None
            raise APIError(ErrCode.AI_001, f"方舟返回 {resp.status_code}：{detail}") from None

    data = resp.json()
    try:
        text = data["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError) as e:
        raise APIError(ErrCode.AI_003, "方舟响应结构异常") from e
    usage = data.get("usage", {}) or {}
    return LLMResult(text=text,
                     prompt_tokens=int(usage.get("prompt_tokens", 0)),
                     completion_tokens=int(usage.get("completion_tokens", 0)))


async def generate_text(model: str, system: str, user: str, *, max_tokens: int = 4000,
                        temperature: float = 0.3) -> str:
    """纯文本生成（不要求 JSON）——视频笔记走 Markdown 直出。"""
    res = await chat(model, [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                     temperature=temperature, max_tokens=max_tokens)
    return (res.text or "").strip()


async def generate_json(model: str, system: str, user: str, schema_cls: type,
                        *, max_tokens: int = 4000) -> tuple[object, LLMResult]:
    res = await chat(model, [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                     temperature=0.2, max_tokens=max_tokens, json_mode=True)
    data = extract_json(res.text)
    return schema_cls.model_validate(data), res


async def probe() -> dict:
    """启动探活：确认 ARK_NOTE_MODEL / ARK_VISION_MODEL 是否真的开通。只读，失败不阻断。"""
    out = {}
    for name, model in (("note", settings.ARK_NOTE_MODEL), ("vision", settings.ARK_VISION_MODEL)):
        if not available():
            out[name] = "disabled"
            continue
        try:
            r = await chat(model, [{"role": "user", "content": "ok"}], max_tokens=8)
            out[name] = "ok" if r.text is not None else "empty"
        except APIError as e:
            out[name] = str(e)[:80]
            _log.error("方舟模型探活失败 %s=%s：%s", name, model, e)
    return out
