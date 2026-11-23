# -*- coding: utf-8 -*-
"""刷题推荐：按「题库 × 章节」聚合进度，像背单词书一样决定今天练哪一章。"""
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from app.models.models import Attempt, Question, QuestionBank
from app.services.mastery import chapter_due_map, chapter_mastery_map

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
    # S6：注入章节掌握度与到期卡片数（只增字段，不改原契约）
    mastery_map = chapter_mastery_map(db, user_id, bank_id)
    due_map = chapter_due_map(db, user_id)
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
            "mastery": round(mastery_map.get((r.bank_id, r.chapter), 0.0), 4),
            "due_cards": int(due_map.get((r.bank_id, r.chapter), 0)),
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
        "mastery": 0.0, "due_cards": 0,
    }


def _empty(bank_id: int | None, chapter: str, bank_name: str = "") -> dict:
    label = _label(_chapter_of(chapter))
    return {
        "bank_id": bank_id, "bank_name": bank_name, "chapter": _chapter_of(chapter),
        "chapter_label": label, "total": 0, "done": 0, "correct_rate": 0.0,
        "due_wrong": 0, "progress": 0.0, "suggestion": "题库还没有题目，先到「题库」导入一份题库吧",
        "reason": "暂无题目可推荐",
    }


def _priority(r: dict) -> float:
    """S6 排序分：掌握度越低、错次越多、到期卡片越多，越优先（0–1）。

    权重：掌握度 0.5 + 错次 0.3 + 到期 0.2；全部为既有数据的归一化，不引入新依赖。
    """
    mastery = r.get("mastery", 0.0) or 0.0
    wrong = min(int(r.get("wrong_open", 0) or 0), 20) / 20.0
    due = min(int(r.get("due_cards", 0) or 0), 20) / 20.0
    return (1.0 - mastery) * 0.5 + wrong * 0.3 + due * 0.2


def pick_next(db: Session, user_id: int, bank_id: int | None = None,
              chapter: str | None = None) -> dict:
    """S6：从纯章节规则升级为「掌握度低 + 错次多 + 到期优先」的综合排序。

    仍只决定「练哪一章」，不调 LLM；保留全部原有响应字段，只新增 mastery/due_cards。
    """
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
            "mastery": round(r.get("mastery", 0.0), 4),
            "due_cards": int(r.get("due_cards", 0)),
        }

    book = "《{}》".format(stats[0].get("bank_name") or "题库")

    # 综合排序：掌握度低 + 错次多 + 到期多为优先；并列时沿用进度/历史顺序做稳定兜底
    stats.sort(key=lambda r: (-_priority(r), r["progress"], r["sort"]))
    r = stats[0]
    label = _label(r["chapter"])
    if r.get("due_cards", 0) > 0 and r.get("wrong_open", 0) > 0:
        reason = ("{} {} 掌握度 {:.0%}，有 {} 张卡到期、{} 道错题待复习，"
                  "建议今天优先补这一章").format(
            book, label, r.get("mastery", 0.0), r.get("due_cards", 0), r["wrong_open"])
    elif r.get("wrong_open", 0) > 0:
        reason = "{} {} 有 {} 道错题待复习（掌握度 {:.0%}），建议今天先攻克".format(
            book, label, r["wrong_open"], r.get("mastery", 0.0))
    elif r.get("due_cards", 0) > 0:
        reason = "{} {} 有 {} 张卡到期（掌握度 {:.0%}），建议今天先复习".format(
            book, label, r.get("due_cards", 0), r.get("mastery", 0.0))
    elif r["done"] == 0:
        reason = "{} {} 还没开始（共 {} 题），建议今天从这里起步".format(
            book, label, r["total"])
    elif r["done"] < r["total"]:
        reason = "{} {} 只练了 {}/{} 题（掌握度 {:.0%}），建议继续推进".format(
            book, label, r["done"], r["total"], r.get("mastery", 0.0))
    else:
        reason = "{} {} 已全部练完，正确率 {:.0%} 最低，建议巩固一遍".format(
            book, label, r["correct_rate"])
    return pack(r, reason)
