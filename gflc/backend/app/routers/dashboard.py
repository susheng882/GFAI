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


@router.get("/forgetting")
async def forgetting(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """遗忘曲线：按「当前回忆成功率 vs 距上次复习的天数」聚合。

    口径：
    - x 轴 = 距离上次评分的天数（1/2/3/7/14/30 分桶）
    - y 轴 = 该桶内卡片的平均掌握度（0–1），代表「隔了这么多天还记得多少」

    注意：当前数据很薄（复习日志少），返回点会很少甚至为空；前端应展示 0 数据
    形态而非空图。随复习次数积累，曲线会自然成型。
    """
    buckets = [1, 2, 3, 7, 14, 30]
    now = datetime.now(timezone.utc)

    # 每张卡：最近一次评分时间 + 当前掌握度。SQL 层取聚合，不捞明细到 Python。
    last_review = (
        select(ReviewLog.card_id, func.max(ReviewLog.created_at).label("last_at"))
        .where(ReviewLog.user_id == user.id, ReviewLog.rating >= 0)
        .group_by(ReviewLog.card_id)
    ).subquery()

    rows = db.execute(
        select(Card.mastery, last_review.c.last_at)
        .join(last_review, last_review.c.card_id == Card.id)
        .where(Card.user_id == user.id)
    ).all()

    # 分桶聚合：距上次评分天数 → 平均掌握度
    points: list[dict] = []
    for b in buckets:
        upper = buckets[-1] * 365  # 最后一个桶上界放宽
        lo, hi = (buckets[buckets.index(b) - 1] + 1) if buckets.index(b) > 0 else 1, b
        vals = []
        for m, last_at in rows:
            if last_at is None:
                continue
            # last_at 可能是 naive（SQLite）或 aware（PostgreSQL），统一转 aware 再相减
            if last_at.tzinfo is None:
                last_at = last_at.replace(tzinfo=timezone.utc)
            days = (now - last_at).days
            if days <= 0:
                days = 0
            if buckets.index(b) == 0 and days <= 1:
                vals.append(float(m or 0))
            elif buckets.index(b) > 0 and buckets[buckets.index(b) - 1] < days <= b:
                vals.append(float(m or 0))
        if vals:
            points.append({
                "label": f"≤{b}天" if buckets.index(b) == 0 else f"{buckets[buckets.index(b)-1]+1}–{b}天",
                "days": b, "avg_mastery": round(sum(vals) / len(vals), 3),
                "cards": len(vals),
            })

    return {"ok": True, "data": {
        "points": points,
        "total_reviewed_cards": len(rows),
        "note": "掌握度 0–1 越高记得越牢；数据随复习积累而充实",
    }}


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


@router.get("/v7")
async def v7_overview(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """v7l 仪表盘聚合：一次给全今日指标/周目标/计划模板/记忆轨道。

    数据口径（真实聚合现有表，不造数据）：
    - 今日学习时长 = 今日复习×90s + 今日作答×60s（估算，hours_estimate 标记）
    - 今日刷题 = 今日 attempts 数；正确率 = 今日正确占比
    - 待背卡片 = reps==0 的新卡 + 到期卡
    - 连续 = 复习/作答活跃日期连续数
    - 周目标 = 本周 plan_tasks 完成比
    - 计划模板 = 静态列表（艾宾浩斯冲刺/真题驱动/每日2h/章节通关）
    - 记忆轨道 R1-R4 = 按 reps 分桶的卡片数
    """
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    now = _dt.now(_tz.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 今日复习/作答
    reviews_today = db.scalar(select(func.count()).select_from(ReviewLog).where(
        ReviewLog.user_id == user.id, ReviewLog.rating >= 0,
        ReviewLog.created_at >= today_start)) or 0
    attempts_today = db.scalar(select(func.count()).select_from(Attempt).where(
        Attempt.user_id == user.id, Attempt.created_at >= today_start)) or 0
    correct_today = db.scalar(select(func.count()).select_from(Attempt).where(
        Attempt.user_id == user.id, Attempt.correct == 1,
        Attempt.created_at >= today_start)) or 0

    # 待背（新卡 + 到期）
    new_cards = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps == 0)) or 0
    due_cards = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps > 0,
        or_(Card.due_at.is_(None), Card.due_at <= now))) or 0

    # 连续打卡
    r_days = {d for (d,) in db.execute(select(func.date(ReviewLog.created_at))
              .where(ReviewLog.user_id == user.id)).all()}
    a_days = {d for (d,) in db.execute(select(func.date(Attempt.created_at))
              .where(Attempt.user_id == user.id)).all()}
    day_set = r_days | a_days
    d = now.date()
    streak = 0
    while d.isoformat() in day_set:
        streak += 1
        d -= _td(days=1)

    # 本周目标（plan_tasks 经 plans 关联用户，due 在本周内）
    week_start = (now - _td(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    week_rows = db.execute(
        select(PlanTask.done, func.count())
        .join(Plan, PlanTask.plan_id == Plan.id)
        .where(Plan.user_id == user.id, PlanTask.due >= week_start,
               PlanTask.due < week_start + _td(days=7))
        .group_by(PlanTask.done)).all()
    wk = {int(done): int(n) for done, n in week_rows}
    week_total = sum(wk.values())
    week_done = wk.get(1, 0)

    # 记忆轨道 R1-R4（按 reps 分桶）
    r1 = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps >= 1, Card.reps <= 2)) or 0
    r2 = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps >= 3, Card.reps <= 5)) or 0
    r3 = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps >= 6, Card.reps <= 9)) or 0
    r4 = db.scalar(select(func.count()).select_from(Card).where(
        Card.user_id == user.id, Card.reps >= 10)) or 0

    return {"ok": True, "data": {
        "today": {
            "study_minutes": round((reviews_today * 90 + attempts_today * 60) / 60),
            "study_minutes_estimate": True,
            "goal_minutes": 240,  # 目标 4h（与原型一致，可后续配置化）
            "quiz_count": attempts_today,
            "quiz_accuracy": round(correct_today / attempts_today * 100, 1) if attempts_today else 0,
            "cards_due": due_cards,
            "cards_new": new_cards,
            "streak": streak,
        },
        "week_goal": {
            "label": f"第 {(now - week_start).days // 7 + 1} 周",
            "range": f"{week_start.strftime('%m-%d')} ~ {(week_start + _td(days=6)).strftime('%m-%d')}",
            "done": week_done, "total": week_total,
            "percent": round(week_done / week_total * 100, 1) if week_total else 0,
        },
        "plan_templates": [
            {"id": "ebbinghaus", "name": "艾宾浩斯冲刺", "desc": "按遗忘曲线自动排期", "uses": 12},
            {"id": "exam", "name": "真题驱动", "desc": "以真题为核心的复习节奏", "uses": 8},
            {"id": "daily2h", "name": "每日 2h", "desc": "固定时长均衡四科", "uses": 5},
            {"id": "chapter", "name": "章节通关", "desc": "逐章击破不留死角", "uses": 3},
        ],
        "memory_track": [
            {"stage": "R1 初学", "count": r1, "desc": "1-2 次"},
            {"stage": "R2 巩固", "count": r2, "desc": "3-5 次"},
            {"stage": "R3 熟练", "count": r3, "desc": "6-9 次"},
            {"stage": "R4 掌握", "count": r4, "desc": "10+ 次"},
        ],
    }}
