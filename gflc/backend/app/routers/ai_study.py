# -*- coding: utf-8 -*-
"""S3 学习型 AI：按薄弱点出题 / 针对错题讲解 / 用我的资料出模拟卷（38 号 §5 S3）。

三个接口的分工刻意不同：
- weak-quiz 不调模型：薄弱度是客观事实（掌握度 + 错次 + 连对次数），用 SQL 排序即可，
  零成本、毫秒级，模型在这里只会引入不稳定；
- explain 与 mock-paper 调中档模型：需要组织语言与命题，但输入被裁剪（前 30 段 / 最近 3 次作答），
  保证单次预算可控。
"""
import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.ai.router import generate_json
from app.core.budget import budget
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.crud import crud
from app.db.session import get_db
from app.models.models import Attempt, Chunk, Document, Question, QuestionBank
from app.routers.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["ai-study"])
_log = logging.getLogger(__name__)

# 连续答对达到此数即视为已稳固，不再进薄弱池
STREAK_SOLID = 3
# 单次薄弱练习上限（前端题量最多 50，但薄弱题一次给太多没有意义）
WEAK_MAX = 20
# 模拟卷：取材与题量上限
PAPER_CHUNKS = 30
PAPER_CHUNK_CHARS = 900
PAPER_MAX = 20

QTYPE_CN = {"single": "单选题", "multiple": "多选题", "fill": "填空题", "short": "简答题"}
_QTYPES = set(QTYPE_CN)


# ---------------------------------------------------------------------------
# 1) 薄弱点出题：纯 SQL，不调模型
# ---------------------------------------------------------------------------
class WeakQuizBody(BaseModel):
    count: int = 5
    bank_id: int | None = None


def _attempt_agg(user_id: int):
    """每题作答次数与错误次数（一次聚合，供排序与 reason 共用）。"""
    return (
        select(
            Attempt.question_id.label("qid"),
            func.count(Attempt.id).label("attempts"),
            func.coalesce(func.sum(case((Attempt.correct == 0, 1), else_=0)), 0).label("wrong_count"),
        )
        .where(Attempt.user_id == user_id)
        .group_by(Attempt.question_id)
        .subquery()
    )


def _streak_sub(user_id: int):
    """连续答对次数 = 最后一次答错之后的答对条数（从没答错则全部算）。

    相关子查询，让「已连续答对 3 次以上」的过滤留在 SQL 侧，而不是捞全表回 Python 数。
    """
    last_wrong_id = (
        select(func.max(Attempt.id))
        .where(Attempt.user_id == user_id,
               Attempt.question_id == Question.id,
               Attempt.correct == 0)
        .correlate(Question)
        .scalar_subquery()
    )
    return (
        select(func.count(Attempt.id))
        .where(Attempt.user_id == user_id,
               Attempt.question_id == Question.id,
               Attempt.correct == 1,
               Attempt.id > func.coalesce(last_wrong_id, 0))
        .correlate(Question)
        .scalar_subquery()
    )


def weak_quiz_stmt(user_id: int, count: int, bank_id: int | None = None):
    """薄弱题查询：掌握度升序 → 错次降序，排除已连续答对 STREAK_SOLID 次的题。

    没做过的题（mastery 默认 0）排在做过之后：它们是「没证据」，不该挤掉真正做错过的题。
    """
    agg = _attempt_agg(user_id)
    conds = [Question.user_id == user_id, _streak_sub(user_id) < STREAK_SOLID]
    if bank_id is not None:
        conds.append(Question.bank_id == bank_id)
    return (
        select(
            Question,
            func.coalesce(agg.c.attempts, 0).label("attempts"),
            func.coalesce(agg.c.wrong_count, 0).label("wrong_count"),
        )
        .outerjoin(agg, agg.c.qid == Question.id)
        .where(*conds)
        .order_by(
            case((func.coalesce(agg.c.attempts, 0) == 0, 1), else_=0),
            Question.mastery.asc(),
            func.coalesce(agg.c.wrong_count, 0).desc(),
            Question.id.asc(),
        )
        .limit(count)
    )


def weak_reason(q: Question, attempts: int, wrong_count: int) -> str:
    """一句话说明为什么选它，前端直接展示在题干下方。"""
    mastery = round(float(q.mastery or 0.0), 2)
    if attempts <= 0:
        return f"还没做过 · 掌握度 {mastery:.2f}"
    if wrong_count > 0:
        return f"错 {int(wrong_count)} 次 · 掌握度 {mastery:.2f}"
    return f"答对 {int(attempts)} 次仍未稳固 · 掌握度 {mastery:.2f}"


