"""add dashboard_layouts

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-21
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    op.drop_table("dashboard_layouts")
