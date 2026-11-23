# -*- coding: utf-8 -*-
"""答案缓存（Q7）：归一化问题 hash → 完整答案数据，TTL 进程内缓存。

命中时由 qa.py 在响应里追加 cache_hit=true；未命中路径完全不变。
任何缓存内部异常都不影响问答主流程。
"""
import hashlib
import os
import re
import threading
import time

_lock = threading.Lock()
_store: dict[str, tuple[float, dict]] = {}

_PUNCT = re.compile(r"[^\w\u4e00-\u9fff]+", re.UNICODE)


def ttl_seconds() -> int:
    try:
        return max(1, int(os.getenv("QA_ANSWER_CACHE_TTL", "600")))
    except ValueError:
        return 600


def enabled() -> bool:
    return os.getenv("QA_ANSWER_CACHE_ENABLED", "true").strip().lower() not in (
        "0", "false", "no", "off", "")


def max_entries() -> int:
    try:
        return max(16, int(os.getenv("QA_ANSWER_CACHE_MAX", "512")))
    except ValueError:
        return 512


def normalize(question: str | None) -> str:
    """归一化：小写、去标点/空白；中文与字母数字保留，兼容口语标点差异。"""
    return _PUNCT.sub("", (question or "").strip().lower())


def make_key(user_id: int, question: str, strategy: str = "",
             document_id: int | None = None) -> str:
    raw = "%s|%s|%s|%s" % (user_id, document_id or 0, strategy or "", normalize(question))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get(key: str) -> dict | None:
    """命中返回数据副本；过期/异常返回 None。"""
    try:
        with _lock:
            item = _store.get(key)
            if not item:
                return None
            ts, data = item
            if time.time() - ts > ttl_seconds():
                _store.pop(key, None)
                return None
            return dict(data)  # 防止调用方改动污染缓存
    except Exception:
        return None


def put(key: str, data: dict) -> None:
    try:
        with _lock:
            if len(_store) >= max_entries():
                # 清掉过期项；仍超限时丢最早写入的一批，避免无限增长
                now = time.time()
                for k in [k for k, (t, _) in _store.items() if now - t > ttl_seconds()]:
                    _store.pop(k, None)
                while len(_store) >= max_entries():
                    _store.pop(next(iter(_store)))
            _store[key] = (time.time(), dict(data))
    except Exception:
        pass


def clear() -> None:
    with _lock:
        _store.clear()


def stats() -> dict:
    with _lock:
        return {"size": len(_store), "ttl": ttl_seconds(), "enabled": enabled()}
