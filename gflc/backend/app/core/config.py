# -*- coding: utf-8 -*-
"""全局配置：所有密钥、endpoint、模型名走环境变量（.env），不硬编码。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 应用
    APP_NAME: str = "GFLC"
    APP_ENV: str = "dev"
    API_PREFIX: str = "/api"
    # 生产同源部署填域名即可；多个来源用逗号分隔
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost"

    # 运行模式（本地零依赖跑通用）
    DEV_MODE: bool = False          # True 时可用 sqlite + 本地存储
    MOCK_AI: bool = False           # True 时用规则生成卡片（无 Key 也能跑通）
    STORAGE_BACKEND: str = "minio"  # minio | local
    LOCAL_STORAGE_DIR: str = "./data/uploads"
    FRONTEND_DIR: str = "./frontend"

    # 数据库（PostgreSQL + pgvector）
    DATABASE_URL: str = "postgresql+psycopg://gflc:gflc@localhost:5432/gflc"

    # Redis（队列 + 会话小状态）
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAXMEMORY: str = "256mb"

    # 对象存储（MinIO，预签名直传）
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_BUCKET: str = "gflc"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_PUBLIC_ENDPOINT: str = "http://localhost:9000"  # 浏览器直传用

    # DeepSeek（三档映射：当前线上为 V4.1-Flash / V4-Pro）
    LLM_API_BASE: str = "https://api.deepseek.com/v1"
    LLM_API_KEY: str = ""
    LLM_LIGHT_MODEL: str = "deepseek-flash"
    LLM_MID_MODEL: str = "deepseek-flash"
    LLM_STRONG_MODEL: str = "deepseek-v4-pro"
    LLM_TIMEOUT_SECONDS: int = 120

    # 成本护栏
    DAILY_TOKEN_QUOTA: int = 20000
    MAX_TASK_TOKENS: int = 8000
    DAILY_COST_LIMIT_CNY: float = 250.0

    # 检索与切片（写入常量，勿随意改）
    RETRIEVAL_SCORE_THRESHOLD: float = 0.7
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 100
    PARAGRAPH_SPLIT_THRESHOLD: int = 800
    PARENT_CHUNK_SIZE: int = 1200

    # 检索提速开关（2026-11-22）：默认走零成本规则路径，关掉两次串行 LLM 调用。
    # 需要极致召回质量时可置 True 恢复 LLM 查询改写 + LLM 语义重排（问答会更慢）。
    QA_USE_LLM_REWRITE: bool = False
    QA_USE_LLM_RERANK: bool = False
    # 问答作答模型：默认沿用强推理模型（质量优先，~18s）。
    # 追求速度可设为 deepseek-flash（中档，带引用约束不变，通常 5-8s）。
    QA_ANSWER_MODEL: str = ""  # 空=用 LLM_STRONG_MODEL

    # 后台任务看门狗：无进度判定超时（提速对齐：需 > 单步 ffmpeg 时长）。
    # 抽帧/OCR 阶段已有心跳刷新时间戳，故这里按最长单步留足余量。
    TASK_TIMEOUT: int = 1800
    TASK_WATCH_INTERVAL: int = 15

    # 会话
    SESSION_SECRET: str = "change-me-in-prod"
    SESSION_COOKIE: str = "gflc_session"
    SESSION_TTL_SECONDS: int = 7 * 24 * 3600
    COOKIE_SECURE: bool = False  # 生产 HTTPS 置 True

    # 文件
    MAX_UPLOAD_MB: int = 512
    PDF_ENGINE: str = "pymupdf"          # pymupdf（轻）| mineru（质量优先，重）
    PRESIGN_EXPIRE_SECONDS: int = 900    # 预签名有效期 15 分钟
    WHISPER_MODEL: str = "base"          # tiny/base/small/medium；中文建议 base 以上
    COOKIES_FILE: str = ""               # 可选：Netscape 格式 cookies.txt（抖音等需要）


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
