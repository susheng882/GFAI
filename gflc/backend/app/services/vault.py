# -*- coding: utf-8 -*-
"""本地 vault：把笔记落成磁盘上的 .md 文件（方案二 · 第一步）。

当前形态：**数据库为主、文件为镜像**（单向导出 + 反向导入），不做文件监听。
等桌面壳接上 Tauri fs 之后，再把「谁是真源」反过来（文件为主、DB 为索引）。

约定（与 Obsidian 互认）：
    <vault>/<项目>/<科目>/<标题>.md
    frontmatter 带 gflc_id / updated / folder，外部改了内容也能按 id 找回原笔记
"""
import logging
import os
import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Note, NoteFolder

_log = logging.getLogger(__name__)

_BAD_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')
_FRONT = re.compile(r"^---\n(.*?)\n---\n?", re.S)


def safe_name(name: str, fallback: str = "未命名") -> str:
    """文件名清洗：去非法字符、压缩空白、限长（Windows 260 路径限制）。"""
    s = _BAD_CHARS.sub("_", (name or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s or fallback)[:120]


def folder_map(db: Session, user_id: int) -> dict[int, NoteFolder]:
    rows = db.scalars(select(NoteFolder).where(NoteFolder.user_id == user_id)).all()
    return {f.id: f for f in rows}


def folder_path(folders: dict[int, NoteFolder], folder_id: int | None) -> list[str]:
    names, cur, seen = [], folder_id, set()
    while cur and cur in folders and cur not in seen:
        seen.add(cur)
        f = folders[cur]
        names.append(safe_name(f.name or "", "未命名分类"))
        cur = f.parent_id
    return list(reversed(names))


def note_path(vault: str, folders: dict[int, NoteFolder], note: Note) -> str:
    parts = [safe_name(p) for p in folder_path(folders, note.folder_id)]
    return os.path.join(vault, *parts, f"{safe_name(note.title, '未命名笔记')}.md")


def render_note(note: Note, folders: dict[int, NoteFolder]) -> str:
    """frontmatter + 正文。frontmatter 用 Obsidian 也认的简单 YAML。"""
    ts = (note.updated_at or note.created_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M")
    tags = note.source or "manual"
    head = (
        "---\n"
        f"gflc_id: {note.id}\n"
        f"title: {note.title or ''}\n"
        f"folder: {'/'.join(folder_path(folders, note.folder_id))}\n"
        f"updated: {ts}\n"
        f"source: {tags}\n"
        "---\n\n"
    )
    return head + (note.content or "").strip() + "\n"


def _atomic_write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".gflc-tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)  # 原子替换，避免写一半断电留下坏文件


def export_notes(db: Session, user_id: int, vault: str, *, only_id: int | None = None) -> dict:
    """把笔记写成 .md 文件。only_id 指定单篇（保存时增量写）。"""
    if not vault:
        return {"ok": False, "reason": "未配置 vault 目录", "written": 0}
    folders = folder_map(db, user_id)
    stmt = select(Note).where(Note.user_id == user_id, Note.kind == "note")
    if only_id:
        stmt = stmt.where(Note.id == only_id)
    notes = db.scalars(stmt).all()
    written, failed = 0, []
    used: dict[str, int] = {}
    for n in notes:
        try:
            path = note_path(vault, folders, n)
            # 同名不同 id 时加后缀，避免互相覆盖
            if path in used and used[path] != n.id:
                base, ext = os.path.splitext(path)
                path = f"{base} ({n.id}){ext}"
            used[path] = n.id
            _atomic_write(path, render_note(n, folders))
            written += 1
        except OSError as e:
            failed.append({"id": n.id, "error": str(e)[:120]})
    _log.info("vault export user=%s written=%s failed=%s", user_id, written, len(failed))
    return {"ok": True, "written": written, "failed": failed[:5], "vault": vault}


def _parse(text: str) -> tuple[dict, str]:
    m = _FRONT.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def _ensure_import_doc(db: Session, user_id: int) -> int:
    """导入的笔记需要一个挂靠文档（NOT NULL 约束），建一个隐藏容器复用。"""
    from app.models.models import Document
    doc = db.scalar(select(Document).where(Document.user_id == user_id,
                                           Document.title == "[[vault]]").limit(1))
    if doc is None:
        doc = Document(user_id=user_id, title="[[vault]]", source_type="note",
                       content_hash=f"vault-{user_id}", storage_key="", size=0,
                       mime="text/markdown", status="ready")
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return doc.id


def import_notes(db: Session, user_id: int, vault: str) -> dict:
    """扫描 vault 里的 .md，按 gflc_id 更新已有笔记；没有 id 的新建。"""
    if not vault or not os.path.isdir(vault):
        return {"ok": False, "reason": "vault 目录不存在", "updated": 0, "created": 0}
    updated = created = 0
    for root, _dirs, files in os.walk(vault):
        for name in files:
            if not name.lower().endswith(".md"):
                continue
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                    raw = f.read()
            except OSError:
                continue
            meta, body = _parse(raw)
            nid = int(meta["gflc_id"]) if meta.get("gflc_id", "").isdigit() else None
            title = meta.get("title") or os.path.splitext(name)[0]
            note = db.get(Note, nid) if nid else None
            if note is not None and note.user_id == user_id:
                if (note.content or "").strip() != body.strip() or note.title != title:
                    note.content, note.title = body.strip(), title
                    updated += 1
            else:
                # 新文件：挂在「vault 导入」这个隐藏文档下（notes.document_id 是 NOT NULL）
                db.add(Note(user_id=user_id, document_id=_ensure_import_doc(db, user_id),
                            title=title, content=body.strip(), source="import", kind="note"))
                created += 1
    db.commit()
    _log.info("vault import user=%s updated=%s created=%s", user_id, updated, created)
    return {"ok": True, "updated": updated, "created": created, "vault": vault}
