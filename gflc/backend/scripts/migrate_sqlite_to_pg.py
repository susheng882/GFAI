# -*- coding: utf-8 -*-
"""SQLite → PostgreSQL 数据迁移（GFLC 上线用）

前置：目标库已由 `alembic upgrade head` 建好表结构。
用法（在 gflc/backend 目录）：
  python scripts/migrate_sqlite_to_pg.py --pg "postgresql+psycopg://gflc:pass@localhost:5432/gflc"
  python scripts/migrate_sqlite_to_pg.py --pg "..." --dry-run     # 只统计不写入
"""
import argparse
import os
import sys

from sqlalchemy import create_engine, func, inspect, select, insert, text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.models.models import Base  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", default="./data/gflc.db")
    ap.add_argument("--pg", default=os.getenv("DATABASE_URL", ""))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="目标表已有数据时清空后写入")
    args = ap.parse_args()

    if not args.pg or "postgresql" not in args.pg:
        ap.error("请用 --pg 或 DATABASE_URL 指定 PostgreSQL 连接串")

    src = create_engine("sqlite:///" + os.path.abspath(args.sqlite))
    dst = create_engine(args.pg)
    src_tables = set(inspect(src).get_table_names())
    dst_tables = set(inspect(dst).get_table_names())

    missing = {t.name for t in Base.metadata.sorted_tables} - dst_tables
    if missing:
        print("目标库缺少表，请先执行 alembic upgrade head：", sorted(missing))
        sys.exit(1)

    total = 0
    with src.connect() as s, dst.connect() as d:
        for table in Base.metadata.sorted_tables:
            name = table.name
            if name not in src_tables or name == "alembic_version":
                continue
            rows = s.execute(select(table)).mappings().all()
            if not rows:
                continue
            existing = d.execute(select(func.count()).select_from(table)).scalar() or 0
            if existing and not args.force:
                print(f"[跳过] {name}: 目标已有 {existing} 行（加 --force 覆盖）")
                continue
            if args.dry_run:
                print(f"[预演] {name}: {len(rows)} 行")
                total += len(rows)
                continue
            if existing:
                d.execute(table.delete())
            d.execute(insert(table), [dict(r) for r in rows])
            d.commit()
            # 修正自增序列，否则插入后主键冲突
            for pk in table.primary_key.columns:
                try:
                    maxid = d.execute(select(func.max(pk))).scalar() or 0
                    d.execute(
                        text("SELECT setval(pg_get_serial_sequence(:t, :c), :v, true)"),
                        {"t": name, "c": pk.name, "v": maxid},
                    )
                    d.commit()
                except Exception as e:
                    print(f"[警告] {name}.{pk.name} 序列修正失败（非自增列可忽略）: {e}")
            print(f"[完成] {name}: {len(rows)} 行")
            total += len(rows)

    print(f"{'预演' if args.dry_run else '迁移'}合计 {total} 行")


if __name__ == "__main__":
    main()
