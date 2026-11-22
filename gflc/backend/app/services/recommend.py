# -*- coding: utf-8 -*-
"""刷题推荐：按「题库 × 章节」聚合进度，像背单词书一样决定今天练哪一章。"""
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from app.models.models import Attempt, Question, QuestionBank

UNC = "未分章"


def _chapter_of(chapter: str | None) -> str:
    return (chapter or "").strip()


def _label(chapter: str) -> str:
    return chapter or UNC


def attempt_agg(user_id: int):
    """每题作答汇总：作答次数 / 正确次数 / 最近一次 attempt id。"""
    return (
        select(
            Attempt.question_id.label("qid"),
            func.count(Attempt.id).label("attempts"),
            func.coalesce(func.sum(Attempt.correct), 0).label("correct"),
            func.max(Attempt.id).label("last_id"),
        )
        .where(Attempt.user_id == user_id)
        .group_by(Attempt.question_id)
        .subquery()
    )


def chapter_stats(db: Session, user_id: int, bank_id: int | None = None) -> list[dict]:
    """按 (bank_id, chapter) 聚合：total / done / correct / attempts / wrong_open。

    全部在 SQL 里聚合，不把题目捞到 Python 侧过滤。
    """
    agg = attempt_agg(user_id)
    last = aliased(Attempt)
    chapter_col = func.coalesce(Question.chapter, "")

    stmt = (
        select(
            Question.bank_id.label("bank_id"),
            chapter_col.label("chapter"),
            func.count(Question.id).label("total"),
            func.count(func.distinct(case((agg.c.attempts > 0, Question.id)))).label("done"),
            func.coalesce(func.sum(agg.c.correct), 0).label("correct"),
            func.coalesce(func.sum(agg.c.attempts), 0).label("attempts"),
            func.coalesce(
                func.sum(case((and_(agg.c.attempts > 0, last.correct == 0), 1), else_=0)), 0
            ).label("wrong_open"),
            func.min(Question.id).label("sort"),
        )
        .outerjoin(agg, agg.c.qid == Question.id)
        .outerjoin(last, last.id == agg.c.last_id)
        .where(Question.user_id == user_id)
        .group_by(Question.bank_id, chapter_col)
    )
    if bank_id is not None:
        stmt = stmt.where(Question.bank_id == bank_id)
    stmt = stmt.order_by(Question.bank_id, func.min(Question.id))

    banks = {
        b.id: b
        for b in db.scalars(select(QuestionBank).where(QuestionBank.user_id == user_id))
    }
    out: list[dict] = []
    for r in db.execute(stmt).all():
        total, done, attempts, correct = int(r.total), int(r.done), int(r.attempts), int(r.correct)
        bank = banks.get(r.bank_id) if r.bank_id else None
        out.append({
            "bank_id": r.bank_id,
            "bank_name": bank.name if bank else "",
            "subject": bank.subject if bank else "",
            "chapter": r.chapter,
            "chapter_label": _label(r.chapter),
            "total": total,
            "done": done,
            "correct": correct,
            "attempts": attempts,
            "wrong_open": int(r.wrong_open),
            "correct_rate": round(correct / attempts, 4) if attempts else 0.0,
            "progress": round(done / total, 4) if total else 0.0,
            "sort": int(r.sort or 0),
        })
    return out


def chapter_stat(db: Session, user_id: int, bank_id: int | None, chapter: str) -> dict:
    """单个章节的最新统计（提交后回传用）。"""
    rows = chapter_stats(db, user_id, bank_id)
    target = _chapter_of(chapter)
    for r in rows:
        if r["chapter"] == target:
            return r
    return {
        "bank_id": bank_id, "bank_name": "", "subject": "", "chapter": target,
        "chapter_label": _label(target), "total": 0, "done": 0, "correct": 0, "attempts": 0,
        "wrong_open": 0, "correct_rate": 0.0, "progress": 0.0, "sort": 0,
    }


def _empty(bank_id: int | None, chapter: str, bank_name: str = "") -> dict:
    label = _label(_chapter_of(chapter))
    return {
        "bank_id": bank_id, "bank_name": bank_name, "chapter": _chapter_of(chapter),
        "chapter_label": label, "total": 0, "done": 0, "correct_rate": 0.0,
        "due_wrong": 0, "progress": 0.0, "suggestion": "题库还没有题目，先到「题库」导入一份题库吧",
        "reason": "暂无题目可推荐",
    }


def pick_next(db: Session, user_id: int, bank_id: int | None = None,
              chapter: str | None = None) -> dict:
    """推荐下一章：错题复习 > 未开始/进度最低 > 正确率最低巩固。"""
    stats = [r for r in chapter_stats(db, user_id, bank_id) if r["total"] > 0]
    if chapter:
        target = _chapter_of(chapter)
        stats = [r for r in stats if r["chapter"] == target]
    if not stats:
        return _empty(bank_id, chapter or "")

    def pack(r: dict, reason: str) -> dict:
        return {
            "bank_id": r["bank_id"], "bank_name": r.get("bank_name", ""),
            "chapter": r["chapter"], "chapter_label": r["chapter_label"],
            "total": r["total"], "done": r["done"], "correct_rate": r["correct_rate"],
            "due_wrong": r["wrong_open"], "progress": r["progress"],
            "suggestion": reason, "reason": reason,
        }

    book = "《{}》".format(stats[0].get("bank_name") or "题库")

    # 1) 错题复习：仍有最近一次做错的题
    wrong = [r for r in stats if r["wrong_open"] > 0 and r["done"] > 0]
    if wrong:
        wrong.sort(key=lambda r: (-r["wrong_open"], r["progress"], r["sort"]))
        r = wrong[0]
        reason = "{} {} 有 {} 道错题待复习（正确率 {:.0%}），建议今天先攻克".format(
            book, _label(r["chapter"]), r["wrong_open"], r["correct_rate"])
        return pack(r, reason)

    # 2) 进度最低：未开始的章节优先
    pending = [r for r in stats if r["done"] < r["total"]]
    if pending:
        pending.sort(key=lambda r: (r["progress"], -r["wrong_open"], r["sort"]))
        r = pending[0]
        if r["done"] == 0:
            reason = "{} {} 还没开始（共 {} 题），建议今天从这里起步".format(
                book, _label(r["chapter"]), r["total"])
        else:
            reason = "{} {} 只练了 {}/{} 题，建议继续推进".format(
                book, _label(r["chapter"]), r["done"], r["total"])
        return pack(r, reason)

    # 3) 全部做完：正确率最低的章节做巩固
    stats.sort(key=lambda r: (r["correct_rate"], r["sort"]))
    r = stats[0]
    reason = "{} {} 已全部练完，正确率 {:.0%} 最低，建议巩固一遍".format(
        book, _label(r["chapter"]), r["correct_rate"])
    return pack(r, reason)
