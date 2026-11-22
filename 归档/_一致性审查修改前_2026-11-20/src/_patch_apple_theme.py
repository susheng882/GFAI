# -*- coding: utf-8 -*-
"""全册 40 张 SVG → Apple 极简主题（2026-11-16）。

一次性语义换色 + 无衬线字族替换，幂等：新色板的值不在映射表 key 中，
重复运行不会二次变色。图 0-1 由 _build_brand_fig.py 单独重绘，此处跳过。
"""
import re
from pathlib import Path
import _gf_brand as B

SRC = Path(__file__).parent

# 旧蓝黄体系 → 新「石墨 / 前进蓝 / 云雾灰」体系
MAP = {
    '#212121': B.INK,      # 正文 / 外框 / 结构线
    '#1B6E9C': B.BLUE,     # 主蓝 → 前进蓝
    '#3C464D': '#3A3A3C',
    '#2B3237': '#48484A',
    '#353F46': '#3A3A3C',
    '#4E5A62': '#48484A',
    '#5B6871': B.GREY,
    '#55626A': B.GREY,
    '#6C7B85': B.GREY2,
    '#83949E': B.GREY2,
    '#8FA1AB': '#A1A1A6',
    '#9AAAB3': '#A1A1A6',
    '#C6DEE9': B.SILVER,   # 浅蓝边框 → 中性银线
    '#B4C3CB': '#C7C7CC',
    '#BED3DE': B.SILVER,
    '#D8E9F1': B.ICE,
    '#E1EFF6': B.ICE,
    '#DCEBF2': B.ICE,
    '#CDE9F6': B.ICE,
    '#8ED7FE': '#A8CEF7',  # 亮蓝强调 → 柔和前进蓝
    '#E4F3FB': '#EEF5FD',
    '#E7F2F8': '#F0F4F8',
    '#ECF5FA': B.MIST,
    '#F0F8FC': B.MIST,
    '#EEF7FB': B.MIST,
    '#F3FAFD': B.MIST,
    '#FBFDFE': '#FAFAFC',
    '#F8EDB8': B.MIST,     # 奶油黄 → 云雾灰（去掉黄底）
    '#F4FF8D': B.SPARK,    # 亮黄点睛 → 火花橙（仅 2 处）
    '#FFFBFF': B.WHITE,
    '#F3F3F3': B.MIST,
    '#D0D0D0': B.SILVER,
}
MAP = {k.upper(): v for k, v in MAP.items()}

OLD_FONT = "'Noto Serif SC','Source Han Serif SC','SimSun',serif"
NEW_FONT = ("-apple-system,BlinkMacSystemFont,'SF Pro Text','Helvetica Neue',"
            "'Segoe UI','PingFang SC','Microsoft YaHei','Noto Sans CJK SC',sans-serif")


def patch(s: str) -> str:
    s = re.sub(r'#[0-9A-Fa-f]{6}',
               lambda m: MAP.get(m.group(0).upper(), m.group(0)), s)
    s = s.replace(OLD_FONT, NEW_FONT)
    return s


def main():
    n = 0
    for f in sorted(SRC.glob('*.svg')):
        if f.name.startswith('图0-1'):
            continue
        old = f.read_text(encoding='utf-8')
        new = patch(old)
        if new != old:
            f.write_text(new, encoding='utf-8')
            n += 1
    print('patched SVG:', n)


if __name__ == '__main__':
    main()
