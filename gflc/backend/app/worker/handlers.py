# -*- coding: utf-8 -*-
"""后台任务处理逻辑。所有重活在此执行，进度通过 update 回写。"""
import asyncio
import hashlib
import logging
import os
import tempfile
import uuid

from pydantic import BaseModel

from app.ai.prompts import (DASHBOARD_SYSTEM, PLAN_SYSTEM, VIDEO_NOTE_SYSTEMS,
                            dashboard_user, plan_user, video_note_user_tpl)
from app.ai.router import generate_json
from app.core.errors import APIError
from app.crud import crud
from app.models.models import (Chunk, DashboardLayout, Document, Note, Plan, PlanTask,
                               Question, QuestionBank)
from app.schemas.schemas import DashConfig, PlanGenResult
from app.services.cards import generate_cards
from app.services.frames import (build_frame_note, dedupe_frames, extract_frames,
                                 frame_dir, has_video_stream, is_doc_frame,
                                 ocr_frames, public_path, render_frame_note_md)
from app.services.pipeline import parse_pdf_to_chunks
from app.services.question_parse import extract_text, parse_questions
from app.services.question_vision import parse_paper
from app.services.storage import download_to, get_storage
from app.services.video import (download_media, extract_audio, quality,
                                segments_to_chunks, transcribe)
from app.worker import runner

_log = logging.getLogger(__name__)


def handle_pdf_parse(db, task, payload, update):
    doc = db.get(Document, payload["document_id"])
    if not doc:
        raise RuntimeError("文档不存在")
    doc.status = "parsing"
    db.commit()
    update(15, "下载文件")
    tmp = os.path.join(tempfile.gettempdir(), f"gflc_{doc.id}_{uuid.uuid4().hex}.pdf")
    try:
        download_to(doc.storage_key, tmp)
        update(40, "解析 PDF")
        n = parse_pdf_to_chunks(db, doc, tmp)
    except Exception:
        doc.status = "failed"
        db.commit()
        raise
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return {"document_id": doc.id, "chunks": n}


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


