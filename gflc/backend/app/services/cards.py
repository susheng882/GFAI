# -*- coding: utf-8 -*-
"""卡片生成：无 Key 或 MOCK_AI 时走规则生成；否则逐块调轻档模型。
按 PDF 大纲把卡片归入「大卡包 → 章节卡包」，单块失败跳过、不卡整篇。"""
import asyncio
import hashlib
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.mock import mock_cards
from app.ai.prompts import CARD_SYSTEM, card_user
from app.ai.router import estimate_cost, generate_json
from app.core.config import settings
from app.core.errors import APIError
from app.models.models import Card, CardAnchor, CardDeck, Chunk, CostLedger, Document, Note
from app.schemas.schemas import CardGenResult

log = logging.getLogger(__name__)

LOG = logging.getLogger(__name__)

_UNSORTED = "未分章"


def _root_deck(db: Session, user_id: int, document_id: int) -> CardDeck:
    deck = db.scalars(
        select(CardDeck).where(CardDeck.user_id == user_id,
                               CardDeck.document_id == document_id,
                               CardDeck.kind == "root")
    ).first()
    if deck:
        return deck
    doc = db.get(Document, document_id)
    title = (doc.title if doc else "") or "我的卡包"
    if title.lower().endswith(".pdf"):
        title = title[:-4]
    deck = CardDeck(user_id=user_id, document_id=document_id, parent_id=None,
                    name=title[:200], kind="root", sort=0)
    db.add(deck)
    db.flush()
    return deck


def _chapter_deck(db: Session, user_id: int, root: CardDeck, name: str, sort: int) -> CardDeck:
    """章节卡包按名称复用，避免重复建包。"""
    name = (name or "").strip()[:200] or _UNSORTED
    deck = db.scalars(
        select(CardDeck).where(CardDeck.user_id == user_id,
                               CardDeck.parent_id == root.id,
                               CardDeck.name == name)
    ).first()
    if deck:
        return deck
    deck = CardDeck(user_id=user_id, document_id=root.document_id, parent_id=root.id,
                    name=name, kind="chapter", sort=sort)
    db.add(deck)
    db.flush()
    return deck


def _chapter_name(ch_heading: str, item_chapter: str) -> str:
    """优先用模型判定的章节，其次用切块时的标题路径（取最末一级作为章节名）。"""
    c = (item_chapter or "").strip()
    if c:
        return c
    h = (ch_heading or "").strip()
    if h:
        parts = [p for p in h.replace(">", "/").split("/") if p.strip()]
        return parts[-1].strip() if parts else h
    return _UNSORTED


