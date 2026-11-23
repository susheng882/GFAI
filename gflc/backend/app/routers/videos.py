# -*- coding: utf-8 -*-
"""视频：上传/链接 → 后台任务（抽音频→转写→切块→多模板笔记）。
另提供历史视频列表、某视频的笔记与转写、关键帧图、删除。"""
import os
import re
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Card, CardDeck, Chunk, Document, Note, Task
from app.routers.deps import get_current_user
from app.services.storage import get_storage
from app.worker import runner

router = APIRouter(prefix="/videos", tags=["videos"])
_ALLOWED = {".mp4", ".mkv", ".mov", ".webm", ".m4a", ".mp3", ".wav", ".flac", ".aac", ".m4v"}
_TEMPLATES = ("summary", "outline", "qa")


def _frame_dir() -> str:
    """关键帧图目录（与后台抽帧写入目录保持一致）。"""
    return os.path.join(os.path.abspath(settings.LOCAL_STORAGE_DIR), "frames")


def _sections_from_md(md: str) -> list[dict]:
    """从图文笔记 Markdown 中还原 sections（`## [mm:ss] 标题`）。"""
    out: list[dict] = []
    for block in (md or "").split("\n## ")[1:]:
        head, _, body = block.partition("\n")
        m = re.match(r"^\[([^\]]*)\]\s*(.*)$", head.strip())
        if not m:  # 非「[mm:ss] 标题」的区块（如末尾关键帧清单）不算正文小节
            continue
        out.append({"ts": m.group(1).strip(), "title": m.group(2).strip(), "content": body.strip()})
    return out


def _parse_templates(raw) -> list[str]:
    """支持逗号分隔字符串或列表，去重并校验。"""
    if isinstance(raw, str):
        items = raw.replace("，", ",").split(",")
    else:
        items = list(raw or [])
    out: list[str] = []
    for t in items:
        t = str(t).strip().lower()
        if not t:
            continue
        if t not in _TEMPLATES:
            raise APIError(ErrCode.COMMON_400, f"不支持的笔记模板：{t}（可选 summary/outline/qa）")
        if t not in out:
            out.append(t)
    return out or ["summary"]


class VideoUrlIn(BaseModel):
    url: str
    title: str = ""
    templates: list[str] = ["summary"]


