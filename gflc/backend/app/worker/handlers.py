# -*- coding: utf-8 -*-
"""后台任务处理逻辑。所有重活在此执行，进度通过 update 回写。"""
import asyncio
import hashlib
import logging
import mimetypes
import os
import re
import subprocess
import tempfile
import uuid

from pydantic import BaseModel

from app.ai.prompts import (DASHBOARD_SYSTEM, PLAN_SYSTEM, VIDEO_NOTE_SYSTEMS,
                            dashboard_user, plan_user, video_note_user_tpl)
from app.ai.router import generate_json
from app.core.config import settings
from app.core.errors import APIError
from app.crud import crud
from app.models.models import (Chunk, DashboardLayout, Document, Note, Plan, PlanTask,
                               Question, QuestionBank, Task)
from app.schemas.schemas import DashConfig, PlanGenResult
from app.services.cards import generate_cards
from app.services.frames import (build_frame_note, dedupe_frames, extract_frames,
                                 extract_grid_frames, frame_dir, has_video_stream,
                                 is_doc_frame, ocr_frames, ocr_grids, public_path,
                                 render_frame_note_md)
from app.services.pipeline import parse_pdf_to_chunks
from app.services.question_parse import extract_text, parse_questions
from app.services.question_vision import parse_paper
from app.services.storage import download_to, get_storage
from app.services.video import (download_media, extract_audio, load_subtitle_segments,
                                quality, segments_to_chunks, transcribe)
from app.worker import runner

_log = logging.getLogger(__name__)


def handle_pdf_parse(db, task, payload, update):
    doc = db.get(Document, payload["document_id"])
    if not doc:
        raise RuntimeError("文档不存在")
    doc.status = "parsing"
    db.commit()
    update(15, "下载文件")
    _ext = os.path.splitext(doc.title or "")[1].lower() or ".pdf"
    if _ext not in (".pdf", ".docx", ".md", ".markdown", ".txt"):
        _ext = ".pdf"
    tmp = os.path.join(tempfile.gettempdir(), f"gflc_{doc.id}_{uuid.uuid4().hex}{_ext}")
    parse_stats: dict = {}
    try:
        download_to(doc.storage_key, tmp)
        update(20, "解析文档")

        def _on_parse_progress(done: int, total: int, stage: str = "ocr") -> None:
            """把解析链路进度映射到任务百分比：OCR 页进度占 20–90，入库 92。

            扫描件 OCR 单页可达 15s，若整段只报一次 40%，用户会以为卡死；
            逐页回写让进度条持续走动。文字层 PDF 在解析完成/分块各给一次。
            """
            if stage == "ocr":
                pct = 20 + (70 * int(done)) // max(1, int(total))
                update(min(90, pct), f"识别扫描页 {done}/{total}")
            elif stage == "text":
                update(60, "解析文档")
            else:
                update(92, "写入知识库")

        n = parse_pdf_to_chunks(db, doc, tmp, stats=parse_stats,
                                on_progress=_on_parse_progress)
    except Exception:
        doc.status = "failed"
        db.commit()
        raise
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    # 扫描件 OCR 的页数/失败页作为可选字段回传，便于前端如实展示部分失败
    return {"document_id": doc.id, "chunks": n, **parse_stats}


def handle_card_generate(db, task, payload, update):
    update(5, "准备生成")
    n = asyncio.run(generate_cards(db, task.user_id, payload["document_id"],
                                   on_progress=lambda p: update(p)))
    return {"document_id": payload["document_id"], "cards": n}


_SUBJECT_KEYS = (("线性代数", ("线性代数", "线代")),
                 ("概率论与数理统计", ("概率", "统计")),
                 ("高等数学", ("高等数学", "高数", "微积分")))


def _infer_subject(chapters: dict[str, int], fallback: str = "") -> str:
    """按章节分布推断科目：单一科目占一半以上就取该科目，三科均衡则归「数学综合」。"""
    hits = {}
    for label, keys in _SUBJECT_KEYS:
        n = sum(c for ch, c in chapters.items() if any(k in (ch or "") for k in keys))
        if n:
            hits[label] = n
    if not hits:
        return fallback or "综合"
    top = max(hits, key=hits.get)
    return top if hits[top] / sum(hits.values()) >= 0.5 else "数学综合"


def _file_hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(blk)
    return h.hexdigest()


def _import_document(db, task, payload, filename: str, content_hash: str):
    """两步上传的文档直接复用；一步到位的重试按内容哈希去重；都没有才新建。"""
    doc_id = payload.get("document_id")
    if doc_id:
        try:
            doc = db.get(Document, int(doc_id))
        except (TypeError, ValueError):
            doc = None
        if doc is not None and doc.user_id == task.user_id and doc.source_type == "question_bank":
            if not doc.storage_key and payload.get("storage_key"):
                doc.storage_key = payload["storage_key"]
            return doc
    old = crud.find_by_hash(db, task.user_id, content_hash)
    if old is not None and old.source_type == "question_bank":
        return old
    return crud.create_document(db, user_id=task.user_id, title=filename,
                                source_type="question_bank", content_hash=content_hash,
                                storage_key=payload.get("storage_key", ""),
                                size=payload.get("size", 0), mime=payload.get("mime", ""))


