# -*- coding: utf-8 -*-
"""笔记：文件夹树 + 笔记 CRUD（含面包屑）+ AI 协作（建议 / 插入 / 转卡片）。"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.ai.prompts import NOTE_TIDY_SYSTEM, note_tidy_user
from app.ai.router import generate_json
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Note, NoteFolder
from app.routers.deps import get_current_user
from app.schemas.schemas import (FolderIn, FolderPatchIn, FolderOut, NoteAiIn,
                                 NoteIn, NoteInsertIn, NotePatchIn)
from app.services import note_ai

router = APIRouter(prefix="/notes", tags=["notes"])

_MAX_LIMIT = 500
_MAX_PAGE_SIZE = 100


class _TidyFolder(BaseModel):
    name: str = ""
    note_ids: list[int] = []
    reason: str = ""


class _TidyMerge(BaseModel):
    ids: list[int] = []
    reason: str = ""


class _TidyResult(BaseModel):
    summary: str = ""
    merge: list[_TidyMerge] = []
    folders: list[_TidyFolder] = []
    missing: list[str] = []
_KIND_RANK = {"project": 0, "subject": 1, "topic": 2}


def _own_note(db: Session, note_id: int, user_id: int) -> Note:
    n = db.scalar(select(Note).where(Note.id == note_id, Note.user_id == user_id))
    if not n:
        raise APIError(ErrCode.AUTH_403, "无权访问该笔记", 403)
    return n


def _own_folder(db: Session, folder_id: int, user_id: int) -> NoteFolder:
    f = db.scalar(select(NoteFolder).where(NoteFolder.id == folder_id,
                                           NoteFolder.user_id == user_id))
    if not f:
        raise APIError(ErrCode.AUTH_403, "无权访问该文件夹", 403)
    return f


def _folder_map(db: Session, user_id: int) -> dict[int, NoteFolder]:
    return {f.id: f for f in db.scalars(select(NoteFolder).where(NoteFolder.user_id == user_id))}


def _children_map(folders: dict[int, NoteFolder]) -> dict[int, list[NoteFolder]]:
    out: dict[int, list[NoteFolder]] = {}
    for f in folders.values():
        if f.parent_id and f.parent_id in folders:
            out.setdefault(f.parent_id, []).append(f)
    return out


def _subtree_ids(folders: dict[int, NoteFolder], root_id: int) -> list[int]:
    kids = _children_map(folders)
    out, stack = [], [root_id]
    while stack:
        cur = stack.pop()
        out.append(cur)
        stack.extend(f.id for f in kids.get(cur, []))
    return out


def _folder_path(folders: dict[int, NoteFolder], folder_id: int | None) -> str:
    """「考研/数学/极限」：沿 parent 链上行，防环。"""
    names, cur, seen = [], folder_id, set()
    while cur and cur in folders and cur not in seen:
        seen.add(cur)
        f = folders[cur]
        names.append(f.name or "")
        cur = f.parent_id
    return "/".join(reversed([n for n in names if n]))


def _sort_key(f: NoteFolder):
    return (_KIND_RANK.get(f.kind or "topic", 9), f.sort or 0, f.id)


def _note_out(n: Note, folder_path: str) -> dict:
    return {"id": n.id, "document_id": n.document_id, "folder_id": n.folder_id,
            "title": n.title or "", "summary": n.summary or "", "content": n.content,
            "points": n.points or [], "source": n.source or "manual", "kind": n.kind or "note",
            "created_at": n.created_at.isoformat() if n.created_at else None,
            "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            "folder_path": folder_path}


def _note_counts(db: Session, user_id: int) -> dict[int, int]:
    rows = db.execute(
        select(Note.folder_id, func.count(Note.id))
        .where(Note.user_id == user_id, Note.folder_id.is_not(None))
        .group_by(Note.folder_id)
    ).all()
    return {int(fid): int(cnt or 0) for fid, cnt in rows}


# ---------- 文件夹树 ----------
@router.get("/folders")
async def list_folders(user=Depends(get_current_user), db: Session = Depends(get_db)):
    folders = _folder_map(db, user.id)
    counts = _note_counts(db, user.id)
    kids = _children_map(folders)

    # 一次 group by 后把数量沿 parent 链累加到祖先
    total = dict(counts)
    for fid, cnt in counts.items():
        cur, seen = folders[fid].parent_id, {fid}
        while cur and cur in folders and cur not in seen:
            seen.add(cur)
            total[cur] = total.get(cur, 0) + cnt
            cur = folders[cur].parent_id

    def dump(f: NoteFolder) -> dict:
        return FolderOut(
            id=f.id, parent_id=f.parent_id, name=f.name, kind=f.kind or "topic",
            sort=f.sort or 0, note_count=total.get(f.id, 0),
            children=[dump(k) for k in sorted(kids.get(f.id, []), key=_sort_key)],
        ).model_dump()

    tops = sorted((f for f in folders.values()
                   if not f.parent_id or f.parent_id not in folders), key=_sort_key)
    return {"ok": True, "data": [dump(f) for f in tops]}


@router.post("/folders")
async def create_folder(body: FolderIn, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    if body.parent_id is not None:
        _own_folder(db, body.parent_id, user.id)
    f = NoteFolder(user_id=user.id, parent_id=body.parent_id,
                   name=body.name.strip()[:200], kind=body.kind or "topic", sort=0)
    db.add(f)
    db.commit()
    db.refresh(f)
    return {"ok": True, "data": FolderOut(id=f.id, parent_id=f.parent_id, name=f.name,
                                          kind=f.kind or "topic", sort=f.sort or 0).model_dump()}


@router.patch("/folders/{folder_id}")
async def patch_folder(folder_id: int, body: FolderPatchIn, user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    f = _own_folder(db, folder_id, user.id)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise APIError(ErrCode.COMMON_400, "文件夹名不能为空")
        f.name = name[:200]
    if body.sort is not None:
        f.sort = body.sort
    if "parent_id" in body.model_fields_set:
        new_parent = body.parent_id
        if new_parent is not None:
            _own_folder(db, new_parent, user.id)
            # 禁止挂到自身或自己的子孙下
            folders = _folder_map(db, user.id)
            if new_parent in _subtree_ids(folders, f.id):
                raise APIError(ErrCode.COMMON_400, "不能移动到自身或其子文件夹下")
        f.parent_id = new_parent

    db.commit()
    db.refresh(f)
    return {"ok": True, "data": FolderOut(id=f.id, parent_id=f.parent_id, name=f.name,
                                          kind=f.kind or "topic", sort=f.sort or 0).model_dump()}


@router.delete("/folders/{folder_id}")
async def delete_folder(folder_id: int, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    _own_folder(db, folder_id, user.id)
    ids = _subtree_ids(_folder_map(db, user.id), folder_id)
    # 笔记只解绑，不随文件夹删除
    detached = db.execute(update(Note)
                          .where(Note.user_id == user.id, Note.folder_id.in_(ids))
                          .values(folder_id=None)).rowcount or 0
    db.execute(delete(NoteFolder).where(NoteFolder.id.in_(ids), NoteFolder.user_id == user.id))
    db.commit()
    return {"ok": True, "data": {"deleted": len(ids), "notes_kept": int(detached)}}


# ---------- 笔记列表 / 最近 ----------
@router.post("/tidy")
async def tidy_folder(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """AI 整理：分析文件夹内笔记，给出合并/归类/缺失建议（只建议，不自动改）。"""
    folder_id = body.get("folder_id")
    folders = _folder_map(db, user.id)
    stmt = select(Note).where(Note.user_id == user.id)
    fname = "全部笔记"
    if folder_id:
        fid = int(folder_id)
        _own_folder(db, fid, user.id)
        stmt = stmt.where(Note.folder_id.in_(_subtree_ids(folders, fid)))
        fname = _folder_path(folders, fid) or "文件夹"
    rows = list(db.scalars(stmt.order_by(Note.id.desc()).limit(60)))
    if len(rows) < 2:
        raise APIError(ErrCode.COMMON_400, "至少需要 2 篇笔记才能整理")
    items = [{"id": n.id, "title": n.title or "",
              "summary": (n.summary or n.content or "")[:150]} for n in rows]
    try:
        obj, _ = await generate_json("mid", NOTE_TIDY_SYSTEM, note_tidy_user(fname, items), _TidyResult)
        data = obj.model_dump()
    except APIError:
        raise
    except Exception as e:
        raise APIError(ErrCode.AI_001, f"整理失败：{str(e)[:120]}") from e
    title_map = {x["id"]: x["title"] for x in items}
    for g in data.get("folders") or []:
        g["titles"] = [title_map.get(i, str(i)) for i in (g.get("note_ids") or [])]
    for g in data.get("merge") or []:
        g["titles"] = [title_map.get(i, str(i)) for i in (g.get("ids") or [])]
    data["folder"] = fname
    data["scanned"] = len(items)
    return {"ok": True, "data": data}


@router.post("/tidy/apply")
async def tidy_apply(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """用户确认后：新建子文件夹并把指定笔记移进去。"""
    name = (body.get("name") or "").strip()
    ids = [int(i) for i in (body.get("note_ids") or [])]
    parent = body.get("folder_id")
    if not name:
        raise APIError(ErrCode.COMMON_400, "请填写文件夹名称")
    if not ids:
        raise APIError(ErrCode.COMMON_400, "请选择要移动的笔记")
    parent_id = int(parent) if parent else None
    if parent_id:
        _own_folder(db, parent_id, user.id)
    # 同名文件夹已存在就复用，避免 AI 建议反复建重复目录
    nf = db.scalar(select(NoteFolder).where(NoteFolder.user_id == user.id,
                                            NoteFolder.parent_id.is_(parent_id) if parent_id is None
                                            else NoteFolder.parent_id == parent_id,
                                            NoteFolder.name == name[:200]))
    reused = nf is not None
    if nf is None:
        nf = NoteFolder(user_id=user.id, parent_id=parent_id, name=name[:200], kind="topic", sort=0)
        db.add(nf)
        db.flush()
    moved = db.query(Note).filter(Note.user_id == user.id, Note.id.in_(ids)).update(
        {"folder_id": nf.id}, synchronize_session=False)
    db.commit()
    return {"ok": True, "data": {"folder_id": nf.id, "name": nf.name,
                                "moved": int(moved or 0), "reused": reused}}


@router.get("/recent")
async def recent_notes(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(
        select(Note).where(Note.user_id == user.id)
        .order_by(Note.updated_at.desc(), Note.id.desc()).limit(10)))
    folders = _folder_map(db, user.id)
    return {"ok": True, "data": [_note_out(n, _folder_path(folders, n.folder_id)) for n in rows]}


@router.get("")
async def list_notes(folder_id: int | None = None, q: str = "", kind: str | None = None,
                     limit: int = 100, page: int | None = None, page_size: int = 30,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    """笔记列表。带 page 返回分页结构；不带 page 保持原来的纯 list（兼容老前端与脚本）。"""
    stmt = select(Note).where(Note.user_id == user.id)
    if folder_id is not None:
        _own_folder(db, folder_id, user.id)
        stmt = stmt.where(Note.folder_id.in_(_subtree_ids(_folder_map(db, user.id), folder_id)))
    kw = q.strip()
    if kw:
        like = f"%{kw}%"
        stmt = stmt.where(or_(Note.title.ilike(like), Note.content.ilike(like)))
    if kind:
        stmt = stmt.where(Note.kind == kind)
    order = (Note.updated_at.desc(), Note.id.desc())
    folders = _folder_map(db, user.id)

    if page is None:  # 兼容路径：老调用方（verify_all.py / 现有前端）
        limit = max(1, min(limit, _MAX_LIMIT))
        rows = list(db.scalars(stmt.order_by(*order).limit(limit)))
        return {"ok": True, "data": [_note_out(n, _folder_path(folders, n.folder_id)) for n in rows]}

    page = max(1, page)
    page_size = max(1, min(page_size, _MAX_PAGE_SIZE))
    try:
        total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
    except Exception:
        total = 0
    rows = list(db.scalars(stmt.order_by(*order)
                           .offset((page - 1) * page_size).limit(page_size)))
    pages = (total + page_size - 1) // page_size
    return {"ok": True, "data": {"items": [_note_out(n, _folder_path(folders, n.folder_id))
                                           for n in rows],
                                 "total": total, "page": page, "page_size": page_size,
                                 "pages": pages}}


# ---------- AI 协作 ----------
@router.post("/ai-suggest")
async def ai_suggest(body: NoteAiIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if body.note_id is not None:
        n = _own_note(db, body.note_id, user.id)
        if not body.title:
            body.title = n.title or ""
        if not body.content:
            body.content = n.content or ""
    out = await note_ai.suggest(db, user.id, body)
    return {"ok": True, "data": out.model_dump()}


@router.post("/insert")
async def insert_text(body: NoteInsertIn, user=Depends(get_current_user),
                      db: Session = Depends(get_db)):
    n = _own_note(db, body.note_id, user.id)
    text, cur = body.text, n.content or ""
    if body.position == "replace":
        n.content = text
    elif body.position == "prepend":
        n.content = text + ("\n\n" + cur if cur else "")
    else:
        n.content = cur + ("\n\n" + text if cur else text)
    db.commit()
    db.refresh(n)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.post("/{note_id}/to-cards")
async def note_to_cards(note_id: int, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    cards, deck_id = await note_ai.to_cards(db, user.id, n)
    return {"ok": True, "data": {"cards": cards, "deck_id": deck_id}}


# ---------- 笔记 CRUD ----------
@router.get("/{note_id}")
async def get_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.post("")
async def create_note(body: NoteIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if body.folder_id is not None:
        _own_folder(db, body.folder_id, user.id)
    title = (body.title or "").strip()[:256]
    # notes.document_id 非空：无关联文档时建占位文档，保证不触发 IntegrityError
    doc = crud.create_document(db, user_id=user.id, title=title or "无标题笔记",
                               source_type="note", content_hash=uuid.uuid4().hex,
                               storage_key="", size=0, mime="")
    n = Note(user_id=user.id, document_id=doc.id, folder_id=body.folder_id, title=title,
             summary=body.summary or "", content=body.content, points=body.points or [],
             source=body.source or "manual", kind=body.kind or "note")
    db.add(n)
    db.commit()
    db.refresh(n)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.patch("/{note_id}")
async def patch_note(note_id: int, body: NotePatchIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    if body.title is not None:
        n.title = body.title.strip()[:256]
    if body.summary is not None:
        n.summary = body.summary
    if body.content is not None:
        n.content = body.content
    if body.points is not None:
        n.points = body.points
    if "folder_id" in body.model_fields_set:
        if body.folder_id is not None:
            _own_folder(db, body.folder_id, user.id)
        n.folder_id = body.folder_id
    db.commit()
    db.refresh(n)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.delete("/{note_id}")
async def delete_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    db.delete(n)
    db.commit()
    return {"ok": True, "data": {"deleted": 1}}
