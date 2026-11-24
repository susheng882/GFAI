# -*- coding: utf-8 -*-
"""彻底清理测试数据：保留主账号与模型配置，删除其余账号及其全部学习数据。

背景：历次验收（e2e/ux/vf/bench/perf 等）在库里累积了 160+ 测试账号与数百份测试文档，
真实数据集必须从干净状态开始。

用法：
    python scripts/purge_test_data.py --keep cfg_probe@gflc.com --dry-run
    python scripts/purge_test_data.py --keep cfg_probe@gflc.com --yes

行为：
1. 删除除 --keep 之外的所有用户（及其 documents/chunks/cards/questions/notes/... 全部下游）
2. 清空 --keep 账号的学习数据（保留账号本身，保留 ai_providers/ai_models/app_settings）
3. 保留平台配置表：ai_providers / ai_models / app_settings / platform_cookies
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402

# 学习数据表（按依赖倒序）
DATA_TABLES = [
    "attempts", "review_logs", "card_anchors", "cards", "questions", "question_banks",
    "chunks", "notes", "note_folders", "card_decks", "plan_tasks", "plans", "tasks",
    "documents", "dashboard_layouts", "cost_ledger",
]
# 有 user_id 直接删的表
HAS_UID = {
    "cards", "questions", "question_banks", "notes", "note_folders", "card_decks",
    "plans", "tasks", "documents", "dashboard_layouts", "cost_ledger", "review_logs",
}
# 需要经上游 JOIN 的表
JOIN_DELETE = {
    "chunks": ("DELETE FROM chunks WHERE document_id IN "
               "(SELECT id FROM documents WHERE user_id = :u)"),
    "attempts": ("DELETE FROM attempts WHERE question_id IN "
                 "(SELECT id FROM questions WHERE user_id = :u)"),
    "card_anchors": ("DELETE FROM card_anchors WHERE note_id IN "
                     "(SELECT id FROM notes WHERE user_id = :u)"),
    "plan_tasks": ("DELETE FROM plan_tasks WHERE plan_id IN "
                   "(SELECT id FROM plans WHERE user_id = :u)"),
}


def wipe_user(db, uid: int) -> int:
    n = 0
    for t in DATA_TABLES:
        if t in HAS_UID:
            n += db.execute(text(f'DELETE FROM "{t}" WHERE user_id = :u'), {"u": uid}).rowcount or 0
        elif t in JOIN_DELETE:
            n += db.execute(text(JOIN_DELETE[t]), {"u": uid}).rowcount or 0
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", required=True, help="保留的主账号邮箱")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        db.execute(text("PRAGMA foreign_keys = OFF"))
        insp = inspect(db.bind)
        tables = set(insp.get_table_names())

        users = db.execute(text("SELECT id, email FROM users ORDER BY id")).fetchall()
        keep = [u for u in users if u[1] == args.keep]
        drop = [u for u in users if u[1] != args.keep]
        if not keep:
            print(f"[FAIL] 主账号不存在：{args.keep}（请先注册）")
            return 1
        keep_id = keep[0][0]

        print(f"用户总数 {len(users)}：保留 1 个（{args.keep}），将删除 {len(drop)} 个")
        # 统计待删学习数据
        total_docs = db.execute(text("SELECT count(*) FROM documents")).scalar() or 0
        total_q = db.execute(text("SELECT count(*) FROM questions")).scalar() or 0
        total_cards = db.execute(text("SELECT count(*) FROM cards")).scalar() or 0
        total_notes = db.execute(text("SELECT count(*) FROM notes")).scalar() or 0
        print(f"当前全库：documents={total_docs} questions={total_q} cards={total_cards} notes={total_notes}")

        if args.dry_run or not args.yes:
            print("\n[dry-run] 未执行。加 --yes 确认。")
            return 0

        print("\n1) 清空主账号学习数据…")
        n = wipe_user(db, keep_id)
        print(f"   删除 {n} 行")

        print("2) 删除其余账号及其数据…")
        m = 0
        for uid, email in drop:
            m += wipe_user(db, uid)
        db.execute(text("DELETE FROM users WHERE id != :k"), {"k": keep_id})
        print(f"   删除 {m} 行数据 + {len(drop)} 个账号")

        db.commit()
        db.execute(text("PRAGMA foreign_keys = ON"))

        left = {
            "users": db.execute(text("SELECT count(*) FROM users")).scalar(),
            "documents": db.execute(text("SELECT count(*) FROM documents")).scalar(),
            "questions": db.execute(text("SELECT count(*) FROM questions")).scalar(),
            "cards": db.execute(text("SELECT count(*) FROM cards")).scalar(),
            "notes": db.execute(text("SELECT count(*) FROM notes")).scalar(),
        }
        print(f"\n[OK] 清理完成：{left}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
