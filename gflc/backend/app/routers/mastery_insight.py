# -*- coding: utf-8 -*-
"""掌握度统一画像（只读聚合）与两套掌握度的安全对齐工具。

背景（38 号规划 §六 P-3 / 37 号评审 I-4）：
    Card.mastery（复习评分侧）与 Question.mastery（刷题侧）各自独立演化，
    同一知识点常给出两个相反结论。本模块**不改数据模型、零迁移**：
    读取时把两套观测聚合成一份画像；需要合并时，只提供「两步确认」的对齐工具。

口径（与 documents.py 的 overview 保持一致）：
    score = 卡片与题目 mastery 的加权均值（卡 0.5 / 题 0.5；
            任一侧无观测时以另一侧为准）
    level：score < 0.35 → not_started；0.35 ≤ score ≤ 0.7 → learning；
            score > 0.7 → mastered
    章节归属：题目读 Question.chapter；卡片读所属章节卡包 CardDeck.name
            （kind='chapter'）。挂在根卡包或未挂卡包的卡片记为「无章节」。

聚合全部在 SQL 层完成（count / sum(case) / avg / sum），两套观测分别聚合后
按 (资料, 章节) 合并；不把明细捞到 Python 再过滤。

对齐工具的安全约束：
    - preview 为纯只读，不 flush / 不 commit；
    - reconcile 只写 mastery 一列，不动 due_at / reps / lapses / fsrs_state；
    - chapter 为空直接 400，避免误触全库改动；
    - 来源侧没有观测时拒绝执行（否则会把另一侧清零）。
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, case, func, select, update
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Attempt, Card, CardDeck, Document, Question
from app.routers.deps import get_current_user

router = APIRouter(prefix="/mastery", tags=["mastery"])

_MAX_ROWS = 20          # by_document / by_chapter 单次返回上限，避免大列表
_DIVERGENCE_TOP = 5     # 差异榜只取落差最大的 5 章
_PREVIEW_LIMIT = 100    # 对齐预览最多展示 100 条，完整数量另给 items_total
_DIRECTIONS = ("card_from_question", "question_from_card")


def _level(score: float) -> str:
    """与 documents.py:197 同一档位定义（0.7 属于学习中的上沿）。"""
    return "not_started" if score < 0.35 else ("learning" if score <= 0.7 else "mastered")


def _score(card_avg: float, card_n: int, q_avg: float, q_n: int) -> float:
    """卡 0.5 / 题 0.5；任一侧无观测（count=0）时以另一侧为准。"""
    if card_n and q_n:
        s = card_avg * 0.5 + q_avg * 0.5
    elif card_n:
        s = card_avg
    elif q_n:
        s = q_avg
    else:
        s = 0.0
    return round(max(0.0, min(1.0, s)), 3)


def _doc_cond(model, document_id: int | None) -> list:
    """可选的资料过滤条件（不传即全库，按 user_id 隔离）。"""
    return [] if document_id is None else [model.document_id == document_id]


def _require_document(db: Session, user_id: int, document_id: int | None) -> None:
    if document_id is None:
        return
    ok = db.scalar(select(Document.id).where(Document.id == document_id,
                                             Document.user_id == user_id))
    if ok is None:
        raise APIError(ErrCode.COMMON_404, "资料不存在", 404)


def _require_chapter(chapter: str) -> str:
    ch = (chapter or "").strip()
    if not ch:
        raise APIError(ErrCode.COMMON_400, "chapter 不能为空，避免全库对齐")
    return ch


# ---------------------------------------------------------------------------
# 只读聚合
# ---------------------------------------------------------------------------
def _overall(db: Session, user_id: int, document_id: int | None) -> dict:
    card_total, card_mastered, card_avg = db.execute(
        select(
            func.count(Card.id),
            func.coalesce(func.sum(case((Card.mastery > 0.7, 1), else_=0)), 0),
            func.coalesce(func.avg(Card.mastery), 0.0),
        ).where(Card.user_id == user_id, *_doc_cond(Card, document_id))
    ).one()

    q_total, q_avg = db.execute(
        select(
            func.count(Question.id),
            func.coalesce(func.avg(Question.mastery), 0.0),
        ).where(Question.user_id == user_id, *_doc_cond(Question, document_id))
    ).one()

    # answered = 有过 attempt 的不同题目数；accuracy 为百分数（与 overview 一致）
    q_answered, q_attempts, q_correct = db.execute(
        select(
            func.count(func.distinct(Attempt.question_id)),
            func.count(Attempt.id),
            func.coalesce(func.sum(case((Attempt.correct == 1, 1), else_=0)), 0),
        ).select_from(Question)
        .outerjoin(Attempt, and_(Attempt.question_id == Question.id,
                                 Attempt.user_id == user_id))
        .where(Question.user_id == user_id, *_doc_cond(Question, document_id))
    ).one()

    c_n = int(card_total or 0)
    q_n = int(q_total or 0)
    c_avg = float(card_avg or 0.0)
    q_avg = float(q_avg or 0.0)
    score = _score(c_avg, c_n, q_avg, q_n)

    return {
        "score": score,
        "level": _level(score),
        "cards": {
            "total": c_n,
            "mastered": int(card_mastered or 0),
            "avg": round(c_avg, 3),
        },
        "questions": {
            "total": q_n,
            "answered": int(q_answered or 0),
            "avg": round(q_avg, 3),
            "accuracy": round(int(q_correct or 0) / int(q_attempts) * 100, 1) if q_attempts else 0.0,
        },
    }


def _chapter_rows(db: Session, user_id: int, document_id: int | None) -> list[dict]:
    """按 (资料, 章节) 分别聚合卡片与题目，再合并成一行。

    返回行含 cards/questions 计数、两侧 mastery 之和、两侧均值与加权 score。
    全部为 SQL 分组结果，Python 侧只做同键相加（等价于 count 相加、sum 相加）。
    """
    card_rows = db.execute(
        select(
            Card.document_id.label("document_id"),
            func.trim(func.coalesce(CardDeck.name, "")).label("chapter"),
            func.count(Card.id).label("total"),
            func.coalesce(func.sum(Card.mastery), 0.0).label("m_sum"),
        )
        .select_from(Card)
        .outerjoin(CardDeck, and_(Card.deck_id == CardDeck.id, CardDeck.kind == "chapter"))
        .where(Card.user_id == user_id, *_doc_cond(Card, document_id))
        .group_by(Card.document_id, func.trim(func.coalesce(CardDeck.name, "")))
    ).all()

    q_rows = db.execute(
        select(
            Question.document_id.label("document_id"),
            func.trim(func.coalesce(Question.chapter, "")).label("chapter"),
            func.count(Question.id).label("total"),
            func.coalesce(func.sum(Question.mastery), 0.0).label("m_sum"),
        )
        .where(Question.user_id == user_id, *_doc_cond(Question, document_id))
        .group_by(Question.document_id, func.trim(func.coalesce(Question.chapter, "")))
    ).all()

    merged: dict[tuple[int, str], dict] = {}

    def _slot(doc_id, chapter) -> dict:
        key = (int(doc_id), chapter or "")
        return merged.setdefault(key, {
            "document_id": int(doc_id), "chapter": chapter or "",
            "cards": 0, "card_sum": 0.0, "questions": 0, "q_sum": 0.0,
        })

    for r in card_rows:
        s = _slot(r.document_id, r.chapter)
        s["cards"] = int(r.total or 0)
        s["card_sum"] = float(r.m_sum or 0.0)
    for r in q_rows:
        s = _slot(r.document_id, r.chapter)
        s["questions"] = int(r.total or 0)
        s["q_sum"] = float(r.m_sum or 0.0)

    out: list[dict] = []
    for s in merged.values():
        ca = s["card_sum"] / s["cards"] if s["cards"] else 0.0
        qa = s["q_sum"] / s["questions"] if s["questions"] else 0.0
        out.append({
            **s,
            "card_avg": ca,
            "q_avg": qa,
            "score": _score(ca, s["cards"], qa, s["questions"]),
        })
    return out


def _by_document(rows: list[dict], titles: dict[int, str]) -> list[dict]:
    grouped: dict[int, dict] = {}
    for r in rows:
        g = grouped.setdefault(r["document_id"], {
            "cards": 0, "card_sum": 0.0, "questions": 0, "q_sum": 0.0,
        })
        g["cards"] += r["cards"]
        g["card_sum"] += r["card_sum"]
        g["questions"] += r["questions"]
        g["q_sum"] += r["q_sum"]

    out: list[dict] = []
    for doc_id, g in grouped.items():
        ca = g["card_sum"] / g["cards"] if g["cards"] else 0.0
        qa = g["q_sum"] / g["questions"] if g["questions"] else 0.0
        score = _score(ca, g["cards"], qa, g["questions"])
        out.append({
            "document_id": doc_id,
            "title": titles.get(doc_id, f"资料 #{doc_id}"),
            "cards": g["cards"],
            "questions": g["questions"],
            "score": score,
            "level": _level(score),
        })
    # 薄弱优先，便于先看最需要补的资料
    out.sort(key=lambda x: (x["score"], x["document_id"]))
    return out[:_MAX_ROWS]


def _by_chapter(rows: list[dict]) -> list[dict]:
    """跨资料按章节名合并；无章节（chapter=''）不进入章节榜。"""
    grouped: dict[str, dict] = {}
    for r in rows:
        ch = r["chapter"]
        if not ch:
            continue
        g = grouped.setdefault(ch, {
            "cards": 0, "card_sum": 0.0, "questions": 0, "q_sum": 0.0,
        })
        g["cards"] += r["cards"]
        g["card_sum"] += r["card_sum"]
        g["questions"] += r["questions"]
        g["q_sum"] += r["q_sum"]

    out: list[dict] = []
    for ch, g in grouped.items():
        ca = g["card_sum"] / g["cards"] if g["cards"] else 0.0
        qa = g["q_sum"] / g["questions"] if g["questions"] else 0.0
        score = _score(ca, g["cards"], qa, g["questions"])
        out.append({
            "chapter": ch,
            "cards": g["cards"],
            "questions": g["questions"],
            "card_score": round(ca, 3),
            "question_score": round(qa, 3),
            "score": score,
            "level": _level(score),
        })
    out.sort(key=lambda x: (x["score"], x["chapter"]))
    return out


def _divergence(chapters: list[dict]) -> list[dict]:
    """只统计两侧都有观测、且结论确实不一致的章节。

    两侧都无观测无从对齐；gap 为 0 表示已经一致，不再计入「差异 N 处」。
    """
    items = []
    for c in chapters:
        if not (c["cards"] and c["questions"]):
            continue
        gap = round(abs(c["card_score"] - c["question_score"]), 3)
        if gap <= 0:
            continue
        items.append({
            "chapter": c["chapter"],
            "card_score": c["card_score"],
            "question_score": c["question_score"],
            "gap": gap,
        })
    items.sort(key=lambda x: (-x["gap"], x["chapter"]))
    return items


@router.get("/insight")
async def mastery_insight(document_id: int | None = Query(default=None),
                          user=Depends(get_current_user), db: Session = Depends(get_db)):
    """两套掌握度的统一画像（只读）。

    可选 document_id 把统计收窄到一份资料（资料详情页用）；不传为全库。
    返回契约见 38 号规划 §六 P-3：overall / by_document / by_chapter / divergence。
    divergence 取落差最大的 5 章；divergence_total 给出完整差异章数，供前端显示 N 处。
    """
    _require_document(db, user.id, document_id)

    rows = _chapter_rows(db, user.id, document_id)
    chapters = _by_chapter(rows)
    divergence = _divergence(chapters)

    doc_ids = sorted({r["document_id"] for r in rows})
    titles: dict[int, str] = {}
    if doc_ids:
        titles = dict(db.execute(
            select(Document.id, Document.title)
            .where(Document.user_id == user.id, Document.id.in_(doc_ids))
        ).all())

    return {"ok": True, "data": {
        "overall": _overall(db, user.id, document_id),
        "by_document": _by_document(rows, titles),
        # 契约只保留章节画像字段；card_score / question_score 仅内部用于算 gap
        "by_chapter": [{
            "chapter": c["chapter"],
            "cards": c["cards"],
            "questions": c["questions"],
            "score": c["score"],
            "level": c["level"],
        } for c in chapters[:_MAX_ROWS]],
        "divergence": divergence[:_DIVERGENCE_TOP],
        "divergence_total": len(divergence),
    }}


# ---------------------------------------------------------------------------
# 对齐工具：preview 只读 → reconcile 写入，两步确认
# ---------------------------------------------------------------------------
class ReconcileIn(BaseModel):
    chapter: str
    direction: str                  # card_from_question | question_from_card
    document_id: int | None = None


def _card_side_stmt(user_id: int, chapter: str, document_id: int | None):
    """章节卡片（只认章节卡包；根卡包与未挂包不算任何章节）。"""
    return (
        select(Card.id, Card.question.label("title"), Card.mastery.label("before"))
        .select_from(Card)
        .join(CardDeck, and_(Card.deck_id == CardDeck.id, CardDeck.kind == "chapter"))
        .where(Card.user_id == user_id, func.trim(CardDeck.name) == chapter,
               *_doc_cond(Card, document_id))
    )


def _question_side_stmt(user_id: int, chapter: str, document_id: int | None):
    return (
        select(Question.id, Question.stem.label("title"), Question.mastery.label("before"))
        .where(Question.user_id == user_id,
               func.trim(func.coalesce(Question.chapter, "")) == chapter,
               *_doc_cond(Question, document_id))
    )


def _side_count_avg(db: Session, user_id: int, chapter: str, document_id: int | None,
                    side: str) -> tuple[int, float]:
    """单侧观测的 count 与均值（SQL 聚合），用于「以谁为准」。"""
    if side == "card":
        total, m_sum = db.execute(
            select(func.count(Card.id), func.coalesce(func.sum(Card.mastery), 0.0))
            .select_from(Card)
            .join(CardDeck, and_(Card.deck_id == CardDeck.id, CardDeck.kind == "chapter"))
            .where(Card.user_id == user_id, func.trim(CardDeck.name) == chapter,
                   *_doc_cond(Card, document_id))
        ).one()
    else:
        total, m_sum = db.execute(
            select(func.count(Question.id), func.coalesce(func.sum(Question.mastery), 0.0))
            .where(Question.user_id == user_id,
                   func.trim(func.coalesce(Question.chapter, "")) == chapter,
                   *_doc_cond(Question, document_id))
        ).one()
    n = int(total or 0)
    return n, (float(m_sum or 0.0) / n if n else 0.0)


def _parse_direction(direction: str) -> tuple[str, str]:
    if direction not in _DIRECTIONS:
        raise APIError(ErrCode.COMMON_400,
                       "direction 只支持 card_from_question / question_from_card")
    if direction == "card_from_question":
        return "question", "card"
    return "card", "question"


@router.get("/reconcile/preview")
async def reconcile_preview(chapter: str = Query(...),
                            direction: str = Query("card_from_question"),
                            document_id: int | None = Query(default=None),
                            user=Depends(get_current_user), db: Session = Depends(get_db)):
    """对齐前的影响预览：只读，不写库、不 flush。"""
    ch = _require_chapter(chapter)
    src_side, tgt_side = _parse_direction(direction)
    _require_document(db, user.id, document_id)

    src_n, src_avg = _side_count_avg(db, user.id, ch, document_id, src_side)
    if src_n == 0:
        label = "题目" if src_side == "question" else "卡片"
        raise APIError(ErrCode.COMMON_400, f"该章节没有{label}掌握度，无法以其为准")

    stmt = (_question_side_stmt if tgt_side == "question" else _card_side_stmt)(
        user.id, ch, document_id)
    rows = list(db.execute(stmt).all())
    after = round(src_avg, 3)

    return {"ok": True, "data": {
        "chapter": ch,
        "document_id": document_id,
        "direction": direction,
        "source": {"side": src_side, "count": src_n, "score": after},
        "target": {"side": tgt_side, "count": len(rows)},
        "items": [{
            "id": int(r.id),
            "title": (r.title or "")[:80],
            "before": round(float(r.before or 0.0), 3),
            "after": after,
        } for r in rows[:_PREVIEW_LIMIT]],
        "items_total": len(rows),
    }}


@router.post("/reconcile")
async def reconcile(body: ReconcileIn, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """执行对齐：把来源侧均值写入目标侧的 mastery（只改这一列）。"""
    ch = _require_chapter(body.chapter)
    src_side, tgt_side = _parse_direction(body.direction)
    _require_document(db, user.id, body.document_id)

    src_n, src_avg = _side_count_avg(db, user.id, ch, body.document_id, src_side)
    if src_n == 0:
        label = "题目" if src_side == "question" else "卡片"
        raise APIError(ErrCode.COMMON_400, f"该章节没有{label}掌握度，无法以其为准")

    stmt = (_question_side_stmt if tgt_side == "question" else _card_side_stmt)(
        user.id, ch, body.document_id)
    ids = [int(r.id) for r in db.execute(stmt).all()]
    if not ids:
        label = "卡片" if tgt_side == "card" else "题目"
        raise APIError(ErrCode.COMMON_400, f"该章节没有可对齐的{label}")

    after = round(src_avg, 3)
    if tgt_side == "card":
        # 只更新 mastery；due_at / reps / lapses / fsrs_state 一律不动
        res = db.execute(
            update(Card).where(Card.id.in_(ids), Card.user_id == user.id).values(mastery=after)
        )
    else:
        res = db.execute(
            update(Question).where(Question.id.in_(ids), Question.user_id == user.id).values(mastery=after)
        )
    db.commit()
    return {"ok": True, "data": {"updated": int(res.rowcount or 0)}}
