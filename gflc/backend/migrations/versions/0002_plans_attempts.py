"""add plans / plan_tasks / attempts

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-21
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401
    # create_all 幂等：只建缺失的表
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    from alembic import op as _op
    _op.drop_table("attempts")
    _op.drop_table("plan_tasks")
    _op.drop_table("plans")
