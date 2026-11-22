# -*- coding: utf-8 -*-
"""GrowthForward 品牌视觉 · Apple 极简体系（2026-11-16）

一套克制的白 + 石墨灰阶，单一前进蓝作主色，火花橙只用于「向前」箭头。
提供几何 G 标 / app icon / 极简吉祥物 / 横向字标，供册页与图 0-1 复用。
所有片段都不依赖 <defs> 中的全局 id（多实例同页安全），需要渐变时传 prefix。
"""
from pathlib import Path

# ---------------------------------------------------------------- 色板
INK    = '#1D1D1F'   # 石墨：正文、主标题、结构线
BLUE   = '#0071E3'   # 前进蓝：唯一主色，表头 / 强调 / 图形标
BLUE_D = '#0058C0'   # 深前进蓝：icon 渐变收尾
ICE    = '#EAF3FF'   # 冰蓝：浅底、选中态
MIST   = '#F5F5F7'   # 云雾：页面底、次级卡
SILVER = '#D2D2D7'   # 银线：边框、分隔线
SPARK  = '#FF9F0A'   # 火花橙：唯一暖色，仅用于向前箭头与天线光点
RISK   = '#B4472F'   # 砖红：风险语义色，独立保留
WHITE  = '#FFFFFF'
GREY   = '#6E6E73'   # 次级文字
GREY2  = '#86868B'   # 弱化文字

PALETTE = [
    ('石墨 Graphite', INK,    '正文与主标题 · 屏幕脸'),
    ('前进蓝 Forward', BLUE,  '主色 · 表头 · 图形标'),
    ('冰蓝 Ice',      ICE,    '浅底 · 选中态 · 数据带'),
    ('云雾 Mist',     MIST,   '页面底 · 次级卡'),
    ('银线 Silver',   SILVER, '边框 · 分隔线'),
    ('火花橙 Spark',  SPARK,  '向前箭头 · 唯一点睛'),
]

FONT = ('-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",'
        '"Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif')
# SVG 属性需单引号字体名，避免与 XML 属性双引号冲突
FONT_SVG = ("-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',"
            "'Segoe UI','PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif")

# ---------------------------------------------------------------- 几何 G 标
# 开口圆环 = 可延展的学习闭环；右上冲出开口的箭头 = 持续向前；
# 环内短横 = G 的字骨，也是「每天前进一小步」的基线。
_G_RING   = 'M 69.5 25.5 A 34 34 0 1 0 79 70'
_G_BAR    = 'M 79 70 L 50 70'
_G_SHAFT  = 'M 69.5 25.5 L 87 8'
_G_ARROW  = 'M 73 6 L 90 6 L 90 23'


def mark(stroke=BLUE, arrow=SPARK, cls='', sw=10):
    """线性图形标；stroke/arrow 可换色用于反白与水印。"""
    c = f' class="{cls}"' if cls else ''
    return (f'<svg{c} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<path d="{_G_RING}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<path d="{_G_BAR}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<path d="{_G_SHAFT}" fill="none" stroke="{arrow}" stroke-width="{sw}" stroke-linecap="round"/>'
            f'<path d="{_G_ARROW}" fill="none" stroke="{arrow}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'</svg>')


def icon(prefix='ic', cls=''):
    """圆角方形 app icon：蓝色渐变 + 单色 G 标，iOS 风格。"""
    c = f' class="{cls}"' if cls else ''
    def p(d, color=WHITE, w=7.4):
        return (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}" '
                f'stroke-linecap="round" stroke-linejoin="round"/>')
    return (f'<svg{c} viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<defs><linearGradient id="{prefix}g" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#0A84FF"/><stop offset="1" stop-color="{BLUE_D}"/>'
            f'</linearGradient></defs>'
            f'<rect width="100" height="100" rx="23" fill="url(#{prefix}g)"/>'
            f'<g transform="translate(7,7) scale(0.86)">'
            f'{p(_G_RING)}{p(_G_BAR)}{p(_G_SHAFT, "#FFD38A")}{p(_G_ARROW, "#FFD38A")}'
            f'</g></svg>')


