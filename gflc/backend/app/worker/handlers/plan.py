# -*- coding: utf-8 -*-
"""学习计划生成任务处理（原 handlers.py 原样迁出）。"""
import asyncio

from app.ai.prompts import PLAN_SYSTEM, plan_user
from app.ai.router import generate_json
from app.models.models import Plan, PlanTask
from app.schemas.schemas import PlanGenResult


def handle_plan_generate(db, task, payload, update):
    days = max(1, min(payload.get("days", 7), 60))
    update(20, "拆解任务")
    obj, _ = asyncio.run(generate_json("mid", PLAN_SYSTEM, plan_user(payload["goal"], days), PlanGenResult))
    update(85, "写入计划")
    plan = Plan(user_id=task.user_id, goal=payload["goal"], days=days)
    db.add(plan)
    db.flush()
    for t in obj.tasks:
        db.add(PlanTask(plan_id=plan.id, day_index=max(1, min(t.day, days)),
                        title=t.title, detail=t.detail))
    db.commit()
    return {"plan_id": plan.id, "days": days, "tasks": len(obj.tasks)}
