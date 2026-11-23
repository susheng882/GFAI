# -*- coding: utf-8 -*-
"""笔记：文件夹树 + 笔记 CRUD（含面包屑）+ AI 协作（建议 / 插入 / 转卡片）。"""
import logging
import re
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.ai.prompts import NOTE_TIDY_SYSTEM, note_tidy_user
from app.ai.router import generate_json
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Card, CardAnchor, Note, NoteFolder
from app.routers.deps import get_current_user
from app.schemas.schemas import (FolderIn, FolderPatchIn, FolderOut, NoteAiIn,
                                 NoteIn, NoteInsertIn, NotePatchIn)
from app.services import note_ai
from app.services.cards import apply_note_anchors, collect_note_anchors, sync_note_anchors

router = APIRouter(prefix="/notes", tags=["notes"])

LOG = logging.getLogger(__name__)
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
    sync_note_anchors(db, n, user.id)  # B12：正文变化即增量解析成卡行
    db.commit()
    db.refresh(n)
    _vault_sync_one(db, user, n)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.post("/{note_id}/to-cards")
async def note_to_cards(note_id: int, user=Depends(get_current_user),
                        db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    cards, deck_id = await note_ai.to_cards(db, user.id, n)
    return {"ok": True, "data": {"cards": cards, "deck_id": deck_id}}


# ---------- 笔记 CRUD ----------
# ---------- 本地 vault（方案二：笔记落成 .md 文件）----------
class VaultIn(BaseModel):
    dir: str = ""
    auto: bool = True


def _vault_dir(db: Session) -> str:
    from app.services import settings_store as _ss
    return (_ss.get_runtime(db, "vault_dir", "") or "").strip()


def _vault_sync_one(db: Session, user, note) -> None:
    """保存后增量写文件；vault 未配置或关闭自动同步时静默跳过。"""
    from app.services import settings_store as _ss
    from app.services import vault as vault_svc
    d = _vault_dir(db)
    if not d or _ss.get_runtime(db, "vault_auto", "1") != "1":
        return
    try:
        vault_svc.export_notes(db, user.id, d, only_id=note.id)
    except Exception as e:  # noqa: BLE001  同步失败不影响保存
        import logging
        logging.getLogger(__name__).warning("vault 增量同步失败：%s", e)


@router.get("/vault")
def vault_status(user=Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    d = _vault_dir(db)
    exists = bool(d) and os.path.isdir(d)
    count = db.scalar(select(func.count()).select_from(Note)
                      .where(Note.user_id == user.id, Note.kind == "note")) or 0
    return {"ok": True, "data": {"dir": d, "exists": exists,
                                 "writable": os.access(d, os.W_OK) if exists else False,
                                 "notes": int(count)}}


@router.put("/vault")
def vault_set(body: VaultIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    from app.services import settings_store as _ss
    d = (body.dir or "").strip()
    if d:
        try:
            os.makedirs(d, exist_ok=True)
        except OSError as e:
            raise APIError(ErrCode.COMMON_400, f"目录不可用：{e}", 400) from e
        if not os.access(d, os.W_OK):
            raise APIError(ErrCode.COMMON_400, "目录没有写权限", 400)
    _ss.set_runtime(db, "vault_dir", d)
    _ss.set_runtime(db, "vault_auto", "1" if body.auto else "0")
    return {"ok": True, "data": {"dir": d, "auto": body.auto}}


@router.post("/vault/export")
def vault_export(user=Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services import vault as vault_svc
    d = _vault_dir(db)
    if not d:
        raise APIError(ErrCode.COMMON_400, "还没设置本地文件夹", 400)
    return {"ok": True, "data": vault_svc.export_notes(db, user.id, d)}


@router.post("/vault/import")
def vault_import(user=Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services import vault as vault_svc
    d = _vault_dir(db)
    if not d:
        raise APIError(ErrCode.COMMON_400, "还没设置本地文件夹", 400)
    return {"ok": True, "data": vault_svc.import_notes(db, user.id, d)}


@router.get("/{note_id}")
async def get_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


# ---------- B12：同源成卡行 ----------
@router.get("/{note_id}/anchors")
def note_anchors(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """成卡行列表 + 同步状态（已同步 / 待同步 / 源已改）+ 来源笔记标题。"""
    n = _own_note(db, note_id, user.id)
    return {"ok": True, "data": collect_note_anchors(db, n, user.id)}


@router.post("/{note_id}/anchors/apply")
def note_anchors_apply(note_id: int, user=Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """用户显式点「同步卡片」：生成/更新卡片，返回更新 N / 新增 M / 跳过 K。"""
    n = _own_note(db, note_id, user.id)
    return {"ok": True, "data": apply_note_anchors(db, n, user.id)}


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
    db.flush()
    sync_note_anchors(db, n, user.id)  # B12：新建即解析「正面 :: 背面」行，原文不动
    db.commit()
    db.refresh(n)
    _vault_sync_one(db, user, n)
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
    if body.content is not None:
        sync_note_anchors(db, n, user.id)  # B12：改正文后锚点 hash 更新，卡片待用户显式同步
    db.commit()
    db.refresh(n)
    _vault_sync_one(db, user, n)
    return {"ok": True, "data": _note_out(n, _folder_path(_folder_map(db, user.id), n.folder_id))}


@router.delete("/{note_id}")
async def delete_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    # B12：笔记删除时锚点级联删除；派生卡片不删除，只清空来源字段使其退化为独立卡
    anchor_cnt = db.execute(delete(CardAnchor).where(CardAnchor.note_id == note_id,
                                                     CardAnchor.user_id == user.id)).rowcount or 0
    card_cnt = db.execute(
        update(Card).where(Card.user_id == user.id, Card.source_note_id == note_id)
        .values(source_note_id=None, anchor_id=None, source_hash=None)).rowcount or 0
    db.delete(n)
    db.commit()
    LOG.info("删除笔记：note_id=%s 级联删除锚点=%s 解绑派生卡片=%s（卡片保留）",
             note_id, anchor_cnt, card_cnt)
    return {"ok": True, "data": {"deleted": 1, "anchors_removed": int(anchor_cnt),
                                 "cards_detached": int(card_cnt)}}

# ---------- 双链 / 文件操作（W2）----------
_WIKI = re.compile(r"\[\[([^\]\n]{1,80})\]\]")


@router.get("/{note_id}/links")
def note_links(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """出链（本文 [[X]]）+ 反链（哪些笔记引用了本文）。对标 Obsidian 的双链面板。"""
    n = _own_note(db, note_id, user.id)
    outgoing, seen = [], set()
    for m in _WIKI.finditer(n.content or ""):
        title = m.group(1).strip()
        if not title or title in seen:
            continue
        seen.add(title)
        tgt = db.scalar(select(Note).where(Note.user_id == user.id, Note.title == title).limit(1))
        outgoing.append({"title": title, "note_id": tgt.id if tgt else None})
    backlinks = []
    if (n.title or "").strip():
        rows = db.scalars(select(Note).where(Note.user_id == user.id, Note.id != n.id,
                                             Note.content.ilike(f"%[[{n.title}]]%")).limit(50)).all()
        backlinks = [{"id": b.id, "title": b.title, "snippet": (b.content or "").replace("\n", " ")[:80]}
                     for b in rows]
    return {"ok": True, "data": {"outgoing": outgoing, "backlinks": backlinks}}


@router.post("/{note_id}/duplicate")
def duplicate_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    n = _own_note(db, note_id, user.id)
    dup = Note(user_id=user.id, document_id=n.document_id, folder_id=n.folder_id,
               title=f"{n.title} (副本)"[:256],
               summary=n.summary or "", content=n.content or "", points=n.points or [],
               source="manual", kind=n.kind or "note")
    db.add(dup)
    db.commit()
    db.refresh(dup)
    return {"ok": True, "data": _note_out(dup, _folder_path(_folder_map(db, user.id), dup.folder_id))}


@router.get("/{note_id}/export")
def export_note(note_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """导出 Markdown（frontmatter 带标题与时间，可直接进 Obsidian）。"""
    n = _own_note(db, note_id, user.id)
    body = (n.content or "").strip()
    head = f"# {n.title or '未命名'}\n\n"
    md = head + body if not body.startswith("#") else body
    from urllib.parse import quote
    filename = quote(f"{n.title or 'note'}.md")
    return Response(content=md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})
