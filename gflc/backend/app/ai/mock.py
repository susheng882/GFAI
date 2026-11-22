# -*- coding: utf-8 -*-
"""Mock 卡片生成：无 LLM Key 时用规则从文本抽取问答，保证流程可跑通。
产出质量是占位的，填 Key 后自动切换真实模型。"""
import re

from app.schemas.schemas import CardGenResult, CardItem

_SENT = re.compile(r"(?<=[。！？；!?;\n])\s*")
_PREFIX = re.compile(r"^[0-9]+[.、)]\s*")                 # 去掉句首编号
_HEADING = re.compile(r"^(第\s*[一二三四五六七八九十百零\d]+\s*[章节讲部分]|本页小结|小结|目录)")  # 标题/小结


def _clean(s: str) -> str:
    return _PREFIX.sub("", s.strip())


def mock_cards(text: str, n: int = 3, page: int = 0) -> CardGenResult:
    sentences = [_clean(s) for s in _SENT.split(text or "") if s.strip()]
    # 优先取正文实质句：去掉标题/小结，长度够
    body = [s for s in sentences if len(s) >= 15 and not _HEADING.match(s)]
    if len(body) < n:
        body += [s for s in sentences if len(s) >= 8 and s not in body and not _HEADING.match(s)]
    cards: list[CardItem] = []
    for s in body[:n]:
        head = s[:22] + ("…" if len(s) > 22 else "")
        cards.append(CardItem(question=f"请补全并回忆要点：{head}", answer=s, tag="自动抽取", page=page))
    if not cards and sentences:
        s = sentences[0]
        cards.append(CardItem(question=f"请回忆：{s[:22]}", answer=s, tag="自动抽取", page=page))
    return CardGenResult(cards=cards)