def _video_pipeline(db, task, src_path, title, update, raw: bytes, templates=None):
    tpls = [t for t in (templates or ["summary"]) if t in _TPL_SCHEMA] or ["summary"]
    workdir = tempfile.mkdtemp(prefix="gflc_v_")
    audio = os.path.join(workdir, "audio.wav")
    update(10, "抽取音频")
    extract_audio(src_path, audio)

    def _tp(p):
        # 转写阶段映射到 10→70
        update(max(10, min(70, int(p * 70 / 85))), "语音转写")

    update(20, "语音转写")
    segs = transcribe(audio, on_progress=_tp)
    chunks = segments_to_chunks(segs)
    if not chunks:
        raise APIError("PARSE-002", "转写结果为空")

    update(72, "写入知识库")
    h = hashlib.sha256(raw).hexdigest()
    key = f"{task.user_id}/video_{uuid.uuid4().hex[:12]}"
    get_storage().save(key, raw)
    doc = crud.create_document(db, user_id=task.user_id, title=title or "视频", source_type="video",
                               content_hash=h, storage_key=key, size=len(raw), mime="video/*")
    for i, c in enumerate(chunks):
        db.add(Chunk(document_id=doc.id, content=c["content"], page=0, chunk_index=i,
                     content_hash=hashlib.sha256(c["content"].encode()).hexdigest(),
                     ts_start=c["ts_start"], ts_end=c["ts_end"]))
    doc.status = "ready"
    db.commit()

    transcript = "\n".join(c["content"] for c in chunks)
    q = quality(transcript)
    step = 25.0 / len(tpls)
    notes: list[dict] = []
    note = None
    for i, tpl in enumerate(tpls):
        base = 72 + step * i
        update(int(base), f"生成{_TPL_NAME[tpl]}笔记")
        try:
            obj, _ = asyncio.run(generate_json("mid", VIDEO_NOTE_SYSTEMS[tpl],
                                               video_note_user_tpl(transcript, tpl), _TPL_SCHEMA[tpl]))
            md = _RENDER[tpl](obj)
            pts = _note_points(obj, tpl)
            row = Note(document_id=doc.id, user_id=task.user_id,
                       title=f"{doc.title} · {_TPL_NAME[tpl]}", summary=obj.summary or "",
                       content=md, points=pts, source="video", kind=tpl)
            db.add(row)
            db.commit()
            db.refresh(row)
            notes.append({"id": row.id, "kind": tpl, "title": row.title, "summary": row.summary,
                          "content": md, "points": pts})
            if note is None:
                note = {"id": row.id, "kind": tpl, "summary": row.summary, "points": pts, "quality": q}
        except Exception as e:  # 单个模板失败不影响其他模板
            _log.warning("视频笔记模板 %s 生成失败：%s", tpl, e)
            try:
                db.rollback()
            except Exception:
                pass
        update(min(95, int(base + step)))

    # ---------- 关键帧图文笔记（PPT/讲义讲解场景，补充语音转写丢失的图表公式） ----------
    frame_items: list[dict] = []
    frame_note: dict = {"summary": "", "sections": [], "markdown": ""}
    if _is_video_src(src_path):
        try:
            update(92, "提取关键帧")
            # 抽帧 ffmpeg 可能全片解码数分钟且无法回写百分比：后台心跳刷新看门狗时间戳，
            # 防止正常执行的长任务被误判 TASK-TIMEOUT。
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
                frames = extract_frames(src_path, frame_dir(), max_frames=24)
            finally:
                _beat_stop.set()
                _beat.join(timeout=2)
            frames = dedupe_frames(frames)[:24]
            for f in frames:
                f["is_doc"] = is_doc_frame(f)
            update(95, "识别关键帧文字")
            ocr_items = asyncio.run(ocr_frames(frames, max_ocr=12)) if frames else []
            by_name = {it["path"]: it for it in ocr_items}
            frame_items = [{
                "ts": f["ts"], "ts_label": f["ts_label"], "path": public_path(f["name"]),
                "text": (by_name.get(f["name"]) or {}).get("text", ""),
                "is_doc": bool(f.get("is_doc")),
            } for f in frames]
            if ocr_items:
                update(97, "生成图文笔记")
                note_obj = asyncio.run(build_frame_note(ocr_items))
                md = render_frame_note_md(note_obj, ocr_items)
                frame_note = {"summary": note_obj.get("summary") or "",
                              "sections": note_obj.get("sections") or [], "markdown": md}
                if md.strip():
                    row = Note(document_id=doc.id, user_id=task.user_id,
                               title=f"{doc.title} · 图文", summary=frame_note["summary"],
                               content=md, points=frame_items, source="video", kind="frames")
                    db.add(row)
                    db.commit()
                    db.refresh(row)
                    notes.append({"id": row.id, "kind": "frames", "title": row.title,
                                  "summary": row.summary, "content": md, "points": frame_items})
        except Exception as e:  # 抽帧失败不影响主流程
            _log.warning("关键帧图文笔记失败：%s", e)
            try:
                db.rollback()
            except Exception:
                pass
    update(98, "整理结果")

    if note is None:
        note = {"summary": transcript[:200], "points": [], "quality": q, "kind": tpls[0]}
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
    return {"document_id": doc.id, "chunks": len(chunks), "segments": len(segs), "note": note,
            "notes": notes, "templates": tpls, "frames": frame_items, "frame_note": frame_note,
            "transcript": [{"start": round(float(s[0]), 1), "end": round(float(s[1]), 1),
                            "text": s[2]} for s in segs]}


def handle_video_upload(db, task, payload, update):
    path = payload["path"]
    try:
        with open(path, "rb") as f:
            raw = f.read()
        return _video_pipeline(db, task, path, payload.get("title") or "视频", update, raw,
                               templates=payload.get("templates"))
    finally:
        if os.path.exists(path):
            os.remove(path)


def handle_video_url(db, task, payload, update):
    update(5, "解析链接")
    workdir = tempfile.mkdtemp(prefix="gflc_dl_")
    audio_path = download_media(payload["url"], workdir)
    update(10, "下载完成")
    with open(audio_path, "rb") as f:
        raw = f.read()
    return _video_pipeline(db, task, audio_path, payload.get("title") or "B站视频", update, raw,
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