@router.post("/weak-quiz")
async def weak_quiz(body: WeakQuizBody, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """按薄弱点出题：不调用模型，纯 SQL 排序，返回与 /quiz/generate 同构的题目。"""
    count = max(1, min(int(body.count or 5), WEAK_MAX))
    rows = db.execute(weak_quiz_stmt(user.id, count, body.bank_id)).all()
    if not rows:
        return {"ok": True, "data": [],
                "message": "当前没有明显薄弱的题目，先去刷一轮"}

    data = [
        {
            "id": q.id, "stem": q.stem, "options": q.options, "qtype": q.qtype,
            "difficulty": q.difficulty, "bank_id": q.bank_id, "chapter": q.chapter,
            # 与 /quiz/generate 的差异只有这三项：前端可直接复用答题组件
            "reason": weak_reason(q, int(attempts), int(wrong)),
            "mastery": round(float(q.mastery or 0.0), 4),
            "wrong_count": int(wrong),
        }
        for q, attempts, wrong in rows
    ]
    return {"ok": True, "data": data}


# ---------------------------------------------------------------------------
# 2) 错题讲解：调模型，返回四段结构
# ---------------------------------------------------------------------------
class ExplainBody(BaseModel):
    question_id: int


class _ExplainOut(BaseModel):
    analysis: str = ""
    why_wrong: str = ""
    steps: list[str] = []
    related: list[str] = []


_EXPLAIN_SYSTEM = (
    "你是错题讲解助手。针对给定题目与用户的作答记录输出结构化讲解，只输出 JSON。要求：\n"
    "1) analysis 说明这道题考什么：考点名称 + 判断依据，不要复述题干；\n"
    "2) why_wrong 结合用户最近几次作答指出具体错因（错在哪一步、和哪个概念混淆）；"
    "没有作答记录时给这类题的通用错因；\n"
    "3) steps 是 3–6 步可直接照做的解题步骤，每步一句话，按顺序编号内容不要带序号；\n"
    "4) related 列 2–4 个关联知识点，供用户接着复习；\n"
    "5) 中文，准确，不编造题目之外的事实；公式用 $...$ 包裹。"
)


def _explain_user(q: Question, attempts: list[Attempt]) -> str:
    lines = [
        f"题型：{QTYPE_CN.get(q.qtype, q.qtype)}",
        f"题目：{q.stem}",
        f"选项：{json.dumps(q.options, ensure_ascii=False) if q.options else '（无选项）'}",
        f"参考答案：{q.answer or '（题库未给答案）'}",
    ]
    if q.chapter:
        lines.append(f"章节：{q.chapter}")
    if q.analysis:
        lines.append(f"题库自带解析：{json.dumps(q.analysis, ensure_ascii=False)[:1200]}")
    if attempts:
        lines.append("用户最近作答（新 → 旧）：")
        for a in attempts:
            mark = "答对" if a.correct else "答错"
            lines.append(f"- {mark}：{(a.user_answer or '未作答')[:120]}")
    else:
        lines.append("用户还没有作答记录，why_wrong 给这类题的通用错因。")
    return ('输出 JSON：{"analysis":"","why_wrong":"","steps":[""],"related":[""]}。\n'
            + "\n".join(lines))


@router.post("/explain")
async def explain(body: ExplainBody, user=Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """针对一道题生成讲解：考点 / 错因 / 步骤 / 关联知识点。"""
    q = db.get(Question, body.question_id)
    if q is None:
        raise APIError(ErrCode.COMMON_404, "题目不存在", 404)
    if q.user_id != user.id:
        raise APIError(ErrCode.AUTH_403, "无权访问该题", 403)

    attempts = list(db.scalars(
        select(Attempt).where(Attempt.user_id == user.id, Attempt.question_id == q.id)
        .order_by(Attempt.id.desc()).limit(3)))

    try:
        obj, res = await generate_json("mid", _EXPLAIN_SYSTEM, _explain_user(q, attempts),
                                       _ExplainOut, user_id=user.id, task_type="ai_explain")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        _log.warning("题目讲解生成失败 q=%s err=%s", q.id, e)
        raise APIError(ErrCode.AI_003, f"讲解生成失败：{e.message}，请稍后重试") from e
    except Exception as e:  # noqa: BLE001  网络等非契约异常同样不静默
        _log.warning("题目讲解异常 q=%s err=%s", q.id, e)
        raise APIError(ErrCode.AI_003, "讲解生成失败：模型调用异常，请稍后重试") from e

    # 成本账本：generate_json 只做预算拦截，记账由业务层补一笔
    try:
        budget.record(user.id, "ai_explain", res.prompt_tokens, res.completion_tokens,
                      settings.LLM_MID_MODEL)
    except Exception as e:  # noqa: BLE001
        _log.warning("讲解成本记账失败 q=%s err=%s", q.id, e)

    data = obj.model_dump()
    data.update({
        "question_id": q.id,
        "stem": q.stem,
        "answer": q.answer,
        "attempts": len(attempts),
    })
    return {"ok": True, "data": data}


# ---------------------------------------------------------------------------
# 3) 用我的资料出模拟卷：调模型 → 落库为题库
# ---------------------------------------------------------------------------
class MockPaperBody(BaseModel):
    document_id: int
    count: int = 10


class _PaperQuestion(BaseModel):
    stem: str = ""
    type: str = "single"
    options: list[str] = []
    answer: str = ""
    explanation: str = ""
    point: str = ""


class _PaperOut(BaseModel):
    title: str = ""
    instructions: str = ""
    questions: list[_PaperQuestion] = []


_PAPER_SYSTEM = (
    "你是命题老师。只依据给定资料片段出一份模拟卷，只输出 JSON。硬性要求：\n"
    "1) 每道题都必须能被片段内容直接支撑，不编造资料之外的知识；\n"
    "2) type 只用 single（四选一）/ multiple（多选）/ fill（填空）/ short（简答）；"
    "选项写满四个且只有一个正确时用 single，answer 写字母（多选写如 ABD），填空写原词；\n"
    "3) explanation 给 2–4 句解析，说明为什么选它、其余为什么错；"
    "point 写该题考查的知识点（不超过 12 字）；\n"
    "4) 题目按资料顺序由易到难排列，题干完整、可独立作答，不出现「如上文」这类指代。"
)


def _paper_user(title: str, count: int, blocks: list[str]) -> str:
    return (
        '输出 JSON：{"title":"","instructions":"","questions":[{"stem":"","type":"single",'
        '"options":["","","",""],"answer":"","explanation":"","point":""}]}。\n'
        f"资料标题：{title}\n需要出 {count} 道题。\n资料内容：\n" + "\n\n".join(blocks)
    )


def _owned_document(db: Session, document_id: int, user_id: int) -> Document:
    """带租户过滤取文档：别人的资料 403，不存在 404（与 questions.py 同口径）。"""
    doc = crud.get_document(db, document_id, user_id)
    if doc is not None:
        return doc
    if db.get(Document, document_id) is not None:
        raise APIError(ErrCode.AUTH_403, "无权访问该文档", 403)
    raise APIError(ErrCode.COMMON_404, "资料不存在", 404)


@router.post("/mock-paper")
async def mock_paper(body: MockPaperBody, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """用指定资料出模拟卷：读前 30 段 → 模型命题 → 落库为题库集 + 题目。"""
    count = max(1, min(int(body.count or 10), PAPER_MAX))
    doc = _owned_document(db, body.document_id, user.id)

    chunks = list(db.scalars(
        select(Chunk).where(Chunk.document_id == doc.id)
        .order_by(Chunk.chunk_index, Chunk.id).limit(PAPER_CHUNKS)))
    blocks: list[str] = []
    for c in chunks:
        text = (c.content or "").strip()
        if not text:
            continue
        page = f"（第 {c.page} 页）" if c.page else ""
        blocks.append(f"片段 {c.chunk_index + 1}{page}：{text[:PAPER_CHUNK_CHARS]}")
    if not blocks:
        raise APIError(ErrCode.COMMON_400, "这份资料还没有可用内容，请先解析后再出模拟卷")

    try:
        obj, res = await generate_json("mid", _PAPER_SYSTEM, _paper_user(doc.title, count, blocks),
                                       _PaperOut, max_tokens=6000,
                                       user_id=user.id, task_type="ai_mock")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        _log.warning("模拟卷生成失败 doc=%s err=%s", doc.id, e)
        raise APIError(ErrCode.AI_003, f"模拟卷生成失败：{e.message}，请稍后重试") from e
    except Exception as e:  # noqa: BLE001
        _log.warning("模拟卷生成异常 doc=%s err=%s", doc.id, e)
        raise APIError(ErrCode.AI_003, "模拟卷生成失败：模型调用异常，请稍后重试") from e

    try:
        budget.record(user.id, "ai_mock", res.prompt_tokens, res.completion_tokens,
                      settings.LLM_MID_MODEL)
    except Exception as e:  # noqa: BLE001
        _log.warning("模拟卷成本记账失败 doc=%s err=%s", doc.id, e)

    items = [x for x in (obj.questions or []) if (x.stem or "").strip()]
    if not items:
        raise APIError(ErrCode.AI_003, "模拟卷生成失败：模型没有返回题目，请稍后重试")

    title = f"AI 模拟卷 · {doc.title}"[:256]
    bank = QuestionBank(user_id=user.id, document_id=doc.id, name=title, subject="",
                        meta={"source": "ai_mock", "requested": count, "generated": len(items),
                              "instructions": (obj.instructions or "")[:500]})
    db.add(bank)
    db.flush()

    for i, it in enumerate(items, 1):
        qtype = (it.type or "single").strip().lower()
        if qtype not in _QTYPES:
            qtype = "single"
        stem = it.stem.strip()
        db.add(Question(
            user_id=user.id, document_id=doc.id, bank_id=bank.id,
            chapter="AI 模拟卷", section="", no=str(i), stem=stem,
            options=it.options or None, answer=(it.answer or "").strip(),
            # 复用题库五段解析结构，交卷回顾（QuizResult）可直接展示
            analysis={"point": (it.point or "").strip(), "approach": (it.explanation or "").strip(),
                      "steps": [], "pitfalls": [], "answer": (it.answer or "").strip()},
            qtype=qtype, difficulty="mid",
        ))
    db.commit()

    note = ""
    if len(items) != count:
        note = f"要 {count} 题，模型实际给出 {len(items)} 题，已按实际数量入库"
    return {"ok": True, "message": note, "data": {
        "bank_id": bank.id, "count": len(items), "title": title,
        "requested": count, "document_id": doc.id,
        "instructions": (obj.instructions or "").strip(), "note": note,
    }}
