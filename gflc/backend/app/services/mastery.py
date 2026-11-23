# -*- coding: utf-8 -*-
"""S6 掌握度服务：把「答题 / 复习评分 → 掌握度 → 复习 due」串成闭环。

设计约束（来自多 Agent 硬门禁）：
- 不引入新依赖、不调用 LLM，全部为本地纯计算 + 数据库聚合；
- 掌握度用 0–1 浮点，答对上升、答错下降，边界裁剪；
- 复习 due 从掌握度派生：掌握度越低，下次复习来得越早；
- 章节掌握度由该章题目掌握度与历史正确率融合得到，供错题本与推荐排序消费。

所有开关用 os.getenv 读取，默认值在此，由集成方统一回填 config/.env.example。
"""
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import (
    Attempt, Card, Chunk, Document, Note, Plan, PlanTask, Question, QuestionBank, Task,
)

# 新增环境变量（默认值即生产可用值，集成方按需回填）
MASTERY_STEP = float(os.getenv("GFLC_MASTERY_STEP", "0.12"))            # 答对/好评一次提升量
MASTERY_PENALTY = float(os.getenv("GFLC_MASTERY_PENALTY", "1.5"))       # 答错相对惩罚倍率
MASTERY_DUE_THRESHOLD = float(os.getenv("GFLC_MASTERY_DUE_THRESHOLD", "0.6"))  # 低于此值视为待复习
MASTERY_BASE_DAYS = float(os.getenv("GFLC_MASTERY_BASE_DAYS", "7"))     # 满分掌握度的复习间隔基准天数

# FSRS 评分（1 Again / 2 Hard / 3 Good / 4 Easy）对应的掌握度增量系数
_RATING_FACTOR = {1: -1.6, 2: -0.4, 3: 1.0, 4: 1.5}


def clamp01(x: float) -> float:
    """把数值裁剪到 [0, 1]。"""
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else float(x))


def _safe_float(v) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(dt: datetime | None) -> datetime | None:
    """SQLite 读回的时间无时区，统一补 UTC 后再与 now 比较。"""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# 卡片：复习评分 → 掌握度 → due
# ---------------------------------------------------------------------------
def card_mastery_after_rating(mastery: float, rating: int) -> float:
    """按 FSRS 评分推算新掌握度（纯函数，便于单测）。"""
    factor = _RATING_FACTOR.get(rating, 0.0)
    return clamp01(_safe_float(mastery) + MASTERY_STEP * factor)


def derive_due_at(mastery: float, *, now: datetime | None = None) -> datetime:
    """从掌握度派生下次复习时间：掌握度 0 → 立刻，掌握度 1 → BASE_DAYS 天后。

    线性插值，确定性、可解释；不依赖 FSRS 的内部状态，便于在只读 review.py
    的场景下通过物化 due_at 来实现「due 从 mastery 派生」。
    """
    m = clamp01(mastery)
    days = MASTERY_BASE_DAYS * m
    return (now or _now()) + timedelta(days=days)


def humanize_interval(days: int) -> str:
    """把间隔天数转成中文可读短语，供评分按钮直接展示（与前端 daysText 口径对齐）。"""
    n = int(days)
    if n <= 0:
        return "刚学完"
    if n == 1:
        return "明天"
    if n == 2:
        return "后天"
    if n == 7:
        return "一周后"
    if n == 14:
        return "两周后"
    if n == 30:
        return "一个月后"
    return f"{n} 天后"


