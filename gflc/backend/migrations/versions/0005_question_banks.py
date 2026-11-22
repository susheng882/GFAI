"""question banks + question chapter fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401
    Base.metadata.create_all(bind=op.get_bind())  # 建 question_banks（已存在则跳过）

    have = _cols("questions")
    for name, ddl in [
        ("bank_id", sa.Column("bank_id", sa.Integer(), nullable=True)),
        ("chapter", sa.Column("chapter", sa.String(128), nullable=True)),
        ("section", sa.Column("section", sa.String(32), nullable=True)),
        ("no", sa.Column("no", sa.String(16), nullable=True)),
    ]:
        if name not in have:
            op.add_column("questions", ddl)


def downgrade():
    with op.batch_alter_table("questions") as b:
        for col in ("bank_id", "chapter", "section", "no"):
            b.drop_column(col)
