# -*- coding: utf-8 -*-
"""对象存储：MinIO（生产，预签名直传）或本地文件（开发，零依赖）。
统一接口 save/read/size/presign_put。"""
import os
from datetime import timedelta
from functools import lru_cache

from app.core.config import settings


class Storage:
    def save(self, key: str, data: bytes) -> int:  # pragma: no cover
        raise NotImplementedError

    def read(self, key: str) -> bytes:  # pragma: no cover
        raise NotImplementedError

    def size(self, key: str) -> int:  # pragma: no cover
        raise NotImplementedError

    def presign_put(self, key: str, content_type: str) -> str | None:
        return None

    def ensure(self) -> None:
        pass


class LocalStorage(Storage):
    def __init__(self, base: str):
        self.base = os.path.abspath(base)
        os.makedirs(self.base, exist_ok=True)

    def _path(self, key: str) -> str:
        p = os.path.abspath(os.path.join(self.base, key))
        # 用 commonpath 而非 startswith，避免 /data/uploads_evil 绕过前缀检查
        if os.path.commonpath([self.base, p]) != self.base:
            raise ValueError("非法存储路径")
        return p

    def save(self, key: str, data: bytes) -> int:
        p = self._path(key)
        os.makedirs(os.path.dirname(p) or self.base, exist_ok=True)
        with open(p, "wb") as f:
            f.write(data)
        return len(data)

    def read(self, key: str) -> bytes:
        with open(self._path(key), "rb") as f:
            return f.read()

    def size(self, key: str) -> int:
        return os.path.getsize(self._path(key))


class MinioStorage(Storage):
    def __init__(self):
        self._c = None

    def client(self):
        if self._c is None:
            from minio import Minio
            self._c = Minio(settings.MINIO_ENDPOINT, access_key=settings.MINIO_ACCESS_KEY,
                            secret_key=settings.MINIO_SECRET_KEY, secure=settings.MINIO_SECURE)
        return self._c

    def ensure(self) -> None:
        c = self.client()
        if not c.bucket_exists(settings.MINIO_BUCKET):
            c.make_bucket(settings.MINIO_BUCKET)

    def save(self, key: str, data: bytes) -> int:
        import io
        self.ensure()
        self.client().put_object(settings.MINIO_BUCKET, key, io.BytesIO(data), length=len(data))
        return len(data)

    def read(self, key: str) -> bytes:
        resp = self.client().get_object(settings.MINIO_BUCKET, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def size(self, key: str) -> int:
        return int(self.client().stat_object(settings.MINIO_BUCKET, key).size)

    def presign_put(self, key: str, content_type: str) -> str:
        url = self.client().presigned_put_object(
            settings.MINIO_BUCKET, key, expires=timedelta(seconds=settings.PRESIGN_EXPIRE_SECONDS))
        internal = settings.MINIO_ENDPOINT
        public = settings.MINIO_PUBLIC_ENDPOINT.rstrip("/")
        if internal in url and public:
            scheme = "https://" if settings.MINIO_SECURE else "http://"
            url = url.replace(f"{scheme}{internal}", public)
        return url


@lru_cache
def get_storage() -> Storage:
    if settings.STORAGE_BACKEND.lower() == "local":
        return LocalStorage(settings.LOCAL_STORAGE_DIR)
    return MinioStorage()


# 兼容调用
def ensure_bucket() -> None:
    get_storage().ensure()


def presign_put(storage_key: str, content_type: str) -> str | None:
    return get_storage().presign_put(storage_key, content_type)


def stat_size(storage_key: str) -> int:
    return get_storage().size(storage_key)


def download_to(storage_key: str, dest: str) -> None:
    data = get_storage().read(storage_key)
    with open(dest, "wb") as f:
        f.write(data)
