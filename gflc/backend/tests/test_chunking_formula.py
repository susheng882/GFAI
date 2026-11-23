# -*- coding: utf-8 -*-
"""切片公式原子化回归：含 $...$ 的长文本切块后，每块里的 $ 必须成对。

本轮修的 bug：分句/重叠尾巴把 LaTeX 公式切成两半，前端渲染直接出错。
这是回归测试，改动 _pack / _split_sentences / _safe_tail 时必须保持全绿。
"""
import re

from app.services.chunking import _pack, _safe_tail, chunk_text

# 公式内部含中文分号/句号：分句器若不做占位保护就会在此切断
FORMULA_A = "$a_{1}；a_{2}。a_{3}=0$"
FORMULA_B = "$b_{1}=1。b_{2}=2$"


def _assert_all_paired(chunks: list[str]) -> None:
    """每块 $ 个数为偶数，且交替替换后不残留 $（即全部成对、无悬空定界符）。"""
    assert chunks
    for c in chunks:
        assert c.count("$") % 2 == 0, f"块内 $ 未成对：{c[:80]}"
        assert "$" not in re.sub(r"\$[^$\n]*\$", "", c), f"块内存在悬空 $：{c[:80]}"


def test_long_text_with_formulas_keeps_dollar_pairs():
    """40 句 × 两个公式的长文本（>800 字走分句 + 多块打包）→ 每块 $ 成对。"""
    para = "".join(f"第{i}步由公式{FORMULA_A}与{FORMULA_B}给出结论。" for i in range(40))
    assert len(para) > 800  # 确保走 _split_sentences 分句分支
    chunks = chunk_text(para, size=120, overlap=30)
    assert len(chunks) > 5
    _assert_all_paired(chunks)
    # 公式必须完整出现在某一块里，不能出现被截断的片段
    joined = "\n".join(chunks)
    assert FORMULA_A in joined
    assert FORMULA_B in joined


def test_pack_keeps_dollar_pairs_with_overlap():
    """直接压 _pack：块间重叠尾巴不得把公式切两半。"""
    units = ["A" * 60 + FORMULA_A, "B" * 60 + FORMULA_B, "C" * 60 + FORMULA_A]
    chunks = _pack(units, size=80, overlap=55)
    assert len(chunks) > 1
    _assert_all_paired(chunks)


def test_safe_tail_moves_cut_to_formula_start():
    """重叠起点若落在公式内部，前移到公式起点，尾巴以完整公式开头。"""
    text = "A" * 60 + FORMULA_A
    tail = _safe_tail(text, 8)  # 起点落在公式区间内
    assert tail == FORMULA_A
    _assert_all_paired([tail])


def test_formula_not_split_across_chunks():
    """只含公式的短文本不受影响：单块内公式原样保留。"""
    chunks = chunk_text(f"前提{FORMULA_A}成立。", size=300, overlap=100)
    assert chunks == [f"前提{FORMULA_A}成立。"]
    _assert_all_paired(chunks)


def test_plain_text_still_splits():
    """无公式文本的切块行为不被本次修复破坏（块数与长度约束保持）。"""
    text = "。".join(["这是一个测试句子" * 5 for _ in range(60)]) + "。"
    chunks = chunk_text(text, size=300, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 300 + 100 + 60 for c in chunks)
    _assert_all_paired(chunks)  # 无 $ 文本天然成对（0 个）
