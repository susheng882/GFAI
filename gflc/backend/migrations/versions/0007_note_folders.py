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
    if "folder_id" not in {i["name"] for i in sa.inspect(bind).get_indexes("notes")}:
        op.create_index("ix_notes_folder_id", "notes", ["folder_id"])


def downgrade():
    with op.batch_alter_table("notes") as b:
        for col in ("folder_id", "content", "source", "kind"):
            b.drop_column(col)
    op.drop_table("note_folders")