def mascot(prefix='ms', cls=''):
    """「小前」极简版：悬浮圆角头 + 深墨屏幕脸 + 两个光点眼睛 + 天线火花。
    无腮红、无渐变高光、无装饰星，只有白 / 石墨 / 银 / 一点火花橙。"""
    c = f' class="{cls}"' if cls else ''
    return (f'<svg{c} viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg" '
            f'preserveAspectRatio="xMidYMid meet">'
            f'<defs><linearGradient id="{prefix}g" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="#FFFFFF"/><stop offset="1" stop-color="{MIST}"/>'
            f'</linearGradient><filter id="{prefix}s" x="-35%" y="-35%" width="170%" height="180%">'
            f'<feDropShadow dx="0" dy="7" stdDeviation="9" flood-color="{INK}" flood-opacity="0.11"/>'
            f'</filter></defs>'
            f'<ellipse cx="100" cy="181" rx="43" ry="6" fill="{BLUE}" opacity="0.09"/>'
            f'<rect x="97" y="22" width="6" height="26" rx="3" fill="{SILVER}"/>'
            f'<circle cx="100" cy="19" r="7" fill="{SPARK}"/>'
            f'<rect x="29" y="84" width="9" height="28" rx="4.5" fill="{SILVER}"/>'
            f'<rect x="162" y="84" width="9" height="28" rx="4.5" fill="{SILVER}"/>'
            f'<rect x="40" y="44" width="120" height="116" rx="38" fill="url(#{prefix}g)" '
            f'stroke="{SILVER}" stroke-width="2" filter="url(#{prefix}s)"/>'
            f'<rect x="55" y="60" width="90" height="76" rx="27" fill="{INK}"/>'
            f'<circle cx="83" cy="94" r="7" fill="{WHITE}"/>'
            f'<circle cx="117" cy="94" r="7" fill="{WHITE}"/>'
            f'<path d="M 91 116 Q 100 123 109 116" fill="none" stroke="{WHITE}" '
            f'stroke-width="3.4" stroke-linecap="round" opacity="0.92"/>'
            f'<circle cx="100" cy="150" r="2.6" fill="{SILVER}"/>'
            f'</svg>')


def logo(small=False, sub=True, cls=''):
    """横向字标：图形标 + GrowthForward + 中文副题。"""
    k = ' gf-logo sm' if small else ' gf-logo'
    return (f'<div class="{k} {cls}"><div class="gf-mark">{mark()}</div>'
            f'<div class="gf-words"><div class="gf-name">Growth<span>Forward</span></div>'
            + (f'<div class="gf-sub">成长向前 · AI 学习伴侣</div>' if sub else '')
            + '</div></div>')


def head_mark():
    """页眉用的微型图形标（不加文字，避免 id / class 冲突）。"""
    return f'<span class="pm">{mark()}</span>'


# ---------------------------------------------------------------- 导出独立资产
def export_assets(folder=None):
    out = Path(folder) if folder else Path(r'F:\GrowthForward_AI学习伴侣\brand_assets')
    out.mkdir(parents=True, exist_ok=True)
    files = {
        'gf_mark.svg': mark(),
        'gf_icon.svg': icon('gfexp'),
        'gf_mascot.svg': mascot('gfexp'),
        'gf_logo.svg': (
            '<svg viewBox="0 0 420 100" xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(0,0) scale(1)">'
            + mark().replace('<svg ', '<svg x="0" y="0" width="100" height="100" ', 1)
            + '</g>'
            + f'<text x="116" y="52" font-family="{FONT_SVG}" font-size="27" font-weight="600" '
              f'letter-spacing="-0.6" fill="{INK}">Growth<tspan fill="{BLUE}">Forward</tspan></text>'
            + f'<text x="117" y="72" font-family="{FONT_SVG}" font-size="10" letter-spacing="1.4" '
              f'fill="{GREY2}">成长向前 · AI 学习伴侣　LEARN. GROW. KEEP MOVING FORWARD.</text>'
            + '</svg>'),
    }
    for n, s in files.items():
        (out / n).write_text(s if s.lstrip().startswith('<svg') else
                             f'<svg xmlns="http://www.w3.org/2000/svg">{s}</svg>', encoding='utf-8')
    return [str(out / n) for n in files]


if __name__ == '__main__':
    for p in export_assets():
        print('wrote', p)
