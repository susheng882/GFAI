# -*- coding: utf-8 -*-
"""请求/响应与 AI 输出契约（Pydantic v2）。AI 结果一律 JSON + 本文件校验。"""
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


# ---------- 通用 ----------
class Ok(BaseModel):
    ok: bool = True
    data: dict | list | None = None
    request_id: str = ""


# ---------- 鉴权 ----------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    role: str

    class Config:
        from_attributes = True


# ---------- 文档 / 任务 ----------
class DocumentOut(BaseModel):
    id: int
    title: str
    source_type: str
    status: str
    doc_version: int
    size: int

    class Config:
        from_attributes = True


class TaskOut(BaseModel):
    id: int
    document_id: int | None
    type: str
    status: str
    progress: int
    error_code: str | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True


class PresignIn(BaseModel):
    filename: str
    content_type: str = "application/octet-stream"
    size: int = 0


class PresignOut(BaseModel):
    upload_url: str
    storage_key: str
    method: str = "PUT"


# ---------- AI 输出契约 ----------
class CardItem(BaseModel):
    question: str
    answer: str
    tag: str = ""
    chapter: str = ""
    page: int = 0


class CardGenResult(BaseModel):
    cards: list[CardItem]


class QuestionAnalysis(BaseModel):
    """五段解析，缺任一段视为失败。"""
    point: str          # 考点分析
    approach: str       # 解题思路
    steps: list[str]    # 详细步骤
    pitfalls: list[str]  # 易错点
    answer: str         # 最终答案


class QuestionGenResult(BaseModel):
    analysis: QuestionAnalysis


class ChatSource(BaseModel):
    chunk_id: int
    page: int = 0
    ts_start: float | None = None


class AnswerResult(BaseModel):
    answer: str
    sources: list[ChatSource] = []
    refused: bool = False


ModelTier = Literal["light", "mid", "strong"]


# ---------- 题库 / 刷题 ----------
class QuestionOut(BaseModel):
    id: int
    stem: str
    options: list | None = None
    answer: str
    analysis: dict | None = None
    qtype: str = "single"
    difficulty: str = "mid"
    page: int = 0
    bank_id: int | None = None
    chapter: str | None = ""
    section: str | None = ""
    no: str | None = ""

    class Config:
        from_attributes = True


class QuizGenIn(BaseModel):
    count: int = 5
    document_id: int | None = None


class QuestionItem(BaseModel):
    stem: str
    options: list[str] = []
    answer: str = ""
    qtype: str = "single"
    analysis: QuestionAnalysis


class QuestionBatch(BaseModel):
    questions: list[QuestionItem]


class QuizSubmitIn(BaseModel):
    question_id: int
    user_answer: str


class QuizResult(BaseModel):
    correct: bool
    answer: str
    analysis: dict | None = None


# ---------- 学习计划 ----------
class PlanTaskItem(BaseModel):
    day: int
    title: str
    detail: str = ""


class PlanGenResult(BaseModel):
    tasks: list[PlanTaskItem]


class PlanIn(BaseModel):
    goal: str
    days: int = 7


# ---------- 问答 ----------
class QaIn(BaseModel):
    question: str
    document_id: int | None = None
    top_k: int = 5


class QaAnswer(BaseModel):
    answer: str


class VideoNote(BaseModel):
    summary: str = ""
    points: list[str] = []


# ---------- AI 主题仪表盘 ----------
class DashCard(BaseModel):
    id: str
    type: Literal["stat", "bar", "ring", "line", "list", "progress"]
    title: str = ""
    value: str = ""
    unit: str = ""
    hint: str = ""
    items: list[str] = []
    data: list[dict] = []   # [{label, value}]
    max: float = 100


class DashConfig(BaseModel):
    title: str = ""
    subtitle: str = ""
    cards: list[DashCard] = []


class DashGenIn(BaseModel):
    theme: str
    scope: Literal["month", "week", "day"] = "week"


class DashOrderIn(BaseModel):
    order: list[str]
    positions: dict = {}
    scope: str = "week"


class DashCardPatchIn(BaseModel):
    card_id: str
    title: str | None = None
    value: str | None = None
    unit: str | None = None
    hint: str | None = None
    items: list[str] | None = None
    data: list[dict] | None = None


# ---------- 卡包 / 卡片 CRUD ----------
class DeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document_id: int | None = None
    parent_id: int | None = None


class DeckPatchIn(BaseModel):
    name: str | None = None


class DeckOut(BaseModel):
    id: int
    document_id: int | None = None
    parent_id: int | None = None
    name: str
    kind: str = "root"
    sort: int = 0
    total: int = 0
    due: int = 0
    done: int = 0

    class Config:
        from_attributes = True


class CardOut(BaseModel):
    id: int
    deck_id: int | None = None
    document_id: int
    question: str
    answer: str
    tag: str = ""
    difficulty: str = "mid"
    page: int = 0
    due_at: str | None = None
    reps: int = 0
    lapses: int = 0

    class Config:
        from_attributes = True


class CardIn(BaseModel):
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    tag: str = ""
    difficulty: str = "mid"
    page: int = 0
    deck_id: int | None = None


class CardPatchIn(BaseModel):
    question: str | None = None
    answer: str | None = None
    tag: str | None = None
    difficulty: str | None = None
    deck_id: int | None = None


# ---------- 笔记 CRUD ----------
class NoteOut(BaseModel):
    id: int
    document_id: int | None = None
    folder_id: int | None = None
    title: str = ""
    summary: str = ""
    content: str | None = None
    points: list | None = None
    source: str = "manual"
    kind: str = "note"
    updated_at: str | None = None

    class Config:
        from_attributes = True


class NoteIn(BaseModel):
    title: str = ""
    summary: str = ""
    content: str | None = None
    points: list[str] = []
    folder_id: int | None = None
    kind: str = "note"
    source: str = "manual"


class NotePatchIn(BaseModel):
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    points: list[str] | None = None
    folder_id: int | None = None


# ---------- 笔记文件夹树 ----------
class FolderIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    parent_id: int | None = None
    kind: str = "topic"      # project / subject / topic


class FolderPatchIn(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort: int | None = None


class FolderOut(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    kind: str = "topic"
    sort: int = 0
    note_count: int = 0
    children: list = []

    class Config:
        from_attributes = True


class NoteAiIn(BaseModel):
    """让 AI 对当前笔记做补充/改写，返回建议，由用户决定是否插入。"""
    note_id: int | None = None
    title: str = ""
    content: str = ""
    instruction: str = ""
    mode: Literal["improve", "expand", "summarize", "quiz"] = "improve"


class NoteAiOut(BaseModel):
    suggestion: str = ""
    points: list[str] = []
    kind: str = "note"


class NoteInsertIn(BaseModel):
    """用户确认后把 AI 建议写入笔记。"""
    note_id: int
    text: str
    position: Literal["append", "replace", "prepend"] = "append"


# ---------- 视频笔记多模板 ----------
VideoTemplate = Literal["summary", "outline", "qa"]



# ---------- 刷题推荐（背单词书式）----------
class QuizRecommend(BaseModel):
    bank_id: int | None = None
    chapter: str = ""
    total: int = 0
    done: int = 0
    correct_rate: float = 0.0
    due_wrong: int = 0
    suggestion: str = ""
    progress: float = 0.0
