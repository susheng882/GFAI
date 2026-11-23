"""mastery / plan due / audit_logs（对齐 12 号评审与 gov-loop 交付）

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-22

背景：多 Agent 并行阶段模型新增了 cards.mastery / questions.mastery /
plan_tasks.due 与 audit_logs 表，但未附迁移，导致旧库上「生成卡片」直接
sqlite3.OperationalError: table cards has no column named mastery（TASK-500）。
本迁移补全结构，幂等：列/表已存在则跳过，可安全重跑。
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    if not insp.has_table(table):
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)  # 建 audit_logs（存在则不动）

    for table, name, ddl in [
        ("cards", "mastery", "FLOAT DEFAULT 0 NOT NULL"),
        ("questions", "mastery", "FLOAT DEFAULT 0 NOT NULL"),
        ("plan_tasks", "due", "TIMESTAMP"),
    ]:
        if name not in _cols(table):
            bind.execute(sa.text('ALTER TABLE "{}" ADD COLUMN "{}" {}'.format(table, name, ddl)))

    for name, table, col in [
        ("ix_cards_mastery", "cards", "mastery"),
        ("ix_questions_mastery", "questions", "mastery"),
        ("ix_plan_tasks_due", "plan_tasks", "due"),
        ("ix_audit_logs_user_id", "audit_logs", "user_id"),
    ]:
        if name not in _indexes(table):
            try:
                bind.execute(sa.text('CREATE INDEX IF NOT EXISTS "{}" ON "{}" ("{}")'.format(name, table, col)))
            except Exception:  # noqa: BLE001  索引名已存在但来源不同，跳过即可
                pass


def downgrade():
    bind = op.get_bind()
    for name, table in [
        ("ix_cards_mastery", "cards"),
        ("ix_questions_mastery", "questions"),
        ("ix_plan_tasks_due", "plan_tasks"),
    ]:
        try:
            bind.execute(sa.text('DROP INDEX IF EXISTS "{}"'.format(name)))
        except Exception:  # noqa: BLE001
            pass
    bind.execute(sa.text("DROP TABLE IF EXISTS audit_logs"))
