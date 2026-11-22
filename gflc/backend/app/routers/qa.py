# -*- coding: utf-8 -*-
"""问答：查询改写 → 多路召回 → 语义重排 → 知识库 / 联网 / 模型知识 三级降级。

流程：
1) query_opt.rewrite 生成带领域限定的检索查询（失败用原问题）；
2) 每条查询各召回 top_k=8，按 chunk_id 去重取最高分；
3) query_opt.rerank 语义重排，只保留 >=3 分的片段（最多 5 个）；
4) 命中知识库 → QA_SYSTEM 带页码作答；模型指出「与问题领域不符」且未限定文档 → 转联网；
5) 联网结果同样重排，全不相关则不硬答，改用模型自身学科知识（mode="model"）。
"""
import json
import logging
from types import SimpleNamespace
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.deepseek import chat, chat_stream
from app.ai.prompts import QA_SYSTEM, QA_WEB_SYSTEM, qa_user, qa_web_user
from app.core.budget import budget, estimate_tokens
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import Document, Note, QuestionBank
from app.routers.deps import get_current_user
from app.schemas.schemas import QaIn
from app.services import query_opt, websearch
from app.services.rag import retrieve, tokenize

router = APIRouter(prefix="/qa", tags=["qa"])
log = logging.getLogger(__name__)

_MIN_CTX_CHARS = 80      # 拼接片段太短视为未命中
_MAX_CTX_CHARS = 3500    # 送入模型的片段上限
_MIN_COVERAGE = 0.34     # 重排不可用时的关键词覆盖率下限（兜底老路径）
_TOP_K = 8               # 单查询召回数
_MAX_SNIPPETS = 5        # 重排后最多保留片段数
_MAX_ANSWER_TOKENS = 3200   # 强档模型含 reasoning token，2000 会被思辨吃光导致空回答
_MODEL_NOTE = "（以下为模型知识，未经资料佐证）"
_REFUSAL = ("未在资料中找到依据", "资料中没有", "资料未提及", "无法依据", "没有提供相关",
            "与问题领域不符", "领域不符", "检索结果与问题领域")
# 短问题更容易歧义（如「泰勒」→ 歌手），才值得花一次改写
_REWRITE_MAX_LEN = 10
# 模型爱在开头复述「领域判断」，属于内部思考泄漏，直接去掉
_PREAMBLE = re.compile(
    r"^(?:问题与|检索|这些片段|上述片段|片段|资料)[^\n]{0,50}(?:相关|相符|不符)[^\n]{0,40}[。.]\s*\n+")

# ---- 检索策略：auto（默认三级降级）/ knowledge / web / model / hybrid ----
_STRATEGIES = ("auto", "knowledge", "web", "model", "hybrid")
_NONE_TEXT = {
    "auto": "知识库与联网检索均未找到可靠依据，建议上传相关资料后再提问。",
    "knowledge": "未在资料中找到依据。可以换个问法，或改用联网 / 混合策略再试。",
    "web": "联网检索未找到与问题相关的可靠结果，可换用资料库或模型知识。",
    "hybrid": "资料与联网检索均未找到可靠依据，建议上传相关资料后再提问。",
    "model": "模型暂不可用，请稍后重试。",
}
_MODEL_SYSTEM = (QA_SYSTEM + "\n注意：本次没有可用检索片段，请直接用你的学科知识回答，"
                             "并在开头注明「（以下为模型知识，未经资料佐证）」。")
# 流式路径由服务端先吐标注，避免模型再写一遍
_MODEL_SYSTEM_STREAM = (QA_SYSTEM + "\n注意：本次没有可用检索片段，请直接用你的学科知识回答。"
                        "系统已在回答开头标注「（以下为模型知识，未经资料佐证）」，正文不要重复这句。")
# hybrid 需要同时区分两类材料的编号，prompts.py 里没有现成的，本文件内自带
_HYBRID_SYSTEM = (
    "你是严谨的学习问答助手。本次同时提供两类材料：【资料片段】来自用户知识库，【联网结果】来自公开网页。规则：\n"
    "1) 引用资料片段用 [n]，引用联网结果用 [Wn]，两套编号不要混用；\n"
    "2) 优先采用资料片段；两者冲突时以资料片段为准，并说明差异；\n"
    "3) 两类材料都不足以回答的部分可补充你的学科知识，但必须单独标注「以下为模型知识」；\n"
    "4) 充分展开：定义、要点/公式（LaTeX）、步骤、适用条件、易错点；\n"
    "5) 中文，结构清晰，不编造数据或文献。"
)


