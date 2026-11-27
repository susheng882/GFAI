# -*- coding: utf-8 -*-
"""核心数据模型（当前 22 张表，迁移链 0001–0011）。
每个 chunk/card/question 都带溯源字段（页码/时间戳），这是产品可信度的地基。

历史注：早期 P0 仅 7 张表，plan/review 等经 0002/0008 等迁移补入；注释中曾提到的
error_case 表未落地（已被 attempts + audit_logs 覆盖），特此澄清避免误导。"""
from datetime import datetime

from sqlalchemy import (JSON, DateTime, Float, ForeignKey, Index, Integer, String,
                        Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user")
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[str] = mapped_column(String(32))  # pdf / video / question_bank
    content_hash: Mapped[str] = mapped_column(String(64), index=True)  # 去重
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/parsing/ready/failed
    doc_version: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(String(512), default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    mime: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32))  # pdf_parse / card_generate / question_import / plan_generate / video_upload / video_url / dashboard_generate
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/running/ready/failed
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checkpoint: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 断点续传
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)      # 任务结果
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    heading_path: Mapped[str] = mapped_column(String(512), default="")
    page: Mapped[int] = mapped_column(Integer, default=0)          # 溯源：页码
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id"), nullable=True)  # 父块（已设计）
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    ts_start: Mapped[float | None] = mapped_column(Float, nullable=True)  # 溯源：视频时间戳起
    ts_end: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CardDeck(Base):
    """卡包：一份文档 = 一个大卡包，内部按 PDF 大纲拆成章节子卡包。"""
    __tablename__ = "card_decks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("card_decks.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    kind: Mapped[str] = mapped_column(String(16), default="root")  # root / chapter
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Card(Base):
    __tablename__ = "cards"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    deck_id: Mapped[int | None] = mapped_column(ForeignKey("card_decks.id"), nullable=True, index=True)
    chunk_id: Mapped[int | None] = mapped_column(ForeignKey("chunks.id"), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    tag: Mapped[str] = mapped_column(String(128), default="")
    difficulty: Mapped[str] = mapped_column(String(16), default="mid")
    page: Mapped[int] = mapped_column(Integer, default=0)  # 溯源
    # 复习排期（py-fsrs）
    fsrs_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    # S6：掌握度（0–1），由复习评分/答题联动更新；与 due_at 共同驱动复习队列
    mastery: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", index=True)
    # B12：同源卡片锚点。旧卡三列均为 NULL，代表「独立卡」，不丢失、不改动。
    source_note_id: Mapped[int | None] = mapped_column(
        ForeignKey("notes.id", ondelete="SET NULL"), nullable=True, index=True)
    anchor_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuestionBank(Base):
    __tablename__ = "question_banks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(256))
    subject: Mapped[str] = mapped_column(String(128), default="")
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    bank_id: Mapped[int | None] = mapped_column(ForeignKey("question_banks.id"), nullable=True, index=True)
    chapter: Mapped[str] = mapped_column(String(128), default="")
    section: Mapped[str] = mapped_column(String(32), default="")
    no: Mapped[str] = mapped_column(String(16), default="")
    stem: Mapped[str] = mapped_column(Text)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str] = mapped_column(String(512), default="")
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 五段：point/approach/steps/pitfalls/answer
    qtype: Mapped[str] = mapped_column(String(32), default="single")
    difficulty: Mapped[str] = mapped_column(String(16), default="mid")
    page: Mapped[int] = mapped_column(Integer, default=0)
    # S6：知识点掌握度（0–1），由 quiz 答题结果联动更新，驱动推荐与错题优先级
    mastery: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CostLedger(Base):
    __tablename__ = "cost_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    task_type: Mapped[str] = mapped_column(String(32), default="")
    model: Mapped[str] = mapped_column(String(64), default="")
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_cny: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    goal: Mapped[str] = mapped_column(String(512))
    days: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlanTask(Base):
    __tablename__ = "plan_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), index=True)
    day_index: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(512))
    detail: Mapped[str] = mapped_column(Text, default="")
    done: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1，SQLite 友好
    # D10：任务到期时间；为空时按 plan.created_at + day_index 派生（兼容历史数据）
    due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    user_answer: Mapped[str] = mapped_column(String(512), default="")
    correct: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewLog(Base):
    """B14：复习日志（每次复习写一条流水，驱动学习热力图与连续打卡）。

    rating：0=标记掌握，1–4=四档评分，-1=延后（defer）。
    延后只留痕，不计入复习量/活跃天数，避免污染评分口径。
    """
    __tablename__ = "review_logs"
    __table_args__ = (
        Index("ix_review_logs_user_created", "user_id", "created_at"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 index=True)


class NoteFolder(Base):
    """笔记文件夹：项目 → 科目 → 内容，三层树（类似 Obsidian 的 vault 目录）。"""
    __tablename__ = "note_folders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("note_folders.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(16), default="topic")  # project / subject / topic
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    folder_id: Mapped[int | None] = mapped_column(ForeignKey("note_folders.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)   # Markdown 正文
    points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="manual")  # manual/ai/video/import
    kind: Mapped[str] = mapped_column(String(16), default="note")      # note/outline/qa/summary
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class CardAnchor(Base):
    """B12 笔记↔卡片同源（方案 B 轻量锚点）。

    正文写「正面 :: 背面」，保存时按行解析出成卡行落到本表；
    notes.content 原文不动。hash 是 front/back 的摘要：变化时标记「源已改」，
    由用户显式点「同步卡片」才回写对应卡，不静默覆盖。
    """
    __tablename__ = "card_anchors"
    __table_args__ = (
        UniqueConstraint("note_id", "line_no", name="uq_card_anchors_note_line"),
        Index("ix_card_anchors_user_anchor", "user_id", "anchor_id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(ForeignKey("notes.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    line_no: Mapped[int] = mapped_column(Integer)  # 1 基行号，定位回正文
    anchor_id: Mapped[str] = mapped_column(String(128), index=True)  # GFLC 自定：gflc::ln::<note_id>::<line_no>
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    hash: Mapped[str] = mapped_column(String(64), index=True)  # sha256(front + \x00 + back)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DashboardLayout(Base):
    __tablename__ = "dashboard_layouts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    theme: Mapped[str] = mapped_column(String(200))
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # AI 生成的卡片配置
    order: Mapped[list | None] = mapped_column(JSON, nullable=True)    # 拖拽后的卡片顺序
    positions: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {cardId: {x,y,w,h}} 自由缩放
    scope: Mapped[str] = mapped_column(String(8), default="week")      # month / week / day
    is_default: Mapped[int] = mapped_column(Integer, default=0)        # 1=当前默认仪表盘
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditLog(Base):
    """V5：账号导出/注销审计。只存动作与 IP 摘要，绝不落原文与凭据。"""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    action: Mapped[str] = mapped_column(String(32))       # export / delete
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_hash: Mapped[str] = mapped_column(String(32), default="")  # IP 的 sha256 摘要，非原文
    detail: Mapped[str] = mapped_column(String(200), default="")  # 非敏感备注，如归档版本/清理计数


# ---------------------------------------------------------------------------
# 配置中心（对标 BiliNote 设置页）：供应商 / 模型 / 运行时配置 / 平台 Cookie
# 密钥一律只存密文（Fernet，密钥由 SESSION_SECRET 派生），接口只返回掩码。
# ---------------------------------------------------------------------------
class AiProvider(Base):
    __tablename__ = "ai_providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))                  # 展示名：方舟 / DeepSeek 官方
    kind: Mapped[str] = mapped_column(String(24), default="openai")  # openai|ark|deepseek|groq
    base_url: Mapped[str] = mapped_column(String(255), default="")
    api_key_enc: Mapped[str] = mapped_column(Text, default="")     # 密文
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AiModel(Base):
    __tablename__ = "ai_models"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("ai_providers.id"), index=True)
    model_id: Mapped[str] = mapped_column(String(96))               # 接口用的真实 model 名
    label: Mapped[str] = mapped_column(String(96), default="")
    purpose: Mapped[str] = mapped_column(String(24), default="note")  # note|vision|long|transcribe|chat
    metered: Mapped[int] = mapped_column(Integer, default=1)
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    is_default: Mapped[int] = mapped_column(Integer, default=0)
    probe_status: Mapped[str] = mapped_column(String(24), default="unknown")  # ok|not_activated|error
    probe_note: Mapped[str] = mapped_column(String(200), default="")
    probed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AppSetting(Base):
    """运行时开关（转录器类型、whisper 大小、并发数、bcut 开关、代理等）。"""
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")           # 一律存字符串，读取方自行转型
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class PlatformCookie(Base):
    """平台登录态（B站 SESSDATA 等）。只存密文，接口永不回显。"""
    __tablename__ = "platform_cookies"
    platform: Mapped[str] = mapped_column(String(24), primary_key=True)  # bilibili|youtube|douyin
    cookie_enc: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(String(120), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                 onupdate=func.now())


class Conversation(Base):
    """AI 伴侣会话（0012）。"""
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(120), default="新对话")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConversationMessage(Base):
    """AI 伴侣消息（0012）。sources=引用溯源，steps=步骤轨迹。"""
    __tablename__ = "conversation_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(12))          # user | assistant
    content: Mapped[str] = mapped_column(Text, default="")
    sources: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    steps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Workspace(Base):
    """工作区（0012）。多工作区切换，数据隔离迁移在 C8 验收时做。"""
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    current: Mapped[int] = mapped_column(Integer, default=0)   # 1=当前
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