def handle_question_import(db, task, payload, update):
    """题库生成，两种 payload：
    - 老路径 {"path", "filename"}：直接读临时文件
    - 新路径 {"document_id", "storage_key", "filename"}：从 storage 读并复用已建文档
    """
    filename = payload.get("filename") or "题库"
    ext = os.path.splitext(filename)[1].lower()
    path = payload.get("path") or ""
    meta: dict = {}
    items: list[dict] = []
    pages = int(payload.get("pages") or 0)
    update(8, "读取文件")
    if not (path and os.path.exists(path)):
        key = payload.get("storage_key")
        if not key:
            raise APIError("PARSE-001", "题库文件已清理，请重新上传")
        path = os.path.join(tempfile.gettempdir(), f"gflc_qb_{uuid.uuid4().hex}{ext or '.pdf'}")
        download_to(key, path)
    try:
        if ext == ".pdf":
            # 试卷/合集：逐页视觉识别（公式保真）
            update(12, "逐页视觉识别")
            res = asyncio.run(parse_paper(path, on_progress=lambda p: update(p)))
            meta = res.get("meta") or {}
            pages = int(res.get("pages") or pages or 0)
            for q in res.get("questions", []):
                sec = q.get("section") or ""
                items.append({
                    "no": str(q.get("no") or ""), "section": sec, "chapter": q.get("chapter") or "",
                    "stem": q.get("stem") or "", "options": q.get("options") or [],
                    "answer": q.get("answer") or "", "analysis": None, "page": q.get("page") or 0,
                })
        else:
            text = extract_text(path)
            update(35, "识别题目")
            objs = asyncio.run(parse_questions(text, max_questions=20, on_progress=lambda p: update(p)))
            for o in objs:
                items.append({"no": "", "section": "", "chapter": "", "stem": o.stem,
                              "options": o.options or [], "answer": o.answer or "",
                              "analysis": o.analysis.model_dump(), "page": 0})
        h = _file_hash(path)
    finally:
        if os.path.exists(path):
            os.remove(path)

    # 去重（同题号+题干前缀）
    seen, uniq = set(), []
    for q in items:
        k = (q["no"], (q["stem"] or "")[:30])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(q)
    if not uniq:
        raise APIError("PARSE-003", "未识别到题目：请确认是试卷/题库 PDF（而非纯图片或空白页）")

    update(92, "写入题库")
    doc = _import_document(db, task, payload, filename, h)
    chapters: dict[str, int] = {}
    for q in uniq:
        ch = q["chapter"] or "未分类"
        chapters[ch] = chapters.get(ch, 0) + 1
    subject = _infer_subject(chapters, meta.get("subject") or "")
    chapters_out = [{"chapter": k, "count": v}
                    for k, v in sorted(chapters.items(), key=lambda kv: -kv[1])]

    # 幂等：同一文档重复生成先清空旧题目与旧题库集，避免题目翻倍
    db.query(Question).filter(Question.document_id == doc.id,
                              Question.user_id == task.user_id).delete(synchronize_session=False)
    db.query(QuestionBank).filter(QuestionBank.document_id == doc.id,
                                  QuestionBank.user_id == task.user_id).delete(synchronize_session=False)
    db.flush()

    bank = QuestionBank(user_id=task.user_id, document_id=doc.id,
                        name=(os.path.splitext(filename)[0] or filename), subject=subject,
                        meta={"pages": pages, "subject_raw": meta.get("subject") or "",
                              "title": meta.get("title") or "", "chapters": chapters_out})
    db.add(bank)
    db.flush()
    for q in uniq:
        sec = q["section"]
        qtype = "single" if "选择" in sec else ("fill" if "填空" in sec else ("short" if sec else "single"))
        db.add(Question(user_id=task.user_id, document_id=doc.id, bank_id=bank.id,
                        chapter=q["chapter"], section=sec, no=q["no"], stem=q["stem"],
                        options=q["options"], answer=q["answer"], analysis=q["analysis"],
                        qtype=qtype, page=q["page"]))
    doc.status = "ready"
    db.commit()
    return {"bank_id": bank.id, "document_id": doc.id, "questions": len(uniq),
            "chapters": chapters_out, "subject": subject, "pages": pages}


def handle_plan_generate(db, task, payload, update):
    days = max(1, min(payload.get("days", 7), 60))
    update(20, "拆解任务")
    obj, _ = asyncio.run(generate_json("mid", PLAN_SYSTEM, plan_user(payload["goal"], days), PlanGenResult))
    update(85, "写入计划")
    plan = Plan(user_id=task.user_id, goal=payload["goal"], days=days)
    db.add(plan)
    db.flush()
    for t in obj.tasks:
        db.add(PlanTask(plan_id=plan.id, day_index=max(1, min(t.day, days)),
                        title=t.title, detail=t.detail))
    db.commit()
    return {"plan_id": plan.id, "days": days, "tasks": len(obj.tasks)}


class _VSummary(BaseModel):
    summary: str = ""
    points: list[str] = []


class _VOutlineLeaf(BaseModel):
    title: str = ""
    children: list[str] = []


class _VOutlineSection(BaseModel):
    title: str = ""
    children: list[_VOutlineLeaf] = []


class _VOutline(BaseModel):
    summary: str = ""
    outline: list[_VOutlineSection] = []


class _VQaItem(BaseModel):
    question: str = ""
    answer: str = ""
    ts: str = ""


class _VQa(BaseModel):
    summary: str = ""
    qas: list[_VQaItem] = []


_TPL_NAME = {"summary": "摘要", "outline": "大纲", "qa": "问答"}
_TPL_SCHEMA: dict[str, type[BaseModel]] = {"summary": _VSummary, "outline": _VOutline, "qa": _VQa}
_VIDEO_SUFFIX = {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".avi", ".flv", ".wmv", ".ts"}


def _is_video_src(path: str) -> bool:
    """只有带视频流的文件才抽帧，纯音频（bestaudio/mp3/wav）跳过。"""
    if os.path.splitext(path or "")[1].lower() not in _VIDEO_SUFFIX:
        return False
    return has_video_stream(path)