def _coverage(question: str, ctx: str) -> float:
    """兜底用：问题关键词有多少比例真的出现在检索片段里。"""
    tokens = [t for t in tokenize(question or "") if len(t) >= 2]
    if not tokens or not ctx:
        return 0.0
    hit = sum(1 for t in set(tokens) if t in ctx)
    return hit / len(set(tokens))


def _doc_titles(db: Session, user_id: int, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    rows = db.scalars(select(Document).where(Document.id.in_(ids), Document.user_id == user_id))
    return {d.id: d.title for d in rows}


async def _ask_llm(system: str, user_text: str, max_tokens: int = _MAX_ANSWER_TOKENS,
                   *, user_id: int | None = None, task_type: str = "qa") -> str:
    """一问一答的必经点：事前做预算拦截，事后补一笔账本（QA 原本不记 CostLedger）。"""
    est = estimate_tokens(system) + estimate_tokens(user_text) + max_tokens // 4
    budget.check(user_id, task_type, est)
    res = await chat(settings.LLM_STRONG_MODEL,
                     [{"role": "system", "content": system}, {"role": "user", "content": user_text}],
                     temperature=0.1, max_tokens=max_tokens, json_mode=False,
                     effort="low")  # V4 为推理模型，降低推理强度避免正文被 reasoning 吃光
    budget.record(user_id, task_type, res.prompt_tokens, res.completion_tokens,
                  settings.LLM_STRONG_MODEL)
    text = (res.text or "").strip()
    if not text:
        log.warning("qa empty answer: task=%s prompt_tokens=%s completion_tokens=%s max=%s",
                    task_type, res.prompt_tokens, res.completion_tokens, max_tokens)
    return _strip_preamble(text)


def _strip_preamble(answer: str) -> str:
    """去掉模型开头的「问题与检索结果同属数学领域，相关。」这类思考泄漏。"""
    if not answer:
        return answer
    cleaned = _PREAMBLE.sub("", answer, count=1).strip()
    return cleaned or answer


def _strip_leading_note(text: str) -> str:
    """去掉模型自己在开头写的「模型知识」标注（服务端会统一补一条，避免重复）。"""
    t = (text or "").lstrip()
    for _ in range(2):
        if t.startswith("（以下为模型知识") or t.startswith("以下为模型知识"):
            idx = t.find("）")
            t = t[idx + 1:].lstrip() if idx > 0 else ""
        else:
            break
    return t


def _excerpt(hits: list) -> str:
    """模型不可用时的原文兜底。"""
    parts = []
    for c in hits[:3]:
        text = (c.content or "").strip().replace("\n", " ")
        parts.append(f"· {text[:220]}")
    return "\n".join(parts)


def _kb_contexts(hits: list, prefix: list[tuple[int, str]] | None = None) -> list[tuple[int, str]]:
    """把片段拼成 (id, text) 列表，总长受 _MAX_CTX_CHARS 限制；prefix 用于笔记优先。"""
    contexts = list(prefix or [])
    used = sum(len(t) for _, t in contexts)
    for c in hits:
        text = (c.content or "").strip()
        if used + len(text) > _MAX_CTX_CHARS:
            text = text[:_MAX_CTX_CHARS - used]
        if text:
            contexts.append((c.id, text))
            used += len(text)
        if used >= _MAX_CTX_CHARS:
            break
    return contexts


def _kb_sources(db: Session, user_id: int, hits: list) -> list[dict]:
    titles = _doc_titles(db, user_id, {c.document_id for c in hits})
    return [{"chunk_id": c.id, "page": c.page or 0, "ts_start": c.ts_start,
             "kind": "knowledge", "title": titles.get(c.document_id, "")} for c in hits]


async def _answer_knowledge(db: Session, user_id: int, hits: list, question: str,
                            confidence: float) -> dict:
    contexts = _kb_contexts(hits)

    try:
        answer = await _ask_llm(QA_SYSTEM, qa_user(question, contexts),
                                user_id=user_id, task_type="qa_knowledge")
        if not answer:
            raise APIError(ErrCode.AI_003, "模型返回为空")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise  # 配额拦截必须让用户看见，不能降级成"模型暂不可用"
        log.warning("qa knowledge llm failed: %s", e)
        answer = "模型暂不可用，以下为原文摘录：\n" + _excerpt(hits)
    except Exception as e:  # 模型异常不打断问答，降级为原文摘录
        log.warning("qa knowledge llm failed: %s", e)
        answer = "模型暂不可用，以下为原文摘录：\n" + _excerpt(hits)

    return {"answer": answer, "sources": _kb_sources(db, user_id, hits), "refused": False,
            "mode": "knowledge", "confidence": confidence}


def _web_sources(results: list[dict]) -> list[dict]:
    return [{"title": r.get("title", ""), "url": r.get("url", ""), "kind": "web"} for r in results]


async def _answer_web(question: str, results: list[dict], confidence: float,
                      user_id: int | None = None) -> dict:
    try:
        answer = await _ask_llm(QA_WEB_SYSTEM, qa_web_user(question, results),
                                user_id=user_id, task_type="qa_web")
        if not answer:
            raise APIError(ErrCode.AI_003, "模型返回为空")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        log.warning("qa web llm failed: %s", e)
        lines = "\n".join(f"{i}. {r.get('title', '')}（{r.get('url', '')}）" for i, r in enumerate(results, 1))
        answer = ("模型暂不可用，以下是联网检索到的原始结果，可自行查阅：\n" + lines +
                  "\n\n提示：以上为公开网页摘要，结论请以原文为准。")
    except Exception as e:
        log.warning("qa web llm failed: %s", e)
        lines = "\n".join(f"{i}. {r.get('title', '')}（{r.get('url', '')}）" for i, r in enumerate(results, 1))
        answer = ("模型暂不可用，以下是联网检索到的原始结果，可自行查阅：\n" + lines +
                  "\n\n提示：以上为公开网页摘要，结论请以原文为准。")
    return {"answer": answer, "sources": _web_sources(results), "refused": False,
            "mode": "web", "confidence": confidence}


async def _answer_model(question: str, user_id: int | None = None) -> dict:
    """检索全不相关时的兜底：直接用模型学科知识作答，并显式标注未经佐证。"""
    try:
        answer = await _ask_llm(QA_WEB_SYSTEM,
                                f"问题：{question}\n\n（没有可用的检索资料，请直接依据学科知识作答。）",
                                user_id=user_id, task_type="qa_model")
        if not answer:
            raise APIError(ErrCode.AI_003, "模型返回为空")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        log.warning("qa model llm failed: %s", e)
        return {"answer": "模型暂不可用，且未检索到可靠资料，建议稍后重试或上传相关资料。",
                "sources": [], "refused": True, "mode": "none", "confidence": 0.0}
    except Exception as e:
        log.warning("qa model llm failed: %s", e)
        return {"answer": "模型暂不可用，且未检索到可靠资料，建议稍后重试或上传相关资料。",
                "sources": [], "refused": True, "mode": "none", "confidence": 0.0}
    if not answer.startswith(_MODEL_NOTE):
        answer = _MODEL_NOTE + "\n" + answer
    return {"answer": answer, "sources": [], "refused": False, "mode": "model",
            "confidence": 0.5}


def _hybrid_user(question: str, contexts: list[tuple[int, str]], results: list[dict]) -> str:
    kb_block = "\n".join(f"[{i + 1}] {c}" for i, (_, c) in enumerate(contexts)) or "（无）"
    web_blocks = [f"[W{i}] {r.get('title', '')}（{r.get('url', '')}）\n{(r.get('snippet') or '')[:600]}"
                  for i, r in enumerate(results, 1)]
    return (f"问题：{question}\n\n【资料片段】\n{kb_block}\n\n"
            f"【联网结果】\n" + ("\n\n".join(web_blocks) or "（无）"))


async def _answer_hybrid(db: Session, user_id: int, hits: list, results: list[dict],
                         question: str, confidence: float) -> dict:
    """资料 + 联网合并作答：sources 里两类都给，编号分别标注。"""
    contexts = _kb_contexts(hits)
    try:
        answer = await _ask_llm(_HYBRID_SYSTEM, _hybrid_user(question, contexts, results),
                                user_id=user_id, task_type="qa_hybrid")
        if not answer:
            raise APIError(ErrCode.AI_003, "模型返回为空")
    except APIError as e:
        if e.code in (ErrCode.QUOTA_001, ErrCode.QUOTA_002):
            raise
        log.warning("qa hybrid llm failed: %s", e)
        answer = ("模型暂不可用，以下为资料摘录与联网结果：\n" + _excerpt(hits) + "\n" +
                  "\n".join(f"{i}. {r.get('title', '')}（{r.get('url', '')}）"
                            for i, r in enumerate(results, 1)))
    except Exception as e:
        log.warning("qa hybrid llm failed: %s", e)
        answer = ("模型暂不可用，以下为资料摘录与联网结果：\n" + _excerpt(hits) + "\n" +
                  "\n".join(f"{i}. {r.get('title', '')}（{r.get('url', '')}）"
                            for i, r in enumerate(results, 1)))

    return {"answer": answer,
            "sources": _kb_sources(db, user_id, hits) + _web_sources(results),
            "refused": False, "mode": "hybrid", "confidence": confidence}


def _no_answer(strategy: str = "auto") -> dict:
    return {"answer": _NONE_TEXT.get(strategy, _NONE_TEXT["auto"]),
            "sources": [], "refused": True, "mode": "none", "confidence": 0.0}


async def _recall(db: Session, user_id: int, queries: list[str],
                  document_id: int | None) -> list:
    """多路召回并按 chunk_id 去重，保留最高分。"""
    merged: dict[int, tuple] = {}
    for q in queries[:3]:
        try:
            part = retrieve(db, user_id, q, document_id, top_k=_TOP_K)
        except Exception as e:
            log.warning("retrieve failed for %r: %s", q, e)
            continue
        for c, s in part:
            if c.id not in merged or s > merged[c.id][1]:
                merged[c.id] = (c, s)
    return [c for c, _ in sorted(merged.values(), key=lambda x: -x[1])[:_TOP_K]]


def _recall_notes(db: Session, user_id: int, queries: list[str], top_k: int = 2) -> list:
    """笔记正文也参与检索（用户手工整理的笔记往往比 PDF 更直接）。"""
    try:
        rows = db.scalars(select(Note).where(Note.user_id == user_id)
                          .order_by(Note.updated_at.desc()).limit(200)).all()
    except Exception:
        return []
    qwords = set()
    for q in queries[:3]:
        qwords.update(w for w in tokenize(q) if len(w) >= 2)
    if not qwords:
        return []
    scored = []
    for n in rows:
        text = f"{n.title or ''} {n.content or n.summary or ''}"
        if not text.strip():
            continue
        hit = sum(1 for w in qwords if w in text)
        if hit >= 2:  # 至少命中两个词，避免"矩阵"这类泛词误召
            scored.append((hit, n))
    scored.sort(key=lambda x: -x[0])
    out = []
    for hit, n in scored[:top_k]:
        body = (n.content or n.summary or "").strip()
        out.append({"id": f"note-{n.id}", "content": f"【笔记】{n.title}\n{body}",
                    "page": 0, "document_id": None, "ts_start": None,
                    "note_title": n.title or "", "hit": hit})
    return out


async def _web_or_model(question: str, queries: list[str], user_id: int | None = None) -> dict:
    """联网检索 → 重排 → 只保留相关条目；全不相关则用模型知识作答。"""
    query = queries[1] if len(queries) > 1 else (queries[0] if queries else question)
    try:
        results = websearch.search(query, top_k=5) or []
    except Exception as e:
        log.warning("websearch failed: %s", e)
        results = []

    if results:
        snippets = [f"{r.get('title', '')} {r.get('snippet', '')}" for r in results]
        try:
            scores = await query_opt.rerank(question, snippets)
        except Exception as e:
            log.warning("web rerank failed: %s", e)
            scores = []
        if len(scores) == len(results):
            picked = [(r, s) for r, s in zip(results, scores) if query_opt.is_relevant(s)][:3]
            if picked:
                conf = round(sum(s for _, s in picked) / len(picked) / 5, 2)
                return await _answer_web(question, [r for r, _ in picked], conf, user_id)
        # 重排全部不相关（或重排不可用）→ 不把无关结果硬塞给模型
    return await _answer_model(question, user_id)


def _domain_words(db: Session, user_id: int) -> list[str]:
    """从题库科目 / 文档标题抽领域词，用于同名词消歧（泰勒 → 泰勒 数学）。"""
    words: list[str] = []
    try:
        subs = db.scalars(select(QuestionBank.subject).where(
            QuestionBank.user_id == user_id).distinct()).all()
        words += [s.strip() for s in subs if s and s.strip()]
        for t in db.scalars(select(Document.title).where(
                Document.user_id == user_id).order_by(Document.id.desc()).limit(8)).all():
            base = re.sub(r"\.(pdf|docx|xlsx|xls|txt|md|mp4|wav|mp3)$", "", (t or "").strip(), flags=re.I)
            base = re.split(r"[-_·\s（(]", base)[0].strip()
            if 2 <= len(base) <= 12:
                words.append(base)
    except Exception:
        pass
    seen, out = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:6]


