# -*- coding: utf-8 -*-
"""重绘图 0-1「品牌视觉系统」· Apple 极简版。
680×960 标准画布，白纸底 / 银线圆角卡 / 单一前进蓝 / 火花橙点睛。
"""
from pathlib import Path
import _gf_brand as B

SRC = Path(__file__).parent
OUT = SRC / '图0-1_品牌形象与设计理念.svg'
FONT = B.FONT_SVG


def T(x, y, s, size=9.2, fill=B.INK, weight='', anchor='', ls='', op=''):
    a = f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}"'
    if weight:
        a += f' font-weight="{weight}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    if ls:
        a += f' letter-spacing="{ls}"'
    if op:
        a += f' opacity="{op}"'
    return a + f'>{s}</text>'


def R(x, y, w, h, rx=9, fill=B.WHITE, stroke=B.SILVER, sw=1):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def L(x1, y1, x2, y2, color=B.SILVER, sw=1):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{color}" stroke-width="{sw}"/>')


def _inner(svg):
    return svg[svg.index('>') + 1:svg.rindex('</svg>')]


def GM(x, y, scale, stroke=B.BLUE, arrow=B.SPARK, sw=9):
    return f'<g transform="translate({x},{y}) scale({scale})">{_inner(B.mark(stroke, arrow, sw=sw))}</g>'


def GI(x, y, scale, prefix, stroke=B.WHITE, arrow='#FFD38A'):
    # icon 内部渐变 id 按 prefix 隔离
    s = B.icon(prefix)
    return f'<g transform="translate({x},{y}) scale({scale})">{_inner(s)}</g>'


def GMS(x, y, scale, prefix):
    return f'<g transform="translate({x},{y}) scale({scale})">{_inner(B.mascot(prefix))}</g>'


def SEC(y, no, cn, en, x=24, w=632):
    return (f'<circle cx="{x+5}" cy="{y-3.5}" r="3.4" fill="{B.BLUE}"/>'
            + T(x + 14, y, f'{no}　{cn}', 10.4, B.INK, 'bold', ls='.3')
            + T(x + w, y, en, 8.2, B.GREY2, anchor='end', ls='.5')
            + L(x, y + 6, x + w, y + 6, B.SILVER, .8))


