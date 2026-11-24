# -*- coding: utf-8 -*-
"""仪表盘：真实统计 / AI 生成（月周日粒度）/ 自由布局缩放 / 单卡编辑 / 今日待办。"""
import os
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import (
    Attempt, Card, CardDeck, Chunk, DashboardLayout, Document, Plan, PlanTask, Question,
    ReviewLog,
)
from app.routers.deps import get_current_user
from app.routers.plans import plan_task_due
from app.schemas.schemas import DashCardPatchIn, DashGenIn, DashOrderIn
from app.services import mastery
from app.worker import runner

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# 新增环境变量：今日待办默认条数（前端可传 limit 覆盖）
TODAY_LIMIT = int(os.getenv("GFLC_TODAY_LIMIT", "50"))


def _day_key(value) -> str:
    """SQLite 的 func.date 返回值是字符串，PostgreSQL 返回 date 对象，统一成 ISO 字符串。"""
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def build_heatmap(days: int, review_rows, quiz_rows, today: date | None = None) -> dict:
    """纯函数：把按天聚合的复习/刷题结果合并成连续日期序列 + 连续打卡。

    review_rows / quiz_rows 形如 [(日期, 次数), ...]，只做内存合并，不再查库。
    total>0 视为当天活跃；current 从今天往前数，中断即停。
    """
    today = today or datetime.now(timezone.utc).date()
    days = max(7, min(int(days), 365))
    start = today - timedelta(days=days - 1)
    review_map = {_day_key(d): int(n) for d, n in review_rows}
    quiz_map = {_day_key(d): int(n) for d, n in quiz_rows}

    series: list[dict] = []
    cursor = start
    while cursor <= today:
        key = cursor.isoformat()
        review = review_map.get(key, 0)
        quiz = quiz_map.get(key, 0)
        series.append({"date": key, "review": review, "quiz": quiz, "total": review + quiz})
        cursor += timedelta(days=1)

    current = 0
    for item in reversed(series):
        if item["total"] <= 0:
            break
        current += 1
    longest = run = 0
    for item in series:
        run = run + 1 if item["total"] > 0 else 0
        longest = max(longest, run)

    return {
        "days": series,
        "streak": {"current": current, "longest": longest},
        "summary": {
            "active_days": sum(1 for i in series if i["total"] > 0),
            "total_reviews": sum(i["review"] for i in series),
            "total_quiz": sum(i["quiz"] for i in series),
        },
    }


def _own_layout(db: Session, layout_id: int, user_id: int) -> DashboardLayout:
    row = db.scalar(select(DashboardLayout).where(DashboardLayout.id == layout_id,
                                                  DashboardLayout.user_id == user_id))
    if not row:
        raise APIError(ErrCode.AUTH_403, "无权访问该仪表盘", 403)
    return row


@router.get("/stats")
async def stats(user=Depends(get_current_user), db: Session = Depends(get_db)):
    uid = user.id
    now = datetime.now(timezone.utc)
    docs = db.scalar(select(func.count()).select_from(Document).where(Document.user_id == uid)) or 0
    chunks = db.scalar(select(func.count()).select_from(Chunk).join(
        Document, Chunk.document_id == Document.id).where(Document.user_id == uid)) or 0
    cards = db.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid)) or 0
    # 复习口径拆分：due = 真·到期（已学过且到期），new = 尚未学的新卡。
    # 原来把 reps==0（新卡）也算进「到期」，导致「今天要复习 120 张」混入了新学量，语义不清。
    due = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == uid, Card.reps > 0,
        or_(Card.due_at.is_(None), Card.due_at <= now))) or 0
    new_cards = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == uid, Card.reps == 0)) or 0
    reviewed = db.scalar(select(func.count()).select_from(Card).where(Card.user_id == uid, Card.reps > 0)) or 0
    questions = db.scalar(select(func.count()).select_from(Question).where(Question.user_id == uid)) or 0
    attempts = db.scalar(select(func.count()).select_from(Attempt).where(Attempt.user_id == uid)) or 0
    correct = db.scalar(select(func.count()).select_from(Attempt).where(
        Attempt.user_id == uid, Attempt.correct == 1)) or 0

    # 最近 7 天作答量：一条 group by 聚合 + Python 补 0，替代原先 7 次逐日查询
    week_start = (now - timedelta(days=6)).date()
    week_rows = db.execute(
        select(func.date(Attempt.created_at), func.count())
        .where(Attempt.user_id == uid,
               func.date(Attempt.created_at).between(week_start.isoformat(), now.date().isoformat()))
        .group_by(func.date(Attempt.created_at))
    ).all()
    week_map = {_day_key(d): int(n) for d, n in week_rows}
    week = []
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).date()
        week.append({"label": day.strftime("%m-%d"), "value": week_map.get(day.isoformat(), 0)})

    decks = db.execute(
        select(CardDeck.name, func.count(Card.id))
        .join(Card, Card.deck_id == CardDeck.id)
        .where(CardDeck.user_id == uid, CardDeck.kind == "chapter")
        .group_by(CardDeck.name).order_by(func.count(Card.id).desc()).limit(6)
    ).all()

    return {"ok": True, "data": {
        "documents": docs, "chunks": chunks, "cards": cards,
        "due": due, "new_cards": new_cards, "reviewed": reviewed,
        "questions": questions, "attempts": attempts,
        "accuracy": round(correct / attempts * 100, 1) if attempts else 0,
        "week": week,
        "chapters": [{"name": n, "cards": int(c)} for n, c in decks],
    }}


