# -*- coding: utf-8 -*-
"""密码与会话安全：Argon2id 哈希、HttpOnly Cookie 会话（存 Redis，登出即失效）。"""
import json
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


# ------------------------- 会话存储 -------------------------
class _MemStore:
    """Redis 不可用时的降级存储（仅开发/测试用）。"""

    def __init__(self):
        self._d: dict[str, tuple[str, float]] = {}

    async def set(self, key: str, val: str, ttl: int):
        self._d[key] = (val, time.time() + ttl)

    async def get(self, key: str):
        item = self._d.get(key)
        if not item:
            return None
        val, exp = item
        if exp < time.time():
            self._d.pop(key, None)
            return None
        return val

    async def delete(self, key: str):
        self._d.pop(key, None)


class _RedisStore:
    def __init__(self, url: str):
        import redis.asyncio as aioredis  # 延迟导入

        self._r = aioredis.from_url(url, decode_responses=True)

    async def set(self, key: str, val: str, ttl: int):
        await self._r.set(key, val, ex=ttl)

    async def get(self, key: str):
        return await self._r.get(key)

    async def delete(self, key: str):
        await self._r.delete(key)


_store = None


async def get_store():
    """优先 Redis；连不上则降级内存（仅开发/测试，生产须有 Redis）。"""
    global _store
    if _store is not None:
        return _store
    try:
        s = _RedisStore(settings.REDIS_URL)
        await s._r.ping()
        _store = s
    except Exception:
        _store = _MemStore()
    return _store


def _key(token: str) -> str:
    return f"gflc:sess:{token}"


async def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    store = await get_store()
    await store.set(_key(token), json.dumps({"uid": user_id}), settings.SESSION_TTL_SECONDS)
    return token


async def read_session(token: str) -> int | None:
    if not token:
        return None
    store = await get_store()
    raw = await store.get(_key(token))
    if not raw:
        return None
    try:
        return int(json.loads(raw)["uid"])
    except Exception:
        return None


async def destroy_session(token: str):
    if token:
        store = await get_store()
        await store.delete(_key(token))
