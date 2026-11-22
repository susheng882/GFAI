"""add tasks.result

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    # 0001 用 metadata.create_all 建表，可能已带上 result（新版模型）
    if "result" not in _cols("tasks"):
        op.add_column("tasks", sa.Column("result", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("tasks") as b:
        b.drop_column("result")
