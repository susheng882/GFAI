# -*- coding: utf-8 -*-
"""学习看板布局生成任务处理（原 handlers.py 原样迁出）。"""
import asyncio

from app.ai.prompts import DASHBOARD_SYSTEM, dashboard_user
from app.ai.router import generate_json
from app.models.models import DashboardLayout
from app.schemas.schemas import DashConfig


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
