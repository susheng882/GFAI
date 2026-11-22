"""card decks + notes/dashboard CRUD fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401

    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = set(insp.get_table_names())

    # 新表 card_decks（create_all 会自动跳过已存在的表）
    Base.metadata.create_all(bind=bind)

    # cards.deck_id
    if "deck_id" not in _cols("cards"):
        op.add_column("cards", sa.Column("deck_id", sa.Integer(), nullable=True))
        op.create_index("ix_cards_deck_id", "cards", ["deck_id"])

    # notes 增列
    nc = _cols("notes")
    for col, ddl in [
        ("user_id", sa.Column("user_id", sa.Integer(), nullable=True)),
        ("title", sa.Column("title", sa.String(256), nullable=True)),
        ("updated_at", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)),
    ]:
        if col not in nc:
            op.add_column("notes", ddl)

    # dashboard_layouts 增列
    dc = _cols("dashboard_layouts")
    for col, ddl in [
        ("positions", sa.Column("positions", sa.JSON(), nullable=True)),
        ("scope", sa.Column("scope", sa.String(8), nullable=True)),
        ("is_default", sa.Column("is_default", sa.Integer(), nullable=True)),
    ]:
        if col not in dc:
            op.add_column("dashboard_layouts", ddl)


def downgrade():
    with op.batch_alter_table("dashboard_layouts") as b:
        for col in ("positions", "scope", "is_default"):
            b.drop_column(col)
    with op.batch_alter_table("notes") as b:
        for col in ("user_id", "title", "updated_at"):
            b.drop_column(col)
    with op.batch_alter_table("cards") as b:
        b.drop_column("deck_id")
    op.drop_table("card_decks")