async def _pick_strategy(request: Request, default: str = "auto") -> str:
    """schemas 不改动：从原始请求体里读 strategy，读不到/非法一律回落 auto。"""
    try:
        raw = await request.json()
    except Exception:
        return default
    if not isinstance(raw, dict):
        return default
    value = str(raw.get("strategy") or default).strip().lower()
    return value if value in _STRATEGIES else default


async def _build_queries(db: Session, user_id: int, question: str) -> list[str]:
    try:
        domain = _domain_words(db, user_id)
        if len(question) < _REWRITE_MAX_LEN:
            queries = await query_opt.rewrite(question, domain)
        else:
            queries = query_opt.rewrite_with_domain(question, domain)
    except Exception as e:
        log.warning("rewrite failed, use raw question: %s", e)
        queries = [question]
    return queries or [question]


async def _kb_relevant(db: Session, user_id: int, question: str, queries: list[str],
                       document_id: int | None) -> tuple[list, float]:
    """召回 + 语义重排，只返回真正相关的片段；任何异常都当作"没命中"。"""
    try:
        hits = await _recall(db, user_id, queries, document_id)
    except Exception as e:
        log.warning("recall failed: %s", e)
        return [], 0.5
    # 笔记也属于「我的资料」，与 PDF/视频片段一起参与判定
    note_hits = []
    if not document_id:
        try:
            for i, n in enumerate(_recall_notes(db, user_id, queries)):
                note_hits.append(SimpleNamespace(id=-(i + 1), content=n["content"], page=0,
                                                 document_id=None, ts_start=None,
                                                 note_title=n.get("note_title", "")))
        except Exception as e:
            log.warning("note recall failed: %s", e)
    # 片段优先（PDF/视频上下文更完整），笔记补充在后，避免笔记挤掉长片段
    if note_hits:
        hits = list(hits) + note_hits

    if not hits:
        return [], 0.5

    cand = hits[:_TOP_K + len(note_hits)]
    scores: list[float] = []
    if len(cand) == 1:
        scores = [5.0 if _coverage(question, cand[0].content or "") >= _MIN_COVERAGE else 0.0]
    else:
        try:
            scores = await query_opt.rerank(question, [(c.content or "")[:400] for c in cand])
        except Exception as e:
            log.warning("kb rerank failed: %s", e)
            scores = []

    if scores and len(scores) == len(cand):
        confidence = round(min(1.0, sum(scores) / len(scores) / 5), 2)
        relevant = [h for h, s in sorted(zip(cand, scores), key=lambda x: -x[1])
                    if query_opt.is_relevant(s)][:_MAX_SNIPPETS]
        if relevant:
            return relevant, confidence
        # 全 0 分多半是重排超时/失败（与"确实不相关"不可区分）→ 继续走覆盖率兜底

    # 重排不可用 → 老路径：关键词覆盖率判定
    ctx_text = "\n".join((c.content or "") for c in cand)
    if len(ctx_text.strip()) >= _MIN_CTX_CHARS and _coverage(question, ctx_text) >= _MIN_COVERAGE:
        return cand[:3], max(confidence, 0.5)
    return [], confidence


