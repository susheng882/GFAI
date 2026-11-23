"""配置中心：供应商 / 模型 / 运行时配置 / 平台 Cookie 四张表

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-22

对标 BiliNote 设置中心：密钥只存密文（Fernet，key 由 SESSION_SECRET 派生），
接口只返回掩码。表结构用 create_all 建（幂等），不删改任何既有表。
"""
import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

_TABLES = ("ai_providers", "ai_models", "app_settings", "platform_cookies")


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

    insp = sa.inspect(bind)
    for name, table, col in [
        ("ix_ai_models_provider_id", "ai_models", "provider_id"),
    ]:
        if insp.has_table(table):
            idx = {i["name"] for i in insp.get_indexes(table)}
            if name not in idx:
                try:
                    bind.execute(sa.text('CREATE INDEX IF NOT EXISTS "{}" ON "{}" ("{}")'.format(
                        name, table, col)))
                except Exception:  # noqa: BLE001
                    pass


def downgrade():
    bind = op.get_bind()
    for t in _TABLES:
        bind.execute(sa.text('DROP TABLE IF EXISTS "{}"'.format(t)))
