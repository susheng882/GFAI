# -*- coding: utf-8 -*-
"""刷题：书目录式总览、动态推荐、组卷、判分、错题本、错题转卡片。"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, delete, func, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Attempt, Card, CardDeck, Question, QuestionBank
from app.routers.deps import get_current_user
from app.schemas.schemas import QuestionOut, QuizSubmitIn
from app.services.mastery import update_question_mastery
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
    qtype: str | None = None  # B11：题型精确筛选 single / multiple / fill / short


# 题型白名单与中文名：只用于入参校验与「无匹配」提示文案
QTYPE_LABELS = {"single": "单选题", "multiple": "多选题", "fill": "填空题", "short": "简答题"}


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
    # B11：题型筛选在 SQL 侧完成（Question.qtype），不在应用层捞全表再过滤
    qtype = (body.qtype or "").strip().lower() or None
    if qtype is not None and qtype not in QTYPE_LABELS:
        raise APIError(ErrCode.COMMON_400, "qtype 只支持 single / multiple / fill / short")
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
    if qtype is not None:
        conds.append(Question.qtype == qtype)  # B11：下推到 WHERE，走 SQL 过滤

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
        # B11：已指定题型却无匹配时返回空列表 + 中文提示，不抛错（前端可提示换题型）
        if qtype is not None:
            return {"ok": True, "data": [], "qtype": qtype,
                    "message": f"当前范围内没有{QTYPE_LABELS[qtype]}，换一种题型或调整章节后再试"}
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
    # S6：答题结果联动掌握度（答对上升、答错下降），与 attempt 同一事务提交
    new_mastery = update_question_mastery(db, q, correct)
    db.add(Attempt(user_id=user.id, question_id=q.id, user_answer=body.user_answer,
                   correct=1 if correct else 0))
    db.commit()
    stats = chapter_stat(db, user.id, q.bank_id, q.chapter or "")
    return {"ok": True, "data": {
        "correct": correct, "answer": q.answer, "analysis": q.analysis,
        "mastery": round(new_mastery, 4),
        "stats": {
            "bank_id": q.bank_id, "chapter": q.chapter,
            "chapter_label": stats["chapter_label"],
            "total": stats["total"], "done": stats["done"],
            "correct_rate": stats["correct_rate"], "progress": stats["progress"],
            "wrong_open": stats["wrong_open"],
        },
    }}


@router.get("/related/{question_id}")
async def related(question_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """同类真题推荐 + 选项分布 + 相关知识点（v7l 刷题页右栏/底部）。"""
    q = db.scalar(select(Question).where(Question.id == question_id, Question.user_id == user.id))
    if not q:
        raise APIError(ErrCode.COMMON_404, "题目不存在", 404)
    # 同章节题目（排除自身，最多 4 道）
    siblings = list(db.scalars(select(Question).where(
        Question.user_id == user.id, Question.chapter == q.chapter, Question.id != q.id)
        .order_by(Question.id).limit(4)))
    related_qs = [{"id": x.id, "stem": (x.stem or "")[:80], "chapter": x.chapter or "未分类"}
                  for x in siblings]
    # 选项分布：本题各选项被选择次数（来自 attempts）
    dist_rows = db.execute(
        select(Attempt.user_answer, func.count()).where(Attempt.question_id == question_id)
        .group_by(Attempt.user_answer)).all()
    total_attempts = sum(n for _, n in dist_rows) or 1
    dist = [{"option": (ans or "空"), "count": n,
             "pct": round(n / total_attempts * 100, 1)} for ans, n in dist_rows]
    # 相关知识点：章节名 + 五段解析的 point
    points = []
    if q.chapter:
        points.append(q.chapter)
    if isinstance(q.analysis, dict) and q.analysis.get("point"):
        points.append(q.analysis["point"][:60])
    return {"ok": True, "data": {
        "related": related_qs, "option_dist": dist, "points": points,
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
        # S6：错题本由 attempts（错次）与 mastery（薄弱度）联动排序
        .order_by(agg.c.wrong_count.desc(), Question.mastery.asc(), agg.c.last_wrong_id.desc())
        .limit(200)
    )
    if bank_id is not None:
        stmt = stmt.where(Question.bank_id == bank_id)

    out = []
    for q, wrong_count, last_answer in db.execute(stmt).all():
        out.append({**QuestionOut.model_validate(q).model_dump(),
                    "last_answer": last_answer or "", "wrong_count": int(wrong_count),
                    "mastery": round(q.mastery or 0.0, 4)})
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


# ---------- 错题 → 卡片（错误 → 强化回路） ----------
# 零迁移：复用 cards 表，document_id 取题目所属文档，溯源靠 anchor_id（gflc::q::<id>）。
WRONG_DECK_NAME = "错题收藏"


def _opt_lines(options) -> list[str]:
    """选项列表 → 「A. 文本」行；已带字母前缀的原样保留，避免出现「A. A. 文本」。"""
    if not isinstance(options, list):
        return []
    out = []
    for i, opt in enumerate(options):
        txt = str(opt).strip()
        if not txt:
            continue
        letter = chr(65 + i)
        out.append(txt if re.match(rf"^{letter}\s*[.、)．]", txt) else f"{letter}. {txt}")
    return out


def _points(v) -> list[str]:
    """analysis 的 steps / pitfalls 兼容 str 与 list，空值返回空列表。"""
    if isinstance(v, str):
        return [v.strip()] if v.strip() else []
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return []


def _card_front(q: Question) -> str:
    """卡片正面：题干 + 选项列表。"""
    head = (q.stem or "").strip()
    opts = "\n".join(_opt_lines(q.options))
    return "\n\n".join(p for p in (head, opts) if p) or "（空题目）"


def _card_back(q: Question) -> str:
    """卡片背面：正确答案 + 解析要点（steps / pitfalls）；无解析时只留答案。"""
    ans = (q.answer or "").strip()
    analysis = q.analysis if isinstance(q.analysis, dict) else {}
    steps, pitfalls = _points(analysis.get("steps")), _points(analysis.get("pitfalls"))
    lines = [f"正确答案：{ans}"] if ans else []
    if steps:
        lines.append("解题要点：")
        lines.extend(f"{i}. {s}" for i, s in enumerate(steps, 1))
    if pitfalls:
        lines.append("易错点：" + "；".join(pitfalls))
    return "\n".join(lines) or "（暂无答案）"


def _wrong_deck(db: Session, user_id: int, document_id: int | None) -> CardDeck:
    """复用该用户的「错题收藏」卡包，没有则自动创建（不做唯一约束，保持零迁移）。"""
    deck = db.scalar(select(CardDeck).where(CardDeck.user_id == user_id,
                                            CardDeck.name == WRONG_DECK_NAME)
                     .order_by(CardDeck.id))
    if deck is not None:
        return deck
    deck = CardDeck(user_id=user_id, document_id=document_id, parent_id=None,
                    name=WRONG_DECK_NAME, kind="root", sort=0)
    db.add(deck)
    db.flush()
    return deck


@router.post("/questions/{question_id}/to-card")
async def question_to_card(question_id: int, user=Depends(get_current_user),
                           db: Session = Depends(get_db)):
    """把一道错题落成复习卡片；同一题重复调用返回已有卡片，不重复建。"""
    q = db.get(Question, question_id)
    if q is None:
        raise APIError(ErrCode.COMMON_404, "题目不存在", 404)
    if q.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权访问该题", 403)

    anchor_id = f"gflc::q::{q.id}"
    exist = db.scalar(select(Card).where(Card.user_id == user.id, Card.anchor_id == anchor_id))
    if exist is not None:
        return {"ok": True, "data": {"id": exist.id, "deck_id": exist.deck_id, "existed": True}}

    deck = _wrong_deck(db, user.id, q.document_id)
    chapter = (q.chapter or "").strip()
    card = Card(user_id=user.id, document_id=q.document_id, deck_id=deck.id,
                question=_card_front(q), answer=_card_back(q),
                tag=f"错题 · {chapter or '未分章'}",
                difficulty=q.difficulty or "mid", page=q.page or 0,
                anchor_id=anchor_id,
                due_at=datetime.now(timezone.utc), reps=0, lapses=0)
    db.add(card)
    db.commit()
    db.refresh(card)
    return {"ok": True, "data": {"id": card.id, "deck_id": card.deck_id, "existed": False}}

