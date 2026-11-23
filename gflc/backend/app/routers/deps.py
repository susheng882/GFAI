# -*- coding: utf-8 -*-
"""依赖：从 HttpOnly Cookie 会话解析当前用户，并做租户隔离。"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.budget import set_current_user_id
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.core.security import read_session
from app.crud import crud
from app.db.session import get_db


def _dev_bypass_allowed() -> bool:
    """开发期免登录：必须显式打开开关，且 APP_ENV 不是 prod。"""
    return bool(getattr(settings, "DEV_AUTH_BYPASS", False)) and \
        settings.APP_ENV.lower() not in ("prod", "production", "live")


def _dev_user(db: Session):
    email = getattr(settings, "DEV_BYPASS_EMAIL", "dev@local") or "dev@local"
    u = crud.get_user_by_email(db, email)
    if u is None:
        from app.models.models import User
        from app.core.security import hash_password
        u = User(email=email, password_hash=hash_password("dev123456"), status="active")
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    set_current_user_id(None)  # 防止同线程/协程复用残留上一个请求的身份
    token = request.cookies.get(settings.SESSION_COOKIE, "")
    uid = await read_session(token)
    if not uid:
        if _dev_bypass_allowed():
            user = _dev_user(db)
            set_current_user_id(user.id)
            return user
        raise APIError(ErrCode.AUTH_401, "未登录或会话已失效", 401)
    user = crud.get_user(db, uid)
    if not user or user.status != "active":
        raise APIError(ErrCode.AUTH_401, "账号不可用", 401)
    set_current_user_id(user.id)  # 供 ai 层做预算拦截
    return user
