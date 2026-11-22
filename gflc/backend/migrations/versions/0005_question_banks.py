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


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401
    Base.metadata.create_all(bind=op.get_bind())  # 建 question_banks
    op.add_column("questions", sa.Column("bank_id", sa.Integer(), nullable=True))
    op.add_column("questions", sa.Column("chapter", sa.String(128), nullable=True))
    op.add_column("questions", sa.Column("section", sa.String(32), nullable=True))
    op.add_column("questions", sa.Column("no", sa.String(16), nullable=True))


def downgrade():
    with op.batch_alter_table("questions") as b:
        for col in ("bank_id", "chapter", "section", "no"):
            b.drop_column(col)
