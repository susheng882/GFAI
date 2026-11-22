# -*- coding: utf-8 -*-
"""GFLC FastAPI 入口：鉴权 + 上传 + PDF 解析切块 + 卡片 + 复习 + 仪表盘 + 前端静态页。"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.errors import APIError, api_error_handler, unhandled_handler
from app.routers import (auth, dashboard, decks, documents, notes, plans, qa,
                         questions, quiz, review, tasks, videos)
from app.services.storage import ensure_bucket
from app.worker import runner
from app.worker.handlers import register_all

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    register_all()
    runner.start()
    yield


_IS_PROD = settings.APP_ENV.lower() in ("prod", "production", "live")
app = FastAPI(
    title="GFLC API", version="0.2.0", lifespan=lifespan,
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
    openapi_url=None if _IS_PROD else "/openapi.json",
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

# 前端静态页（存在才挂载，避免本地无前端时报错）
_fd = settings.FRONTEND_DIR
if os.path.isdir(_fd):
    app.mount("/", StaticFiles(directory=_fd, html=True), name="frontend")
