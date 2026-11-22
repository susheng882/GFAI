# -*- coding: utf-8 -*-

# [2026-11-16 已停用] 当前为 Apple 极简体系；本脚本会把主题/封面改回旧版，请勿运行，仅作历史留档。
raise SystemExit("[已停用] 历史改版脚本：当前主题由 _gf_brand.py / _patch_apple_theme.py / _booklet.py 维护")

"""一键重建全部 40 张 BP 学术图 + A4 图表册。
运行：D:/anaconda3/python.exe _rebuild_all.py

顺序不可调换：
  1. _build_figs_a/c/d/e/f  —— 既有 18 张（仍按旧名产出）
  2. _build_bp_a/b/c/d      —— BP 新增 22 张（直接按新图号命名）
  3. _renumber              —— 把既有 18 张重编为 BP 图号并重命名（幂等）
  4. _normalize             —— 旧图归一化已停用（默认跳过，避免二次缩放损伤）
  5. _typography            —— 只处理未带标记的图，必须放在所有生成器之后
  6. _convert               —— 40 张纯图 PNG（统一 1588×2246，零删除覆盖写）
  7. _booklet               —— 商业计划书式 A4 PDF + 统一尺寸页图

注意：16:20 之后对部分 SVG 做过定点修订，全量重建会把它们覆盖回生成器版本。
日常只需单独运行增量生成器 + _convert.py + _booklet.py。
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PY = sys.executable

STEPS = [
    "_build_figs_a.py",     # 竞品矩阵 / 定价热图 / 遗忘曲线 / 理论矩阵 / 成本图表
    "_build_figs_c.py",     # 功能全景 / 甘特图
    "_build_figs_d.py",     # 长任务 / 直传 / NL 问数 泳道流程图
    "_build_figs_f.py",     # AI 管线 / 护栏降级 / 测试门禁 / 七层架构
    "_build_figs_e.py",     # 服务器矩阵 / 采购清单 宽幅实证矩阵
    "_build_bp_a.py",       # BP: 品牌 / 执行摘要 / 市场机会（6 张）
    "_build_bp_b.py",       # BP: 价值主张 + 六功能域展开（7 张）
    "_build_bp_c.py",       # BP: AI / 运维 / 财务 / 团队 / 风险（8 张）
    "_build_bp_d.py",       # BP: 图 8-2 能力证据与外部依赖可替换性（1 张）
    "_renumber.py",         # 18 张旧图重编为 BP 图号
    "_normalize.py",        # 默认跳过
    "_typography.py",       # 流水线最后一步：字号治理
    "_convert.py",
    "_booklet.py",
]

for step in STEPS:
    print(f"\n===== {step} =====", flush=True)
    r = subprocess.run([PY, step], cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-6:]) if out.strip() else "(no output)"
    print(tail, flush=True)
    if r.returncode != 0:
        print(f"!! FAILED {step} (exit {r.returncode})", flush=True)
        sys.exit(r.returncode)
print("\n===== ALL DONE =====", flush=True)
