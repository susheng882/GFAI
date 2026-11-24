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
# 导出 Markdown 的区块顺序：四类产物按「读一遍」的顺序排，时间戳原样保留
# 导出区块顺序：完整笔记（kind=markdown，内容最全）→ 摘要 → 大纲 → 问答 → 图文。
# 主笔记放最前，让「带走」的产物以完整叙述为主体，四类模板作为补充视角。
_EXPORT_BLOCKS = (("markdown", "完整笔记"), ("summary", "摘要"), ("outline", "大纲"),
                  ("qa", "问答"), ("frames", "图文"))


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


_FRAME_MD_RE = re.compile(r"!\[([^\]]*)\]\((/api/videos/frames/[^)\s]+)\)")


def _inline_frame_images(md: str) -> str:
    """把关键帧的相对 URL 内嵌为 base64，让导出的 md 脱离本服务也能显示图。

    找不到文件的关键帧保持原样（不丢图床链接，也不因缺文件让整篇导出失败）。
    """
    import base64
    import mimetypes

    def repl(m: re.Match) -> str:
        alt, url = m.group(1), m.group(2)
        name = os.path.basename(url.split("?")[0])
        path = os.path.join(_frame_dir(), name)
        if not os.path.isfile(path):
            return m.group(0)
        try:
            if os.path.getsize(path) > 4 * 1024 * 1024:   # 单图超过 4MB 不内嵌，避免 md 过大
                return m.group(0)
            mime = mimetypes.guess_type(path)[0] or "image/jpeg"
            b64 = base64.b64encode(open(path, "rb").read()).decode("ascii")
            return f"![{alt}](data:{mime};base64,{b64})"
        except Exception:  # noqa: BLE001  单图失败不影响整篇导出
            return m.group(0)

    return _FRAME_MD_RE.sub(repl, md)


def _demote_headings(md: str, by: int = 2) -> str:
    """正文标题整体降级，避免模板自带的 `##` 与导出文件的 `#`/`##` 撞层级。"""
    def _repl(m):
        return "#" * min(6, len(m.group(1)) + by) + " " + m.group(2)

    return re.sub(r"(?m)^(#{1,6})\s+(.*)$", _repl, md or "")


def _like_pattern(term: str) -> str:
    """关键词 → LIKE 模式；转义用户输入里的 % _ \\，避免被当成通配符。"""
    escaped = re.sub(r"([\\%_])", r"\\\1", term)
    return f"%{escaped}%"


def _snippet(text: str, term: str, span: int = 60) -> str:
    """命中词前后各取 span 字，命中的那一段用 ** 包住。"""
    body = text or ""
    pos = body.lower().find(term.lower())
    if pos < 0:  # 极端情况（大小写折叠差异）退化为开头一段
        return body[:span * 2].strip()
    start = max(0, pos - span)
    end = min(len(body), pos + len(term) + span)
    head = ("…" if start > 0 else "") + body[start:pos]
    tail = body[pos + len(term):end] + ("…" if end < len(body) else "")
    return f"{head}**{body[pos:pos + len(term)]}**{tail}".strip()


_TS_RE = re.compile(r"\[(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\]")


def _chunk_start_sec(chunk: Chunk) -> float | None:
    """起点秒数：优先转写元数据 ts_start，其次从内容开头的 [mm:ss] 解析。"""
    if chunk.ts_start is not None:
        return round(float(chunk.ts_start), 1)
    m = _TS_RE.search((chunk.content or "")[:40])
    if not m:
        return None
    return float(int(m.group(1) or 0) * 3600 + int(m.group(2)) * 60 + int(m.group(3)))


def _video_doc(db: Session, document_id: int, user_id: int) -> Document:
    """取自己的视频文档；不存在 404、类型不符 400，都带中文原因。"""
    doc = crud.get_document(db, document_id, user_id)
    if not doc:
        raise APIError(ErrCode.COMMON_404, "视频不存在或已被删除", 404)
    if doc.source_type != "video":
        raise APIError(ErrCode.COMMON_400, "该记录不是视频，没有可用的视频笔记", 400)
    return doc


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


@router.get("/{document_id}/export")
async def export_video_markdown(document_id: int, inline_images: int = 0,
                                user=Depends(get_current_user),
                                db: Session = Depends(get_db)):
    """导出整段视频的 Markdown：完整笔记 + 摘要/大纲/问答/图文，`[mm:ss]` 原样保留。

    inline_images=1 时把关键帧相对路径转成 base64 data URI，导出的 md 拿到别的机器
    也能看到图（代价是文件变大）；默认 0 保持轻量，图片走 /api/videos/frames 相对路径。
    """
    doc = _video_doc(db, document_id, user.id)
    rows = list(db.scalars(select(Note).where(Note.document_id == doc.id).order_by(Note.id)))
    by_kind: dict[str, Note] = {}
    for n in rows:
        by_kind.setdefault(n.kind, n)
    blocks = [(label, by_kind[kind]) for kind, label in _EXPORT_BLOCKS if by_kind.get(kind)]
    if not blocks:
        raise APIError(ErrCode.COMMON_404, "该视频还没有生成笔记，暂无可导出内容", 404)

    parts = [f"# {doc.title or '视频笔记'}", ""]
    for label, note in blocks:
        parts += [f"## {label}", ""]
        lines = (note.content or "").strip().split("\n")
        # 模板常以同名标题开头（摘要模板是 `## 摘要`），去掉它与区块标题重复
        if lines and re.fullmatch(r"#{1,6}\s*" + re.escape(label), lines[0].strip()):
            lines = lines[1:]
        body = _demote_headings("\n".join(lines).strip()).strip()
        parts += [body, ""] if body else ["（暂无内容）", ""]
    md = "\n".join(parts).strip() + "\n"
    if inline_images:
        md = _inline_frame_images(md)

    from urllib.parse import quote
    name = re.sub(r'[\\/:*?"<>|\r\n]+', "_", doc.title or "视频笔记").strip(" ._")[:80] or "视频笔记"
    return Response(content=md, media_type="text/markdown; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name + '.md')}"})


@router.get("/{document_id}/search")
async def search_video_transcript(document_id: int, q: str = "", limit: int = 20,
                                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    """文稿检索：LIKE 过滤下推到 SQL，只回命中切块（含前后各 60 字片段与起点秒数）。"""
    doc = _video_doc(db, document_id, user.id)
    term = (q or "").strip()[:50]
    if not term:
        raise APIError(ErrCode.COMMON_400, "请输入要检索的关键词")
    lim = max(1, min(int(limit or 20), 50))
    where = (Chunk.document_id == doc.id, Chunk.content.like(_like_pattern(term), escape="\\"))
    total = int(db.scalar(select(func.count(Chunk.id)).where(*where)) or 0)
    rows = list(db.scalars(select(Chunk).where(*where)
                           .order_by(Chunk.chunk_index).limit(lim)))
    hits = [{
        "chunk_index": int(c.chunk_index or 0),
        "snippet": _snippet(c.content or "", term),
        "start_sec": _chunk_start_sec(c),
    } for c in rows]
    return {"ok": True, "data": {"q": term, "total": total, "hits": hits}}


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
