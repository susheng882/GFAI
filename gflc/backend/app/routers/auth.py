# -*- coding: utf-8 -*-
"""注册 / 登录 / 登出 / 当前用户。会话走 HttpOnly Cookie，密码 Argon2id。"""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.core.security import create_session, destroy_session, verify_password
from app.crud import crud
from app.db.session import get_db
from app.routers.deps import get_current_user
from app.schemas.schemas import LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


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
async def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise APIError(ErrCode.AUTH_401, "邮箱或密码错误", 401)
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