@router.get("/heatmap")
async def heatmap(days: int = 365, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """B14：学习热力图 + 连续打卡。

    两条 group by 聚合（复习日志 / 刷题作答），日期补齐在 Python 里做，
    不逐日查库。defer 记的 rating=-1 只留痕，不计入复习量与活跃天数。
    """
    span = max(7, min(int(days or 365), 365))
    today = datetime.now(timezone.utc).date()
    start = (today - timedelta(days=span - 1)).isoformat()
    end = today.isoformat()

    review_rows = db.execute(
        select(func.date(ReviewLog.created_at), func.count())
        .where(ReviewLog.user_id == user.id, ReviewLog.rating >= 0,
               func.date(ReviewLog.created_at).between(start, end))
        .group_by(func.date(ReviewLog.created_at))
    ).all()
    quiz_rows = db.execute(
        select(func.date(Attempt.created_at), func.count())
        .where(Attempt.user_id == user.id,
               func.date(Attempt.created_at).between(start, end))
        .group_by(func.date(Attempt.created_at))
    ).all()
    return {"ok": True, "data": build_heatmap(span, review_rows, quiz_rows, today=today)}


@router.get("/today")
async def today(limit: int | None = None, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    """D10：把复习 due 与 PlanTask.due 合并成统一「今日待办」队列。

    字段：type(review/plan) / title / due / source_id；返回按到期时间升序。
    前端 React Agent 可直接消费 data.items。
    """
    cap = max(1, min(limit or TODAY_LIMIT, 200))

    # 复习 due 从掌握度派生（物化低掌握度卡片为立即到期，不改动只读的 review.py）
    mastery.refresh_due_from_mastery(db, user.id)
    cards = mastery.due_cards_for_user(db, user.id, cap)
    items: list[dict] = []
    for c in cards:
        due = c.due_at
        if due is not None and due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        items.append({
            "type": "review",
            "title": "复习卡片：{}".format((c.question or "")[:60]),
            "due": due.isoformat() if due else None,
            "source_id": c.id,
            "mastery": round(c.mastery or 0.0, 4),
            "reps": int(c.reps or 0),
        })

    # 计划任务 due：显式 due 优先，否则按 plan 创建日 + day_index 派生
    plans = list(db.scalars(select(Plan).where(Plan.user_id == user.id)))
    plan_map = {p.id: p for p in plans}
    if plans:
        tasks = list(db.scalars(select(PlanTask).where(
            PlanTask.plan_id.in_([p.id for p in plans]), PlanTask.done == 0)))
        for t in tasks:
            due = plan_task_due(plan_map[t.plan_id], t)
            items.append({
                "type": "plan",
                "title": t.title,
                "due": due.isoformat() if due else None,
                "source_id": t.id,
                "plan_id": t.plan_id,
                "day": int(t.day_index or 0),
                "done": False,
            })

    # 无 due 的排末位；同时按 source_id 保证顺序稳定
    items.sort(key=lambda x: (x["due"] is None, x["due"] or "", x["source_id"]))
    counts = {
        "review": sum(1 for i in items if i["type"] == "review"),
        "plan": sum(1 for i in items if i["type"] == "plan"),
    }
    return {"ok": True, "data": {
        "date": datetime.now(timezone.utc).date().isoformat(),
        "total": len(items), "counts": counts, "items": items[:cap],
    }}


@router.get("/loop")
async def loop_status(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """闭环状态条：资料 → 笔记 → 卡片 → 刷题 → 复习，五步进度 + 卡点原因 + 今日待办。

    数据全部来自现有表的只读聚合（见 services/mastery.py::build_loop_status），
    不返回用户原文与凭据；空账号 / 无资料 / 无题库均返回安全默认值（count=0、done=false）。
    """
    return {"ok": True, "data": mastery.build_loop_status(db, user.id)}


@router.post("/generate")
async def generate(body: DashGenIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """按主题 + 时间粒度生成仪表盘（会带上用户真实学习数据）。"""
    theme = (body.theme or "").strip()
    if not theme:
        raise APIError(ErrCode.COMMON_400, "请填写仪表盘主题")
    t = runner.create_task(db, user.id, "dashboard_generate")
    runner.submit(t.id, "dashboard_generate", {"theme": theme, "scope": body.scope})
    return {"ok": True, "data": {"task_id": t.id}}


@router.get("/latest")
async def latest(scope: str | None = None, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    stmt = select(DashboardLayout).where(DashboardLayout.user_id == user.id)
    if scope:
        stmt = stmt.where(DashboardLayout.scope == scope)
    row = db.scalar(stmt.order_by(DashboardLayout.is_default.desc(), DashboardLayout.id.desc()).limit(1))
    if not row:
        return {"ok": True, "data": None}
    return {"ok": True, "data": {
        "id": row.id, "theme": row.theme, "config": row.config, "order": row.order,
        "positions": row.positions or {}, "scope": row.scope or "week",
        "is_default": bool(row.is_default),
    }}


@router.get("/list")
async def list_layouts(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(DashboardLayout).where(DashboardLayout.user_id == user.id)
                           .order_by(DashboardLayout.is_default.desc(), DashboardLayout.id.desc()).limit(20)))
    return {"ok": True, "data": [{"id": r.id, "theme": r.theme, "scope": r.scope or "week",
                                  "is_default": bool(r.is_default)} for r in rows]}


@router.put("/{layout_id}/order")
async def save_order(layout_id: int, body: DashOrderIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    row.order = body.order
    if body.positions:
        row.positions = body.positions
    if body.scope in ("month", "week", "day"):
        row.scope = body.scope
    db.commit()
    return {"ok": True, "data": {"id": row.id, "order": row.order,
                                 "positions": row.positions, "scope": row.scope}}


@router.patch("/{layout_id}/card")
async def patch_card(layout_id: int, body: DashCardPatchIn, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """编辑单张卡片内容（标题/数值/清单/图表数据）。"""
    row = _own_layout(db, layout_id, user.id)
    cfg = dict(row.config or {})
    cards = [dict(c) for c in cfg.get("cards", [])]
    hit = None
    for c in cards:
        if c.get("id") == body.card_id:
            hit = c
            break
    if hit is None:
        raise APIError(ErrCode.COMMON_404, "卡片不存在", 404)
    for field in ("title", "value", "unit", "hint"):
        v = getattr(body, field)
        if v is not None:
            hit[field] = v
    if body.items is not None:
        hit["items"] = body.items
    if body.data is not None:
        hit["data"] = body.data
    cfg["cards"] = cards
    row.config = cfg
    db.commit()
    return {"ok": True, "data": {"card": hit}}


@router.post("/{layout_id}/default")
async def set_default(layout_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    db.query(DashboardLayout).filter(DashboardLayout.user_id == user.id).update(
        {"is_default": 0}, synchronize_session=False)
    row.is_default = 1
    db.commit()
    return {"ok": True, "data": {"id": row.id, "is_default": True}}


@router.delete("/{layout_id}")
async def delete_layout(layout_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = _own_layout(db, layout_id, user.id)
    db.delete(row)
    db.commit()
    return {"ok": True, "data": {"deleted": True}}
