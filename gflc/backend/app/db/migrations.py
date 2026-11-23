# -*- coding: utf-8 -*-
"""S6/D10/V5 幂等迁移：在既有 SQLite/PostgreSQL 库上补列、建表、建索引。

用法：
    # 直接用默认 DATABASE_URL（settings 读取，不改 .env）
    python -m app.db.migrations
    # 指定独立临时 SQLite 库自测
    python -m app.db.migrations /tmp/gflc_test.db
    python -m app.db.migrations sqlite:////tmp/gflc_test.db
    # 或用环境变量指定目标库
    GFLC_MIGRATION_DATABASE_URL=sqlite:////tmp/gflc_test.db python -m app.db.migrations

策略：列存在则跳过（幂等），可反复执行；create_all 只补缺失表，不删改任何现有表/列。
"""
import os
import sys

import sqlalchemy as sa
from sqlalchemy import create_engine, text


def _cols(bind, table: str) -> set[str]:
    if not sa.inspect(bind).has_table(table):
        return set()
    return {c["name"] for c in sa.inspect(bind).get_columns(table)}


def _indexes(bind, table: str) -> set[str]:
    if not sa.inspect(bind).has_table(table):
        return set()
    return {i["name"] for i in sa.inspect(bind).get_indexes(table)}


def run_migrations(bind) -> int:
    """执行幂等迁移，返回本次实际发生的 DDL 变更数。"""
    from app.db.session import Base
    import app.models.models  # noqa: F401  确保新表/新字段注册到 metadata

    changes = 0

    # 1) 补缺失的表（audit_logs 等）；已存在的表 create_all 不动
    before = set(sa.inspect(bind).get_table_names())
    Base.metadata.create_all(bind=bind)
    after = set(sa.inspect(bind).get_table_names())
    changes += len(after - before)

    # 2) 补缺失的列（已存在则跳过）；用通用 DDL，SQLite/PostgreSQL 均可直接执行
    add_specs = [
        ("cards", "mastery", "FLOAT DEFAULT 0 NOT NULL"),
        ("questions", "mastery", "FLOAT DEFAULT 0 NOT NULL"),
        ("plan_tasks", "due", "TIMESTAMP"),
        # B12 / alembic 0010：同源锚点溯源列，旧卡保持 NULL（独立卡）
        ("cards", "source_note_id", "INTEGER"),
        ("cards", "anchor_id", "VARCHAR(128)"),
        ("cards", "source_hash", "VARCHAR(64)"),
    ]
    for table, name, ddl in add_specs:
        if name not in _cols(bind, table):
            bind.execute(text('ALTER TABLE "{}" ADD COLUMN "{}" {}'.format(table, name, ddl)))
            changes += 1

    # 3) 补缺失的索引（列可能由旧库 ALTER 而来，索引不会自动建）
    idx_specs = [
        ("ix_cards_mastery", "cards", "mastery"),
        ("ix_questions_mastery", "questions", "mastery"),
        # B12 / alembic 0010：ALTER 出来的列需显式补索引（card_anchors 由 create_all 建，索引随表）
        ("ix_cards_source_note_id", "cards", "source_note_id"),
        ("ix_cards_anchor_id", "cards", "anchor_id"),
    ]
    for name, table, col in idx_specs:
        if name not in _indexes(bind, table) and col in _cols(bind, table):
            # IF NOT EXISTS 在 SQLite 与 PostgreSQL 均受支持，重复执行安全
            bind.execute(text('CREATE INDEX IF NOT EXISTS "{}" ON "{}" ("{}")'.format(name, table, col)))
            changes += 1

    # 4) alembic 0011：review_logs 由上面 create_all 建表（索引随表），
    #    旧库若手工建表缺复合索引则补齐（热力图按 user_id + 日期范围取数）
    if "review_logs" in set(sa.inspect(bind).get_table_names()) and \
            "ix_review_logs_user_created" not in _indexes(bind, "review_logs"):
        bind.execute(text(
            'CREATE INDEX IF NOT EXISTS "ix_review_logs_user_created" '
            'ON "review_logs" ("user_id", "created_at")'))
        changes += 1

    return changes


def main() -> int:
    url = os.getenv("GFLC_MIGRATION_DATABASE_URL", "")
    args = sys.argv[1:]
    if args:
        arg = args[0]
        if "://" in arg:
            url = arg
        else:
            url = "sqlite:///" + os.path.abspath(arg)
    if not url:
        from app.core.config import settings
        url = settings.DATABASE_URL

    connect_args = {"check_same_thread": False} if str(url).startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    with engine.begin() as conn:
        n = run_migrations(conn)
    print("迁移完成，DDL 变更数：{}（目标：{}）".format(n, url.split("@")[-1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