async def _web_keep(question: str, queries: list[str], limit: int = 4) -> tuple[list[dict], float]:
    """联网检索 + 重排过滤，只保留相关条目。"""
    query = queries[1] if len(queries) > 1 else (queries[0] if queries else question)
    try:
        results = websearch.search(query, top_k=5) or []
    except Exception as e:
        log.warning("websearch failed: %s", e)
        return [], 0.0
    if not results:
        return [], 0.0

    try:
        scores = await query_opt.rerank(
            question, [(r.get("title", "") + " " + (r.get("snippet") or ""))[:380] for r in results])
    except Exception as e:
        log.warning("web rerank failed: %s", e)
        scores = []

    if scores and len(scores) == len(results):
        picked = [(r, s) for r, s in zip(results, scores) if query_opt.is_relevant(s)][:limit]
        if picked:
            conf = round(sum(s for _, s in picked) / len(picked) / 5, 2)
            return [r for r, _ in picked], conf
        if max(scores) > 0:  # 重排正常但都不相关 → 不硬塞
            return [], 0.0
    # 重排不可用（全 0/超时）→ 保守保留前 3（与旧流式路径一致）
    return results[:3], 0.35


def _none_text(strategy: str) -> str:
    return _NONE_TEXT.get(strategy, _NONE_TEXT["auto"])