def humanize_seconds(secs: float) -> str:
    """把秒级间隔转成中文可读短语，供「评分显示上次间隔」使用。

    mastery 派生的 derive_due_at 是天级线性插值，低掌握度时恒为 0 天，
    四档全显示「刚学完」无法区分；FSRS 排期是分钟/小时级，用它才有区分度。
    与 POST /review/{id} 的真实写库结果同源。
    """
    s = max(0.0, float(secs))
    if s < 60:
        return "1 分钟内"
    minutes = s / 60.0
    if minutes < 60:
        return f"{max(1, round(minutes))} 分钟"
    hours = minutes / 60.0
    if hours < 24:
        return f"{max(1, round(hours))} 小时"
    days = int(hours // 24)
    return humanize_interval(days)


def preview_card_schedule(mastery: float, rating: int, *, now: datetime | None = None) -> dict:
    """纯预览：按评分推算新掌握度与下次复习 due，不修改卡片对象、不访问数据库。

    与 update_card_mastery 同源（card_mastery_after_rating + derive_due_at），
    但只返回计算结果，供 POST /review/preview 在只读场景下复用，避免预览时写库。
    """
    before = clamp01(_safe_float(mastery))
    after = card_mastery_after_rating(before, rating)
    base = now or _now()
    due = derive_due_at(after, now=base)
    secs = max(0.0, (due - base).total_seconds())
    days = int(secs // 86400) + (1 if secs % 86400 > 0 else 0)
    return {
        "rating": rating,
        "days": days,
        "label": humanize_interval(days),
        "mastery_before": before,
        "mastery_after": after,
        "due_at": due,
    }


def is_due(mastery: float, due_at: datetime | None, *, now: datetime | None = None) -> bool:
    """是否到期：掌握度低于阈值，或排期时间已到/为空。"""
    now = now or _now()
    due = _as_aware(due_at)
    return clamp01(mastery) < MASTERY_DUE_THRESHOLD or due is None or due <= now


def update_card_mastery(card: Card, rating: int, *, commit: bool = False, db: Session | None = None) -> float:
    """复习评分后更新卡片掌握度，并把 due_at 物化为掌握度派生值。

    注意：review.py 为只读（不在本 Agent 所有权内），因此这里只修改 Card 上的字段；
    集成方如需在 /review/{id} 评分处同步，只需调用本函数一行即可。
    """
    new = card_mastery_after_rating(card.mastery, rating)
    card.mastery = new
    card.due_at = derive_due_at(new)
    if commit and db is not None:
        db.commit()
    return new


def refresh_due_from_mastery(db: Session, user_id: int) -> int:
    """把到期判定物化到 Card.due_at：低掌握度卡片直接置为立即到期。

    这样 /review/due（只读、仍按 due_at<=now 过滤）会自动纳入「掌握度低」的卡片，
    实现 review 的 due 从 mastery 派生，而不改动 review.py 本身。
    返回被改为立即到期的卡片数。
    """
    rows = list(db.scalars(select(Card).where(Card.user_id == user_id)))
    now = _now()
    changed = 0
    for c in rows:
        if is_due(c.mastery, c.due_at, now=now):
            due = _as_aware(c.due_at)
            if clamp01(c.mastery) < MASTERY_DUE_THRESHOLD and (due is None or due > now):
                c.due_at = now
                changed += 1
    if changed:
        db.commit()
    return changed


# ---------------------------------------------------------------------------
# 题目 / 章节：答题 → 掌握度聚合
# ---------------------------------------------------------------------------
def question_mastery_after_correct(mastery: float, correct: bool) -> float:
    """答题后掌握度：答对 +STEP，答错 -STEP×PENALTY。"""
    delta = MASTERY_STEP if correct else -MASTERY_STEP * MASTERY_PENALTY
    return clamp01(_safe_float(mastery) + delta)


def update_question_mastery(db: Session, question: Question, correct: bool,
                            *, commit: bool = False) -> float:
    """更新单题掌握度（调用方控制提交时机，避免重复 commit）。"""
    new = question_mastery_after_correct(question.mastery, correct)
    question.mastery = new
    if commit:
        db.commit()
    return new


def chapter_mastery_map(db: Session, user_id: int, bank_id: int | None = None) -> dict:
    """按 (bank_id, chapter) 返回章节掌握度（0–1）。

    融合：题目 mastery 平均值 与 历史正确率（各占一半），历史无数据时退回 0。
    纯 SQL 聚合，不把题目捞到 Python 侧逐条算。
    """
    agg = (
        select(
            Question.bank_id.label("bank_id"),
            func.coalesce(Question.chapter, "").label("chapter"),
            func.avg(Question.mastery).label("avg_mastery"),
            func.count(Question.id).label("total"),
        )
        .where(Question.user_id == user_id)
        .group_by(Question.bank_id, func.coalesce(Question.chapter, ""))
        .subquery()
    )
    att = (
        select(
            Question.bank_id.label("bank_id"),
            func.coalesce(Question.chapter, "").label("chapter"),
            func.count(Attempt.id).label("attempts"),
            func.coalesce(func.sum(Attempt.correct), 0).label("correct"),
        )
        .join(Question, Attempt.question_id == Question.id)
        .where(Attempt.user_id == user_id)
        .group_by(Question.bank_id, func.coalesce(Question.chapter, ""))
        .subquery()
    )
    stmt = (
        select(agg.c.bank_id, agg.c.chapter, agg.c.avg_mastery, agg.c.total,
               func.coalesce(att.c.attempts, 0).label("attempts"),
               func.coalesce(att.c.correct, 0).label("correct"))
        .outerjoin(att, (
            ((att.c.bank_id == agg.c.bank_id) |
             (att.c.bank_id.is_(None) & agg.c.bank_id.is_(None)))
            & (att.c.chapter == agg.c.chapter)
        ))
    )
    if bank_id is not None:
        stmt = stmt.where(agg.c.bank_id == bank_id)
    out: dict = {}
    for r in db.execute(stmt).all():
        avg_m = clamp01(_safe_float(r.avg_mastery))
        attempts = int(r.attempts or 0)
        accuracy = clamp01(_safe_float(r.correct) / attempts) if attempts else avg_m
        score = clamp01((avg_m + accuracy) / 2.0) if attempts else avg_m
        out[(r.bank_id, r.chapter)] = score
    return out


def chapter_due_map(db: Session, user_id: int) -> dict:
    """按文档统计到期卡片数，供推荐排序的「到期优先」用。

    卡片没有 chapter 字段，按其 document_id 关联同文档题目，近似映射到章节。
    返回 {(bank_id, chapter): due_count}。
    """
    now = _now()
    rows = db.execute(
        select(Question.bank_id, func.coalesce(Question.chapter, "").label("chapter"),
               Question.document_id)
        .where(Question.user_id == user_id)
    ).all()
    due_by_doc: dict = {}
    for d, n in db.execute(
        select(Card.document_id, func.count(Card.id))
        .where(Card.user_id == user_id,
               (Card.due_at.is_(None)) | (Card.due_at <= now) | (Card.mastery < MASTERY_DUE_THRESHOLD))
        .group_by(Card.document_id)
    ).all():
        due_by_doc[d] = int(n)
    out: dict = {}
    for bank_id, chapter, doc_id in rows:
        key = (bank_id, chapter)
        out[key] = out.get(key, 0) + due_by_doc.get(doc_id, 0)
    return out


def due_cards_for_user(db: Session, user_id: int, limit: int = 50) -> list[Card]:
    """复习到期卡片：掌握度低或排期已到，按掌握度升序（最薄弱优先）。"""
    now = _now()
    return list(db.scalars(
        select(Card).where(
            Card.user_id == user_id,
            (Card.due_at.is_(None)) | (Card.due_at <= now) | (Card.mastery < MASTERY_DUE_THRESHOLD),
        ).order_by(Card.mastery.asc(), Card.due_at.asc(), Card.id.asc()).limit(limit)
    ))


# ---------------------------------------------------------------------------
# 闭环状态条：资料 → 笔记 → 卡片 → 刷题 → 复习
# ---------------------------------------------------------------------------
def _scalar_count(db: Session, model, *conds) -> int:
    """只读计数助手：空表返回 0，不抛异常。"""
    return int(db.scalar(select(func.count()).select_from(model).where(*conds)) or 0)


def build_loop_status(db: Session, user_id: int) -> dict:
    """五步闭环进度聚合，只查现有表、只读、不返回任何用户原文与凭据。

    前端可消费字段：steps[].{count,done,blocker,action,fix_action}、
    overall（完成百分比）、today（今日待办数）、blocked_step（首个卡点）。
    action/fix_action 为 React 前端页面路由，与 gflc/web/src/App.jsx 保持一致。
    """
    now = _now()

    # ---------- 第 1 步：资料 ----------
    # 口径与 documents.list_documents 一致：排除题库文件与笔记建卡产生的占位文档
    _material_kinds = ("question_bank", "note")
    doc_status_rows = db.execute(
        select(func.coalesce(Document.status, "pending"), func.count(Document.id))
        .where(Document.user_id == user_id, Document.source_type.notin_(_material_kinds))
        .group_by(Document.status)
    ).all()
    status_count = {(r[0] or "pending"): int(r[1] or 0) for r in doc_status_rows}
    material_total = sum(status_count.values())
    # 「已就绪」还要真正切出内容块，避免 status=ready 但无 chunks 的假完成
    parsed_docs = int(db.scalar(
        select(func.count(func.distinct(Document.id)))
        .join(Chunk, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id, Document.status == "ready",
               Document.source_type.notin_(_material_kinds))
    ) or 0)
    failed_docs = status_count.get("failed", 0)
    processing_docs = (status_count.get("pending", 0) + status_count.get("parsing", 0)
                       + status_count.get("uploaded", 0))
    # 21 号计划里的关键断点：扫描件无文字层 → pdf_parse 任务失败码 PARSE-002
    scan_failed = _scalar_count(db, Task, Task.user_id == user_id, Task.type == "pdf_parse",
                                Task.status == "failed", Task.error_code == "PARSE-002")
    if material_total == 0:
        material_blocker = "还没有资料，请先上传 PDF / Word / Markdown 文件"
    elif parsed_docs == 0:
        if scan_failed:
            material_blocker = "扫描件未识别（无文字层），请换用文字版 PDF 或等待 OCR 能力接入"
        elif failed_docs:
            material_blocker = "资料解析失败，请检查解析任务并重试"
        elif processing_docs:
            material_blocker = "资料正在解析中，请稍候"
        else:
            material_blocker = "资料尚未解析出内容块，请重新解析"
    else:
        material_blocker = None
    material_warning = ("有 {} 份资料解析失败，部分内容不可用".format(failed_docs)
                        if parsed_docs and failed_docs else None)

    # ---------- 第 2 步：笔记 ----------
    note_count = _scalar_count(db, Note, Note.user_id == user_id)
    if parsed_docs == 0:
        note_blocker = "还没有可写笔记的资料，请先上传并解析资料"
    elif note_count == 0:
        note_blocker = "还没有笔记，可在资料下新建或用 AI 整理生成"
    else:
        note_blocker = None

    # ---------- 第 3 步：卡片 ----------
    card_count = _scalar_count(db, Card, Card.user_id == user_id)
    reviewed_count = _scalar_count(db, Card, Card.user_id == user_id, Card.reps > 0)
    failed_card_tasks = _scalar_count(db, Task, Task.user_id == user_id,
                                      Task.type == "card_generate", Task.status == "failed")
    if note_count == 0:
        card_blocker = "还没有笔记，先从笔记生成卡片"
    elif card_count == 0:
        card_blocker = ("卡片生成任务失败，请重新生成" if failed_card_tasks
                        else "还没有卡片，可从笔记转卡片或在资料页生成")
    else:
        card_blocker = None
    card_warning = ("有 {} 次卡片生成任务失败".format(failed_card_tasks)
                    if card_count and failed_card_tasks else None)

    # ---------- 第 4 步：刷题 ----------
    question_count = _scalar_count(db, Question, Question.user_id == user_id)
    bank_count = _scalar_count(db, QuestionBank, QuestionBank.user_id == user_id)
    attempt_count = _scalar_count(db, Attempt, Attempt.user_id == user_id)
    correct_count = _scalar_count(db, Attempt, Attempt.user_id == user_id, Attempt.correct == 1)
    if question_count == 0:
        quiz_blocker = ("题库文件已导入但未解析出题目，请检查导入任务" if bank_count
                        else "题库为空，请先导入题库")
    elif attempt_count == 0:
        quiz_blocker = "题库已就绪，还没有作答记录，去做几道题"
    else:
        quiz_blocker = None

    # ---------- 第 5 步：复习 ----------
    # 与 due_cards_for_user 同口径：到期为空 / 排期已到 / 掌握度低于阈值
    due_count = int(db.scalar(
        select(func.count()).select_from(Card).where(
            Card.user_id == user_id,
            (Card.due_at.is_(None)) | (Card.due_at <= now) | (Card.mastery < MASTERY_DUE_THRESHOLD),
        )
    ) or 0)
    # 今日待办中的计划任务：口径与 dashboard.today 一致（所有未完成任务）
    plan_pending = int(db.scalar(
        select(func.count()).select_from(PlanTask).where(
            PlanTask.done == 0,
            PlanTask.plan_id.in_(select(Plan.id).where(Plan.user_id == user_id)),
        )
    ) or 0)
    if card_count == 0:
        review_blocker = "还没有卡片，无法复习"
    elif reviewed_count == 0:
        review_blocker = "还没有复习记录，先去复习到期卡片"
    else:
        review_blocker = None

    # 统一步骤结构：count 为该步 headline 数字，total 为资源总量，detail 给出原始明细
    def _step(key, label, count, total, done, blocker, action, action_label, description,
              *, detail=None, warning=None, fix_action=None, fix_label=None):
        return {
            "key": key, "label": label, "count": int(count), "total": int(total),
            "done": bool(done), "blocker": blocker, "warning": warning,
            "action": action, "action_label": action_label,
            "fix_action": fix_action, "fix_label": fix_label,
            "description": description, "detail": detail or {},
        }

    steps = [
        _step("material", "资料", parsed_docs, material_total, parsed_docs > 0,
              material_blocker, "/docs", "查看资料", "已解析出内容的资料数",
              detail={"docs": material_total, "parsed": parsed_docs, "failed": failed_docs,
                      "processing": processing_docs, "scan_unreadable": scan_failed},
              warning=material_warning,
              fix_action="/docs" if material_total == 0 else None,
              fix_label="上传资料" if material_total == 0 else None),
        _step("note", "笔记", note_count, note_count, note_count > 0,
              note_blocker, "/notes", "查看笔记", "笔记篇数",
              detail={"notes": note_count},
              fix_action="/notes" if note_count == 0 else None,
              fix_label="写笔记" if note_count == 0 else None),
        _step("card", "卡片", card_count, card_count, card_count > 0,
              card_blocker, "/deck", "查看卡片", "卡片张数",
              detail={"cards": card_count, "reviewed": reviewed_count,
                      "failed_tasks": failed_card_tasks},
              warning=card_warning,
              fix_action="/deck" if card_count == 0 else None,
              fix_label="生成卡片" if card_count == 0 else None),
        _step("quiz", "刷题", question_count, question_count, attempt_count > 0,
              quiz_blocker, "/study", "去刷题", "题库题目数",
              detail={"questions": question_count, "banks": bank_count,
                      "attempts": attempt_count, "correct": correct_count},
              fix_action="/study" if question_count == 0 else None,
              fix_label="导入题库" if question_count == 0 else None),
        _step("review", "复习", due_count, card_count, reviewed_count > 0,
              review_blocker, "/review", "去复习", "待复习卡片数",
              detail={"due": due_count, "cards": card_count, "reviewed": reviewed_count},
              fix_action="/review" if card_count == 0 else None,
              fix_label="去背卡片" if card_count == 0 else None),
    ]

    completed = sum(1 for s in steps if s["done"])
    blocked = next((s["key"] for s in steps if not s["done"]), None)
    return {
        "steps": steps,
        "overall": round(completed / len(steps) * 100),
        "overall_detail": {"completed": completed, "total": len(steps)},
        "today": due_count + plan_pending,
        "today_detail": {"review": due_count, "plan": plan_pending},
        "blocked_step": blocked,
    }