async def generate_cards(db: Session, user_id: int, document_id: int, max_chunks: int = 10,
                         on_progress=None) -> int:
    chunks = list(db.scalars(
        select(Chunk).where(Chunk.document_id == document_id).order_by(Chunk.chunk_index).limit(max_chunks)
    ))
    use_mock = settings.MOCK_AI or not settings.LLM_API_KEY
    root = _root_deck(db, user_id, document_id)
    total = 0

    # 并发生成：原来逐块串行（27 张卡 117s，约 11s/块）。方舟账号并发上限 2，
    # 所以用信号量 2 路并发 —— 不改限流额度，只把等待时间叠起来。
    if not use_mock and len(chunks) > 1:
        from app.core.config import settings as _cfg
        limit = max(1, int(getattr(_cfg, "ARK_MAX_CONCURRENCY", 2) or 2))
        sem = asyncio.Semaphore(limit)
        done = 0

        async def _one(ch):
            async with sem:
                try:
                    obj, res = await generate_json(
                        "light", CARD_SYSTEM, card_user(ch.content, 3, ch.page, ch.heading_path),
                        CardGenResult)
                    return ch, obj.cards, res
                except APIError as e:
                    # 静默跳过会让「卡片数=0」无从排查，这里至少留一条可定位的日志
                    log.warning("成卡失败（chunk=%s）：%s %s", getattr(ch, "id", "?"),
                                getattr(e, "code", ""), getattr(e, "message", str(e)))
                    return ch, [], None

        results = await asyncio.gather(*[_one(ch) for ch in chunks])
        for i, (ch, items, res) in enumerate(results):
            done += 1
            if on_progress:
                on_progress(int(8 + 84 * done / max(1, len(chunks))))
            for item in items:
                deck = _chapter_deck(db, user_id, root, _chapter_name(ch.heading_path, item.chapter), i)
                db.add(Card(user_id=user_id, document_id=document_id, deck_id=deck.id, chunk_id=ch.id,
                            question=item.question, answer=item.answer, tag=item.tag,
                            page=item.page or ch.page, due_at=datetime.now(timezone.utc)))
            if res is not None:
                db.add(CostLedger(user_id=user_id, task_type="card_generate", model=settings.LLM_LIGHT_MODEL,
                                  prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
                                  cost_cny=estimate_cost(settings.LLM_LIGHT_MODEL,
                                                         res.prompt_tokens, res.completion_tokens)))
            total += len(items)
        db.commit()
        return total

    for i, ch in enumerate(chunks):
        if on_progress:
            on_progress(int(8 + 84 * (i + 1) / max(1, len(chunks))))
        res = None
        if use_mock:
            items = mock_cards(ch.content, 3, ch.page).cards
        else:
            try:
                obj, res = await generate_json(
                    "light", CARD_SYSTEM, card_user(ch.content, 3, ch.page, ch.heading_path), CardGenResult)
            except APIError:
                continue  # 单块失败跳过
            items = obj.cards
        for item in items:
            deck = _chapter_deck(db, user_id, root, _chapter_name(ch.heading_path, item.chapter), i)
            db.add(Card(user_id=user_id, document_id=document_id, deck_id=deck.id, chunk_id=ch.id,
                        question=item.question, answer=item.answer, tag=item.tag,
                        page=item.page or ch.page, due_at=datetime.now(timezone.utc)))
        if res is not None:
            db.add(CostLedger(user_id=user_id, task_type="card_generate", model=settings.LLM_LIGHT_MODEL,
                              prompt_tokens=res.prompt_tokens, completion_tokens=res.completion_tokens,
                              cost_cny=estimate_cost(settings.LLM_LIGHT_MODEL,
                                                     res.prompt_tokens, res.completion_tokens)))
        total += len(items)
    db.commit()
    return total


# ---------------------------------------------------------------------------
# B12：笔记↔卡片同源（方案 B 轻量锚点）
# 约定：正文里写「正面 :: 背面」即成卡行；不重写编辑器、不改 notes.content 原文。
# 状态：已同步（hash 一致） / 待同步（尚未生成卡片） / 源已改（hash 不一致）。
# ---------------------------------------------------------------------------
ANCHOR_SEP = " :: "                 # GFLC 自定语法，不抄竞品 == / >> / ^id / #card
ANCHOR_PREFIX = "gflc::ln::"        # 自定行锚前缀
MAX_ANCHOR_LINE = 2000              # 单行超过该长度跳过，防灌库
STATUS_SYNCED = "已同步"
STATUS_PENDING = "待同步"
STATUS_CHANGED = "源已改"


def anchor_hash(front: str, back: str) -> str:
    """成卡行摘要：只覆盖正反面，标题/行号等其它变化不影响卡片身份。"""
    return hashlib.sha256((front + "\x00" + back).encode("utf-8")).hexdigest()


def make_anchor_id(note_id: int, line_no: int) -> str:
    """GFLC 自定行锚：gflc::ln::<note_id>::<line_no>。"""
    return f"{ANCHOR_PREFIX}{note_id}::{line_no}"


