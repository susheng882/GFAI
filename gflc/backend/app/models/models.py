# -*- coding: utf-8 -*-
"""核心数据模型（P0 建 7 张表；plan/review/error_case 进 P1 迁移补）。
每个 chunk/card/question 都带溯源字段（页码/时间戳），这是产品可信度的地基。"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
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
    type: Mapped[str] = mapped_column(String(32))  # pdf_parse / video_parse / card_generate ...
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


class Attempt(Base):
    __tablename__ = "attempts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    user_answer: Mapped[str] = mapped_column(String(512), default="")
    correct: Mapped[bool] = mapped_column(Integer, default=0)  # 0/1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