def _render_summary_md(obj: _VSummary) -> str:
    lines = ["## 摘要", (obj.summary or "").strip(), "", "## 要点"]
    lines += [f"- {p.strip()}" for p in obj.points if (p or "").strip()]
    return "\n".join(lines).strip() + "\n"


def _render_outline_md(obj: _VOutline) -> str:
    lines: list[str] = []
    for sec in obj.outline:
        if not (sec.title or "").strip():
            continue
        lines.append(f"# {sec.title.strip()}")
        for leaf in sec.children:
            if (leaf.title or "").strip():
                lines.append(f"## {leaf.title.strip()}")
            lines += [f"- {c.strip()}" for c in leaf.children if (c or "").strip()]
    return "\n".join(lines).strip() + "\n"


def _render_qa_md(obj: _VQa) -> str:
    parts = []
    for qa in obj.qas:
        if not (qa.question or "").strip():
            continue
        ts = f"（{qa.ts.strip()}）" if (qa.ts or "").strip() else ""
        parts.append(f"### Q: {qa.question.strip()}{ts}\n{(qa.answer or '').strip()}\n")
    return "\n".join(parts).strip() + "\n"


_RENDER = {"summary": _render_summary_md, "outline": _render_outline_md, "qa": _render_qa_md}


def _note_points(obj, tpl: str) -> list[str]:
    if tpl == "outline":
        return [s.title.strip() for s in obj.outline if (s.title or "").strip()]
    if tpl == "qa":
        return [q.question.strip() for q in obj.qas if (q.question or "").strip()]
    return [p.strip() for p in obj.points if (p or "").strip()]


# ---------------------------------------------------------------------------
# A5：阶段化 checkpoint / 真断点续传（只写 task.checkpoint，不改状态机枚举）
# ---------------------------------------------------------------------------
def _cp_get(task) -> dict:
    cp = getattr(task, "checkpoint", None)
    return dict(cp) if isinstance(cp, dict) else {}


def _cp_save(db, task, **stages):
    """把已完成阶段写入 task.checkpoint；写失败 WARNING，不影响主流程。"""
    try:
        cp = _cp_get(task)
        data = dict(cp.get("video_stages") or {})
        data.update(stages)
        cp["video_stages"] = data
        task.checkpoint = cp
        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        _log.warning("视频任务 checkpoint 写入失败（task=%s）：%s", getattr(task, "id", "?"), e)


def _replace_old_note(db, doc_id: int, kind: str) -> None:
    """同一资料的同类 AI 笔记只保留最新一份。

    复用取材（秒传）重跑会再生成一遍笔记，之前会留下 2 份 summary / 2 份 outline，
    用户在笔记列表里看到重复条目。这里在写入前清掉旧同类（仅 source=video）。
    """
    try:
        db.query(Note).filter(Note.document_id == doc_id, Note.kind == kind,
                              Note.source == "video").delete(synchronize_session=False)
        db.commit()
    except Exception as e:  # noqa: BLE001  清理失败不影响写入
        _log.warning("旧笔记清理失败（doc=%s kind=%s）：%s", doc_id, kind, e)
        try:
            db.rollback()
        except Exception:
            pass


def _ts_mmss(sec: float) -> str:
    s = max(0, int(round(float(sec or 0))))
    return f"{s // 60:02d}:{s % 60:02d}"


def _reuse_material_by_url(db, task) -> dict | None:
    """同一用户、同一链接若已有转写取材，直接复用（秒传 / 免重复 ASR）。

    只读 checkpoint，不跨用户；最近 10 个同类型任务里取第一条命中的。
    """
    url = ((_cp_get(task).get("payload") or {}).get("url") or "").strip()
    if not url:
        return None
    try:
        from sqlalchemy import select
        rows = db.scalars(
            select(Task).where(Task.user_id == task.user_id, Task.id != task.id,
                               Task.type.in_(("video_url",)), Task.status == "ready")
            .order_by(Task.id.desc()).limit(10)
        ).all()
    except Exception as e:  # noqa: BLE001  复用是优化项，失败就走正常转写
        _log.warning("同源复用查询失败：%s", e)
        return None
    for r in rows:
        cp = r.checkpoint if isinstance(r.checkpoint, dict) else {}
        if ((cp.get("payload") or {}).get("url") or "").strip() != url:
            continue
        m = (cp.get("video_stages") or {}).get("material") or {}
        if m.get("doc_id") and m.get("segments"):
            return m
    return None


def _rehydrate_source(task, workdir: str) -> str | None:
    """续传时源文件已被 handle_video_upload 清理 → 从 checkpoint 的 video_key 取回。"""
    key = (_cp_get(task).get("video_stages") or {}).get("video_key")
    if not key:
        return None
    ext = os.path.splitext(key)[1] or ".mp4"
    dst = os.path.join(workdir, "resume_source" + ext)
    try:
        download_to(key, dst)
        return dst
    except Exception as e:
        _log.warning("续传源文件恢复失败（key=%s）：%s", key, e)
        return None


def _append_sources(sections: list[dict], items: list[dict]) -> list[dict]:
    """D8：给图文笔记每节补数值型 ts_start，供前端 ≤2s 跳转。"""
    by_label = {it.get("ts_label"): it.get("ts_start") for it in items if it.get("ts_label")}
    out = []
    for s in sections or []:
        d = dict(s)
        d["ts_start"] = by_label.get(d.get("ts"), 0.0)
        out.append(d)
    return out