@router.post("/upload")
async def upload_video(file: UploadFile = File(...), templates: str = Form("summary"),
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED:
        raise APIError(ErrCode.FILE_002, f"不支持 {ext}（支持常见视频/音频格式）")
    tpls = _parse_templates(templates)
    data = await file.read()
    if len(data) > settings.MAX_UPLOAD_MB * 1024 * 1024:
        raise APIError(ErrCode.FILE_001, "文件超过上限")
    tmp = os.path.join(tempfile.gettempdir(), f"gflc_up_{uuid.uuid4().hex}{ext}")
    with open(tmp, "wb") as f:
        f.write(data)
    t = runner.create_task(db, user.id, "video_upload")
    runner.submit(t.id, "video_upload",
                  {"path": tmp, "title": file.filename or "视频", "templates": tpls})
    return {"ok": True, "data": {"task_id": t.id}}


@router.post("/url")
async def from_url(body: VideoUrlIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not (body.url or "").strip():
        raise APIError(ErrCode.COMMON_400, "请提供视频链接")
    tpls = _parse_templates(body.templates)
    t = runner.create_task(db, user.id, "video_url")
    runner.submit(t.id, "video_url",
                  {"url": body.url.strip(), "title": body.title or "链接视频", "templates": tpls})
    return {"ok": True, "data": {"task_id": t.id}}


@router.get("/frames/{filename}")
async def get_frame(filename: str, user=Depends(get_current_user)):
    """关键帧图片（仅限 frames 目录内的文件名，禁止路径穿越）。"""
    name = (filename or "").strip()
    if (not name or name != os.path.basename(name) or ".." in name
            or "/" in name or "\\" in name or not name.lower().endswith((".jpg", ".jpeg", ".png"))):
        raise APIError(ErrCode.COMMON_400, "非法文件名")
    path = os.path.join(_frame_dir(), name)
    if not os.path.isfile(path):
        raise APIError(ErrCode.FILE_002, "帧图不存在", 404)
    return FileResponse(path, media_type="image/jpeg")


def _segment_map(db: Session, user_id: int) -> dict[int, int]:
    """从历史任务结果里取每个视频的转写分段数。"""
    out: dict[int, int] = {}
    rows = db.scalars(select(Task).where(Task.user_id == user_id,
                                         Task.type.in_(("video_upload", "video_url")))
                      .order_by(Task.id.desc()).limit(100)).all()
    for t in rows:
        r = t.result or {}
        did = r.get("document_id")
        if did and int(did) not in out:
            out[int(did)] = int(r.get("segments") or 0)
    return out


@router.get("")
async def list_videos(user=Depends(get_current_user), db: Session = Depends(get_db)):
    docs = list(db.scalars(select(Document).where(Document.user_id == user.id,
                                                  Document.source_type == "video")
                           .order_by(Document.id.desc()).limit(30)))
    ids = [d.id for d in docs]
    notes_map: dict[int, list[dict]] = {}
    chunk_map: dict[int, int] = {}
    if ids:
        for n in db.scalars(select(Note).where(Note.document_id.in_(ids)).order_by(Note.id)).all():
            notes_map.setdefault(n.document_id, []).append(
                {"id": n.id, "kind": n.kind, "title": n.title})
        for did, c in db.execute(select(Chunk.document_id, func.count(Chunk.id))
                                 .where(Chunk.document_id.in_(ids))
                                 .group_by(Chunk.document_id)).all():
            chunk_map[int(did)] = int(c)
    seg_map = _segment_map(db, user.id)
    data = [{
        "document_id": d.id,
        "title": d.title,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "segments": seg_map.get(d.id, 0),
        "chunks": chunk_map.get(d.id, 0),
        "notes": notes_map.get(d.id, []),
    } for d in docs]
    return {"ok": True, "data": data}


@router.get("/{document_id}/notes")
async def video_notes(document_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, document_id, user.id)
    if not doc or doc.source_type != "video":
        raise APIError(ErrCode.AUTH_403, "无权访问该视频", 403)
    notes = list(db.scalars(select(Note).where(Note.document_id == doc.id).order_by(Note.id)))
    chunks = list(db.scalars(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.chunk_index)))
    frames: list[dict] = []
    frame_note: dict = {"summary": "", "sections": [], "markdown": ""}
    for n in notes:
        if n.kind == "frames":
            frames = n.points if isinstance(n.points, list) else []
            frame_note = {"summary": n.summary or "", "sections": _sections_from_md(n.content or ""),
                          "markdown": n.content or ""}
            break
    return {"ok": True, "data": {
        "document_id": doc.id,
        "title": doc.title,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "transcript": [{
            "start": round(c.ts_start, 1) if c.ts_start is not None else None,
            "end": round(c.ts_end, 1) if c.ts_end is not None else None,
            "text": c.content,
        } for c in chunks],
        "notes": [{
            "id": n.id, "kind": n.kind, "title": n.title, "summary": n.summary,
            "content": n.content, "points": n.points or [],
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in notes],
        "frames": frames,
        "frame_note": frame_note,
    }}


@router.delete("/{document_id}")
async def delete_video(document_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    doc = crud.get_document(db, document_id, user.id)
    if not doc or doc.source_type != "video":
        raise APIError(ErrCode.AUTH_403, "无权访问该视频", 403)
    n_notes = db.query(Note).filter(Note.document_id == doc.id).delete(synchronize_session=False)
    n_chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).delete(synchronize_session=False)
    n_cards = db.query(Card).filter(Card.document_id == doc.id).delete(synchronize_session=False)
    n_decks = db.query(CardDeck).filter(CardDeck.document_id == doc.id).delete(synchronize_session=False)
    db.delete(doc)
    db.commit()
    return {"ok": True, "data": {"deleted": True, "notes": n_notes, "chunks": n_chunks,
                                "cards": n_cards, "decks": n_decks}}

@router.get("/{document_id}/stream")
async def stream_video(document_id: int, request: Request,
                       user=Depends(get_current_user), db: Session = Depends(get_db)):
    """本地存储的视频流式返回，**支持 Range**（浏览器才能拖进度/秒开）。

    Starlette 0.37 的 FileResponse 不带 Range 支持（实测请求 bytes=0-1023 返回 200 + 全量
    55MB），所以这里自己实现 206 分段响应。
    """
    from fastapi.responses import StreamingResponse
    from app.models.models import Document
    from app.services.storage import LocalStorage, get_storage

    doc = db.get(Document, document_id)
    if not doc or doc.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权访问该视频", 403)
    if not doc.storage_key:
        raise APIError(ErrCode.COMMON_404, "该记录没有关联的视频文件", 404)
    st = get_storage()
    if not isinstance(st, LocalStorage):
        raise APIError(ErrCode.COMMON_400, "当前存储后端不支持在线播放", 400)
    path = st._path(doc.storage_key)
    if not os.path.exists(path):
        raise APIError(ErrCode.COMMON_404, "视频文件已不存在", 404)

    # 历史数据里 mime 被写成 "video/*"（非法通配），浏览器会直接拒绝播放 → 按真实后缀兜底
    media = (doc.mime or "").strip()
    if not media or "*" in media:
        import mimetypes
        media = mimetypes.guess_type(path)[0] or (
            "audio/mpeg" if path.endswith(".mp3") else "video/mp4")

    size = os.path.getsize(path)
    range_header = request.headers.get("range") or ""
    m = re.match(r"bytes=(\d*)-(\d*)", range_header.strip())
    if not m or (not m.group(1) and not m.group(2)):
        return StreamingResponse(_file_iter(path, 0, size - 1), media_type=media,
                                 headers={"Accept-Ranges": "bytes", "Content-Length": str(size),
                                          "Content-Disposition": _disposition(doc.title)})

    if m.group(1):
        start = int(m.group(1))
        end = int(m.group(2)) if m.group(2) else size - 1
    else:  # bytes=-N 表示末尾 N 字节
        start = max(0, size - int(m.group(2)))
        end = size - 1
    if start >= size:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{size}"})
    end = min(end, size - 1)
    return StreamingResponse(_file_iter(path, start, end), status_code=206, media_type=media,
                             headers={"Accept-Ranges": "bytes",
                                      "Content-Range": f"bytes {start}-{end}/{size}",
                                      "Content-Length": str(end - start + 1),
                                      "Content-Disposition": _disposition(doc.title)})


def _file_iter(path: str, start: int, end: int, chunk: int = 256 * 1024):
    with open(path, "rb") as f:
        f.seek(start)
        remain = end - start + 1
        while remain > 0:
            block = f.read(min(chunk, remain))
            if not block:
                break
            remain -= len(block)
            yield block


def _disposition(title: str) -> str:
    from urllib.parse import quote
    return f"inline; filename*=UTF-8''{quote(title or 'video')}"
