# -*- coding: utf-8 -*-
"""重绘图统一版式库：680×960 画布 / 632 全宽内容区 / 固定字号（带 typography-v2 标记，跳过二次放大）。
所有区块以 X0=24、CW=632 严格对齐，杜绝旧图等比缩放造成的左右留白与文字压盖。"""
from _figlib import W, H, INK, GREY, RED, FONT, t, r, ln, path, icon, table, box, esc

X0, CW = 24, 632


def frame2(title, subtitle, body, legend, cap_cn, cap_en, tag="GFLC · 2026"):
    """与 _figlib.frame 同骨架，但字号固定、带幂等标记，字号治理脚本会跳过。"""
    head = [
        '<!-- typography-v2 -->',
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">',
        r(0, 0, W, H, "#FFFFFF", None, 0),
        r(8, 8, 664, 944, "#FFFFFF", INK, 1.4),
        r(16, 16, 648, 928, "none", "#C6DEE9", 0.5),
        '<defs><marker id="ar" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
        '<path d="M0,0 L7,3.5 L0,7 z" fill="#212121"/></marker>'
        '<marker id="arg" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
        '<path d="M0,0 L7,3.5 L0,7 z" fill="#83949E"/></marker></defs>',
        t(340, 40, title, 14, "middle", "bold"),
        t(340, 58, subtitle, 9.6, "middle", fill=GREY),
        ln(24, 66, 656, 66, INK, 0.8),
    ]
    if tag:
        head.append(t(656, 40, tag, 8.6, "end", fill=GREY))
    foot = [
        ln(24, 862, 656, 862, "#BED3DE", 0.6),
        t(24, 878, legend, 9.2, fill="#3C464D"),
        t(340, 906, cap_cn, 12.5, "middle", "bold"),
        t(340, 924, cap_en, 9.5, "middle", fill="#2B3237", style="italic"),
        "</svg>",
    ]
    return "\n".join(head + [body] + foot)


def sect(y, label, x=X0, size=10.5):
    return t(x, y, label, size, weight="bold")


def grid(y, widths, headers, rows, header_h=26, row_h=32, font=9.0, hf=9.0,
         aligns=None, fills=None, first_bold=True, x=X0):
    """全宽矩阵表包装，返回 (svg, 总高)。widths 之和应等于 CW。"""
    a = aligns or ["start"] * len(widths)
    s, h = table(x, y, widths, headers, rows, header_h=header_h, row_h=row_h,
                 font=font, header_font=hf, aligns=a, fills=fills, first_bold=first_bold)
    return s, h


def band(y, items, h=24, fs=9.0):
    from _figlib import PRIMARY
    o = [r(X0, y, CW, h, PRIMARY, PRIMARY, 0.6)]
    step = CW / len(items)
    for i, s in enumerate(items):
        o.append(t(X0 + 8 + i * step, y + h - 8, s, fs, weight="bold", fill="#FFFFFF"))
    return "\n".join(o)


def cards(y, h, items, gap=8, fill="#F3FAFD", tsize=9.6, lsize=8.6, with_icon=True):
    """横排卡片：items = [(标题, [行1, 行2, ...], 图标名), ...]"""
    n = len(items)
    w = (CW - gap * (n - 1)) / n
    o = []
    for i, (title, lines, ic) in enumerate(items):
        x = X0 + i * (w + gap)
        o.append(r(x, y, w, h, fill, INK, 0.8))
        if with_icon and ic:
            o.append(icon(ic, x + 7, y + 5, 0.62))
            tx = x + 26
        else:
            tx = x + 8
        o.append(t(tx, y + 17, title, tsize, weight="bold"))
        for k, s in enumerate(lines):
            o.append(t(x + 8, y + 33 + k * 13, s, lsize, fill="#3C464D"))
    return "\n".join(o)


def notebox(y, lines, h=None, fill="#FBFDFE", fs=9.0, title=None, icon_name="book"):
    h = h or (24 + 15 * len(lines))
    o = [r(X0, y, CW, h, fill, "#9AAAB3", 0.8, "5 3")]
    yy = y + 18
    if title:
        o.append(icon(icon_name, X0 + 9, y + 6, 0.6))
        o.append(t(X0 + 32, y + 18, title, 9.4, weight="bold"))
        yy = y + 35
    for i, s in enumerate(lines):
        o.append(t(X0 + 12, yy + i * 14, s, fs, fill="#2B3237"))
    return "\n".join(o), h


def nd(x, y, w, h, title, sub="", kind="proc", fill="#FFFFFF"):
    """标准流程图符号：term 圆角起止 / proc 矩形 / dec 菱形 / data 平行四边形。"""
    o = []
    if kind == "term":
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="1.2"/>')
    elif kind == "dec":
        o.append(f'<path d="M {x+w/2},{y} L {x+w},{y+h/2} L {x+w/2},{y+h} L {x},{y+h/2} Z" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
    elif kind == "data":
        o.append(f'<path d="M {x+9},{y} L {x+w},{y} L {x+w-9},{y+h} L {x},{y+h} Z" '
                 f'fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
    else:
        o.append(r(x, y, w, h, fill, INK, 1.1))
    lines = [title] + ([sub] if sub else [])
    for i, s in enumerate(lines):
        yy = y + h / 2 + 3.2 - (len(lines) - 1) * 5.4 + i * 10.8
        o.append(t(x + w / 2, yy, s, 9.2 if i == 0 else 8.4, "middle",
                   "bold" if i == 0 else "", INK if i == 0 else "#4E5A62"))
    return "\n".join(o)


def lane(y, h, label, sub, fill="#FFFFFF"):
    o = [r(X0, y, CW, h, fill, "#BED3DE", 0.7),
         r(X0, y, 78, h, "#FBFDFE", "#BED3DE", 0.7)]
    o.append(t(X0 + 6, y + 21, label, 9.2, weight="bold"))
    if sub:
        o.append(t(X0 + 6, y + 37, sub, 8.4, fill=GREY))
    return "\n".join(o)


def legend_flow(y):
    o = [r(X0, y, CW, 44, "#F3FAFD", "#9AAAB3", 0.8)]
    o.append(nd(X0 + 10, y + 10, 58, 24, "处理", kind="proc"))
    o.append(t(X0 + 74, y + 27, "处理步骤", 8.8))
    o.append(f'<path d="M {X0+158},{y+10} L {X0+184},{y+22} L {X0+158},{y+34} L {X0+132},{y+22} Z" '
             f'fill="#FFFFFF" stroke="{INK}" stroke-width="1"/>')
    o.append(t(X0 + 192, y + 27, "判定分支", 8.8))
    o.append(f'<rect x="{X0+258}" y="{y+10}" width="58" height="24" rx="12" '
             f'fill="#FFFFFF" stroke="{INK}" stroke-width="1"/>')
    o.append(t(X0 + 322, y + 27, "起止", 8.8))
    o.append(f'<path d="M {X0+366},{y+10} L {X0+412},{y+10} L {X0+402},{y+34} L {X0+356},{y+34} Z" '
             f'fill="#FFFFFF" stroke="{INK}" stroke-width="1"/>')
    o.append(t(X0 + 418, y + 27, "数据 / 存储　·　实线＝同步　虚线＝异步　朱红＝异常出口", 8.8, fill="#3C464D"))
    return "\n".join(o)


def arrow(x1, y1, x2, y2, dash="", color=INK, sw=1.0):
    return ln(x1, y1, x2, y2, color, sw, dash, True)


def elbow(d, color=INK, dash="", sw=1.0):
    return path(d, color, sw, dash, True)