def _video_pipeline(db, task, src_path: str, title: str, update, raw: bytes | None = None,
                    templates=None, storage_key: str | None = None):
    """视频/音频主流水线。

    阶段顺序 = 快结果优先（A4）：取材(字幕/ASR) → 文稿+切块+大纲笔记先落库 →
    图文笔记后台补齐。每阶段写 checkpoint（A5），中断重试跳过已完成段。
    """
    tpls = [t for t in (templates or ["summary"]) if t in _TPL_SCHEMA] or ["summary"]
    # 配置中心优先：把 DB 里的平台 Cookie 落成 cookies.txt，字幕通道才可能命中
    try:
        from app.services import settings_store as _ss
        _ck = _ss.materialize_cookie(db, "bilibili")
        if _ck:
            settings.COOKIES_FILE = _ck
            _log.info("取材使用 B 站 Cookie：%s", _ck)
    except Exception as _e:  # noqa: BLE001  配置读取失败不影响任务
        _log.warning("Cookie 注入失败：%s", _e)
    workdir = tempfile.mkdtemp(prefix="gflc_v_")
    stages_all = _cp_get(task).get("video_stages") or {}
    skipped: list[str] = []
    sub_temp: list[str] = []
    log_ctx = f"task={getattr(task, 'id', '?')} user={task.user_id}"
    grid_calls = 0

    # 续传：原临时源文件已被清理 → 从 checkpoint 的 video_key 取回
    src = src_path
    if not src or not os.path.isfile(src):
        src = _rehydrate_source(task, workdir)
        if src:
            skipped.append("source:rehydrated")
    if not src or not os.path.isfile(src):
        raise APIError("PARSE-001", "视频源文件已清理且无可用备份，请重新上传")
    if raw is None:
        with open(src, "rb") as f:
            raw = f.read()

    # 源文件按内容哈希 Deterministic key 提前落存储，供真续传用（A5）
    h = hashlib.sha256(raw).hexdigest()
    video_key = stages_all.get("video_key") or f"{task.user_id}/video_{h[:16]}"
    if not stages_all.get("video_key"):
        try:
            get_storage().save(video_key, raw)
            _cp_save(db, task, video_key=video_key)
        except Exception as e:
            _log.warning("源视频备份落存储失败（%s），本次不支持断点续传：%s", log_ctx, e)

    # ---------- 阶段 1：取材（字幕优先 A1/S2，否则原 ASR 路径不变） ----------
    mat = stages_all.get("material") or {}
    # 同源复用（秒传）：同一用户提交过同一个链接且已有转写 → 直接继承，省掉整段 ASR。
    # 60 分钟视频转写实测约 35 分钟，这一条是「重复提交 2 秒出结果」的关键。
    if not (mat.get("doc_id") and mat.get("segments")):
        prev = _reuse_material_by_url(db, task)
        if prev:
            mat = prev
            _cp_save(db, task, material=prev)
            skipped.append("material:reused")
            _log.info("同源复用转写 %s segments=%s", log_ctx, len(prev.get("segments") or []))
    doc = None
    if mat.get("doc_id") and mat.get("segments"):
        try:
            doc = db.get(Document, int(mat["doc_id"]))
        except (TypeError, ValueError):
            doc = None
    if doc is not None:
        segs = [(float(x[0]), float(x[1]), str(x[2])) for x in mat["segments"]]
        source_mode = mat.get("source_mode") or "whisper"
        subtitle_source = mat.get("subtitle_source") or ""
        whisper_calls = int(mat.get("whisper_calls") or 0)
        q = mat.get("quality") or quality("\n".join(c["content"] for c in segments_to_chunks(segs)))
        skipped.append("material:transcribe")
        _log.info("resume 跳过取材阶段 %s source=%s whisper_calls=%s", log_ctx, source_mode, whisper_calls)
        update(70, "复用已完成取材")
    else:
        # 取材策略由配置中心决定：auto=字幕→必剪→whisper；subtitle/bcut/whisper 可强制单一路径
        mode = _transcriber_mode(db)
        sub_segs, sub_meta = (None, {})
        if mode in ("auto", "subtitle"):
            sub_segs, sub_meta = load_subtitle_segments(src, storage_key, workdir, log_ctx=log_ctx)
        sub_temp = list(sub_meta.get("temp_files") or [])
        if sub_segs:
            segs = sub_segs
            source_mode = "subtitle"
            subtitle_source = sub_meta.get("source") or ""
            whisper_calls = 0
            update(70, "字幕取材完成（跳过转写）")
        else:
            # 2) 必剪云转写：免登录免费，实测 RTF 0.028（27 分钟视频约 45 秒）。
            #    无官方 SLA → 失败必须能降级到本地 Whisper，绝不阻断任务。
            segs, source_mode = (None, "whisper") if mode == "subtitle" else _try_bcut(
                src, workdir, update, log_ctx)
            if segs:
                subtitle_source = "bcut"
                whisper_calls = 0
            else:
                # 3) 本地 Whisper（切片并行 RTF≈0.09）
                audio = os.path.join(workdir, "audio.wav")
                update(10, "抽取音频")
                extract_audio(src, audio)

                def _tp(p):
                    update(max(10, min(70, int(p * 70 / 85))), "语音转写")

                update(20, "语音转写")
                segs = transcribe(audio, on_progress=_tp)
                source_mode = "whisper"
                subtitle_source = ""
                whisper_calls = 1

    chunks = segments_to_chunks(segs)
    if not chunks:
        raise APIError("PARSE-002", "转写结果为空")

    update(72, "写入知识库")
    if doc is None:
        # mime 必须具体：之前写死 "video/*" 是非法通配符，浏览器 <video> 直接拒绝播放
        _mime = mimetypes.guess_type(src)[0] or ("audio/mpeg" if src.endswith(".mp3") else "video/mp4")
        doc = crud.create_document(db, user_id=task.user_id, title=title or "视频", source_type="video",
                                   content_hash=h, storage_key=video_key, size=len(raw), mime=_mime)
        transcript = "\n".join(c["content"] for c in chunks)
        q = quality(transcript)
        for i, c in enumerate(chunks):
            db.add(Chunk(document_id=doc.id, content=c["content"], page=0, chunk_index=i,
                         content_hash=hashlib.sha256(c["content"].encode()).hexdigest(),
                         ts_start=c["ts_start"], ts_end=c["ts_end"]))
        # D9：low 质量不写 ready，落 needs_review；同时在返回数据打低置信标记
        needs_review = (q == "low")
        doc.status = "needs_review" if needs_review else "ready"
        if needs_review:
            _log.warning("转写质量 low，不写 ready，转 needs_review：%s quality=%s source=%s",
                         log_ctx, q, source_mode)
        db.commit()

        # A4 快结果：文稿（带时间戳）先落库，大纲/摘要随后；图文笔记最后补
        transcript_md = "## 文稿\n" + "\n".join(
            f"[{_ts_mmss(c['ts_start'])}] {c['content']}" for c in chunks) + "\n"
        if not db.query(Note).filter(Note.document_id == doc.id, Note.kind == "transcript").first():
            trow = Note(document_id=doc.id, user_id=task.user_id, title=f"{doc.title} · 文稿",
                        summary=transcript[:200], content=transcript_md, points=[],
                        source="video", kind="transcript")
            db.add(trow)
            db.commit()
            db.refresh(trow)
        _cp_save(db, task, material={
            "doc_id": doc.id, "segments": [[float(s[0]), float(s[1]), s[2]] for s in segs],
            "source_mode": source_mode, "subtitle_source": subtitle_source,
            "whisper_calls": whisper_calls, "quality": q, "chunk_count": len(chunks),
        })
    else:
        q = mat.get("quality") or "ok"
        needs_review = (q == "low")
        # 带时间戳的转写：笔记里的 ts 才有依据（原来只拼正文，模型只能瞎猜 ts）
        transcript = "\n".join(f"[{_ts_mmss(c.get('ts_start') or 0)}] {c['content']}"
                               for c in chunks)

    note_stage = stages_all.get("notes") or {}
    done_notes = set(note_stage.get("done") or [])

    # ---------- 阶段 2：三模板笔记（大纲/摘要/问答），并发生成后再落库 ----------
    # 原来三个模板串行 await：实测 60 分钟视频 摘要 37s + 大纲 44s + 问答 82s = 164s。
    # LLM 调用是 IO 等待，并发后总耗时≈最慢的一个（~82s），落库仍按顺序串行，避免写冲突。
    notes: list[dict] = []
    note = None
    pending = [t for t in tpls if t not in done_notes]
    for t in tpls:
        if t in done_notes:
            skipped.append(f"note:{t}")
            _log.info("resume 跳过已完成笔记 %s/%s", log_ctx, t)

    if pending:
        update(74, "并发生成三份笔记")

        async def _gen_all():
            async def _one(tpl: str):
                # 大纲/问答节点多，mid 档 3000 token 会被截断成半截 JSON（实测 60 分钟视频必挂）。
                # mid 仍偶发「Unterminated string」（模型漏转义引号/换行）→ 换 strong 再试一次。
                mt = {"outline": 6000, "qa": 5000}.get(tpl, 4000)
                last = None
                for tier, _mt in (("mid", mt), ("strong", max(mt, 6000))):
                    try:
                        obj, _ = await generate_json(tier, VIDEO_NOTE_SYSTEMS[tpl],
                                                    video_note_user_tpl(transcript, tpl),
                                                    _TPL_SCHEMA[tpl], max_tokens=_mt)
                        return tpl, obj
                    except Exception as e:  # noqa: BLE001
                        last = e
                        _log.warning("笔记模板 %s 在 %s 档失败，换档重试：%s", tpl, tier, e)
                raise last
            return await asyncio.gather(*[_one(t) for t in pending], return_exceptions=True)

        results = asyncio.run(_gen_all())
        for tpl, res in zip(pending, results):
            if isinstance(res, BaseException):
                # 单个模板失败不影响其他模板（长视频实测就是这里先挂的）
                _log.warning("视频笔记模板 %s 生成失败：%s", tpl, res)
                continue
            _, obj = res
            try:
                md = _RENDER[tpl](obj)
                pts = _note_points(obj, tpl)
                _replace_old_note(db, doc.id, tpl)
                row = Note(document_id=doc.id, user_id=task.user_id,
                           title=f"{doc.title} · {_TPL_NAME[tpl]}", summary=obj.summary or "",
                           content=md, points=pts, source="video", kind=tpl)
                db.add(row)
                db.commit()
                db.refresh(row)
                done_notes.add(tpl)
                _cp_save(db, task, notes={"done": sorted(done_notes),
                                          "transcript_note_id": note_stage.get("transcript_note_id")})
            except Exception as e:  # noqa: BLE001  落库失败不影响其他模板
                _log.warning("视频笔记模板 %s 落库失败：%s", tpl, e)
                try:
                    db.rollback()
                except Exception:
                    pass
        update(90, "笔记写入完成")

    # ---------- 阶段 2.5：单篇 Markdown 笔记（对标 BiliNote）+ 按时间点抽帧插图 ----------
    # 与三模板并存（配置中心 note_markdown / note_templates 各自可控）：
    # Markdown 负责「一篇读到底」，三模板继续供卡包与复习消费。
    md_note = None
    try:
        from app.services import settings_store as _ss
        from app.services import video_note as vnote
        if _ss.get_runtime(db, "note_markdown", "1") == "1" and vnote.available() and _is_video_src(src):
            update(90, "生成 Markdown 笔记")
            md_source = "\n".join(f"[{_ts_mmss(c.get('ts_start') or 0)}] {c['content']}" for c in chunks)
            md = vnote.build_markdown(md_source, doc.title)
            if md:
                shots: dict[int, str] = {}
                if _ss.get_runtime(db, "screenshot_enabled", "1") == "1":
                    pts = vnote.screenshot_points(md)
                    shots = vnote.grab_frames(
                        src, frame_dir(), pts, doc_id=doc.id,
                        min_gap=int(_ss.get_runtime(db, "screenshot_min_gap", "180") or 180),
                        max_n=int(_ss.get_runtime(db, "screenshot_max", "20") or 20),
                    )
                md = vnote.content_links(vnote.apply_screenshots(md, shots))
                _replace_old_note(db, doc.id, "markdown")
                _kps = vnote.keypoints(md)
                row = Note(document_id=doc.id, user_id=task.user_id,
                           title=f"{doc.title} · 笔记", summary=md[:180],
                           content=md, points=_kps,
                           source="video", kind="markdown")
                db.add(row)
                db.commit()
                db.refresh(row)
                md_note = {"id": row.id, "kind": "markdown", **vnote.stats(md, shots)}
                _cp_save(db, task, markdown=md_note)
                _log.info("markdown 笔记完成 %s %s", log_ctx, md_note)
    except Exception as e:  # noqa: BLE001  失败不影响三模板与图文
        _log.warning("Markdown 笔记阶段失败（三模板仍可用）：%s", e)
        try:
            db.rollback()
        except Exception:
            pass

    # ---------- 阶段 3：图文笔记（A3 网格拼图优先，失败回退逐帧 OCR） ----------
    frame_items: list[dict] = []
    frame_note: dict = {"summary": "", "sections": [], "markdown": ""}
    fstage = stages_all.get("frames") or {}
    if fstage.get("done") and fstage.get("note_id"):
        frow = db.get(Note, int(fstage["note_id"]))
        if frow is not None:
            frame_items = list(frow.points or [])
            frame_note = {"summary": frow.summary or "",
                          "sections": fstage.get("sections") or [], "markdown": frow.content or ""}
            skipped.append("frames:ocr")
            _log.info("resume 跳过已完成图文笔记 %s", log_ctx)

    if not frame_items and _is_video_src(src) and _frames_ocr_enabled(db):
        try:
            update(92, "提取关键帧拼图")
            # ffmpeg 全片解码期间回写心跳，防止正常长任务被看门狗误判超时（复用现有 beat）
            import threading
            _beat_stop = threading.Event()

            def _heartbeat():
                while not _beat_stop.wait(20):
                    try:
                        update.beat()
                    except Exception:
                        pass

            _beat = threading.Thread(target=_heartbeat, daemon=True, name="gflc-frame-beat")
            _beat.start()
            try:
                grids = extract_grid_frames(src, frame_dir(), max_frames=24, cols=4, rows=3)
                ocr_items: list[dict] = []
                if grids:
                    update(95, "识别拼图文字")
                    ocr_items, grid_calls = asyncio.run(ocr_grids(grids, max_calls=2))
                if not grids or not ocr_items:
                    # 回退：保留原 extract_frames + ocr_frames 的 Semaphore(4) 并发路径
                    _log.warning("网格拼图未产出可用文字，回退逐帧 OCR %s", log_ctx)
                    frames = dedupe_frames(extract_frames(src, frame_dir(), max_frames=24))[:24]
                    for f in frames:
                        f["is_doc"] = is_doc_frame(f)
                    ocr_items = asyncio.run(ocr_frames(frames, max_ocr=12)) if frames else []
                    by_name = {it["path"]: it for it in ocr_items}
                    frame_items = [{
                        "ts": f["ts"], "ts_start": f["ts"], "ts_label": f["ts_label"],
                        "path": public_path(f["name"]),
                        "text": (by_name.get(f["name"]) or {}).get("text", ""),
                        "is_doc": bool(f.get("is_doc")), "source": "frame",
                    } for f in frames]
                else:
                    # 网格模式：逐格还原到统一时间轴锚点 ts_start（D8）
                    for g in grids:
                        cells = [it for it in ocr_items
                                 if os.path.basename(str(it.get("path", ""))) == g["name"]]
                        exact = [c for c in cells if c.get("cell")]
                        fallback = next((c for c in cells if not c.get("cell")), None)
                        for idx, t in enumerate(g.get("times") or [], 1):
                            cell = next((c for c in exact if c.get("cell") == idx), None)
                            if cell is None and idx == 1:
                                cell = fallback  # 模型未按格输出时，整段文本挂到首格
                            frame_items.append({
                                "ts": round(float(t), 2), "ts_start": round(float(t), 2),
                                "ts_label": _ts_mmss(t), "path": public_path(g["name"]),
                                "text": (cell or {}).get("text", ""),
                                "is_doc": bool(cell), "source": "grid",
                            })
                    if not frame_items:
                        g = grids[0]
                        frame_items = [{
                            "ts": g["ts_start"], "ts_start": g["ts_start"],
                            "ts_label": _ts_mmss(g["ts_start"]), "path": public_path(g["name"]),
                            "text": ocr_items[0].get("text", "") if ocr_items else "",
                            "is_doc": True, "source": "grid",
                        }]
            finally:
                _beat_stop.set()
                _beat.join(timeout=2)

            if ocr_items:
                frame_items = _dedupe_frames(frame_items)
                update(97, "生成图文笔记")
                note_obj = asyncio.run(build_frame_note(ocr_items))
                sections = _append_sources(note_obj.get("sections") or [], ocr_items)
                md = render_frame_note_md(note_obj, ocr_items)
                frame_note = {"summary": note_obj.get("summary") or "",
                              "sections": sections, "markdown": md}
                if md.strip():
                    _replace_old_note(db, doc.id, "frames")
                    row = Note(document_id=doc.id, user_id=task.user_id,
                               title=f"{doc.title} · 图文", summary=frame_note["summary"],
                               content=md, points=frame_items, source="video", kind="frames")
                    db.add(row)
                    db.commit()
                    db.refresh(row)
                    _cp_save(db, task, frames={"done": True, "note_id": row.id,
                                               "sections": sections, "grid_ocr_calls": grid_calls})
        except Exception as e:  # 抽帧失败不影响主流程
            _log.warning("关键帧图文笔记失败：%s", e)
            try:
                db.rollback()
            except Exception:
                pass
    update(98, "整理结果")

    # 返回值从 DB 重建，保证续传时已生成的笔记仍能返回；字段只追加不删改
    kinds = list(tpls) + (["frames"] if frame_note.get("markdown") else [])
    rows = db.query(Note).filter(Note.document_id == doc.id, Note.kind.in_(kinds)).order_by(Note.id).all()
    notes = [{"id": r.id, "kind": r.kind, "title": r.title, "summary": r.summary,
              "content": r.content, "points": r.points or []} for r in rows]
    if note is None:
        first = next((n for n in notes if n["kind"] == tpls[0]), None)
        note = {"id": first["id"], "kind": tpls[0], "summary": first["summary"],
                "points": first["points"], "quality": q} if first else {
            "summary": transcript[:200], "points": [], "quality": q, "kind": tpls[0]}
    if skipped:
        _log.info("resume_skipped_segments=%s %s", skipped, log_ctx)
    update(99, "整理结果")

    for f in os.listdir(workdir):
        try:
            os.remove(os.path.join(workdir, f))
        except OSError:
            pass
    try:
        os.rmdir(workdir)
    except OSError:
        pass
    for p in sub_temp:
        try:
            os.remove(p)
        except OSError:
            pass
    # 速度提示：B站/YouTube 的官方（AI）字幕要登录 cookie 才拿得到。
    # 有字幕时取材接近 0 秒，走 ASR 则长视频是分钟级——这条提示直接决定用户体感。
    speed_hint = ""
    if source_mode == "whisper" and not getattr(settings, "COOKIES_FILE", ""):
        speed_hint = ("当前走本地语音转写。配置 COOKIES_FILE（浏览器登录后导出的 cookies.txt）"
                      "可优先使用平台字幕，1 小时视频的取材时间从分钟级降到秒级。")
    return {"document_id": doc.id, "chunks": len(chunks), "segments": len(segs), "note": note,
            "notes": notes, "templates": tpls, "frames": frame_items, "frame_note": frame_note,
            "transcript": [{"start": round(float(s[0]), 1), "end": round(float(s[1]), 1),
                            "text": s[2], "ts_start": round(float(s[0]), 1)} for s in segs],
            "source_mode": source_mode, "subtitle_source": subtitle_source,
            "whisper_calls": whisper_calls, "quality": q, "needs_review": bool(q == "low"),
            "low_confidence": bool(q == "low"), "resume_skipped_segments": skipped,
            "speed_hint": speed_hint,
            "grid_ocr_calls": grid_calls, "markdown_note": md_note}


