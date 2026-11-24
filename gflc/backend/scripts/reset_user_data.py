# -*- coding: utf-8 -*-
"""清空指定用户的学习数据，保留账号与模型/供应商配置。

用途：把测试期累积的模拟数据清掉，重建为真实真题数据集。

保留：users / ai_providers / ai_models / app_settings / platform_cookies
清空：documents 及其下游（chunks/cards/questions/notes/attempts/review_logs/...）、
      plans / plan_tasks / card_decks / question_banks / note_folders / tasks /
      dashboard_layouts / cost_ledger / audit_logs / card_anchors

用法：
    python scripts/reset_user_data.py --email a@b.com --yes
    python scripts/reset_user_data.py --email a@b.com --dry-run   # 只统计不删
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.models.models import User  # noqa: E402

# 按依赖倒序删（先子后父），避免外键报错
DELETE_ORDER = [
    "attempts", "review_logs", "card_anchors", "cards", "questions", "question_banks",
    "chunks", "notes", "note_folders", "card_decks", "plan_tasks", "plans", "tasks",
    "documents", "dashboard_layouts", "cost_ledger", "audit_logs",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--yes", action="store_true", help="确认执行删除")
    ap.add_argument("--dry-run", action="store_true", help="只统计将删除的行数")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).one_or_none()
        if not user:
            print(f"[FAIL] 用户不存在：{args.email}")
            return 1
        uid = user.id

        insp = inspect(db.bind)
        tables = set(insp.get_table_names())

        # 统计
        counts: dict[str, int] = {}
        for t in DELETE_ORDER:
            if t not in tables:
                continue
            cols = {c["name"] for c in insp.get_columns(t)}
            if "user_id" in cols:
                n = db.execute(text(f'SELECT count(*) FROM "{t}" WHERE user_id = :u'),
                               {"u": uid}).scalar() or 0
            else:
                # 无 user_id 的表（如 chunks/attempts）按上游归属统计
                n = 0
            counts[t] = int(n)

        # chunks / attempts / card_anchors 没有 user_id，用 JOIN 统计
        join_counts = {
            "chunks": ("chunks", "SELECT count(*) FROM chunks c JOIN documents d "
                                 "ON c.document_id = d.id WHERE d.user_id = :u"),
            "attempts": ("attempts", "SELECT count(*) FROM attempts a JOIN questions q "
                                    "ON a.question_id = q.id WHERE q.user_id = :u"),
            "card_anchors": ("card_anchors", "SELECT count(*) FROM card_anchors ca "
                                            "JOIN notes n ON ca.note_id = n.id WHERE n.user_id = :u"),
            "review_logs": ("review_logs", "SELECT count(*) FROM review_logs r WHERE r.user_id = :u"),
        }
        for t, (name, sql) in join_counts.items():
            if name in tables:
                try:
                    counts[t] = int(db.execute(text(sql), {"u": uid}).scalar() or 0)
                except Exception:  # noqa: BLE001
                    pass

        total = sum(counts.values())
        print(f"用户 {args.email}（id={uid}）将清空：共 {total} 行")
        for t, n in counts.items():
            if n:
                print(f"  {t:20s} {n}")

        if args.dry_run or not args.yes:
            print("\n[dry-run] 未执行删除。加 --yes 确认执行。")
            return 0

        print("\n开始删除…")
        for t in DELETE_ORDER:
            if t not in tables:
                continue
            cols = {c["name"] for c in insp.get_columns(t)}
            if "user_id" in cols:
                n = db.execute(text(f'DELETE FROM "{t}" WHERE user_id = :u'), {"u": uid}).rowcount
            elif t == "chunks":
                n = db.execute(text(
                    "DELETE FROM chunks WHERE document_id IN "
                    "(SELECT id FROM documents WHERE user_id = :u)"), {"u": uid}).rowcount
            elif t == "attempts":
                n = db.execute(text(
                    "DELETE FROM attempts WHERE question_id IN "
                    "(SELECT id FROM questions WHERE user_id = :u)"), {"u": uid}).rowcount
            elif t == "card_anchors":
                n = db.execute(text(
                    "DELETE FROM card_anchors WHERE note_id IN "
                    "(SELECT id FROM notes WHERE user_id = :u)"), {"u": uid}).rowcount
            else:
                continue
            if n:
                print(f"  删除 {t}: {n} 行")
        db.commit()

        # 兜底：确认没有残留文档
        left = db.execute(text("SELECT count(*) FROM documents WHERE user_id = :u"),
                          {"u": uid}).scalar()
        print(f"\n[OK] 完成。剩余文档 {left} 条")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
