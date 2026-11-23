"""B12 笔记↔卡片同源（方案 B 轻量锚点）：card_anchors 表 + cards 溯源列。

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-23

正文写「正面 :: 背面」→ 保存时解析成 card_anchors 行；cards 只增三列
（source_note_id / anchor_id / source_hash，均可空），旧卡三列为 NULL，代表独立卡。
表结构用 SQLAlchemy Table.create(checkfirst=True) 建，列/索引存在则跳过，可安全重跑。
downgrade 用 DROP COLUMN（SQLite >= 3.35 / PostgreSQL）可逆。
"""
import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

_ADD_COLS = (
    ("cards", "source_note_id", "INTEGER"),
    ("cards", "anchor_id", "VARCHAR(128)"),
    ("cards", "source_hash", "VARCHAR(64)"),
)


def _cols(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def _indexes(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if not insp.has_table(table):
        return set()
    return {i["name"] for i in insp.get_indexes(table)}


def _create_index(bind, name: str, table: str, cols_sql: str) -> None:
    if name not in _indexes(bind, table):
        bind.execute(sa.text(
            'CREATE INDEX IF NOT EXISTS "{}" ON "{}" ({})'.format(name, table, cols_sql)))


def upgrade_bind(bind) -> None:
    """供 alembic 与独立 SQLite 测试共用的 upgrade 逻辑（幂等）。"""
    from app.db.session import Base
    import app.models.models  # noqa: F401  确保 CardAnchor / Card 新列注册到 metadata

    # 1) 建 card_anchors 表（含唯一约束 uq_card_anchors_note_line 与列索引）
    Base.metadata.tables["card_anchors"].create(bind=bind, checkfirst=True)

    # 2) cards 只增列，不改旧列；旧卡新列保持 NULL
    for table, name, ddl in _ADD_COLS:
        if name not in _cols(bind, table):
            bind.execute(sa.text(
                'ALTER TABLE "{}" ADD COLUMN "{}" {}'.format(table, name, ddl)))

    # 3) 旧库 ALTER 出来的列不会自动带索引，显式补齐
    _create_index(bind, "ix_card_anchors_user_anchor", "card_anchors", '"user_id", "anchor_id"')
    _create_index(bind, "ix_cards_source_note_id", "cards", '"source_note_id"')
    _create_index(bind, "ix_cards_anchor_id", "cards", '"anchor_id"')


def downgrade_bind(bind) -> None:
    """逆向：先删索引，再删列，最后删表（幂等）。"""
    for name, table in (
        ("ix_cards_anchor_id", "cards"),
        ("ix_cards_source_note_id", "cards"),
        ("ix_card_anchors_user_anchor", "card_anchors"),
    ):
        if name in _indexes(bind, table):
            bind.execute(sa.text('DROP INDEX IF EXISTS "{}"'.format(name)))
    for table, name, _ in reversed(_ADD_COLS):
        if name in _cols(bind, table):
            bind.execute(sa.text('ALTER TABLE "{}" DROP COLUMN "{}"'.format(table, name)))
    if sa.inspect(bind).has_table("card_anchors"):
        bind.execute(sa.text('DROP TABLE IF EXISTS "card_anchors"'))


def upgrade():
    upgrade_bind(op.get_bind())


def downgrade():
    downgrade_bind(op.get_bind())