def _transcriber_mode(db) -> str:
    """取材策略：auto | subtitle | bcut | whisper（配置中心可改）。"""
    try:
        from app.services import settings_store as _ss
        v = _ss.get_runtime(db, "transcriber", "auto")
        return v if v in ("auto", "subtitle", "bcut", "whisper") else "auto"
    except Exception:  # noqa: BLE001
        return "auto"


def _frames_ocr_enabled(db) -> bool:
    """图文关键帧 OCR 开关。默认关：Markdown 笔记已带按点截图，再跑一遍网格 OCR 是重复烧钱。"""
    try:
        from app.services import settings_store as _ss
        return _ss.get_runtime(db, "frames_ocr", "0") == "1"
    except Exception:  # noqa: BLE001
        return False


def _dedupe_frames(items: list[dict]) -> list[dict]:
    """去掉重复关键帧：同一道题常被抽到两张（时间相邻且 OCR 文字高度重合）。

    规则：按时间排序后，若与上一条时间差 <90s 且文字前 40 字相似度 ≥0.75，则丢弃。
    """
    if not items:
        return items
    out: list[dict] = []
    for it in sorted(items, key=lambda x: float(x.get("ts") or 0)):
        text = (it.get("text") or "").strip()
        ts = float(it.get("ts") or 0)
        dup = False
        for prev in out[-3:]:
            gap = abs(ts - float(prev.get("ts") or 0))
            if gap >= 90:
                continue
            a = re.sub(r"\s+", "", text)[:40]
            b = re.sub(r"\s+", "", (prev.get("text") or ""))[:40]
            if not a or not b:
                continue
            same = sum(1 for x, y in zip(a, b) if x == y) / max(len(a), len(b))
            if same >= 0.75:
                dup = True
                break
        if not dup:
            out.append(it)
    _log.info("关键帧去重 %s → %s", len(items), len(out))
    return out