@router.post("")
async def ask(body: QaIn, request: Request, user=Depends(get_current_user),
              db: Session = Depends(get_db)):
    strategy = await _pick_strategy(request)
    question = (body.question or "").strip()
    if not question:
        raise APIError(ErrCode.COMMON_400, "问题不能为空")

    # 模型知识：不检索、不联网，开头标注未经佐证
    if strategy == "model":
        data = await _answer_model(question, user.id)
        return {"ok": True, "data": {**data, "strategy": "model"}}

    queries = await _build_queries(db, user.id, question)

    kb_hits, confidence = [], 0.5
    if strategy in ("auto", "knowledge", "hybrid"):
        kb_hits, confidence = await _kb_relevant(db, user.id, question, queries, body.document_id)

    # 只查知识库：没命中就直说，绝不外扩联网
    if strategy == "knowledge":
        if not kb_hits:
            return {"ok": True, "data": {**_no_answer("knowledge"), "strategy": "knowledge"}}
        data = await _answer_knowledge(db, user.id, kb_hits, question, confidence)
        if any(k in data["answer"] for k in _REFUSAL):
            data = {**_no_answer("knowledge"), "sources": data["sources"]}
        return {"ok": True, "data": {**data, "strategy": "knowledge"}}

    # 只联网：跳过知识库，结果经重排过滤
    if strategy == "web":
        results, wconf = await _web_keep(question, queries)
        if not results:
            return {"ok": True, "data": {**_no_answer("web"), "strategy": "web"}}
        data = await _answer_web(question, results, wconf, user.id)
        return {"ok": True, "data": {**data, "strategy": "web"}}

    # 混合：两边都当上下文，sources 合并
    if strategy == "hybrid":
        results, wconf = await _web_keep(question, queries)
        if kb_hits and results:
            data = await _answer_hybrid(db, user.id, kb_hits, results, question, confidence)
        elif kb_hits:
            data = await _answer_knowledge(db, user.id, kb_hits, question, confidence)
            if any(k in data["answer"] for k in _REFUSAL):
                data = {**_no_answer("hybrid"), "sources": data["sources"]}
        elif results:
            data = await _answer_web(question, results, wconf, user.id)
        else:
            data = _no_answer("hybrid")
        return {"ok": True, "data": {**data, "strategy": "hybrid"}}

    # ---- auto：保持原有三级降级 ----
    if kb_hits:
        data = await _answer_knowledge(db, user.id, kb_hits, question, confidence)
        # 模型判定"资料领域不符/无依据"时，未限定文档才外扩到网络
        if not body.document_id and any(k in data["answer"] for k in _REFUSAL):
            data = await _web_or_model(question, queries, user.id)
            return {"ok": True, "data": {**data, "strategy": f"auto→{data.get('mode')}"}}
        return {"ok": True, "data": {**data, "strategy": "auto→knowledge"}}

    if body.document_id:  # 限定文档内检索时不外扩
        return {"ok": True, "data": {**_no_answer("auto"), "strategy": "auto→none"}}

    data = await _web_or_model(question, queries, user.id)
    return {"ok": True, "data": {**data, "strategy": f"auto→{data.get('mode')}"}}