def parse_anchor_lines(content: str | None, note_id: int,
                       user_id: int | None) -> dict:
    """纯函数：把整段 Markdown 解析为成卡行列表，不修改原文。

    - 1 基行号；只取第一次出现的 ` :: ` 作分隔，答案里再含分隔符则整体归入答案；
    - front/back 任一为空 → 跳过并记日志，不算成卡行；
    - 含分隔符但整行超 MAX_ANCHOR_LINE → 跳过并记日志，不静默丢弃；
    - 内容重复的不同行 → 各成独立锚点（唯一键 note_id+line_no），记 info 便于排查。

    返回 {"anchors": [...], "skipped_long": int, "skipped_empty": int}。
    """
    anchors: list[dict] = []
    skipped_long = skipped_empty = 0
    seen: dict[str, int] = {}
    if not content:
        LOG.info("成卡行解析：note_id=%s 正文为空，解析出 0 条锚点", note_id)
        return {"anchors": anchors, "skipped_long": 0, "skipped_empty": 0}

    for line_no, raw in enumerate(content.splitlines(), start=1):
        if ANCHOR_SEP not in raw:
            continue
        if len(raw) > MAX_ANCHOR_LINE:
            skipped_long += 1
            LOG.warning("成卡行解析跳过超长行：note_id=%s line_no=%s length=%s（上限 %s）",
                        note_id, line_no, len(raw), MAX_ANCHOR_LINE)
            continue
        front, back = raw.split(ANCHOR_SEP, 1)
        front, back = front.strip(), back.strip()
        if not front or not back:
            skipped_empty += 1
            LOG.warning("成卡行解析跳过空正面/空背面：note_id=%s line_no=%s", note_id, line_no)
            continue
        key = front + "\x00" + back
        if key in seen:
            LOG.info("成卡行内容重复：note_id=%s line_no=%s 与第 %s 行相同，按独立锚点处理",
                     note_id, line_no, seen[key])
        else:
            seen[key] = line_no
        anchors.append({
            "note_id": note_id,
            "user_id": user_id,
            "line_no": line_no,
            "anchor_id": make_anchor_id(note_id, line_no),
            "front": front,
            "back": back,
            "hash": anchor_hash(front, back),
        })
    if skipped_long or skipped_empty:
        LOG.warning("成卡行解析完成：note_id=%s 有效=%s 超长跳过=%s 空面跳过=%s",
                    note_id, len(anchors), skipped_long, skipped_empty)
    return {"anchors": anchors, "skipped_long": skipped_long,
            "skipped_empty": skipped_empty}


def sync_note_anchors(db: Session, note: Note, user_id: int | None = None) -> dict:
    """笔记保存路径调用：按当前正文增量同步 card_anchors（调用方负责 commit，本函数只 flush）。

    已存在且 hash 相同 → 不动；hash 不同 → 更新正反面/摘要（卡片状态随后标「源已改」）；
    正文里已删除的成卡行 → 删除锚点（已生成的卡片保留，仅解绑来源信息由删除笔记路径处理）。
    """
    uid = user_id if user_id is not None else note.user_id
    parsed = parse_anchor_lines(note.content, note.id, uid)
    incoming = {a["line_no"]: a for a in parsed["anchors"]}
    existing = {a.line_no: a for a in db.scalars(
        select(CardAnchor).where(CardAnchor.note_id == note.id)).all()}

    created = updated = removed = 0
    for line_no, item in incoming.items():
        old = existing.get(line_no)
        if old is None:
            db.add(CardAnchor(note_id=note.id, user_id=uid, line_no=line_no,
                              anchor_id=item["anchor_id"], front=item["front"],
                              back=item["back"], hash=item["hash"]))
            created += 1
        elif (old.hash != item["hash"] or old.front != item["front"]
              or old.back != item["back"] or old.anchor_id != item["anchor_id"]):
            old.front, old.back, old.hash = item["front"], item["back"], item["hash"]
            old.anchor_id, old.user_id = item["anchor_id"], uid
            updated += 1
    for line_no, old in existing.items():
        if line_no not in incoming:
            db.delete(old)
            removed += 1
    db.flush()
    stats = {"created": created, "updated": updated, "removed": removed,
             "skipped_long": parsed["skipped_long"],
             "skipped_empty": parsed["skipped_empty"], "total": len(incoming)}
    LOG.info("锚点同步完成：note_id=%s 新增=%s 更新=%s 移除=%s 有效行=%s",
             note.id, created, updated, removed, len(incoming))
    return stats


