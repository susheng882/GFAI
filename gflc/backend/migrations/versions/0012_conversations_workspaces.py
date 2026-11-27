# -*- coding: utf-8 -*-
"""0012：AI 伴侣会话 + 工作区（阶段 C 后端）。

conversations / conversation_messages：AI 伴侣独立页的会话持久化
workspaces：多工作区切换（当前仅落表，数据迁移在 C8 验收时做）
"""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(120), default="新对话"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("conversation_id", sa.Integer, sa.ForeignKey("conversations.id"), nullable=False, index=True),
        sa.Column("role", sa.String(12), nullable=False),          # user | assistant
        sa.Column("content", sa.Text, default=""),
        sa.Column("sources", sa.JSON, nullable=True),               # 引用溯源
        sa.Column("steps", sa.JSON, nullable=True),                 # 步骤轨迹
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("current", sa.Integer, default=0),                # 1=当前工作区
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workspaces")
    op.drop_table("conversation_messages")
    op.drop_table("conversations")
