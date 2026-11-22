# -*- coding: utf-8 -*-
"""切片算法单测（纯函数，不依赖 DB / 外部服务）。"""
from app.services.chunking import chunk_pages, chunk_text


def test_empty_returns_empty():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_single_chunk():
    chunks = chunk_text("这是一个很短的段落。", size=300, overlap=100)
    assert len(chunks) == 1
    assert "很短" in chunks[0]


def test_long_text_split_with_limit():
    text = "。".join(["这是一个测试句子" * 5 for _ in range(60)]) + "。"
    chunks = chunk_text(text, size=300, overlap=100)
    assert len(chunks) > 1
    # 每块不应远超目标长度（允许重叠与单句溢出）
    assert all(len(c) <= 300 + 100 + 60 for c in chunks)


def test_overlap_present():
    text = "".join([f"第{i}段内容。" for i in range(200)])
    chunks = chunk_text(text, size=100, overlap=30)
    assert len(chunks) > 1
    # 相邻块应存在一定重叠
    assert chunks[0][-10:] in chunks[1] or chunks[1][:10] in chunks[0]


def test_chunk_pages_keep_page_number():
    pages = [(1, "第一页内容。" * 40), (2, "第二页内容。" * 40)]
    out = chunk_pages(pages, size=120, overlap=20)
    assert out
    assert {c["page"] for c in out} == {1, 2}
    assert all("content" in c and c["content"] for c in out)