def collect_note_anchors(db: Session, note: Note, user_id: int) -> dict:
    """GET /notes/{id}/anchors 的数据组装：成卡行 + 逐条同步状态（含来源笔记标题）。"""
    rows = list(db.scalars(
        select(CardAnchor).where(CardAnchor.note_id == note.id,
                                 CardAnchor.user_id == user_id)
        .order_by(CardAnchor.line_no)).all())
    cards: dict[str, Card] = {}
    if rows:
        cards = {c.anchor_id: c for c in db.scalars(
            select(Card).where(Card.user_id == user_id,
                               Card.anchor_id.in_([a.anchor_id for a in rows]))).all()}

    items, counts = [], {STATUS_SYNCED: 0, STATUS_PENDING: 0, STATUS_CHANGED: 0}
    for a in rows:
        card = cards.get(a.anchor_id)
        if card is None:
            status = STATUS_PENDING
        elif (card.source_hash or "") == a.hash:
            status = STATUS_SYNCED
        else:
            status = STATUS_CHANGED
        counts[status] += 1
        items.append({
            "id": a.id, "note_id": a.note_id, "line_no": a.line_no,
            "anchor_id": a.anchor_id, "front": a.front, "back": a.back,
            "hash": a.hash, "status": status, "card_id": card.id if card else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })
    return {
        "note_id": note.id,
        "note_title": note.title or "",
        "items": items,
        "summary": {"total": len(items), "synced": counts[STATUS_SYNCED],
                    "pending": counts[STATUS_PENDING], "changed": counts[STATUS_CHANGED]},
    }


def apply_note_anchors(db: Session, note: Note, user_id: int) -> dict:
    """POST /notes/{id}/anchors/apply：显式把成卡行生成/更新为卡片。

    - 已有同 anchor_id 的卡：hash 一致跳过；hash 不一致才更新正反面与 source_hash，
      保留 fsrs_state/due_at/reps/lapses/mastery，不重置复习进度（用户显式点同步才更新）。
    - 重复 apply 不产生重复卡：同一 (user_id, anchor_id) 只认一张。
    """
    rows = list(db.scalars(
        select(CardAnchor).where(CardAnchor.note_id == note.id,
                                 CardAnchor.user_id == user_id)
        .order_by(CardAnchor.line_no)).all())
    result = {"note_id": note.id, "note_title": note.title or "",
              "created": 0, "updated": 0, "skipped": 0}
    if not rows:
        LOG.info("同步卡片：note_id=%s 无成卡行，无需处理", note.id)
        return result

    cards = {c.anchor_id: c for c in db.scalars(
        select(Card).where(Card.user_id == user_id,
                           Card.anchor_id.in_([a.anchor_id for a in rows]))).all()}
    deck = None
    for a in rows:
        card = cards.get(a.anchor_id)
        if card is None:
            if deck is None:
                root = _root_deck(db, user_id, note.document_id)
                deck = _chapter_deck(db, user_id, root, note.title or "笔记", 0)
            db.add(Card(user_id=user_id, document_id=note.document_id, deck_id=deck.id,
                        question=a.front, answer=a.back, tag="", page=0,
                        due_at=datetime.now(timezone.utc),
                        source_note_id=note.id, anchor_id=a.anchor_id, source_hash=a.hash))
            result["created"] += 1
        elif (card.source_hash or "") == a.hash:
            result["skipped"] += 1
        else:
            card.question, card.answer = a.front, a.back
            card.source_hash, card.source_note_id = a.hash, note.id
            result["updated"] += 1
    db.commit()
    LOG.info("同步卡片完成：note_id=%s 新增=%s 更新=%s 跳过=%s",
             note.id, result["created"], result["updated"], result["skipped"])
    return result
