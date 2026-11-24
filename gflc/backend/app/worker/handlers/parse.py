# -*- coding: utf-8 -*-
"""文档解析 / 卡片生成 / 题库导入任务处理（原 handlers.py 原样迁出）。"""
import asyncio
import hashlib
import os
import tempfile
import uuid

from app.core.errors import APIError
from app.crud import crud
from app.models.models import Document, Question, QuestionBank
from app.services.cards import generate_cards
from app.services.pipeline import parse_pdf_to_chunks
from app.services.question_parse import extract_text, parse_questions
from app.services.question_vision import parse_paper
from app.services.storage import download_to


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
