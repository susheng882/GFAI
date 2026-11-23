# -*- coding: utf-8 -*-
"""三档路由 + 契约校验 + 纠正性重试 + 成本估算。
分档依据容错空间：轻档可模板兜底、中档需组织、强档要求准确可解释。"""
from pydantic import BaseModel, ValidationError

from app.ai.deepseek import LLMResult, chat, extract_json
from app.core.budget import budget, current_user_id, estimate_tokens
from app.core.config import settings
from app.core.errors import APIError, ErrCode

import logging

_log = logging.getLogger(__name__)

# tier -> (model, temperature, max_tokens)
TIERS: dict[str, tuple[str, float, int]] = {
    "light": (settings.LLM_LIGHT_MODEL, 0.2, 1500),
    "mid": (settings.LLM_MID_MODEL, 0.3, 3000),
    "strong": (settings.LLM_STRONG_MODEL, 0.1, 8192),
}

# 粗略单价（元 / 百万 token）：(input, output)，用于成本看板估算
PRICE: dict[str, tuple[float, float]] = {
    "deepseek-flash": (2.0, 8.0),
    "deepseek-v4-pro": (4.0, 16.0),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    p_in, p_out = PRICE.get(model, (2.0, 8.0))
    return round(prompt_tokens / 1e6 * p_in + completion_tokens / 1e6 * p_out, 6)


async def generate_json(tier: str, system: str, user: str, schema_cls: type[BaseModel],
                        *, temperature: float | None = None, max_tokens: int | None = None,
                        user_id: int | None = None, task_type: str = "llm") -> tuple[BaseModel, LLMResult]:
    """调模型 → 提取 JSON → Pydantic 校验；失败纠正性重试一次。

    预算：调用前按 prompt 长度估算并拦截（QUOTA-001/002），user_id 缺省时取当前请求用户，
    取不到则只做单任务上限校验。账本仍由各业务层写 CostLedger，这里不重复记账。

    max_tokens 可覆盖档位默认值：长视频的大纲/问答笔记节点多，mid 档 3000 会被截断，
    模型输出变成半截 JSON（"Expecting ',' delimiter"），必须按业务单独放宽。
    """
    model, temp, max_tok = TIERS.get(tier, TIERS["mid"])
    if max_tokens:
        max_tok = int(max_tokens)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    uid = user_id if user_id is not None else current_user_id()
    budget.check(uid, task_type or f"llm_{tier}",
                 estimate_tokens(system) + estimate_tokens(user) + 200)  # +200 预留输出/重试余量

    # 方舟优先：deepseek-v4-1-flash 上下文 1M（长转写不用压缩）+ 支持 json_object。
    # 失败或未开通时静默回落 DeepSeek 官方通道，保证可用性。
    from app.ai import ark
    use_ark = ark.available() and tier in ("mid", "strong")

    async def _call(msgs: list[dict]) -> LLMResult:
        t = temp if temperature is None else temperature
        if use_ark:
            from app.services.settings_store import cached
            _n = cached("note")
            try:
                return await ark.chat(_n[2] if _n else settings.ARK_NOTE_MODEL, msgs, temperature=t,
                                      max_tokens=max_tok, json_mode=False)
            except APIError as e:
                _log.warning("方舟调用失败，回落 DeepSeek：%s", e)
        return await chat(model, msgs, temperature=t, max_tokens=max_tok)

    res = await _call(messages)

    last_err: Exception | None = None
    for attempt in range(2):
        try:
            data = extract_json(res.text)
            return schema_cls.model_validate(data), res
        except (APIError, ValidationError) as e:
            last_err = e
            if attempt == 0:
                messages = messages + [
                    {"role": "assistant", "content": res.text[:4000]},
                    {"role": "user", "content": f"上面的输出不符合契约（{e}）。请只修正错误，"
                                                 f"重新输出合法 JSON，不要任何解释。"},
                ]
                res = await _call(messages)
    raise APIError(ErrCode.AI_003, f"契约校验失败：{last_err}")
