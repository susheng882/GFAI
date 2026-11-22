# -*- coding: utf-8 -*-
"""成本预算护栏：事前拦截（超限抛 QUOTA-001/002）+ 事后记账 + 进程内缓存。

设计要点
- 限额从环境变量读，带默认值（不改 config.py）：DAILY_USER_TOKENS / DAILY_USER_COST_CNY /
  SINGLE_TASK_TOKENS / BUDGET_ENABLED。每次调用现读，便于压测进程用 env 覆盖。
- 用量数据源是 CostLedger（按 user_id + created_at 当日/本月聚合），独立 SessionLocal 会话，
  不参与业务事务，读不到就退化为 0，绝不影响主流程。
- 线程安全：缓存用 RLock + 有界 OrderedDict；DB 会话每次新建，不跨线程共享。
- 记账归属：卡片/笔记等业务层已自行写 CostLedger，这里不重复写；record() 只用于原本没有
  账本的路径（如 QA），避免一套调用记两笔账。
"""
import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select

from app.core.errors import APIError, ErrCode
from app.db.session import SessionLocal
from app.models.models import CostLedger

log = logging.getLogger(__name__)

# 默认限额（env 可覆盖）
_DEF_DAILY_TOKENS = 300_000
_DEF_DAILY_COST_CNY = 2.0
_DEF_SINGLE_TASK_TOKENS = 60_000

_CACHE_MAX = 512
_usage_cache: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
_cache_lock = threading.RLock()

# 当前请求的用户（上下文变量；HTTP 依赖里写入，供 ai 层读取）
_current_user_id: int | None = None
_ctx_lock = threading.RLock()


# ---------------------------------------------------------------- env 读取
def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.getenv(name, "")).strip() or default)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.getenv(name, "")).strip() or default)
    except (TypeError, ValueError):
        return default


def enabled() -> bool:
    return str(os.getenv("BUDGET_ENABLED", "true")).strip().lower() not in ("0", "false", "no", "off")


def limits() -> dict:
    return {
        "daily_user_tokens": _env_int("DAILY_USER_TOKENS", _DEF_DAILY_TOKENS),
        "daily_user_cost_cny": _env_float("DAILY_USER_COST_CNY", _DEF_DAILY_COST_CNY),
        "single_task_tokens": _env_int("SINGLE_TASK_TOKENS", _DEF_SINGLE_TASK_TOKENS),
        "enabled": enabled(),
    }


# ------------------------------------------------------- 当前用户（上下文）
def set_current_user_id(user_id: int | None) -> None:
    global _current_user_id
    with _ctx_lock:
        _current_user_id = user_id


def current_user_id() -> int | None:
    with _ctx_lock:
        return _current_user_id


# ------------------------------------------------------------ 进程内缓存
def cache_key(*parts) -> str:
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def get_cached(key: str) -> Any:
    now = time.time()
    with _cache_lock:
        hit = _usage_cache.get(key)
        if not hit:
            return None
        expire_at, value = hit
        if expire_at < now:
            _usage_cache.pop(key, None)
            return None
        _usage_cache.move_to_end(key)
        return value


def set_cached(key: str, value: Any, ttl: int = 3600) -> None:
    with _cache_lock:
        _usage_cache[key] = (time.time() + ttl, value)
        _usage_cache.move_to_end(key)
        while len(_usage_cache) > _CACHE_MAX:
            _usage_cache.popitem(last=False)


def bust(key: str) -> None:
    with _cache_lock:
        _usage_cache.pop(key, None)


# ------------------------------------------------------------ token 估算
def estimate_tokens(text: str) -> int:
    """中文按 1.5 字/token、其余按 4 字符/token 粗估（宁可略高，不放过超额）。"""
    if not text:
        return 0
    cjk = 0
    for ch in text:
        o = ord(ch)
        if 0x3400 <= o <= 0x9FFF or 0xF900 <= o <= 0xFAFF or 0x3000 <= o <= 0x303F:
            cjk += 1
    other = len(text) - cjk
    return max(1, int(cjk / 1.5 + other / 4))


