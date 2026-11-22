"""note folders tree + note content fields

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-21
"""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _cols(table: str) -> set[str]:
    insp = sa.inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade():
    from app.db.session import Base
    import app.models.models  # noqa: F401

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)  # 建 note_folders

    nc = _cols("notes")
    for col, ddl in [
        ("folder_id", sa.Column("folder_id", sa.Integer(), nullable=True)),
        ("content", sa.Column("content", sa.Text(), nullable=True)),
        ("source", sa.Column("source", sa.String(16), nullable=True)),
        ("kind", sa.Column("kind", sa.String(16), nullable=True)),
    ]:
        if col not in nc:
            op.add_column("notes", ddl)
    idx = sa.inspect(bind).get_indexes("notes")
    idx_names = {i["name"] for i in idx}
    idx_cols = {c for i in idx for c in (i.get("column_names") or [])}
    # 注意：要比对索引名或索引列，不能拿列名去比索引名（老写法永远为真）
    if "ix_notes_folder_id" not in idx_names and "folder_id" not in idx_cols:
        op.create_index("ix_notes_folder_id", "notes", ["folder_id"])


def downgrade():
    with op.batch_alter_table("notes") as b:
        for col in ("folder_id", "content", "source", "kind"):
            b.drop_column(col)
    op.drop_table("note_folders")
