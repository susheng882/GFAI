"""init schema (P0)

Revision ID: 0001
Revises:
Create Date: 2026-11-21

说明：初始建表直接用 metadata.create_all，保证迁移与 ORM 模型永远一致；
后续增量变更改用 autogenerate。
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401  注册所有表
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401
    Base.metadata.drop_all(bind=op.get_bind())
