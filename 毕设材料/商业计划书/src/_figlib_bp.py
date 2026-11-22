# -*- coding: utf-8 -*-
"""商业计划书图表册版式引擎：自动填满 680×960 全宽画布，区块严格网格对齐。

specs = [(区块标签, 类型, 参数), ...]
类型：grid 严格对齐矩阵表 / cards 横排卡片 / note 注释框 / band 阶段带 / raw 自绘片段
纵向空间自动分配给 grid 行高，保证「内容铺满、不留大片空白」且字号固定不会被二次放大。
"""
from _figlib import W, H, INK, GREY, RED, t, r, ln, icon, save
from _figlib2 import frame2, sect, grid, band, cards, notebox, X0, CW

Y0, YEND = 78, 852


def _measure(s):
    lab, kind, d = s
    head = 18 if lab else 0
    if kind == 'grid':
        return head + d.get('hh', 26) + (d.get('rh', 30) + d.get('_extra', 0)) * len(d['rows'])
    if kind == 'cards':
        return head + d.get('h', 96) + d.get('_extra2', 0)
    if kind == 'note':
        lines = d['lines']
        h = d.get('h') or (24 + 15 * len(lines) + (17 if d.get('title') else 0))
        return head + h
    if kind == 'band':
        return head + d.get('h', 24)
    if kind == 'raw':
        return head + d.get('h', 40)
    return 0


def compose(title, subtitle, legend, cap_cn, cap_en, specs):
    """按 specs 自动排布并铺满内容区，返回完整 SVG 文本。"""
    n = len(specs)
    gap = 10
    target = YEND - Y0

    base = sum(_measure(s) for s in specs) + gap * (n - 1)
    rest = target - base
    nrows = sum(len(s[2]['rows']) for s in specs if s[1] == 'grid')
    if nrows and rest > 0:
        ex = min(14.0, rest / nrows)
        for s in specs:
            if s[1] == 'grid':
                s[2]['_extra'] = ex
        rest -= ex * nrows
    if rest > 8:
        cs = [s for s in specs if s[1] == 'cards']
        if cs:
            for s in cs:
                s[2]['_extra2'] = min(30.0, rest / len(cs))
    if base > target:
        gap = 5

    body, y = [], Y0
    for lab, kind, d in specs:
        if lab:
            body.append(sect(y + 12, lab))
        cy = y + (18 if lab else 0)
        if kind == 'grid':
            s, _ = grid(cy, d['widths'], d['headers'], d['rows'],
                        header_h=d.get('hh', 26),
                        row_h=d.get('rh', 30) + d.get('_extra', 0),
                        font=d.get('font', 9.0), hf=d.get('hf', 9.0),
                        aligns=d.get('aligns'), fills=d.get('fills'),
                        first_bold=d.get('first_bold', True))
            body.append(s)
        elif kind == 'cards':
            body.append(cards(cy, d.get('h', 96) + d.get('_extra2', 0), d['items'],
                              gap=d.get('gap', 8), fill=d.get('fill', '#F3FAFD'),
                              tsize=d.get('tsize', 9.6), lsize=d.get('lsize', 8.8),
                              with_icon=d.get('with_icon', True)))
        elif kind == 'note':
            s, _ = notebox(cy, d['lines'], h=d.get('h'), fs=d.get('fs', 9.0),
                           title=d.get('title'), icon_name=d.get('icon', 'book'))
            body.append(s)
        elif kind == 'band':
            body.append(band(cy, d['items'], h=d.get('h', 24), fs=d.get('fs', 9.0)))
        elif kind == 'raw':
            v = d['svg']
            body.append(v(cy) if callable(v) else v)
        y = cy + (_measure((lab, kind, d)) - (18 if lab else 0)) + gap

    return frame2(title, subtitle, "\n".join(body), legend, cap_cn, cap_en)


# 常用列宽模板（和恒为 CW=632）
CW2 = [316, 316]
CW3 = [120, 256, 256]
CW3E = [160, 236, 236]
CW4 = [96, 168, 184, 184]
CW4E = [110, 150, 186, 186]
CW5 = [88, 120, 140, 140, 144]
CW5E = [96, 116, 140, 140, 140]
CW6 = [84, 102, 102, 112, 116, 116]


def L(*items):
    """把字符串列表转成 | 分隔的多行单元格。"""
    return "|".join(items)
