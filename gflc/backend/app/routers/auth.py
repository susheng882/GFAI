# -*- coding: utf-8 -*-
"""注册 / 登录 / 登出 / 当前用户 / 数据导出 / 账号注销。会话走 HttpOnly Cookie，密码 Argon2id。"""
import json
import threading
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.core.security import create_session, destroy_session, verify_password
from app.crud import crud
from app.db.session import get_db
from app.routers.deps import get_current_user
from app.schemas.schemas import LoginIn, RegisterIn, UserOut
from app.services.export_service import (
    EXPORT_SCHEMA_VERSION, build_export, purge_user_data, write_audit,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class DeleteIn(BaseModel):
    """注销入参：二次确认二选一——confirm=true 或当前密码。"""
    confirm: bool = False
    password: str | None = None

# S5：登录失败锁定（进程内；单 worker 足够，多实例需换 Redis 共享计数）
_MAX_LOGIN_FAILS = 5
_LOGIN_LOCK_SECONDS = 900
_login_fails: dict[str, tuple[int, float]] = {}
_login_lock = threading.Lock()


def _login_key(email: str, request: Request) -> str:
    ip = request.client.host if request.client else "-"
    return f"{email.strip().lower()}|{ip}"


def _check_login_limit(key: str) -> None:
    now = time.time()
    with _login_lock:
        cnt, first = _login_fails.get(key, (0, 0))
        if cnt >= _MAX_LOGIN_FAILS and now - first < _LOGIN_LOCK_SECONDS:
            left = int(_LOGIN_LOCK_SECONDS - (now - first))
            raise APIError(ErrCode.AUTH_401, f"登录失败次数过多，请在 {left} 秒后重试", 429)
        if now - first >= _LOGIN_LOCK_SECONDS:
            _login_fails.pop(key, None)


def _record_login_fail(key: str) -> None:
    now = time.time()
    with _login_lock:
        cnt, first = _login_fails.get(key, (0, now))
        _login_fails[key] = (cnt + 1, first)
        # 防止字典无限膨胀：顺手清理过期项
        if len(_login_fails) > 5000:
            for k in [k for k, (_, f) in _login_fails.items() if now - f >= _LOGIN_LOCK_SECONDS]:
                _login_fails.pop(k, None)


def _clear_login_fail(key: str) -> None:
    with _login_lock:
        _login_fails.pop(key, None)


def _set_cookie(response: Response, token: str):
    response.set_cookie(
        key=settings.SESSION_COOKIE, value=token, httponly=True,
        samesite="lax", secure=settings.COOKIE_SECURE, max_age=settings.SESSION_TTL_SECONDS, path="/",
    )


@router.post("/register")
async def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, body.email):
        raise APIError(ErrCode.COMMON_400, "邮箱已注册", 409)
    user = crud.create_user(db, body.email, body.password)
    token = await create_session(user.id)
    _set_cookie(response, token)
    return {"ok": True, "data": {"user": UserOut.model_validate(user).model_dump()}}


@router.post("/login")
async def login(body: LoginIn, response: Response, request: Request,
                db: Session = Depends(get_db)):
    key = _login_key(body.email, request)
    _check_login_limit(key)
    user = crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        _record_login_fail(key)
        raise APIError(ErrCode.AUTH_401, "邮箱或密码错误", 401)
    _clear_login_fail(key)
    token = await create_session(user.id)
    _set_cookie(response, token)
    return {"ok": True, "data": {"user": UserOut.model_validate(user).model_dump()}}


@router.post("/logout")
async def logout(request: Request, response: Response):
    await destroy_session(request.cookies.get(settings.SESSION_COOKIE, ""))
    response.delete_cookie(settings.SESSION_COOKIE, path="/")
    return {"ok": True, "data": None}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return {"ok": True, "data": {"user": UserOut.model_validate(user).model_dump()}}


def _require_second_factor(confirm: bool, password: str | None, user) -> None:
    """二次确认：confirm=true 或当前密码正确，二者任一即可，防止误触。"""
    if confirm:
        return
    if password and verify_password(password, user.password_hash):
        return
    raise APIError(ErrCode.COMMON_400, "请确认操作：携带 confirm=true 或提供当前密码", 400)


@router.get("/export")
async def export_account(request: Request, confirm: bool = False, password: str | None = None,
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    """V5：导出当前用户全部业务数据为机器可读 JSON 归档（敏感字段脱敏，留审计）。"""
    _require_second_factor(confirm, password, user)
    archive = build_export(db, user.id)
    write_audit(db, user.id, "export", request,
                detail="schema={}".format(EXPORT_SCHEMA_VERSION))
    db.commit()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    filename = "gflc-export-{}-{}.json".format(user.id, ts)
    return Response(
        content=json.dumps(archive, ensure_ascii=False, indent=2),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(filename)},
    )


@router.post("/delete")
async def delete_account(body: DeleteIn, request: Request, response: Response,
                         user=Depends(get_current_user), db: Session = Depends(get_db)):
    """V5：注销当前账号——级联清理业务数据/存储对象/检索缓存，销毁会话并留审计。"""
    _require_second_factor(body.confirm, body.password, user)
    token = request.cookies.get(settings.SESSION_COOKIE, "")
    result = purge_user_data(db, user.id, request)
    await destroy_session(token)
    response.delete_cookie(settings.SESSION_COOKIE, path="/")
    return {"ok": True, "data": result}
