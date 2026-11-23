# -*- coding: utf-8 -*-
"""GFLC FastAPI 入口：鉴权 + 上传 + PDF 解析切块 + 卡片 + 复习 + 仪表盘 + 前端静态页。"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.errors import APIError, api_error_handler, unhandled_handler
from app.routers import (auth, dashboard, decks, documents, notes, plans, qa,
                         questions, quiz, review, settings as settings_router,
                         tasks, videos)
from app.services.storage import ensure_bucket
from app.worker import runner
from app.worker.handlers import register_all

log = logging.getLogger(__name__)


def _check_runtime_consistency() -> None:
    """D1：本机 dev 栈与生产栈配置混用会让"本地全绿、上线必炸"。

    只告警不阻断：开发/验收默认 dev 模式，强行 raise 会破坏现有流程；
    但生产特征（APP_ENV=prod）出现 dev 配置时必须留下显式日志，不能静默。
    """
    prod = settings.APP_ENV.lower() in ("prod", "production", "live")
    issues: list[str] = []
    if prod:
        if settings.DEV_MODE:
            issues.append("DEV_MODE=true（应使用真实数据库与对象存储）")
        if not settings.COOKIE_SECURE:
            issues.append("COOKIE_SECURE=false（HTTPS 下会话 Cookie 不安全）")
        if settings.STORAGE_BACKEND == "local":
            issues.append("STORAGE_BACKEND=local（无预签名直传）")
        if str(settings.DATABASE_URL).startswith("sqlite"):
            issues.append("DATABASE_URL 指向 SQLite（应为 PostgreSQL+pgvector）")
        if settings.SESSION_SECRET == "change-me-in-prod":
            issues.append("SESSION_SECRET 仍为默认值")
    for issue in issues:
        log.error("生产配置不一致：%s", issue)
    if issues:
        log.error("以上配置与 APP_ENV=prod 冲突，上线门禁 G3/G2 不会通过；请修正后重启。")
    elif not prod:
        log.info("当前为 dev 运行栈；上线前须在生产栈（pgvector/Redis/MinIO/HTTPS）重跑验收。")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _check_runtime_consistency()
    # 结构自检：多 Agent 并行期出现过「模型加了列但没带迁移」，旧库上建卡片直接
    # TASK-500。这里启动即对齐（幂等），并把变更数打到日志，绝不静默。
    try:
        from app.db.migrations import run_migrations
        from app.db.session import engine
        n = run_migrations(engine)
        if n:
            log.warning("schema drift repaired at startup: %d DDL changes（请确认 alembic head 已对齐）", n)
        else:
            log.info("schema up to date")
    except Exception as e:  # noqa: BLE001  结构自检失败不阻断启动，但必须留痕
        log.error("schema self-check failed: %s", e)
    # S6：MinIO 可能比 app 慢就绪（compose 用 service_started），失败要重试并留痕，
    # 不能像以前那样静默 pass——否则存储不可用会让所有上传失败且无日志可查。
    for attempt in range(1, 6):
        try:
            ensure_bucket()
            log.info("storage bucket ready")
            break
        except Exception as e:
            log.warning("ensure_bucket attempt %d/5 failed: %s", attempt, e)
            if attempt == 5:
                log.error("storage bucket unavailable after 5 attempts; uploads will fail")
            else:
                await asyncio.sleep(2 * attempt)
    # 配置中心：首次启动把 .env 里的 Key 加密写入 DB，之后可在设置页维护
    try:
        from app.db.session import SessionLocal
        from app.services.settings_store import refresh_cache, seed_defaults
        _db = SessionLocal()
        try:
            seed_defaults(_db)
            log.info("配置中心生效模型：%s", refresh_cache(_db))
        finally:
            _db.close()
    except Exception as e:  # noqa: BLE001
        log.warning("配置中心初始化失败（不影响启动）：%s", e)

    register_all()
    runner.start()
    yield


_IS_PROD = settings.APP_ENV.lower() in ("prod", "production", "live")
app = FastAPI(
    title="GFLC API", version="0.2.0", lifespan=lifespan,
    # 接口文档挪到 /api/docs：/docs 已被前端「文档」页面占用，dev 下会被 Swagger 抢走路由
    docs_url=None if _IS_PROD else "/api/docs",
    redoc_url=None if _IS_PROD else "/api/redoc",
    openapi_url=None if _IS_PROD else "/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.add_exception_handler(APIError, api_error_handler)
app.add_exception_handler(Exception, unhandled_handler)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = uuid.uuid4().hex[:12]
    resp = await call_next(request)
    resp.headers["X-Request-ID"] = request.state.request_id
    return resp


@app.get("/health")
async def health():
    return {"ok": True, "data": {"status": "up", "app": settings.APP_NAME}}


@app.get(settings.API_PREFIX + "/config")
async def client_config():
    return {"ok": True, "data": {
        "mock_ai": settings.MOCK_AI or not settings.LLM_API_KEY,
        "storage": settings.STORAGE_BACKEND,
        "max_upload_mb": settings.MAX_UPLOAD_MB,
    }}


app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(documents.router, prefix=settings.API_PREFIX)
app.include_router(decks.router, prefix=settings.API_PREFIX)
app.include_router(notes.router, prefix=settings.API_PREFIX)
app.include_router(review.router, prefix=settings.API_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_PREFIX)
app.include_router(questions.router, prefix=settings.API_PREFIX)
app.include_router(quiz.router, prefix=settings.API_PREFIX)
app.include_router(plans.router, prefix=settings.API_PREFIX)
app.include_router(qa.router, prefix=settings.API_PREFIX)
app.include_router(videos.router, prefix=settings.API_PREFIX)
app.include_router(tasks.router, prefix=settings.API_PREFIX)
app.include_router(settings_router.router, prefix=settings.API_PREFIX)

class SPAStaticFiles(StaticFiles):
    """React Router 深链接回退：未知的非 API 路径返回 index.html。

    与 Vite/React 的 BrowserRouter 配合；/api/* 仍保持原 404 语义，
    避免把接口拼写错误伪装成页面。
    """

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            # StaticFiles 抛的是 starlette 版 HTTPException（fastapi.HTTPException 是它的子类，
            # 只能接住子类接不住父类）——之前写 fastapi 版导致所有深链接都返回 JSON 404。
            if exc.status_code == 404 and not path.startswith("api/"):
                return await super().get_response("index.html", scope)
            raise


# 前端静态页（存在才挂载，避免本地无前端时报错）
_fd = settings.FRONTEND_DIR
if os.path.isdir(_fd):
    app.mount("/", SPAStaticFiles(directory=_fd, html=True), name="frontend")
