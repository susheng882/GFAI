# -*- coding: utf-8 -*-
"""统一错误码与异常，所有接口失败都返回 {ok:false, error:{code,message}, request_id}。"""
from fastapi import Request
from fastapi.responses import JSONResponse


class ErrCode:
    AUTH_401 = "AUTH-401"   # 未登录 / 会话失效
    AUTH_403 = "AUTH-403"   # 越权
    PARSE_001 = "PARSE-001"  # 文件不可读
    PARSE_002 = "PARSE-002"  # 暂无可抽取文本
    PARSE_003 = "PARSE-003"  # 切分失败
    AI_001 = "AI-001"        # 模型超时
    AI_002 = "AI-002"        # 引用缺失
    AI_003 = "AI-003"        # 契约校验失败
    AI_004 = "AI-004"        # 分数低于阈值拒答
    QUOTA_001 = "QUOTA-001"  # 超日配额
    QUOTA_002 = "QUOTA-002"  # 超单任务上限
    FILE_001 = "FILE-001"    # 超体积上限
    FILE_002 = "FILE-002"    # 格式不在白名单
    COMMON_400 = "COMMON-400"
    COMMON_404 = "COMMON-404"  # 资源不存在
    COMMON_500 = "COMMON-500"


class APIError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def _rid(request: Request) -> str:
    return getattr(request.state, "request_id", "")


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content={"ok": False, "error": {"code": exc.code, "message": exc.message}, "request_id": _rid(request)},
    )


async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": {"code": ErrCode.COMMON_500, "message": "服务器内部错误"}, "request_id": _rid(request)},
    )
