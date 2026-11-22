# -*- coding: utf-8 -*-
"""刷题：书目录式总览、动态推荐、组卷、判分、错题本。"""
import re

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Attempt, Question, QuestionBank
from app.routers.deps import get_current_user
from app.schemas.schemas import QuestionOut, QuizSubmitIn
from app.services.recommend import attempt_agg, chapter_stat, chapter_stats, pick_next

router = APIRouter(prefix="/quiz", tags=["quiz"])


class QuizGenBody(BaseModel):
    """组卷入参（在 QuizGenIn 基础上扩展，保持旧字段兼容）。"""
    count: int = 5
    document_id: int | None = None
    bank_id: int | None = None
    chapter: str | None = None
    only_wrong: bool = False
    mode: str | None = None  # recommend / new / wrong


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "").strip().upper())


def _letters(s: str) -> str:
    return "".join(sorted(set(re.findall(r"[A-D]", _norm(s)))))


def _judge(qtype: str, ua: str, ca: str, options: list | None) -> bool:
    """严格判分：多选比字母集合，单选允许选项文本→字母映射，填空长度受控。"""
    nu, nc = _norm(ua), _norm(ca)
    if not nu:
        return False
    if nu == nc:
        return True
    if qtype in ("single", "multiple"):
        lu, lc = _letters(ua), _letters(ca)
        if lc and lu and lu == lc:
            return True
        if options:  # 用户输入的是选项文本
            idx = "".join(sorted(chr(65 + i) for i, o in enumerate(options) if _norm(o) == nu))
            if idx and lc and idx == lc:
                return True
        return False
    if qtype in ("fill", "short"):  # 答案被完整包含且长度接近，避免 "A" 命中 "ABC"
        return nc in nu and len(nu) <= len(nc) + 10
    return False


def _last_attempt_sub(user_id: int):
    """每题最近一次 attempt id。"""
    return (
        select(func.max(Attempt.id).label("lid"))
        .where(Attempt.user_id == user_id)
        .group_by(Attempt.question_id)
        .subquery()
    )


def _chapter_filter(stmt, chapter: str):
    return stmt.where(func.coalesce(Question.chapter, "") == chapter)