@router.post("/stream")
async def ask_stream(body: QaIn, request: Request, user=Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """流式问答（NDJSON）。事件：status → sources → delta* →（可选 notice）→ done。

    首字节立即返回"正在检索"，避免用户干等；检索与回答都在生成器内执行，
    使用独立 Session（流式期间依赖注入的 Session 可能已关闭）。
    strategy 与 /qa 一致：auto / knowledge / web / model / hybrid。
    """
    strategy = await _pick_strategy(request)
    question = (body.question or "").strip()
    if not question:
        raise APIError(ErrCode.COMMON_400, "问题不能为空")
    user_id = user.id
    document_id = body.document_id

    async def gen():
        yield json.dumps({"type": "status", "hint": "正在检索你的资料…"}, ensure_ascii=False) + "\n"

        from app.db.session import SessionLocal
        system, user_text, mode, sources, confidence = "", "", "none", [], 0.0
        lead = ""  # 需要强制置顶的前缀（模型知识标注）
        sdb = SessionLocal()
        try:
            queries = await _build_queries(sdb, user_id, question)

            if strategy == "model":
                system, user_text = _MODEL_SYSTEM_STREAM, f"问题：{question}"
                mode, lead = "model", _MODEL_NOTE + "\n"
            else:
                need_kb = strategy in ("auto", "knowledge", "hybrid")
                kb_hits, confidence = ([], 0.5)
                if need_kb:
                    kb_hits, confidence = await _kb_relevant(
                        sdb, user_id, question, queries, document_id)
                notes_hit = _recall_notes(sdb, user_id, queries) if need_kb else []
                need_web = strategy in ("web", "hybrid") or (
                    strategy == "auto" and not kb_hits and not notes_hit and not document_id)
                web_results, wconf = ([], 0.0)
                if need_web:
                    web_results, wconf = await _web_keep(question, queries)

                note_prefix, note_sources = [], []
                for n in notes_hit:
                    note_prefix.append((0, n["content"]))
                    note_sources.append({"kind": "note", "title": n["note_title"], "page": 0})

                if strategy == "knowledge":
                    if kb_hits:
                        contexts = _kb_contexts(kb_hits, note_prefix)
                        sources = note_sources + _kb_sources(sdb, user_id, kb_hits)
                        system, user_text, mode = QA_SYSTEM, qa_user(question, contexts), "knowledge"
                        confidence = max(confidence, 0.7 if note_sources else 0.0)
                elif strategy == "web":
                    if web_results:
                        sources = _web_sources(web_results)
                        system, user_text = QA_WEB_SYSTEM, qa_web_user(question, web_results)
                        mode, confidence = "web", wconf
                elif strategy == "hybrid":
                    if kb_hits and web_results:
                        contexts = _kb_contexts(kb_hits, note_prefix)
                        sources = (note_sources + _kb_sources(sdb, user_id, kb_hits)
                                   + _web_sources(web_results))
                        system = _HYBRID_SYSTEM
                        user_text = _hybrid_user(question, contexts, web_results)
                        mode, confidence = "hybrid", max(confidence, 0.7)
                    elif kb_hits:
                        contexts = _kb_contexts(kb_hits, note_prefix)
                        sources = note_sources + _kb_sources(sdb, user_id, kb_hits)
                        system, user_text, mode = QA_SYSTEM, qa_user(question, contexts), "knowledge"
                        confidence = max(confidence, 0.7 if note_sources else 0.0)
                    elif web_results:
                        sources = _web_sources(web_results)
                        system, user_text = QA_WEB_SYSTEM, qa_web_user(question, web_results)
                        mode, confidence = "web", wconf
                else:  # auto：保持原有三级降级
                    if kb_hits or note_prefix:
                        contexts = _kb_contexts(kb_hits, note_prefix)
                        sources = note_sources + _kb_sources(sdb, user_id, kb_hits)
                        system, user_text, mode = QA_SYSTEM, qa_user(question, contexts), "knowledge"
                        confidence = max(confidence, 0.7 if note_sources else 0.0)
                    elif web_results:
                        sources = _web_sources(web_results)
                        system, user_text = QA_WEB_SYSTEM, qa_web_user(question, web_results)
                        mode, confidence = "web", wconf
                    else:
                        system, user_text = _MODEL_SYSTEM_STREAM, f"问题：{question}"
                        mode, lead = "model", _MODEL_NOTE + "\n"
        except Exception as e:  # 检索/重排异常都降级，不抛 500
            log.warning("qa stream prepare failed: %s", e)
            system, user_text, mode, sources = "", "", "none", []
        finally:
            sdb.close()

        label = f"auto→{mode}" if strategy == "auto" else strategy
        if not system:
            # 明确"没依据"：不联网、不编造，直接给结论
            msg = _none_text(strategy)
            yield json.dumps({"type": "sources", "mode": "none", "strategy": strategy,
                              "sources": [], "confidence": 0.0, "hint": "未找到可靠依据"},
                             ensure_ascii=False) + "\n"
            yield json.dumps({"type": "delta", "text": msg}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done", "full": msg}, ensure_ascii=False) + "\n"
            return

        yield json.dumps({"type": "sources", "mode": mode, "strategy": strategy,
                          "sources": sources, "confidence": confidence,
                          "hint": ("已检索 %d 条资料" % len(sources)) if sources else "无外部资料，改用学科知识",
                          }, ensure_ascii=False) + "\n"

        buf: list[str] = []   # 模型原始输出（判断 refusal / 估算长度）
        out: list[str] = []   # 实际下发的文本（done.full 用它，保证与 deltas 一致）
        msgs = [{"role": "system", "content": system}, {"role": "user", "content": user_text}]

        def _emit(text: str) -> str:
            if text:
                out.append(text)
            return json.dumps({"type": "delta", "text": text}, ensure_ascii=False) + "\n"

        decided, pending = not lead, []
        try:
            async for piece in chat_stream(settings.LLM_MID_MODEL, msgs,
                                           temperature=0.1, max_tokens=_MAX_ANSWER_TOKENS, effort="low"):
                buf.append(piece)
                if not decided:
                    # 先攒一小段，剥掉模型自带的标注后再补服务端的，避免出现两条
                    pending.append(piece)
                    joined = "".join(pending)
                    if len(joined.lstrip()) < 26 and "\n" not in joined:
                        continue
                    head = _strip_leading_note(joined)
                    pending, decided = [], True
                    yield _emit(lead)
                    if head:
                        yield _emit(head)
                    continue
                if piece:
                    yield _emit(piece)
            if pending:
                head = "".join(pending)
                pending = []
                if lead and not decided:
                    head = _strip_leading_note(head)
                    yield _emit(lead)
                if head:
                    yield _emit(head)
            # 资料命中了但内容不对路 → 仅 auto 用学科知识补答（显式 knowledge 不外扩）
            now_text = "".join(buf)
            if strategy == "auto" and mode == "knowledge" and any(k in now_text for k in _REFUSAL):
                yield json.dumps({"type": "notice",
                                  "text": "\n\n_（检索到的资料与问题不符，下面用学科知识补充）_\n\n"},
                                 ensure_ascii=False) + "\n"
                sys2 = (QA_SYSTEM + "\n注意：本次检索片段与问题领域不符，请直接依据你的学科知识完整作答，"
                        "给出定义、公式（LaTeX）、条件与例子，不要提及检索片段。")
                async for piece in chat_stream(
                        settings.LLM_STRONG_MODEL,
                        [{"role": "system", "content": sys2},
                         {"role": "user", "content": f"问题：{question}"}],
                        temperature=0.1, max_tokens=_MAX_ANSWER_TOKENS, effort="low"):
                    buf.append(piece)
                    yield _emit(piece)
            if len("".join(buf)) < 220 and mode in ("knowledge", "model"):
                yield json.dumps({"type": "notice",
                                  "text": "\n\n_（内容偏简，正在用更强的模型补充…）_\n\n"},
                                 ensure_ascii=False) + "\n"
                async for piece in chat_stream(settings.LLM_STRONG_MODEL, msgs,
                                               temperature=0.1, max_tokens=_MAX_ANSWER_TOKENS, effort="low"):
                    buf.append(piece)
                    yield _emit(piece)
        except Exception as e:
            log.warning("qa stream failed: %s", e)
            yield json.dumps({"type": "error", "message": str(e)[:160]}, ensure_ascii=False) + "\n"
        # 流式路径也要记账，否则成本看板会失真
        try:
            from app.ai.router import estimate_cost
            from app.models.models import CostLedger
            from app.db.session import SessionLocal

            tok_in = int((len(system) + len(user_text)) / 1.5)
            tok_out = int(len("".join(buf)) / 1.5)
            ldb = SessionLocal()
            ldb.add(CostLedger(user_id=user_id, task_type="qa_stream", model=settings.LLM_MID_MODEL,
                               prompt_tokens=tok_in, completion_tokens=tok_out,
                               cost_cny=estimate_cost(settings.LLM_MID_MODEL, tok_in, tok_out)))
            ldb.commit()
            ldb.close()
        except Exception as e:
            log.warning("qa stream cost record failed: %s", e)

        yield json.dumps({"type": "done", "full": "".join(out), "strategy": label},
                         ensure_ascii=False) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/suggest")
async def suggest(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """示例问题：基于用户文档标题拼接，不调模型。"""
    docs = list(db.scalars(select(Document).where(Document.user_id == user.id)
                           .order_by(Document.id.desc()).limit(2)))
    questions: list[str] = []
    for d in docs:
        title = (d.title or "").rsplit(".", 1)[0].strip()[:24]
        if not title:
            continue
        questions.append(f"《{title}》的核心内容是什么？")
        questions.append(f"《{title}》里有哪些重点概念？")

    for q in ("帮我梳理这份资料的知识框架", "间隔重复为什么能提升记忆效率？",
              "如何安排一周的复习计划？", "这个知识点在实际中怎么用？"):
        if len(questions) >= 4:
            break
        questions.append(q)
    return {"ok": True, "data": questions[:4]}
