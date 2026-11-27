# -*- coding: utf-8 -*-
"""工作区（0012）：多工作区切换。当前仅工作区本身 CRUD；
数据隔离（documents/notes 等加 workspace_id）在 C8 验收时做，本模块先定接口契约。"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import User, Workspace
from app.routers.deps import get_current_user

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


class WsIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)


def _out(w: Workspace) -> dict:
    return {"id": w.id, "name": w.name, "current": bool(w.current),
            "created_at": w.created_at.isoformat() if w.created_at else None}


@router.get("")
async def list_workspaces(user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    rows = list(db.scalars(select(Workspace).where(Workspace.user_id == user.id)
                           .order_by(Workspace.id)))
    if not rows:
        # 无工作区时兜底建默认「默认工作区」并置当前
        w = Workspace(user_id=user.id, name="默认工作区", current=1,
                      created_at=datetime.now(timezone.utc))
        db.add(w)
        db.commit()
        db.refresh(w)
        rows = [w]
    return {"ok": True, "data": [_out(w) for w in rows]}


@router.post("")
async def create_workspace(body: WsIn, user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    w = Workspace(user_id=user.id, name=body.name.strip()[:80],
                  created_at=datetime.now(timezone.utc))
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"ok": True, "data": _out(w)}


@router.patch("/{ws_id}/current")
async def switch_workspace(ws_id: int, user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    w = db.scalar(select(Workspace).where(
        Workspace.id == ws_id, Workspace.user_id == user.id))
    if not w:
        raise APIError(ErrCode.COMMON_404, "工作区不存在", 404)
    db.execute(update(Workspace).where(Workspace.user_id == user.id)
               .values(current=0))
    w.current = 1
    db.commit()
    return {"ok": True, "data": _out(w)}


@router.patch("/{ws_id}")
async def rename_workspace(ws_id: int, body: WsIn,
                           user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    w = db.scalar(select(Workspace).where(
        Workspace.id == ws_id, Workspace.user_id == user.id))
    if not w:
        raise APIError(ErrCode.COMMON_404, "工作区不存在", 404)
    w.name = body.name.strip()[:80]
    db.commit()
    return {"ok": True, "data": _out(w)}


@router.delete("/{ws_id}")
async def delete_workspace(ws_id: int, user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    w = db.scalar(select(Workspace).where(
        Workspace.id == ws_id, Workspace.user_id == user.id))
    if not w:
        raise APIError(ErrCode.COMMON_404, "工作区不存在", 404)
    n_other = db.scalar(select(func.count()).select_from(Workspace)
                        .where(Workspace.user_id == user.id)) or 0
    if n_other <= 1:
        raise APIError(ErrCode.COMMON_400, "至少保留一个工作区")
    was_current = bool(w.current)
    db.delete(w)
    db.commit()
    if was_current:
        first = db.scalar(select(Workspace).where(Workspace.user_id == user.id)
                          .order_by(Workspace.id).limit(1))
        if first:
            db.execute(update(Workspace).where(Workspace.id == first.id)
                       .values(current=1))
            db.commit()
    return {"ok": True, "data": {"deleted": ws_id}}