@router.get("/overview")
async def overview(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """书目录：题库集 + 章节数 + 题数 + 整体进度。"""
    stats = chapter_stats(db, user.id)
    banks = list(db.scalars(select(QuestionBank).where(QuestionBank.user_id == user.id)
                            .order_by(QuestionBank.id.desc()).limit(50)))

    by_bank: dict = {}
    for r in stats:
        b = by_bank.setdefault(r["bank_id"], {"chapters": 0, "total": 0, "done": 0,
                                              "correct": 0, "attempts": 0, "wrong_open": 0})
        b["chapters"] += 1
        for k in ("total", "done", "correct", "attempts", "wrong_open"):
            b[k] += r[k]

    out, covered = [], set()
    for bk in banks:
        s = by_bank.get(bk.id, {})
        covered.add(bk.id)
        total, done = int(s.get("total", 0)), int(s.get("done", 0))
        attempts, correct = int(s.get("attempts", 0)), int(s.get("correct", 0))
        out.append({
            "id": bk.id, "name": bk.name, "subject": bk.subject,
            "total": total, "chapters": int(s.get("chapters", 0)),
            "done": done, "correct_rate": round(correct / attempts, 4) if attempts else 0.0,
            "progress": round(done / total, 4) if total else 0.0,
            "wrong_open": int(s.get("wrong_open", 0)),
            "created_at": bk.created_at.isoformat() if bk.created_at else None,
        })
    # 未挂到题库集的题目（历史数据）单独成一组，保证不丢
    orphan = by_bank.get(None)
    if orphan:
        total, done = int(orphan["total"]), int(orphan["done"])
        attempts, correct = int(orphan["attempts"]), int(orphan["correct"])
        out.append({
            "id": None, "name": "未归类题库", "subject": "",
            "total": total, "chapters": int(orphan["chapters"]), "done": done,
            "correct_rate": round(correct / attempts, 4) if attempts else 0.0,
            "progress": round(done / total, 4) if total else 0.0,
            "wrong_open": int(orphan["wrong_open"]), "created_at": None,
        })

    total = sum(r["total"] for r in stats)
    done = sum(r["done"] for r in stats)
    attempts = sum(r["attempts"] for r in stats)
    correct = sum(r["correct"] for r in stats)
    return {"ok": True, "data": {
        "banks": out,
        "total": total, "done": done, "chapters": len(stats),
        "attempts": attempts,
        "correct_rate": round(correct / attempts, 4) if attempts else 0.0,
        "progress": round(done / total, 4) if total else 0.0,
        "wrong_open": sum(r["wrong_open"] for r in stats),
        "recommend": pick_next(db, user.id),
    }}


@router.get("/recommend")
async def recommend(bank_id: int | None = None, chapter: str | None = None,
                    user=Depends(get_current_user), db: Session = Depends(get_db)):
    """今天练哪一章：错题复习 > 进度最低 > 正确率最低巩固。"""
    rec = pick_next(db, user.id, bank_id, chapter)
    return {"ok": True, "data": rec}


@router.get("/chapters")
async def chapters(bank_id: int | None = None, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    rows = chapter_stats(db, user.id, bank_id)
    rows.sort(key=lambda r: r["sort"])
    return {"ok": True, "data": rows}


@router.post("/generate")
async def generate(body: QuizGenBody, user=Depends(get_current_user),
                   db: Session = Depends(get_db)):
    count = max(1, min(body.count, 50))
    mode = (body.mode or ("wrong" if body.only_wrong else "new")).lower()
    bank_id, chapter = body.bank_id, body.chapter
    pinned_chapter = None

    if mode == "recommend" and not (chapter or "").strip():
        rec = pick_next(db, user.id, bank_id)
        if not rec.get("total"):
            raise APIError(ErrCode.COMMON_400, rec.get("suggestion") or "题库为空，请先导入题库")
        bank_id = rec["bank_id"]
        pinned_chapter = rec["chapter"]

    # 条件全为 SQL 侧过滤，聚合列只用于排序
    conds = [Question.user_id == user.id]
    if bank_id is not None:
        conds.append(Question.bank_id == bank_id)
    if body.document_id:
        conds.append(Question.document_id == body.document_id)
    if (chapter or "").strip():
        conds.append(Question.chapter == chapter.strip())
    if pinned_chapter is not None:
        conds.append(func.coalesce(Question.chapter, "") == pinned_chapter)

    agg = attempt_agg(user.id)
    stmt = select(Question).outerjoin(agg, agg.c.qid == Question.id).where(*conds)

    if mode == "wrong" or body.only_wrong:
        la = _last_attempt_sub(user.id)
        last_a = aliased(Attempt)
        wrong_ids = (select(last_a.question_id)
                     .join(la, la.c.lid == last_a.id)
                     .where(last_a.correct == 0).scalar_subquery())
        stmt = stmt.where(Question.id.in_(wrong_ids))

    # 优先没做过的题；不足时由同一查询补齐已做过的
    stmt = stmt.order_by(
        case((func.coalesce(agg.c.attempts, 0) == 0, 0), else_=1), func.random()
    ).limit(count)
    picked = list(db.scalars(stmt))
    if not picked:
        msg = "本题库暂无错题，换个章节练练吧" if (mode == "wrong" or body.only_wrong) \
            else "题库为空，请先在「题库」导入题目"
        raise APIError(ErrCode.COMMON_400, msg)

    # 出题时不给答案
    return {"ok": True, "data": [
        {"id": q.id, "stem": q.stem, "options": q.options, "qtype": q.qtype,
         "difficulty": q.difficulty, "bank_id": q.bank_id, "chapter": q.chapter}
        for q in picked
    ]}


@router.post("/submit")
async def submit(body: QuizSubmitIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.scalar(select(Question).where(Question.id == body.question_id, Question.user_id == user.id))
    if not q:
        raise APIError(ErrCode.AUTH_403, "无权访问该题", 403)
    ua, ca = body.user_answer, q.answer
    correct = _judge(q.qtype, ua, ca, q.options)
    db.add(Attempt(user_id=user.id, question_id=q.id, user_answer=body.user_answer,
                   correct=1 if correct else 0))
    db.commit()
    stats = chapter_stat(db, user.id, q.bank_id, q.chapter or "")
    return {"ok": True, "data": {
        "correct": correct, "answer": q.answer, "analysis": q.analysis,
        "stats": {
            "bank_id": q.bank_id, "chapter": q.chapter,
            "chapter_label": stats["chapter_label"],
            "total": stats["total"], "done": stats["done"],
            "correct_rate": stats["correct_rate"], "progress": stats["progress"],
            "wrong_open": stats["wrong_open"],
        },
    }}


@router.get("/wrong")
async def wrong(bank_id: int | None = None, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    """错题本：最近一次作答为错的题 + 最近一次错误答案 + 错误次数。"""
    la = _last_attempt_sub(user.id)
    last_a = aliased(Attempt)
    agg = (
        select(
            Attempt.question_id.label("qid"),
            func.count(Attempt.id).label("wrong_count"),
            func.max(Attempt.id).label("last_wrong_id"),
        )
        .where(Attempt.user_id == user.id, Attempt.correct == 0)
        .group_by(Attempt.question_id)
        .subquery()
    )
    stmt = (
        select(Question, agg.c.wrong_count, last_a.user_answer)
        .join(agg, agg.c.qid == Question.id)
        .join(last_a, last_a.id == agg.c.last_wrong_id)
        .join(la, la.c.lid == agg.c.last_wrong_id)  # 只有「最近一次仍错」才在错题本
        .where(Question.user_id == user.id)
        .order_by(agg.c.wrong_count.desc(), agg.c.last_wrong_id.desc())
        .limit(200)
    )
    if bank_id is not None:
        stmt = stmt.where(Question.bank_id == bank_id)

    out = []
    for q, wrong_count, last_answer in db.execute(stmt).all():
        out.append({**QuestionOut.model_validate(q).model_dump(),
                    "last_answer": last_answer or "", "wrong_count": int(wrong_count)})
    return {"ok": True, "data": out}


@router.delete("/attempts/{question_id}")
async def reset_attempts(question_id: int, user=Depends(get_current_user),
                         db: Session = Depends(get_db)):
    q = db.scalar(select(Question).where(Question.id == question_id,
                                         Question.user_id == user.id))
    if not q:
        raise APIError(ErrCode.AUTH_403, "无权访问该题", 403)
    res = db.execute(delete(Attempt).where(Attempt.user_id == user.id,
                                           Attempt.question_id == question_id))
    db.commit()
    return {"ok": True, "data": {"question_id": question_id, "deleted": int(res.rowcount or 0)}}

