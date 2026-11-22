# -*- coding: utf-8 -*-
"""学术图表统一图形库：A4 比例 680×960 标准画布、严格对齐矩阵表、矢量图标、泳道流程图、统计图表。"""
import html

W, H = 680, 960
INK = "#212121"       # 深墨 · 正文与外框（参考图底色）
PRIMARY = "#1B6E9C"   # 主蓝 · 表头 / 区块标签 / 主标题（亮蓝降明度派生）
ACCENT = "#8ED7FE"    # 亮蓝 · 强调 / 箭头 / 色块
YELLOW = "#F4FF8D"    # 亮黄 · 关键数据高亮
CREAM = "#F8EDB8"     # 奶油黄 · 次级浅底
GOLD = "#C9A227"      # 深黄 · 亮黄底上的文字
PAPER = "#FFFFFF"     # 白纸底
GREY = "#55626A"
LIGHT = "#E4F3FB"
RED = "#B4472F"
FONT = "'Noto Serif SC','Source Han Serif SC','SimSun',serif"


def esc(s):
    return html.escape(str(s), quote=False)


def t(x, y, s, size=8.2, anchor="start", weight="", fill=INK, style="", ls=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    b = f' font-weight="{weight}"' if weight else ""
    c = f' font-style="{style}"' if style else ""
    d = f' letter-spacing="{ls}"' if ls else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"{a}{b}{c}{d}>'
            f'{esc(s)}</text>')


def r(x, y, w, h, fill="#FFFFFF", stroke=INK, sw=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    s = "none" if stroke is None else stroke
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{s}" stroke-width="{sw}"{d}/>')


def ln(x1, y1, x2, y2, stroke=INK, sw=1, dash="", arrow=False):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    a = ' marker-end="url(#ar)"' if arrow else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}{a}/>')


def path(d, stroke=INK, sw=1, dash="", arrow=False, fill="none"):
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    a = ' marker-end="url(#ar)"' if arrow else ""
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dd}{a}/>'


def circ(cx, cy, rad, fill=INK, stroke=INK, sw=0.8):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


# ---------- 矢量图标（24×24 网格，黑白线条） ----------
_ICONS = {
    "book": '<path d="M2 5 C6 3 9 4 12 6 C15 4 18 3 22 5 L22 19 C18 17 15 18 12 20 C9 18 6 17 2 19 Z"/><path d="M12 6 L12 20"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 6 L12 12 L16 15"/>',
    "brain": '<path d="M12 5 C9 2 5 3 4 7 C2 9 3 13 5 14 C4 18 7 21 10 20 L12 21 L14 20 C17 21 20 18 19 14 C21 13 22 9 20 7 C19 3 15 2 12 5 Z"/><path d="M12 5 L12 21 M6 10 L9 10 M15 10 L18 10"/>',
    "card": '<rect x="3" y="4" width="18" height="16" rx="1"/><path d="M6 9 L18 9 M6 13 L18 13 M6 17 L13 17"/>',
    "chart": '<path d="M3 20 L21 20 M5 20 L5 13 M10 20 L10 7 M15 20 L15 10 M20 20 L20 4"/>',
    "gear": '<circle cx="12" cy="12" r="4"/><path d="M12 2 L12 5 M12 19 L12 22 M2 12 L5 12 M19 12 L22 12 M5 5 L7 7 M17 17 L19 19 M19 5 L17 7 M7 17 L5 19"/>',
    "cloud": '<path d="M6 18 C3 18 2 15 4 13 C3 10 6 8 9 9 C10 5 16 5 17 9 C21 9 22 13 20 15 C21 17 19 18 18 18 Z"/>',
    "shield": '<path d="M12 2 L21 6 L21 12 C21 17 17 21 12 22 C7 21 3 17 3 12 L3 6 Z"/><path d="M8 12 L11 15 L16 9"/>',
    "loop": '<path d="M20 9 A8 8 0 0 0 5 8 M4 4 L4 9 L9 9 M4 15 A8 8 0 0 0 19 16 M20 20 L20 15 L15 15"/>',
    "video": '<rect x="2" y="5" width="20" height="14" rx="1"/><path d="M10 9 L16 12 L10 15 Z"/>',
    "doc": '<path d="M5 2 L15 2 L19 6 L19 22 L5 22 Z"/><path d="M15 2 L15 6 L19 6 M8 11 L16 11 M8 15 L16 15 M8 19 L13 19"/>',
    "quiz": '<circle cx="12" cy="12" r="9"/><path d="M9 9 C9 6 15 6 15 9 C15 12 12 12 12 15"/><circle cx="12" cy="18.5" r="0.8" fill="#212121"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5" fill="#212121"/>',
    "db": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5 L4 19 C4 21 20 21 20 19 L20 5 M4 12 C4 14 20 14 20 12"/>',
    "coin": '<circle cx="12" cy="12" r="9"/><path d="M8 7 L12 12 L16 7 M12 12 L12 18 M8 13 L16 13 M8 16 L16 16"/>',
    "flow": '<rect x="2" y="3" width="7" height="5" rx="1"/><rect x="15" y="3" width="7" height="5" rx="1"/><rect x="8.5" y="16" width="7" height="5" rx="1"/><path d="M5.5 8 L5.5 12 L12 12 L12 16 M18.5 8 L18.5 12 L12 12"/>',
    "eye": '<path d="M2 12 C5 7 9 5 12 5 C15 5 19 7 22 12 C19 17 15 19 12 19 C9 19 5 17 2 12 Z"/><circle cx="12" cy="12" r="3"/>',
    "layers": '<path d="M12 2 L22 7 L12 12 L2 7 Z M2 12 L12 17 L22 12 M2 17 L12 22 L22 17"/>',
    "check": '<rect x="3" y="3" width="18" height="18" rx="1"/><path d="M7 12 L11 16 L17 8"/>',
    "warn": '<path d="M12 2 L22 21 L2 21 Z"/><path d="M12 9 L12 15"/><circle cx="12" cy="18" r="0.9" fill="#212121"/>',
}


