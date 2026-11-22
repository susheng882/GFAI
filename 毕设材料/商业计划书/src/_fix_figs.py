# -*- coding: utf-8 -*-
"""修正首轮质检发现的排版问题：热图溢出、纵轴反向、表格溢出、留白补齐。"""
from pathlib import Path

ROOT = Path(__file__).parent
A = ROOT / "_build_figs_a.py"
B = ROOT / "_build_figs_b.py"

RA = [
    ("gx, gy, cw2, rh = 356, 104, 54, 38", "gx, gy, cw2, rh = 356, 104, 47, 38"),
    ("gx + 62 + j * cw2", "gx + 58 + j * cw2"),
    # 图 1-1 底部留白补「实证复核方法」框
    ('    b.append(t(X0, y + 94, "数据源：产品报告第二章（二）（四）· 技术方案 1.4 节 · 图 1-2 定价对照", 8.2, fill=GREY))\n    return frame(',
     '''    b.append(t(X0, y + 94, "数据源：产品报告第二章（二）（四）· 技术方案 1.4 节 · 图 1-2 定价对照", 8.2, fill=GREY))
    y4 = y + 104
    b.append(r(X0, y4, CW, 62, "#FAFAFA", INK, 0.8))
    b.append(icon("eye", X0 + 10, y4 + 8, 0.7))
    b.append(t(X0 + 34, y4 + 20, "实证复核方法与数据来源", 8.8, weight="bold"))
    b.append(t(X0 + 12, y4 + 38, "采集路径：厂商官网定价页 / 官方帮助中心 / 2026 年第三方定价复核页；能力判定以产品主力使用场景为准，", 7.8))
    b.append(t(X0 + 12, y4 + 53, "跨类能力以「是否需插件或人工」为 ○／● 分界；所有条目均标注上线状态，未上线或仅内测的产品不纳入本矩阵。", 7.8))
    return frame('''),
    # 图 4-2 纵轴刻度方向
    ("        yy = ay + ah - i * (ah / 5)", "        yy = ay + i * (ah / 5)"),
    # 图 4-2 阈值线位置
    ('''    b.append(ln(ax, ay + ah * 0.15, ax + aw, ay + ah * 0.15, "#888888", 0.8, "4 3"))
    b.append(t(ax + aw - 2, ay + ah * 0.15 - 4, "目标保持率 R*=0.90", 7.2, "end", fill="#555555"))
    b.append(ln(ax, ay + ah * 0.30, ax + aw, ay + ah * 0.30, RED, 0.9, "4 3"))
    b.append(t(ax + aw - 2, ay + ah * 0.30 - 4, "回炉阈值 θ=0.85", 7.2, "end", fill=RED))''',
     '''    b.append(ln(ax, ay + ah * 0.10, ax + aw, ay + ah * 0.10, "#888888", 0.8, "4 3"))
    b.append(t(ax + aw - 2, ay + ah * 0.10 - 4, "目标保持率 R*=0.90", 7.2, "end", fill="#555555"))
    b.append(ln(ax, ay + ah * 0.15, ax + aw, ay + ah * 0.15, RED, 0.9, "4 3"))
    b.append(t(ax + aw - 2, ay + ah * 0.15 + 11, "回炉阈值 θ=0.85", 7.2, "end", fill=RED))'''),
    # 图 4-2 表格压缩，避免越过 862 图例带
    ('header_h=28, row_h=38, font=7.8, aligns=["start", "middle", "start"])',
     'header_h=26, row_h=34, font=7.8, aligns=["start", "middle", "start"])'),
    ('header_h=26, row_h=30, font=7.4, aligns=["start", "start", "middle"])',
     'header_h=24, row_h=28, font=7.4, aligns=["start", "start", "middle"])'),
    ("    yy = y + 10 + hh2 + 8", "    yy = y + 10 + hh2 + 6"),
    # 图 5-3 底部留白补 LLM 单价表
    ('''        b.append(t(X0 + 12, y3 + 22 + i * 20, s, 8.0, fill="#333333"))
    return frame("运行成本解析与服务器云服务选型（图表版）",''',
     '''        b.append(t(X0 + 12, y3 + 22 + i * 20, s, 8.0, fill="#333333"))
    b.append(t(X0, 674, "F　LLM API 单价 × 三档路由映射（元/百万 tokens，按量付费口径）", 9, weight="bold"))
    rows3 = [
        ["轻档 qwen-flash", "¥0.15", "¥1.50", "意图解析 / 格式整理 / 摘要", "单次成本 <0.001 元量级"],
        ["中档 qwen-plus", "¥0.80", "¥2.00", "常规笔记 / 卡片 / 题目解析", "主线默认档位"],
        ["强档 qwen-max", "¥2.40", "¥9.60", "复杂推理 / 组卷 / 低置信重跑", "仅护栏判定后启用"],
        ["DeepSeek-V4.1 Flash", "$0.15", "$0.60", "供应商可替换的备选端点", "美元计价，peak 时段翻倍"],
    ]
    tb3, _ = table(X0, 684, [122, 70, 70, 218, 152],
                   ["模型档位", "输入单价", "输出单价", "用途", "备注"], rows3,
                   header_h=24, row_h=30, font=7.6,
                   aligns=["start", "middle", "middle", "start", "start"])
    b.append(tb3)
    return frame("运行成本解析与服务器云服务选型（图表版）",'''),
]

RB = [
    ("header_h=26, row_h=36, font=7.6", "header_h=24, row_h=32, font=7.6"),
    ("header_h=26, row_h=40, font=7.6", "header_h=24, row_h=32, font=7.6"),
    ("    y = 518 + hh + 10", "    y = 518 + hh + 8"),
    ("    y = 490 + hh + 10", "    y = 490 + hh + 8"),
    ("b.append(t(X0, y + 68,", "b.append(t(X0, y + 62,"),
    ("b.append(t(X0, y + 84,", "b.append(t(X0, y + 78,"),
]


def apply(path, rules):
    s = path.read_text(encoding="utf-8")
    for old, new in rules:
        n = s.count(old)
        if n == 0:
            print("  MISS", path.name, "|", old[:60].replace("\n", " "))
        else:
            s = s.replace(old, new)
            print("  ok", path.name, "x", n, "|", old[:48].replace("\n", " "))
    path.write_text(s, encoding="utf-8")


if __name__ == "__main__":
    apply(A, RA)
    apply(B, RB)