def _try_bcut(src: str, workdir: str, update, log_ctx: str):
    """必剪云转写；任何异常都返回 (None, "whisper") 交给本地兜底。"""
    from app.services.bcut import BcutError, transcribe_bcut

    try:
        audio_mp3 = os.path.join(workdir, "bcut.mp3")
        update(12, "抽取音频")
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src, "-vn",
             "-ac", "1", "-ar", "16000", "-b:a", "64k", audio_mp3],
            check=True, capture_output=True, timeout=600,
        )
        update(22, "云端转写（必剪）")
        # 云转写期间刷心跳，避免长任务被看门狗判超时
        import threading
        stop = threading.Event()

        def _beat():
            while not stop.wait(20):
                try:
                    update.beat()
                except Exception:  # noqa: BLE001
                    pass

        th = threading.Thread(target=_beat, daemon=True, name="gflc-bcut-beat")
        th.start()
        try:
            segs = transcribe_bcut(audio_mp3)
        finally:
            stop.set()
            th.join(timeout=2)
        if segs:
            _log.info("取材命中 bcut %s segments=%s", log_ctx, len(segs))
            update(70, "云端转写完成")
            return segs, "bcut"
        return None, "whisper"
    except BcutError as e:
        _log.warning("必剪转写不可用，降级本地 Whisper %s：%s", log_ctx, e)
        return None, "whisper"
    except Exception as e:  # noqa: BLE001  兜底：任何异常都不阻断任务
        _log.warning("必剪转写异常，降级本地 Whisper %s：%s", log_ctx, e)
        return None, "whisper"


