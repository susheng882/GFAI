# -*- coding: utf-8 -*-
"""2026-11-15 市场数据口径复核补丁（零删除、仅文本替换）。

复核结论：
1) 3.5 亿在线学习用户为 2024 年高点；CNNIC 第 57 次《中国互联网络发展状况统计报告》
   （2026-02-05 发布，数据截至 2025-12）为在线教育用户 3.27 亿，同比 -7.89%。
2) 2027 研考报名于 2026-10-15～24 结束、初试 2026-12-19～20，教育部《2027 年全国
   硕士研究生招生工作管理规定》（教学〔2026〕2号）已发布，但截至 2026-11-15
   官方最终报名人数尚未公布；315～335 万为机构测算区间，非官方数据。
3) 2026 年 343 万为教育部 2025-11-24 公布的最近一期官方值，保留为历史锚点。

本脚本同步修订：所有源 SVG、生成器源码、图册脚本中的旧口径，并给图 2-3 补来源链接。
"""
from pathlib import Path
import shutil

ROOT = Path(__file__).parent
ARCH = ROOT.parent.parent.parent / "归档" / "_市场数据口径修订前_2026-11-15"
ARCH.mkdir(parents=True, exist_ok=True)

REPL = [
    # --- 先处理长串 / 精确结构，避免被后面的短串截断 ---
    ('kpi=[("3.5 亿", "在线学习用户"), ("343 万", "2026 考研")',
     'kpi=[("3.27 亿", "在线教育用户"), ("315–335 万", "2027 研考测算")'),
    ("在线学习用户 3.5 亿 × 年均 ¥1655 ≈ 5793 亿元/年（理论天花板）",
     "在线教育用户 3.27 亿 × 年均 ¥1655 ≈ 5412 亿元/年（理论天花板）"),
    ("以 2026 考研报名 343 万人为锚定核心圈", "以 2027 研考备考人群为锚定（官方人数未公布）"),
    ("TAM 3.5 亿在线学习用户；2026 考研报名 343 万人为高意愿锚定圈。",
     "TAM 锚定 CNNIC 3.27 亿在线教育用户；2027 研考官方人数未公布，机构测算 315–335 万仅作参考区间。"),
    ("3.5 亿用户｜343 万考研", "3.27 亿｜2027 研考待公布"),
    ("IIM 2026 / 中国教育在线", "CNNIC 57次 / 教育部 2026"),
    ("TAM 3.5 亿用户、SAM 备考自学细分", "TAM 3.27 亿用户、SAM 备考自学细分"),
    ("IIM / 多鲸 / 艾瑞 / 中国教育在线 2026", "CNNIC / 教育部 / 多鲸 / 艾瑞 / 中国教育在线"),
    # --- 在线教育用户口径：3.5 亿 → CNNIC 3.27 亿 ---
    ("突破 3.5 亿人", "3.27 亿人"),
    ("IIM 平台市场趋势展望 2026", "CNNIC 第 57 次报告 2026-02"),
    ("活跃用户占比升至 68%", "截至 2025-12，同比 −7.89%"),
    ("3.5 亿人 × ¥1655/年", "3.27 亿人 × ¥1655/年"),
    ("≈ 5793 亿元/年", "≈ 5412 亿元/年"),
    # --- 考研口径：2026 官方值 → 2027 官方状态 + 非官方测算 ---
    ("中国教育在线 2026（教育部口径）", "教育部教学〔2026〕2号"),
    ("连续三年下降，仍为高意愿细分", "机构测算 315–335 万（非官方）"),
    # --- 全局短串放最后 ---
    ("在线学习用户", "在线教育用户"),
    ("考研报名人数", "2027 研考报名"),
    ("343 万人", "尚未公布"),
]

files = sorted(ROOT.glob("*.svg")) + sorted(ROOT.glob("*.py"))
files = [p for p in files if p.name != Path(__file__).name]
hits = {a: 0 for a, _ in REPL}
changed = []
for p in files:
    s = p.read_text(encoding="utf-8")
    o = s
    for a, b in REPL:
        n = o.count(a)
        if n:
            hits[a] += n
            o = o.replace(a, b)
    if o != s:
        shutil.copy2(p, ARCH / p.name)   # 修订前原件留档，不删除任何交付物
        changed.append(p.name)
        p.write_text(o, encoding="utf-8")

print("=== 替换命中统计 ===")
for a, b in REPL:
    print(f"  {hits[a]:3d} × {a[:46]}")
print("=== 改动文件 ===")
for n in changed:
    print("  ", n)

# --- 图 2-3：扩底部口径框，补三条可核验来源链接 ---
p = ROOT / "图2-3_市场规模测算TAM-SAM-SOM.svg"
s = p.read_text(encoding="utf-8")
old_rect = '<rect x="24.0" y="781.0" width="632.0" height="54.0"'
assert old_rect in s, "口径框 rect 未找到"
s = s.replace(old_rect, '<rect x="24.0" y="781.0" width="632.0" height="84.0"')

legend_old = ('<text x="24.0" y="878.0" font-size="9.2" fill="#444444">'
              '图例：窄口径＝平台市场规模；广义口径含课程交易与 B2B；所有数值标注来源与年份，假设项显式声明。</text>')
assert legend_old in s, "图例行未找到"
legend_new = ('<text x="24.0" y="878.0" font-size="8.6" fill="#444444">'
              '来源③ 2027 测算 315–335 万（非官方）mbachina.com/html/xw/202610/663518.html'
              '　｜　CNNIC 57 次 cnnic.cn　｜　图例：窄口径＝平台市场，假设项显式声明</text>')
s = s.replace(legend_old, legend_new)

anchor = '<text x="36.0" y="830.0" font-size="9.0"'
assert anchor in s, "口径声明末行未找到"
src_lines = [
    '<text x="36.0" y="845.0" font-size="8.4" fill="#555555">'
    '来源① 2027 研考规定（报名 10/15–24、初试 12/19–20；人数未公布）：moe.gov.cn › 教学〔2026〕2号</text>',
    '<text x="36.0" y="859.0" font-size="8.4" fill="#555555">'
    '来源② 2026 官方 343 万（2025-11-24 教育部公布）：eol.cn/news/yaowen/202511/t20251124_2702608.shtml</text>',
]
s = s.replace(anchor, "\n".join(src_lines) + "\n" + anchor)
p.write_text(s, encoding="utf-8")
print("=== 图 2-3 来源链接 ===  已插入 2 行 + 图例行改写；原文件已备份至", ARCH.name)