def icon(name, x, y, s=0.85, color=INK):
    g = _ICONS.get(name, _ICONS["card"])
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({s})" fill="none" '
            f'stroke="{color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">{g}</g>')


# ---------- 标准画布 ----------
def frame(title, subtitle, body, legend, cap_cn, cap_en, tag=""):
    head = [
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">',
        f'<rect x="0" y="0" width="{W}" height="{H}" fill="#FFFFFF"/>',
        r(8, 8, 664, 944, "#FFFFFF", INK, 1.4),
        r(16, 16, 648, 928, "none", "#C6DEE9", 0.5),
        '<defs><marker id="ar" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
        '<path d="M0,0 L7,3.5 L0,7 z" fill="#212121"/></marker>'
        '<marker id="arg" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
        '<path d="M0,0 L7,3.5 L0,7 z" fill="#83949E"/></marker></defs>',
        t(340, 40, title, 14, "middle", "bold"),
        t(340, 58, subtitle, 9, "middle", fill=GREY),
        ln(24, 66, 656, 66, INK, 0.8),
    ]
    if tag:
        head.append(t(656, 40, tag, 7.6, "end", fill=GREY))
    foot = [
        ln(24, 862, 656, 862, "#BED3DE", 0.6),
        t(24, 878, legend, 8.2, fill="#3C464D"),
        t(340, 906, cap_cn, 12.5, "middle", "bold"),
        t(340, 924, cap_en, 9.5, "middle", fill="#2B3237", style="italic"),
        "</svg>",
    ]
    return "\n".join(head + [body] + foot)


# ---------- 严格对齐矩阵表 ----------
def table(x, y, widths, headers, rows, header_h=30, row_h=44, font=8.0,
          header_font=7.8, first_bold=True, zebra=True, fills=None, aligns=None):
    """单元格内容可为 str 或 list[str]（多行）。返回 (svg, 总高度)。"""
    out = []
    total = sum(widths)
    cx = [x]
    for w in widths:
        cx.append(cx[-1] + w)
    aligns = aligns or ["start"] + ["middle"] * (len(widths) - 1)
    # 表头
    out.append(r(x, y, total, header_h, PRIMARY, PRIMARY, 0.8))
    for j, hcell in enumerate(headers):
        lines = hcell.split("|") if isinstance(hcell, str) else hcell
        for k, s in enumerate(lines):
            yy = y + header_h / 2 + 4 - (len(lines) - 1) * 5.5 + k * 11
            ax = (cx[j] + 6) if aligns[j] == "start" else ((cx[j] + cx[j + 1]) / 2)
            out.append(t(ax, yy, s, header_font, aligns[j], "bold", "#FFFFFF"))
    for j in range(1, len(widths)):
        out.append(ln(cx[j], y, cx[j], y + header_h, "#FFFFFF", 0.4))
    # 数据行
    yy = y + header_h
    for i, row in enumerate(rows):
        h = row_h[i] if isinstance(row_h, (list, tuple)) else row_h
        fill = (fills[i] if fills and i < len(fills) else None) or (LIGHT if zebra and i % 2 else PAPER)
        out.append(r(x, yy, total, h, fill, "#9AAAB3", 0.6))
        for j in range(1, len(widths)):
            out.append(ln(cx[j], yy, cx[j], yy + h, "#C6DEE9", 0.4))
        for j, cell in enumerate(row):
            lines = cell.split("|") if isinstance(cell, str) else cell
            n = len(lines)
            for k, s in enumerate(lines):
                ly = yy + h / 2 + 3 - (n - 1) * 5.2 + k * 10.4
                ax = (cx[j] + 6) if aligns[j] == "start" else ((cx[j] + cx[j + 1]) / 2)
                bold = "bold" if (first_bold and j == 0) else ""
                out.append(t(ax, ly, s, font if j else font + 0.4, aligns[j], bold))
        yy += h
    return "\n".join(out), yy - y


def box(x, y, w, h, title, lines=(), fill="#FFFFFF", sw=1, icon_name=None, tsize=9, lsize=7.8):
    out = [r(x, y, w, h, fill, INK, sw)]
    if icon_name:
        out.append(icon(icon_name, x + 8, y + 6, 0.72))
        tx = x + 27
    else:
        tx = x + 9
    out.append(t(tx, y + 17, title, tsize, weight="bold"))
    for i, s in enumerate(lines):
        out.append(t(x + 9, y + 32 + i * 12, s, lsize, fill="#3C464D"))
    return "\n".join(out)


def diamond(cx, cy, w, h, lines, fill="#FFFFFF"):
    out = [f'<path d="M {cx},{cy - h/2} L {cx + w/2},{cy} L {cx},{cy + h/2} L {cx - w/2},{cy} Z" '
           f'fill="{fill}" stroke="{INK}" stroke-width="1.1"/>']
    for i, s in enumerate(lines):
        out.append(t(cx, cy + 3 - (len(lines) - 1) * 5 + i * 10, s, 7.6, "middle"))
    return "\n".join(out)


def save(name, svg, root):
    p = root / (name + ".svg")
    p.write_text(svg, encoding="utf-8")
    print("  wrote", p.name, len(svg), "bytes")
