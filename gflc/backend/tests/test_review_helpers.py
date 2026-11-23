# -*- coding: utf-8 -*-
"""复习辅助纯函数单测：humanize_seconds / preview_card_schedule（不依赖 DB / 外部服务）。"""
from datetime import datetime, timezone

from app.services.mastery import humanize_interval, humanize_seconds, preview_card_schedule


def test_humanize_seconds_four_tiers_distinct():
    """四个量级（秒/分/时/天）必须给出四种不同文案，否则评分按钮四档无法区分。"""
    labels = [humanize_seconds(s) for s in (30, 600, 7200, 86400 * 3)]
    assert labels == ["1 分钟内", "10 分钟", "2 小时", "3 天后"]
    assert len(set(labels)) == 4


def test_humanize_seconds_boundaries():
    """边界：<=0 与 <60 秒同档；整点进位到上一档；天档复用 humanize_interval。"""
    assert humanize_seconds(0) == "1 分钟内"
    assert humanize_seconds(-5) == "1 分钟内"      # 负数按 0 处理，不出现「-x 分钟」
    assert humanize_seconds(59) == "1 分钟内"
    assert humanize_seconds(65) == "1 分钟"
    assert humanize_seconds(3600) == "1 小时"
    assert humanize_seconds(86400) == "明天"
    assert humanize_seconds(86400 * 7) == "一周后"


def test_preview_card_schedule_fields():
    """返回字段齐全，且 rating / days / label / mastery_after 与纯函数口径一致。"""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    pv = preview_card_schedule(0.5, 3, now=now)
    assert {"rating", "days", "label", "mastery_before", "mastery_after", "due_at"} <= set(pv)
    assert pv["rating"] == 3
    assert pv["mastery_before"] == 0.5
    # 0.5 + MASTERY_STEP(0.12) * 1.0 = 0.62
    assert abs(pv["mastery_after"] - 0.62) < 1e-9
    assert isinstance(pv["days"], int) and pv["days"] >= 1
    assert pv["label"] == humanize_interval(pv["days"])
    assert isinstance(pv["due_at"], datetime) and pv["due_at"] > now


def test_preview_card_schedule_does_not_mutate():
    """预览是只读的：入参不被改写、同参重复调用结果完全一致。"""
    mastery = 0.5
    first = preview_card_schedule(mastery, 3)
    second = preview_card_schedule(mastery, 3)
    assert mastery == 0.5
    assert first["mastery_after"] == second["mastery_after"]
    assert first["days"] == second["days"]
    assert first["label"] == second["label"]
    # mastery_after 只在返回值里，不会回写传入的掌握度
    assert first["mastery_after"] != mastery


def test_preview_days_increase_with_rating():
    """同一掌握度下：评分越好，下次复习越远；Again 必须早于 Easy。"""
    days = [preview_card_schedule(0.5, r)["days"] for r in (1, 2, 3, 4)]
    assert days == sorted(days)
    assert days[0] < days[-1]
    labels = [preview_card_schedule(0.5, r)["label"] for r in (1, 2, 3, 4)]
    assert len(set(labels)) >= 2


def test_preview_mastered_card_clamped():
    """满分附近的高分不溢出：mastery_after 上限 1.0，天档落到 BASE_DAYS=7。"""
    pv = preview_card_schedule(0.98, 4)
    assert pv["mastery_after"] == 1.0
    assert pv["days"] == 7
    assert pv["label"] == "一周后"
