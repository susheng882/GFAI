# -*- coding: utf-8 -*-
"""定点修订（2026-11-15 晚）：
1) 图 3-10 遗忘曲线收回绘图区、横轴单位标签避开 R4 刻度、阈值标注垫底；
2) 图 3-2 / 3-3 / 3-5 功能章节的 AI 主导措辞改为功能视角，AI 实现细节后置到第四、五章。

只做精确字符串替换并校验命中数，不重新生成整张 SVG —— 这些图在 16:20 之后有手工修订
（图号、副标题、字号治理），全量重建会把它们覆盖回旧内容。
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
ARCH = ROOT.parent.parent.parent / "归档" / "_主题色改版前备份_2026-11-15"
ARCH.mkdir(parents=True, exist_ok=True)

# (文件, 旧串, 新串, 期望命中数)
PATCH = [
    # ---------- 图 3-10：曲线越界与标注 ----------
    ("图3-10_学习闭环与遗忘曲线调度机制.svg",
     "M 60,108 C 95,220 140,282 210,305 C 280,320 350,324 390,326",
     "M 60,108 C 95,220 140,278 210,299 C 280,311 350,315 390,316", 1),
    ("图3-10_学习闭环与遗忘曲线调度机制.svg",
     '<text x="386.0" y="334.0" font-size="8.8" fill="#666666" text-anchor="end">时间 t（天）</text>',
     '<text x="412.0" y="334.0" font-size="8.8" fill="#666666" text-anchor="end">t / d</text>', 1),
    ("图3-10_学习闭环与遗忘曲线调度机制.svg",
     '<text x="388.0" y="125.0" font-size="8.8" fill="#555555" text-anchor="end">目标保持率 R*=0.90</text>',
     '<rect x="298" y="112" width="94" height="16" fill="#FFFFFF" opacity="0.92"/>'
     '<text x="388.0" y="125.0" font-size="8.8" fill="#555555" text-anchor="end">目标保持率 R*=0.90</text>', 1),
    ("图3-10_学习闭环与遗忘曲线调度机制.svg",
     '<text x="388.0" y="150.5" font-size="8.8" fill="#B4472F" text-anchor="end">回炉阈值 θ=0.85</text>',
     '<rect x="306" y="138" width="86" height="16" fill="#FFFFFF" opacity="0.92"/>'
     '<text x="388.0" y="150.5" font-size="8.8" fill="#B4472F" text-anchor="end">回炉阈值 θ=0.85</text>', 1),
    # ---------- 图 3-2：38 项功能全景五阶段泳道 ----------
    ("图3-2_功能全景流程图.svg", "③ AI 处理管线", "③ 内容解析与生成", 2),
    ("图3-2_功能全景流程图.svg", "AI Pipeline", "Content Parsing", 2),
    ("图3-2_功能全景流程图.svg",
     "错题回炉：低掌握度知识点 → 回流 AI 管线生成变式练习",
     "错题回炉：低掌握度知识点 → 回流内容解析链路生成变式练习", 1),
    ("图3-2_功能全景流程图.svg", ">AI 管线<", ">内容解析<", 1),
    # ---------- 图 3-3：理论依据矩阵 ----------
    ("图3-3_功能模块设计理论依据矩阵.svg", ">AI 管线<", ">内容解析<", 2),
    # ---------- 图 3-2 图例/说明中的残留口径 ----------
    ("图3-2_功能全景流程图.svg", ">三级取材 · 三档路由 <", ">三级取材 · 契约校验 <", 1),
]


def main():
    by_file = {}
    for f, old, new, n in PATCH:
        by_file.setdefault(f, []).append((old, new, n))
    for fname, rules in by_file.items():
        p = ROOT / fname
        if not p.exists():
            raise SystemExit("缺文件：" + fname)
        shutil.copy2(p, ARCH / fname)
        s = p.read_text(encoding="utf-8")
        for old, new, n in rules:
            hit = s.count(old)
            if hit == 0 and new in s:
                print(f"  {fname} 已应用，跳过：{old[:34]}")
                continue  # 幂等：中断后重跑
            if hit != n:
                raise SystemExit(f"{fname} 命中不符：期望 {n} 实得 {hit} —— {old[:60]}")
            s = s.replace(old, new)
        p.write_text(s, encoding="utf-8")
        print(f"{fname}：{len(rules)} 组替换全部命中")

    # 残留检查
    left = []
    for f in ["图3-2_功能全景流程图.svg", "图3-3_功能模块设计理论依据矩阵.svg"]:
        s = (ROOT / f).read_text(encoding="utf-8")
        for m in re.finditer(r">[^<]*AI[^<]*<", s):
            left.append((f, m.group(0)[:60]))
    print("第三章功能图残留 AI 字样：", left or "无")
    s310 = (ROOT / "图3-10_学习闭环与遗忘曲线调度机制.svg").read_text(encoding="utf-8")
    print("图 3-10 曲线终点 y=316、不穿横轴：", "390,316" in s310,
          "| 轴单位已收窄：", ">t / d<" in s310,
          "| 阈值垫底：", s310.count('opacity="0.92"') == 2)


if __name__ == "__main__":
    main()