def handle_video_upload(db, task, payload, update):
    path = payload["path"]
    try:
        return _video_pipeline(db, task, path, payload.get("title") or "视频", update,
                               templates=payload.get("templates"),
                               storage_key=payload.get("storage_key"))
    finally:
        if path and os.path.exists(path):
            os.remove(path)


def handle_video_url(db, task, payload, update):
    update(5, "解析链接")
    stages = _cp_get(task).get("video_stages") or {}
    if stages.get("video_key") and stages.get("material"):
        # A5：续传时直接使用已备份源文件，不再重新下载（省一次网络+一次取材）
        _log.info("resume 跳过链接下载 %s", f"task={getattr(task, 'id', '?')}")
        return _video_pipeline(db, task, "", payload.get("title") or "B站视频", update,
                               templates=payload.get("templates"))
    workdir = tempfile.mkdtemp(prefix="gflc_dl_")
    audio_path = download_media(payload["url"], workdir)
    update(10, "下载完成")
    return _video_pipeline(db, task, audio_path, payload.get("title") or "B站视频", update,
                           templates=payload.get("templates"))


def _dash_facts(db, user_id: int) -> dict:
    """收集用户真实学习数据，喂给 AI，避免编造进度。"""
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func, or_, select

    from app.models.models import Attempt, Card, CardDeck, Document, Question

    now = datetime.now(timezone.utc)
    cards = db.scalar(select(func.count()).select_from(Card).where(Card.user_id == user_id)) or 0
    due = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user_id, or_(Card.reps == 0, Card.due_at.is_(None), Card.due_at <= now))) or 0
    reviewed = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user_id, Card.reps > 0)) or 0
    docs = db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user_id)) or 0
    questions = db.scalar(select(func.count()).select_from(Question).where(Question.user_id == user_id)) or 0
    attempts = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == user_id)) or 0
    correct = db.scalar(select(func.count()).select_from(Attempt).where(
        Attempt.user_id == user_id, Attempt.correct == 1)) or 0

    decks = db.execute(
        select(CardDeck.name, func.count(Card.id))
        .join(Card, Card.deck_id == CardDeck.id)
        .where(CardDeck.user_id == user_id, CardDeck.kind == "chapter")
        .group_by(CardDeck.name).order_by(func.count(Card.id).desc()).limit(6)
    ).all()

    week = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        n = db.scalar(select(func.count()).select_from(Attempt).where(
            Attempt.user_id == user_id, func.date(Attempt.created_at) == day.isoformat())) or 0
        week.append({"label": day.strftime("%m-%d"), "value": int(n)})

    return {
        "文档数": docs, "卡片数": cards, "已复习卡片": reviewed, "待复习": due,
        "题库题目数": questions, "已作答次数": attempts,
        "正确率": round(correct / attempts * 100, 1) if attempts else 0,
        "章节卡包": [{"name": n, "cards": int(c)} for n, c in decks],
        "最近7天作答": week,
    }