def build():
    o = []
    o.append(f'<svg viewBox="0 0 680 960" xmlns="http://www.w3.org/2000/svg" font-family="{FONT}">')
    o.append(f'<rect x="0" y="0" width="680" height="960" fill="{B.WHITE}"/>')
    o.append(f'<rect x="8" y="8" width="664" height="944" rx="10" fill="{B.WHITE}" stroke="{B.SILVER}" stroke-width="1"/>')

    # ------------------------------------------------ 页眉
    o.append(f'<rect x="24" y="24" width="18" height="18" rx="5" fill="{B.BLUE}"/>')
    o.append(GM(25.5, 25.5, .15, stroke=B.WHITE, arrow=B.WHITE, sw=14))
    o.append(T(50, 38, 'GrowthForward · 品牌形象与设计理念', 14, B.INK, 'bold'))
    o.append(T(50, 53, 'Brand Identity / Visual System / Design Rationale / Applications', 9, B.GREY2))
    o.append(T(656, 38, 'GFLC · 2026', 8.6, B.GREY2, anchor='end'))
    o.append(T(656, 53, 'Apple-inspired minimal system', 8.2, B.GREY2, anchor='end'))
    o.append(L(24, 64, 656, 64, B.INK, 1))

    # ------------------------------------------------ 01 标志构造
    o.append(SEC(82, '01', '标志构造', 'LOGO CONSTRUCTION'))
    o.append(R(24, 96, 310, 146, 11, '#FAFAFC'))
    o.append(GM(44, 100, .78))
    o.append(f'<text x="140" y="148" font-size="21" font-weight="bold" letter-spacing="-.6" '
             f'fill="{B.INK}">Growth<tspan fill="{B.BLUE}">Forward</tspan></text>')
    o.append(T(141, 166, '成长向前 · AI 学习伴侣', 9.4, B.GREY, ls='.6'))
    o.append(L(40, 186, 314, 186, B.SILVER, .8))
    o.append(T(40, 202, '开口圆环 = 可延展的学习闭环', 9, B.INK))
    o.append(T(40, 217, '冲出开口的箭头 = 持续向前', 9, B.INK))
    o.append(T(40, 233, '环内短横 = G 的字骨与每日基线', 8.6, B.GREY2))

    o.append(R(342, 96, 314, 146, 11, '#FAFAFC'))
    o.append(T(354, 113, 'App Icon · 圆角方形', 9.6, B.INK, 'bold'))
    o.append(GI(356, 122, .78, 'ic1'))
    o.append(GI(433, 134, .56, 'ic2'))
    o.append(GI(490, 143, .40, 'ic3'))
    o.append(T(356, 207, '蓝色渐变 + 单色 G 标，23% 圆角', 8.6, B.GREY))
    o.append(L(342, 216, 656, 216, B.SILVER, .8))
    o.append(R(354, 222, 78, 14, 7, B.WHITE))
    o.append(GM(357, 222.5, .13, sw=12))
    o.append(T(374, 232.5, '单色版', 8.2, B.GREY2))
    o.append(R(440, 222, 78, 14, 7, B.INK, B.INK))
    o.append(GM(443, 222.5, .13, stroke=B.WHITE, arrow=B.WHITE, sw=12))
    o.append(T(460, 232.5, '反白版', 8.2, B.WHITE))
    o.append(T(528, 232.5, '最小尺寸 16 px', 8.2, B.GREY2))

    # ------------------------------------------------ 02 吉祥物
    o.append(SEC(256, '02', '吉祥物「小前」', 'MASCOT · MINIMAL REBOOT'))
    o.append(R(24, 270, 196, 166, 11, '#FAFAFC'))
    o.append(GMS(52, 272, .76, 'ms1'))
    o.append(T(122, 428, '小前  Qian', 9.4, B.INK, 'bold', anchor='middle'))
    o.append(R(228, 270, 428, 166, 11, B.WHITE))
    items = [
        ('① 圆角头', '120×116 px 圆角 38，白到云雾的极淡渐变，柔和落影'),
        ('② 屏幕脸', '深墨圆角矩形，两个白色光点 + 一条微笑弧，无五官堆叠'),
        ('③ 火花天线', '银色细杆 + 火花橙光点，是全形象唯一的彩色'),
        ('④ 悬浮阴影', '前进蓝 9% 椭圆投影，表达「轻量、安静、不打扰」'),
    ]
    for k, (t, d) in enumerate(items):
        y = 288 + k * 34
        o.append(f'<circle cx="{242}" cy="{y-3}" r="2.6" fill="{B.BLUE}"/>')
        o.append(T(252, y, t, 9.4, B.INK, 'bold'))
        o.append(T(310, y, d, 8.6, B.GREY))
        if k < 3:
            o.append(L(240, y + 8, 644, y + 8, '#EDEDEF', .7))
    o.append(L(240, 412, 644, 412, B.SILVER, .8))
    o.append(T(240, 428, '设计取舍：去掉腮红、渐变高光与装饰星；仅白 / 石墨 / 银 / 一点火花橙，可在 24 px 下辨识。', 8.6, B.GREY2))

    # ------------------------------------------------ 03 色彩系统
    o.append(SEC(452, '03', '色彩系统', 'COLOR SYSTEM'))
    pal = [
        ('石墨 Graphite', B.INK, '正文 · 主标题 · 屏幕脸', B.WHITE),
        ('前进蓝 Forward', B.BLUE, '主色 · 表头 · 图形标', B.WHITE),
        ('冰蓝 Ice', B.ICE, '浅底 · 选中态 · 数据带', B.INK),
        ('云雾 Mist', B.MIST, '页面底 · 次级卡', B.INK),
        ('银线 Silver', B.SILVER, '边框 · 分隔线', B.INK),
        ('火花橙 Spark', B.SPARK, '向前箭头 · 唯一点睛', B.WHITE),
    ]
    for k, (nm, c, use, tc) in enumerate(pal):
        x = 24 + k * 106
        o.append(R(x, 466, 100, 96, 9, B.WHITE))
        o.append(f'<rect x="{x+7}" y="{473}" width="86" height="34" rx="6" fill="{c}" stroke="{B.SILVER}" stroke-width=".6"/>')
        o.append(T(x + 7, 522, nm, 8.8, B.INK, 'bold'))
        o.append(T(x + 7, 535, c, 8.4, B.BLUE))
        o.append(T(x + 7, 552, use, 7.8, B.GREY2))
    o.append(T(24, 578, f'语义例外：风险 / 异常仅用砖红 {B.RISK}；其余场景一律不引入第三种彩色，保证 A4 黑白打印仍可读。', 8.6, B.GREY))
    o.append(L(24, 586, 656, 586, B.SILVER, .8))

    # ------------------------------------------------ 04 字体与图形规范
    o.append(SEC(602, '04', '字体与图形规范', 'TYPOGRAPHY AND GRID'))
    o.append(R(24, 616, 632, 74, 9, B.WHITE))
    specs = [
        ('字族', 'SF Pro / 苹方 / 雅黑，全册无衬线'),
        ('字重', '标题 600 · 正文 400 · 弱化加灰'),
        ('圆角', '卡片 14 px · icon 23% · 胶囊全圆'),
        ('网格', '8 pt 基准 · 图幅 680×960'),
        ('线条', '0.5–1 px 银线，禁止粗黑框'),
        ('留白', '层级靠字号灰度，不靠彩色块'),
    ]
    for k, (a, b) in enumerate(specs):
        col, row = k % 2, k // 2
        x = 34 + col * 306
        y = 634 + row * 22
        o.append(f'<rect x="{x}" y="{y-9}" width="52" height="15" rx="7.5" fill="{B.ICE}"/>')
        o.append(T(x + 26, y + 2, a, 8.4, B.BLUE, 'bold', anchor='middle'))
        o.append(T(x + 60, y + 2, b, 8.0, B.INK))

    # ------------------------------------------------ 05 应用矩阵
    o.append(SEC(706, '05', '应用矩阵', 'APPLICATION MATRIX'))
    apps = [
        ('页眉微标', '10 px 图形标 + 书名，全册 54 页统一'),
        ('扉页水印', '大号 G 标 4% 透明度，作为章节底纹'),
        ('图页角标', 'GFLC · 年份，右下角弱化标注'),
        ('App Icon', '圆角方形蓝底，桌面与小程序入口'),
        ('封面封底', '白纸底 + 大标题 + 极简「小前」'),
        ('图表强调', '前进蓝表头 / 冰蓝浅底 / 砖红风险'),
    ]
    for k, (t, d) in enumerate(apps):
        x = 24 + k * 106
        o.append(R(x, 720, 100, 76, 9, '#FAFAFC'))
        o.append(f'<rect x="{x+9}" y="{729}" width="18" height="18" rx="5" fill="{B.ICE}"/>')
        o.append(GM(x + 10, 730, .16, sw=12))
        o.append(T(x + 9, 762, t, 8.8, B.INK, 'bold'))
        o.append(T(x + 9, 777, d[:10], 7.3, B.GREY2))
        o.append(T(x + 9, 789, d[10:], 7.3, B.GREY2))

    # ------------------------------------------------ 06 设计理念
    o.append(SEC(812, '06', '设计理念', 'DESIGN RATIONALE'))
    pillars = [
        ('生长 Growth', '开口 + 箭头 = 每天向前一步'),
        ('可信 Trust', '数据带来源口径，图形不做虚饰'),
        ('克制 Restraint', '单一主色 · 大量白 · 细线圆角'),
    ]
    for k, (t, d) in enumerate(pillars):
        x = 24 + k * 212
        o.append(R(x, 826, 206, 52, 9, B.WHITE))
        o.append(f'<rect x="{x}" y="{826}" width="3" height="52" rx="1.5" fill="{B.BLUE}"/>')
        o.append(T(x + 12, 845, t, 9.2, B.BLUE, 'bold'))
        o.append(T(x + 12, 862, d, 8.2, B.INK))

    # ------------------------------------------------ 图例与图题
    o.append(L(24, 890, 656, 890, B.SILVER, .8))
    o.append(T(24, 903, f'图例：● 前进蓝＝主色与推进；● 火花橙＝向前箭头；● 石墨＝结构性信息；{B.RISK} 为唯一保留的风险语义色。', 8.4, B.GREY))
    o.append(T(340, 922, '图 0-1　品牌形象与设计理念', 12.5, B.INK, 'bold', anchor='middle'))
    o.append(T(340, 939, 'Fig. 0-1 Brand identity, visual system and design rationale', 9.2, B.GREY2, anchor='middle', ls='.2'))
    o.append('</svg>')
    return '\n'.join(o)


if __name__ == '__main__':
    OUT.write_text(build(), encoding='utf-8')
    print('wrote', OUT.name, len(build()), 'chars')
