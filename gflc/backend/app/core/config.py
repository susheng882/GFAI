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
    # 开发期免登录：仅 DEV_MODE/非 prod 生效，启动打 WARNING；prod 下强制忽略。
    PARSE_DENOISE: bool = True          # 解析去噪：丢页眉页脚/页码/水印
    DEV_AUTH_BYPASS: bool = False
    DEV_BYPASS_EMAIL: str = "dev@local" 

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

    # 火山方舟（OpenAI 兼容）。默认作为「笔记生成 + 视觉识图」的主通道，DeepSeek 官方 key 留作备用。
    # 注意：/models 会列 55 个，但当前账号真正开通的只有 4 个，启动时会探活并回退。
    ARK_API_BASE: str = "https://ark.cn-beijing.volces.com/api/v3"
    ARK_API_KEY: str = ""
    ARK_NOTE_MODEL: str = "deepseek-v4-1-flash-261017"
    ARK_VISION_MODEL: str = "deepseek-v4-1-flash-261017"
    ARK_LONG_MODEL: str = "kimi-k3-1-pro-261024"
    ARK_DISABLE_THINKING: bool = True     # 推理模型不关思考会把 max_tokens 吃光
    # 实测该账号 3 并发即 429（且排队 171s 才返回），必须限流 + 退避
    ARK_MAX_CONCURRENCY: int = 2
    ARK_TIMEOUT_SECONDS: int = 100
    ARK_ENABLED: bool = True              # 关掉则全部回落 DeepSeek 官方通道

    # 视频取材链：字幕(需 cookie) → 必剪云转写 → 本地 Whisper
    # bcut 是 B 站自家接口，免登录免费（实测 RTF 0.028），无 SLA，失败自动降级。
    BCUT_ENABLED: bool = True
    BCUT_TIMEOUT_SECONDS: int = 900
    # 视频任务并发数（独立于其他任务的单线程队列）：整季 16P 靠它才不排队一小时
    VIDEO_CONCURRENCY: int = 5

    # 成本护栏（单一真源）
    # budget.py 以本组字段为默认值，同名环境变量仍可覆盖（压测用）。
    # 默认值对齐真实单次成本：PDF ¥0.12 / 视频 ¥0.4，免费层 3 次/日 ≈ ¥0.5。
    BUDGET_ENABLED: bool = True
    DAILY_USER_TOKENS: int = 300_000
    DAILY_USER_COST_CNY: float = 2.0
    SINGLE_TASK_TOKENS: int = 60_000
    # 兼容旧字段：MAX_TASK_TOKENS 是"单次生成 max_tokens 上限"（deepseek.py 用），
    # 与 SINGLE_TASK_TOKENS（预算预检上限）语义不同，勿混用；另两项已废弃仅留兼容。
    MAX_TASK_TOKENS: int = 8000
    DAILY_TOKEN_QUOTA: int = 300_000       # deprecated → DAILY_USER_TOKENS
    DAILY_COST_LIMIT_CNY: float = 2.0      # deprecated → DAILY_USER_COST_CNY

    # 检索与切片（写入常量，勿随意改）
    # 统一置信度量纲（0~1）：query_opt 的相关线 = QA_MIN_CONFIDENCE × 5。
    # RETRIEVAL_SCORE_THRESHOLD 为旧字段，保留兼容但不再被检索链路读取。
    QA_MIN_CONFIDENCE: float = 0.6
    QA_COVERAGE_FLOOR: float = 0.34
    RETRIEVAL_SCORE_THRESHOLD: float = 0.6  # deprecated → QA_MIN_CONFIDENCE
    CHUNK_SIZE: int = 300
    CHUNK_OVERLAP: int = 100
    PARAGRAPH_SPLIT_THRESHOLD: int = 800
    PARENT_CHUNK_SIZE: int = 1200
    RETRIEVAL_MAX_CHUNKS: int = 800         # 单次召回语料上限，触顶告警而非静默截断

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
    # 扫描件（无文字层）视觉 OCR 兜底：逐页渲染后并发转录，回灌同一分块/入库链路。
    # 实际读取在 services/question_vision.py 与 pipeline.py（os.getenv），此处集中声明默认值。
    OCR_ENABLED: bool = True             # 0/false 关闭，保留原 PARSE-002 失败契约
    # 扫描页渲染 DPI，三档统一 140：110 已证伪更慢（121.86s）；180 已 A/B（2026-11-23，
    # 公式 86→86 / 78→78、字符方向不一致），无实质收益，故 quality 档也不上调
    OCR_DPI: int = 140
    OCR_MAX_TOKENS: int = 16000          # 单页 OCR 输出 token 上限（整页转录，需放宽）
    OCR_MAX_CONCURRENCY: int = 2         # 逐页并发上限，防止方舟 3 并发即 429
    # 28 号诊断报告新增旋钮（实际读取在 services/question_vision.py / chunking.py）：
    # 三档预设共用同一链路，仅在同一组旋钮上取值；下方单项环境变量可覆盖预设。
    # 默认 balanced = 纯文本直出 + 分栏提示 + 公式配平 + 失败页重试 + 页级缓存。
    OCR_PROFILE: str = "balanced"        # balanced | quality | fast
    OCR_OUTPUT_FORMAT: str = "plain"     # plain（推荐，默认）| json（旧行为，回归对照用）
    OCR_JPEG_QUALITY: int = 72           # JPEG 传输质量；quality 档 85、fast 档 60
    OCR_COLUMN_AWARE: bool = True        # prompt 注入「分栏先左后右逐栏转录」
    OCR_FORMULA_CHECK: bool = True       # $...$ 配平/长度异常检测，可疑页记入 stats，不阻断入库
    OCR_CACHE_ENABLED: bool = True       # 页级缓存：内容 hash+页码+dpi+模型+prompt 版本+profile
    OCR_FAILED_PAGE_RETRY: bool = True   # 失败页串行纯文本重试 1 次，仍失败才跳过
    OCR_OBSERVABILITY: bool = True       # 采集每页指标（chars/formula_count/seconds/json_retry）到 stats
    OCR_CHUNK_SIZE: int = 0              # >0 时对含公式的页放大块长（0=沿用 CHUNK_SIZE=300）
    PRESIGN_EXPIRE_SECONDS: int = 900    # 预签名有效期 15 分钟
    WHISPER_MODEL: str = "base"          # tiny/base/small/medium；中文建议 base 以上
    # 长音频切片并行数：Whisper 是 CPU 密集且默认单路，串行会把 60 分钟视频拖到 26 分钟。
    # 实测 4.5 分钟音频：1 片 RTF 0.44 / 6 片 RTF 0.11（20 核机器）。小机器调成 2–4。
    WHISPER_PARALLEL: int = 6
    WHISPER_CPU_THREADS: int = 8          # 单片线程数（与并行数相乘不要远超物理核数）
    WHISPER_BEAM: int = 5                 # 短音频单路时用 5；并行路径固定 beam1（快 2 倍）
    COOKIES_FILE: str = ""               # 可选：Netscape 格式 cookies.txt（抖音等需要）


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
