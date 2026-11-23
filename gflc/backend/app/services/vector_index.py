# -*- coding: utf-8 -*-
"""向量索引（Q1/V1）：sqlite-vec + raw sqlite3，连到 settings.DATABASE_URL 的 sqlite 文件。

- vec_chunks 按 chunk_key 与检索语料（文档块 / 笔记块）一一对应，按 content_hash 增量写入；
- 元数据列（user_id / document_id / source_type）支持过滤，笔记与文档共用同一张表（D7）；
- 任何环境问题（非 sqlite / 扩展不可用 / 建表失败 / 检索异常）只关闭向量路并告警，
  绝不抛给问答主流程。
"""
import logging
import os
import sqlite3
import threading

from app.core.config import settings
from app.services import embedding

log = logging.getLogger(__name__)

_TABLE = "vec_chunks"
_META = "vec_meta"
_lock = threading.RLock()
_state: dict = {"conn": None, "ready": None}


def vector_enabled() -> bool:
    """VECTOR_ENABLED 开关（默认 true）；关掉时 rag 的检索退化为纯 BM25。"""
    return os.getenv("VECTOR_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off", "")


def _sqlite_path() -> str | None:
    url = (settings.DATABASE_URL or "").strip()
    if not url.startswith("sqlite"):
        return None
    rest = url.split(":///", 1)[1] if ":///" in url else url.split("://", 1)[-1]
    if rest.endswith(":memory:") or rest == ":memory:":
        return None
    if rest.startswith("/"):  # 绝对路径（Windows 盘符路径经 url 拆分后通常也是 / 开头）
        return rest
    return os.path.abspath(rest)


def _connect():
    path = _sqlite_path()
    if not path:
        log.warning("DATABASE_URL 非文件型 sqlite，向量路关闭（问答仍走 BM25）")
        return None
    try:
        import sqlite_vec  # 延迟导入，缺依赖时只降级不崩溃
        conn = sqlite3.connect(path, timeout=15.0, check_same_thread=False)
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        conn.execute(
            f"CREATE VIRTUAL TABLE IF NOT EXISTS {_TABLE} USING vec0("
            f"embedding float[{embedding.DIM}], chunk_key TEXT PRIMARY KEY, "
            f"user_id INTEGER, document_id INTEGER, source_type TEXT, content_hash TEXT)")
        conn.execute(f"CREATE TABLE IF NOT EXISTS {_META}(key TEXT PRIMARY KEY, value TEXT)")
        conn.commit()
        # 后端变化（hash ↔ bge）时旧向量空间不可复用，清空重建
        want = embedding.backend()
        row = conn.execute(f"SELECT value FROM {_META} WHERE key='backend'").fetchone()
        if row is None or row[0] != want:
            conn.execute(f"DELETE FROM {_TABLE}")
            conn.execute(f"INSERT OR REPLACE INTO {_META}(key,value) VALUES('backend',?)", (want,))
            conn.commit()
        return conn
    except Exception as e:
        log.warning("sqlite-vec 向量索引初始化失败，向量路关闭: %s", e)
        try:
            conn.close()
        except Exception:
            pass
        return None


def conn_or_none():
    if _state["ready"] is None:
        with _lock:
            if _state["ready"] is None:
                conn = _connect()
                _state["conn"] = conn
                _state["ready"] = conn is not None
    return _state["conn"] if _state["ready"] else None


def available() -> bool:
    return vector_enabled() and conn_or_none() is not None


def _serialize(vec: list[float]):
    import sqlite_vec
    return sqlite_vec.serialize_float32(vec)


def sync(items: list[dict]) -> int:
    """增量写入。items=[{key,text,content_hash,user_id,document_id,source_type}]，返回实际写入条数。"""
    conn = conn_or_none()
    if conn is None or not items:
        return 0
    try:
        vecs = embedding.embed([it["text"] for it in items])
    except Exception as e:
        log.warning("向量化失败，跳过本轮同步: %s", e)
        return 0
    written = 0
    try:
        with _lock:
            for it, vec in zip(items, vecs):
                key = str(it["key"])
                row = conn.execute(
                    f"SELECT content_hash FROM {_TABLE} WHERE chunk_key=?", (key,)).fetchone()
                if row and row[0] == it["content_hash"]:
                    continue
                if row:
                    conn.execute(f"DELETE FROM {_TABLE} WHERE chunk_key=?", (key,))
                conn.execute(
                    f"INSERT INTO {_TABLE}(embedding,chunk_key,user_id,document_id,source_type,content_hash) "
                    f"VALUES(?,?,?,?,?,?)",
                    (_serialize(vec), key, int(it.get("user_id") or 0),
                     int(it.get("document_id") or 0), it.get("source_type") or "document",
                     str(it["content_hash"])))
                written += 1
            conn.commit()
    except Exception as e:
        log.warning("向量索引写入失败: %s", e)
        try:
            conn.rollback()
        except Exception:
            pass
    return written


def search(query: str, k: int, user_id: int,
           document_id: int | None = None) -> dict[str, float]:
    """向量 Top-K，返回 {chunk_key: 0~1 相似度}；失败返回空字典。"""
    if not available():
        return {}
    conn = conn_or_none()
    try:
        vec = embedding.embed_one(query)
        sql = f"SELECT chunk_key,distance FROM {_TABLE} WHERE embedding MATCH ? AND user_id=?"
        args: list = [_serialize(vec), int(user_id)]
        if document_id:
            sql += " AND document_id=?"
            args.append(int(document_id))
        sql += " ORDER BY distance LIMIT ?"
        args.append(max(1, int(k)))
        rows = conn.execute(sql, args).fetchall()
        # sqlite-vec 默认 L2 距离；映射为 0~1 相似度（距离越小越接近 1）
        return {r[0]: round(1.0 / (1.0 + float(r[1])), 4) for r in rows}
    except Exception as e:
        log.warning("向量检索失败: %s", e)
        return {}