def handle_dashboard_generate(db, task, payload, update):
    theme = payload["theme"]
    scope = payload.get("scope", "week")
    update(15, "读取真实数据")
    facts = _dash_facts(db, task.user_id)
    update(30, "设计布局")
    obj, _ = asyncio.run(generate_json("mid", DASHBOARD_SYSTEM,
                                       dashboard_user(theme, scope, facts), DashConfig))
    update(88, "保存布局")
    db.query(DashboardLayout).filter(DashboardLayout.user_id == task.user_id).update(
        {"is_default": 0}, synchronize_session=False)
    row = DashboardLayout(user_id=task.user_id, theme=theme, config=obj.model_dump(),
                          order=[c.id for c in obj.cards], positions={}, scope=scope, is_default=1)
    db.add(row)
    db.commit()
    return {"layout_id": row.id, "theme": theme, "cards": len(obj.cards), "scope": scope}


def register_all():
    runner.register("pdf_parse", handle_pdf_parse)
    runner.register("card_generate", handle_card_generate)
    runner.register("question_import", handle_question_import)
    runner.register("plan_generate", handle_plan_generate)
    runner.register("video_upload", handle_video_upload)
    runner.register("video_url", handle_video_url)
    runner.register("dashboard_generate", handle_dashboard_generate)