# ---------------------------------------------------------------- 预算
class Budget:
    """单例即可：Budget() 无状态，全部数据来自 CostLedger + 进程缓存。"""

    # ---- 用量聚合 ----
    def usage(self, user_id: int | None) -> dict:
        if not user_id:
            return {"today_tokens": 0, "today_cost_cny": 0.0, "today_calls": 0,
                    "month_tokens": 0, "month_cost_cny": 0.0, "month_calls": 0}
        ck = cache_key("usage", user_id)
        cached = get_cached(ck)
        if cached is not None:
            return cached

        now = datetime.now(timezone.utc)
        today = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        month = today.replace(day=1)
        try:
            with SessionLocal() as db:
                def _agg(since) -> tuple[int, float, int]:
                    row = db.execute(
                        select(func.coalesce(func.sum(CostLedger.prompt_tokens), 0),
                               func.coalesce(func.sum(CostLedger.completion_tokens), 0),
                               func.coalesce(func.sum(CostLedger.cost_cny), 0.0),
                               func.count(CostLedger.id))
                        .where(CostLedger.user_id == user_id, CostLedger.created_at >= since)
                    ).one()
                    return int(row[0] + row[1]), float(row[2] or 0.0), int(row[3])

                d_tokens, d_cost, d_calls = _agg(today)
                m_tokens, m_cost, m_calls = _agg(month)
        except Exception as e:  # 账本读不到时不让主流程挂
            log.warning("budget usage query failed: %s", e)
            return {"today_tokens": 0, "today_cost_cny": 0.0, "today_calls": 0,
                    "month_tokens": 0, "month_cost_cny": 0.0, "month_calls": 0}

        data = {"today_tokens": d_tokens, "today_cost_cny": round(d_cost, 6), "today_calls": d_calls,
                "month_tokens": m_tokens, "month_cost_cny": round(m_cost, 6), "month_calls": m_calls}
        set_cached(ck, data, ttl=2)
        return data

    def remaining(self, user_id: int | None) -> dict:
        lim = limits()
        u = self.usage(user_id)
        return {
            "tokens_today": max(0, lim["daily_user_tokens"] - u["today_tokens"]),
            "cost_cny_today": round(max(0.0, lim["daily_user_cost_cny"] - u["today_cost_cny"]), 6),
            "single_task_tokens": lim["single_task_tokens"],
            "limits": lim,
        }

    # ---- 事前拦截 ----
    def check(self, user_id: int | None, task_type: str, est_tokens: int) -> None:
        if not enabled():
            return
        lim = limits()
        est = max(0, int(est_tokens or 0))

        if est > lim["single_task_tokens"]:
            raise APIError(
                ErrCode.QUOTA_002,
                f"单次任务预估 {est} tokens，超过单任务上限 {lim['single_task_tokens']} tokens。"
                f"请拆分任务或缩小范围后重试。",
            )
        if not user_id:
            return

        u = self.usage(user_id)
        if u["today_tokens"] + est > lim["daily_user_tokens"]:
            left = max(0, lim["daily_user_tokens"] - u["today_tokens"])
            raise APIError(
                ErrCode.QUOTA_001,
                f"今日 token 额度已用尽（剩余 {left} tokens，本次预估需 {est} tokens）。"
                f"请明天再试，或减少单次任务量（如少传一些资料、缩短问题）。",
            )
        if u["today_cost_cny"] >= lim["daily_user_cost_cny"]:
            raise APIError(
                ErrCode.QUOTA_001,
                f"今日成本额度已用尽（已花 {u['today_cost_cny']:.4f} 元，上限 "
                f"{lim['daily_user_cost_cny']:.2f} 元）。请明天再试或减少单次任务量。",
            )
        log.debug("budget ok user=%s task=%s est=%s used_today=%s",
                  user_id, task_type, est, u["today_tokens"])

    # ---- 事后记账（仅给原本无账本的路径用，避免重复记账）----
    def record(self, user_id: int | None, task_type: str, tokens_in: int, tokens_out: int,
               model: str, *, write_ledger: bool = True) -> None:
        if not user_id:
            return
        tokens_in, tokens_out = int(tokens_in or 0), int(tokens_out or 0)
        try:
            from app.ai.router import estimate_cost  # 延迟导入，避免循环依赖
            cost = estimate_cost(model, tokens_in, tokens_out)
        except Exception:
            cost = 0.0
        if write_ledger:
            try:
                with SessionLocal() as db:
                    db.add(CostLedger(user_id=user_id, task_type=task_type[:32], model=model[:64],
                                      prompt_tokens=tokens_in, completion_tokens=tokens_out,
                                      cost_cny=cost))
                    db.commit()
            except Exception as e:
                log.warning("budget record failed: %s", e)
        bust(cache_key("usage", user_id))


budget = Budget()
