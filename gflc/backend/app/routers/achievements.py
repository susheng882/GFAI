# -*- coding: utf-8 -*-
"""成长记录与成就（阶段 C）：纯聚合现有表，不建新表。

指标口径：
- 学习天数 = review_logs 与 attempts 的活跃日期并集
- 累计时长 = 复习次数 × 90s + 作答次数 × 60s（估算口径，标注 estimate）
- 背卡 = reps>0 的卡片数；正确率 = attempts 正确占比
- 能力五维：memory/understand/speed/accuracy/persistence，0-100
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Attempt, Card, ReviewLog, User
from app.routers.deps import get_current_user

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
async def overview(user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    uid = user.id
    now = datetime.now(timezone.utc)

    # 活跃天数（复习+作答并集）
    r_days = {d for (d,) in db.execute(
        select(func.date(ReviewLog.created_at)).where(ReviewLog.user_id == uid)).all()}
    a_days = {d for (d,) in db.execute(
        select(func.date(Attempt.created_at)).where(Attempt.user_id == uid)).all()}
    active_days = len(r_days | a_days)

    # 复习与作答量
    reviews = db.scalar(select(func.count()).select_from(ReviewLog)
                        .where(ReviewLog.user_id == uid, ReviewLog.rating >= 0)) or 0
    attempts = db.scalar(select(func.count()).select_from(Attempt)
                         .where(Attempt.user_id == uid)) or 0
    correct = db.scalar(select(func.count()).select_from(Attempt)
                        .where(Attempt.user_id == uid, Attempt.correct == 1)) or 0

    cards_done = db.scalar(select(func.count()).select_from(Card)
                           .where(Card.user_id == uid, Card.reps > 0)) or 0
    cards_total = db.scalar(select(func.count()).select_from(Card)
                            .where(Card.user_id == uid)) or 0

    # 连续打卡（今天起往前数，缺一天即断）
    day_set = r_days | a_days
    streak = 0
    d = now.date()
    while d.isoformat() in day_set:
        streak += 1
        d -= timedelta(days=1)

    # 达成率 = 已背卡 / 总卡
    completion = round(cards_done / cards_total * 100, 1) if cards_total else 0.0
    accuracy = round(correct / attempts * 100, 1) if attempts else 0.0
    # 估算时长（口径：复习 90s/次，作答 60s/次）
    hours_est = round((reviews * 90 + attempts * 60) / 3600, 1)

    # 等级：XP = 复习×2 + 答对×3 + 天数×5
    xp = reviews * 2 + correct * 3 + active_days * 5
    level = int(xp // 100) + 1
    xp_next = (level) * 100

    # 能力五维（0-100）：记忆=平均掌握度×100；理解=正确率；
    # 速度=近期每日作答均值归一；坚持=连续天数/30；persistence 同坚持
    avg_mastery = db.scalar(select(func.avg(Card.mastery))
                            .where(Card.user_id == uid, Card.reps > 0)) or 0.0
    abilities = {
        "memory": int(round(float(avg_mastery) * 100)),
        "understand": int(round(accuracy)),
        "speed": int(min(100, attempts * 2)),
        "accuracy": int(round(accuracy)),
        "persistence": int(min(100, round(streak / 30 * 100))),
    }

    milestones = [
        {"name": "首卡开背", "done": cards_done >= 1},
        {"name": "连续 7 天", "done": streak >= 7},
        {"name": "刷题 100 道", "done": attempts >= 100},
        {"name": "连续 30 天", "done": streak >= 30},
        {"name": "全库掌握", "done": completion >= 90 and cards_total > 0},
    ]

    return {"ok": True, "data": {
        "level": level, "xp": xp, "xp_next": xp_next,
        "stats": {"days": active_days, "hours": hours_est, "hours_estimate": True,
                  "cards": cards_done, "cards_total": cards_total,
                  "accuracy": accuracy, "completion": completion},
        "streak": streak,
        "abilities": abilities,
        "milestones": milestones,
    }}
