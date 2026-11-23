# -*- coding: utf-8 -*-
"""笔记成卡行解析单测：parse_anchor_lines 纯函数，不依赖 DB。

语法：正文里一行写作「正面 :: 背面」即成卡行（GFLC 自定，不抄竞品）。
"""
from app.services.cards import MAX_ANCHOR_LINE, anchor_hash, parse_anchor_lines


def test_basic_lines_parsed():
    """两行合法成卡行 → 2 条锚点，字段完整且行号为 1 基。"""
    out = parse_anchor_lines("正面一 :: 背面一\n正面二 :: 背面二", 7, 3)
    anchors = out["anchors"]
    assert len(anchors) == 2
    assert out["skipped_long"] == 0 and out["skipped_empty"] == 0
    first = anchors[0]
    assert {"note_id", "user_id", "line_no", "anchor_id", "front", "back", "hash"} <= set(first)
    assert first["note_id"] == 7 and first["user_id"] == 3
    assert (first["front"], first["back"]) == ("正面一", "背面一")
    assert first["line_no"] == 1 and anchors[1]["line_no"] == 2
    assert first["anchor_id"] == "gflc::ln::7::1"
    assert first["hash"] == anchor_hash("正面一", "背面一")
    assert first["hash"] != anchors[1]["hash"]


def test_line_no_is_one_based_with_leading_blanks():
    """前面有空行时行号仍按原文 1 基计数，锚点 id 与实际行号一致。"""
    out = parse_anchor_lines("\n\n标题\n问题 :: 答案", 1, 1)
    anchors = out["anchors"]
    assert len(anchors) == 1
    assert anchors[0]["line_no"] == 4
    assert anchors[0]["anchor_id"] == "gflc::ln::1::4"


def test_empty_front_or_back_skipped():
    """空正面 / 空背面 / 全空白 都跳过，只计 skipped_empty，不产生锚点。"""
    content = " :: 只有答案\n只有问题 :: \n   ::   \n正常 :: 成卡"
    out = parse_anchor_lines(content, 2, 9)
    assert out["skipped_empty"] == 3
    assert out["skipped_long"] == 0
    assert len(out["anchors"]) == 1
    assert out["anchors"][0]["front"] == "正常"


def test_long_line_skipped():
    """单行超过 MAX_ANCHOR_LINE（2000）跳过并计数；恰好 2000 字仍保留。"""
    # 1000 + " :: "(4) + 996 = 2000，正好等于上限 → 保留
    ok_line = "f" * 1000 + " :: " + "b" * (MAX_ANCHOR_LINE - 1004)
    assert len(ok_line) == MAX_ANCHOR_LINE
    # 再多 1 字 → 超限跳过
    too_long = "f" * 1000 + " :: " + "b" * (MAX_ANCHOR_LINE - 1003)
    out = parse_anchor_lines(ok_line + "\n" + too_long, 5, 5)
    assert out["skipped_long"] == 1
    assert len(out["anchors"]) == 1
    assert out["anchors"][0]["line_no"] == 1


def test_duplicate_lines_become_separate_anchors():
    """内容重复的不同行各成独立锚点（唯一键是 note_id + line_no），hash 相同。"""
    out = parse_anchor_lines("同一题 :: 同一答\n同一题 :: 同一答", 4, 4)
    anchors = out["anchors"]
    assert len(anchors) == 2
    assert [a["line_no"] for a in anchors] == [1, 2]
    assert anchors[0]["anchor_id"] != anchors[1]["anchor_id"]
    assert anchors[0]["hash"] == anchors[1]["hash"]


def test_line_without_separator_ignored():
    """无分隔符的行是普通正文，既不产锚点也不计入任何跳过项。"""
    content = "# 标题\n普通段落，没有分隔符\n另一个普通段落"
    out = parse_anchor_lines(content, 1, 1)
    assert out["anchors"] == []
    assert out["skipped_long"] == 0
    assert out["skipped_empty"] == 0


def test_split_on_first_separator_only():
    """只按第一次出现的分隔符切分，背面里再含分隔符整体归入答案。"""
    out = parse_anchor_lines("问题 :: 答案 :: 补充说明", 1, 1)
    assert len(out["anchors"]) == 1
    assert out["anchors"][0]["front"] == "问题"
    assert out["anchors"][0]["back"] == "答案 :: 补充说明"


def test_empty_content_returns_empty():
    """空 / None 正文直接返回空结果，不抛异常。"""
    for content in ("", None):
        out = parse_anchor_lines(content, 1, 1)
        assert out == {"anchors": [], "skipped_long": 0, "skipped_empty": 0}
