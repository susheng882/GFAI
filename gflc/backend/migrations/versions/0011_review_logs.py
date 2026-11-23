"""B14 学习热力图：review_logs 复习日志表

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-23

每次复习 / 标记掌握 / 延后写一条流水，热力图与连续打卡按天聚合。
表用 SQLAlchemy Table.create(checkfirst=True) 建，索引缺失则补齐，可安全重跑；
downgrade 先删索引再删表，可逆。
"""
import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

_INDEXES = (
    ("ix_review_logs_user_id", '"user_id"'),
    ("ix_review_logs_created_at", '"created_at"'),
    ("ix_review_logs_card_id", '"card_id"'),
    # 热力图主查询：按用户 + 日期范围取数
    ("ix_review_logs_user_created", '"user_id", "created_at"'),
)


def _indexes(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade_bind(bind) -> None:
    """供 alembic 与独立 SQLite 测试共用的 upgrade 逻辑（幂等）。"""
    from app.db.session import Base
    import app.models.models  # noqa: F401  确保 ReviewLog 注册到 metadata

    Base.metadata.tables["review_logs"].create(bind=bind, checkfirst=True)
    # 旧库若手工建过表，索引不会自动补齐，这里显式补
    for name, cols_sql in _INDEXES:
        if name not in _indexes(bind, "review_logs"):
            bind.execute(sa.text(
                'CREATE INDEX IF NOT EXISTS "{}" ON "review_logs" ({})'.format(name, cols_sql)))


def downgrade_bind(bind) -> None:
    """逆向：先删索引，再删表（幂等）。"""
    for name, _ in _INDEXES:
        if name in _indexes(bind, "review_logs"):
            bind.execute(sa.text('DROP INDEX IF EXISTS "{}"'.format(name)))
    if sa.inspect(bind).has_table("review_logs"):
        bind.execute(sa.text('DROP TABLE IF EXISTS "review_logs"'))


def upgrade():
    upgrade_bind(op.get_bind())


def downgrade():
    downgrade_bind(op.get_bind())
