# -*- coding: utf-8 -*-
"""向量嵌入（Q1/V1）：懒加载单例，优先 BAAI/bge-large-zh-v1.5，失败降级到确定性哈希向量。

硬约束：任何依赖缺失 / 模型加载失败 / 推理异常，都只记 WARNING 并降级，
绝不把异常抛给问答主流程（问答整体不得因向量失败而失败）。
"""
import hashlib
import logging
import math
import os
import threading

log = logging.getLogger(__name__)

# 模型名可用 QA_EMBED_MODEL 覆盖；哈希兜底维度与 bge-large-zh-v1.5 一致（1024），
# 避免写入后切换后端造成 sqlite-vec 表维度不兼容。
MODEL_NAME = os.getenv("QA_EMBED_MODEL", "BAAI/bge-large-zh-v1.5")
DIM = 1024

_state: dict = {"model": None, "backend": None, "tried": False}
_lock = threading.Lock()


def _hash_vector(text: str, dim: int = DIM) -> list[float]:
    """确定性字符 unigram+bigram 带符号哈希向量（L2 归一化）。

    不使用 Python 内建 hash()：它在进程间随机化，会导致同一文本每次得到不同向量。
    """
    vec = [0.0] * dim
    s = (text or "").lower()
    grams = list(s) + [s[i:i + 2] for i in range(len(s) - 1)]
    if not grams:
        return vec
    for g in grams:
        h = hashlib.blake2b(g.encode("utf-8", "ignore"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % dim
        sign = 1.0 if (h[4] & 1) else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def _model_available_locally() -> bool:
    """快速判断权重是否完整缓存，避免为"缓存里根本没有权重"白白付 torch 导入成本。"""
    if os.path.isdir(MODEL_NAME):  # 本地路径直接交给 sentence-transformers
        return True
    hf_home = os.getenv("HF_HOME") or os.path.join(os.path.expanduser("~"), ".cache", "huggingface")
    cache = os.path.join(hf_home, "hub")
    root = os.path.join(cache, "models--" + MODEL_NAME.replace("/", "--"))
    if not os.path.isdir(root):
        return False
    for base, _, files in os.walk(os.path.join(root, "snapshots")):
        if any(f in ("model.safetensors", "pytorch_model.bin") for f in files):
            return True
    return False


def _load_model():
    """尝试加载 sentence-transformers；任何异常都返回 None，不得联网等待。"""
    if not _model_available_locally():
        log.warning("向量模型 %s 权重未完整缓存，跳过加载并降级到确定性哈希向量", MODEL_NAME)
        return None
    # 模型权重必须来自本机缓存：缓存不全时立刻失败降级，绝不在问答请求里联网下载。
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:  # 依赖未安装（本机环境常见）
        log.warning("向量模型依赖不可用，降级到确定性哈希向量: %s", e)
        return None
    try:
        try:
            model = SentenceTransformer(MODEL_NAME, device="cpu", local_files_only=True)
        except TypeError:  # 老版本无该参数
            model = SentenceTransformer(MODEL_NAME, device="cpu")
        got = int(model.get_sentence_embedding_dimension() or 0)
        if got != DIM:
            log.warning("向量模型维度=%s 与期望 %s 不符，降级到哈希向量", got, DIM)
            return None
        return model
    except Exception as e:
        log.warning("向量模型 %s 加载失败，降级到确定性哈希向量: %s", MODEL_NAME, e)
        return None


def _ensure() -> None:
    with _lock:
        if _state["tried"]:
            return
        _state["tried"] = True
        model = _load_model()
        if model is not None:
            _state["model"] = model
            _state["backend"] = "bge"
            log.info("向量模型已加载: %s (dim=%d)", MODEL_NAME, DIM)
        else:
            _state["backend"] = "hash"
            log.warning("向量检索使用确定性字符 n-gram 哈希向量(dim=%d)，语义召回能力有限；"
                        "安装 sentence-transformers 后可自动切换到 %s", DIM, MODEL_NAME)


def backend() -> str:
    """返回 'bge' 或 'hash'，供向量索引判断是否需重建旧向量。"""
    _ensure()
    return _state["backend"]


def embed(texts: list[str]) -> list[list[float]]:
    """返回与 texts 等长的 L2 归一化向量；推理失败整批降级为哈希向量。"""
    texts = [t or "" for t in texts]
    if not texts:
        return []
    _ensure()
    model = _state["model"]
    if model is not None:
        try:
            raw = model.encode(texts, normalize_embeddings=True,
                               show_progress_bar=False, batch_size=32)
            return [[float(x) for x in row] for row in raw]
        except Exception as e:
            log.warning("向量推理失败，本批降级到哈希向量: %s", e)
    return [_hash_vector(t) for t in texts]


def embed_one(text: str) -> list[float]:
    return embed([text])[0]
