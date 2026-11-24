# -*- coding: utf-8 -*-
"""把批量导入采集的性能数据渲染成 PNG 报告。

输入：bulk_ingest.py 产出的 JSON（可多个，按 --inputs 逗号分隔合并）
输出：一张多面板 PNG（默认 perf_report.png）

面板布局（2×3）：
  ① 文件大小 vs 解析耗时（散点 + 拟合趋势）
  ② 各文件吞吐（MB/s，横向条形）
  ③ token 用量（prompt/completion 堆叠）
  ④ 资源占用（CPU / 内存峰值）
  ⑤ 汇总卡（文件数 / 总耗时 / 总 token / 总成本 / 平均速度）
  ⑥ 累计耗时曲线（按导入顺序）

配色遵循 gflc-design 纸墨体系：背景 #f7f4ee、墨蓝 #1f4d6b、正文 #1f1b16。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# 纸墨配色（与 gflc-design token 对齐）
BG = "#f7f4ee"
CARD = "#fdfbf7"
INK = "#1f1b16"
INK2 = "#4a4238"
MUTED = "#7b7266"
PRIMARY = "#1f4d6b"
ACCENT = "#f5df87"
SUCCESS = "#2f6b4f"
WARNING = "#8a6220"
BORDER = "#dcd5c8"


def pick_cn_font() -> str:
    """挑一个可用的中文字体，避免方块。"""
    prefer = ["Microsoft YaHei", "SimHei", "Adobe Heiti Std", "Source Han Sans SC",
              "Noto Sans CJK SC", "SimSun", "FangSong"]
    names = {f.name for f in font_manager.fontManager.ttflist}
    for p in prefer:
        if p in names:
            return p
    return "DejaVu Sans"


def load_items(inputs: list[str]) -> list[dict]:
    items: list[dict] = []
    for p in inputs:
        path = Path(p)
        if not path.exists():
            print(f"[skip] 不存在：{p}")
            continue
        d = json.loads(path.read_text(encoding="utf-8"))
        for it in d.get("items") or []:
            if it.get("status") == "succeeded":
                items.append(it)
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="逗号分隔的 JSON 路径")
    ap.add_argument("--out", default="perf_report.png")
    ap.add_argument("--title", default="GFLC 真实数据录入 · 解析性能报告")
    args = ap.parse_args()

    items = load_items([s.strip() for s in args.inputs.split(",") if s.strip()])
    if not items:
        print("[FAIL] 没有成功的条目，无法出报告")
        return 1

    font = pick_cn_font()
    plt.rcParams["font.sans-serif"] = [font]
    plt.rcParams["axes.unicode_minus"] = False

    # 只取有耗时数据的（笔记类无解析耗时，单独计数）
    parsed = [x for x in items if float(x.get("parse_s") or 0) > 0]
    notes_like = [x for x in items if float(x.get("parse_s") or 0) <= 0]

    size_mb = np.array([(x.get("size") or 0) / 1048576 for x in parsed], dtype=float)
    parse_s = np.array([float(x.get("parse_s") or 0) for x in parsed], dtype=float)
    speed = np.array([float(x.get("speed_mb_s") or 0) for x in parsed], dtype=float)
    tok = np.array([float(x.get("tokens_delta") or 0) for x in parsed], dtype=float)
    cpu = np.array([float(x.get("cpu_peak") or 0) for x in parsed], dtype=float)
    mem = np.array([float(x.get("mem_peak") or 0) for x in parsed], dtype=float)
    cost = sum(float(x.get("cost_delta") or 0) for x in items)
    names = [str(x.get("name") or "")[:16] for x in parsed]

    fig = plt.figure(figsize=(17.5, 10.8), dpi=140, facecolor=BG)
    gs = fig.add_gridspec(2, 3, hspace=0.46, wspace=0.26,
                          left=0.055, right=0.975, top=0.875, bottom=0.085)

    def style(ax, title: str):
        ax.set_facecolor(CARD)
        for sp in ax.spines.values():
            sp.set_color(BORDER)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.set_title(title, color=INK, fontsize=12, fontweight="normal", pad=10, loc="left")
        ax.grid(True, color=BORDER, alpha=0.55, linewidth=0.7)
        ax.set_axisbelow(True)

    fig.text(0.055, 0.955, args.title, color=INK, fontsize=17)
    fig.text(0.055, 0.915,
             f"资料 {len(parsed)} 份 · 笔记 {len(notes_like)} 篇 · 字体 {font} · "
             f"数据来自 bulk_ingest 实测，非估算",
             color=MUTED, fontsize=10)

    # ① 大小 vs 耗时
    ax1 = fig.add_subplot(gs[0, 0])
    style(ax1, "① 文件大小 → 解析耗时")
    if len(size_mb):
        ax1.scatter(size_mb, parse_s, s=46, color=PRIMARY, alpha=0.85,
                    edgecolor=CARD, linewidth=1.2, zorder=3)
        if len(size_mb) >= 2 and size_mb.std() > 1e-6:
            k, b = np.polyfit(size_mb, parse_s, 1)
            xs = np.linspace(size_mb.min(), size_mb.max(), 50)
            ax1.plot(xs, k * xs + b, color=WARNING, linewidth=1.6, linestyle="--",
                     label=f"线性趋势 {k:.0f}s/MB")
            # 图例放右下：右上通常是最慢/最大文件的数据点，放右上会遮住它
            ax1.legend(frameon=False, fontsize=9, labelcolor=INK2, loc="lower right")
    ax1.set_xlabel("文件大小 (MB)", color=INK2, fontsize=10)
    ax1.set_ylabel("解析耗时 (秒)", color=INK2, fontsize=10)

    # ② 吞吐
    ax2 = fig.add_subplot(gs[0, 1])
    style(ax2, "② 吞吐速度（MB/s，越低越慢）")
    if len(speed):
        order = np.argsort(speed)
        take = order[: min(12, len(order))]
        ax2.barh(range(len(take)), speed[take], color=PRIMARY, alpha=0.85, height=0.62)
        ax2.set_yticks(range(len(take)))
        ax2.set_yticklabels([names[i] for i in take], fontsize=7, color=INK2)
        # 只有 1 个点时自动 ylim 会把条形放宽到充满面板，这里显式锁住范围
        ax2.set_ylim(-0.8, len(take) - 0.2)
        ax2.set_xlabel("MB/s", color=INK2, fontsize=10)

    # ③ token
    ax3 = fig.add_subplot(gs[0, 2])
    style(ax3, "③ token 用量（视觉识别，单位：千）")
    if len(tok):
        order = np.argsort(-tok)[: min(12, len(tok))]
        ax3.bar(range(len(order)), tok[order] / 1000, color=PRIMARY, alpha=0.85, width=0.66)
        ax3.set_xticks(range(len(order)))
        ax3.set_xticklabels([names[i][:10] for i in order], rotation=45,
                            ha="right", fontsize=7, color=INK2)
        ax3.set_xlim(-0.8, len(order) - 0.2)
        ax3.set_ylabel("千 tokens", color=INK2, fontsize=10)

    # ④ 资源
    ax4 = fig.add_subplot(gs[1, 0])
    style(ax4, "④ 资源占用峰值（%）")
    if len(cpu):
        idx = np.arange(len(parsed))
        ax4.plot(idx, cpu, marker="o", markersize=4, color=PRIMARY, linewidth=1.6, label="CPU")
        ax4.plot(idx, mem, marker="s", markersize=4, color=SUCCESS, linewidth=1.6, label="内存")
        ax4.set_ylim(0, 105)
        ax4.set_xlabel("导入顺序", color=INK2, fontsize=10)
        ax4.set_ylabel("%", color=INK2, fontsize=10)
        ax4.legend(frameon=False, fontsize=9, labelcolor=INK2)

    # ⑤ 汇总卡
    ax5 = fig.add_subplot(gs[1, 1])
    ax5.set_facecolor(CARD)
    for sp in ax5.spines.values():
        sp.set_color(BORDER)
    ax5.set_xticks([]); ax5.set_yticks([])
    ax5.set_title("⑤ 汇总", color=INK, fontsize=12, fontweight="normal", pad=10, loc="left")
    rows = [
        ("资料份数", f"{len(parsed)}"),
        ("笔记篇数", f"{len(notes_like)}"),
        ("总解析耗时", f"{parse_s.sum() / 60:.1f} 分钟"),
        ("平均耗时/份", f"{parse_s.mean():.0f} 秒" if len(parse_s) else "—"),
        ("平均速度", f"{speed.mean():.3f} MB/s" if len(speed) else "—"),
        ("总 tokens", f"{tok.sum():,.0f}"),
        ("总成本", f"¥{cost:.3f}"),
        ("总文件体积", f"{size_mb.sum():.1f} MB"),
    ]
    for i, (k, v) in enumerate(rows):
        y = 0.90 - i * 0.115
        ax5.text(0.06, y, k, color=MUTED, fontsize=10, transform=ax5.transAxes)
        # 不用 monospace：该族在中文字体里往往缺汉字字形，会把「分钟/秒」渲染成方块
        ax5.text(0.94, y, v, color=INK, fontsize=12, ha="right",
                 transform=ax5.transAxes, fontfamily=font)

    # ⑥ 累计耗时
    ax6 = fig.add_subplot(gs[1, 2])
    style(ax6, "⑥ 累计耗时（按导入顺序）")
    if len(parse_s):
        cum = np.cumsum(parse_s) / 60
        xs = np.arange(1, len(cum) + 1)
        ax6.plot(xs, cum, color=PRIMARY, linewidth=2, marker="o" if len(cum) == 1 else None,
                 markersize=6)
        # 单点时 fill_between 会因 x 范围为 0 而画不出，只在 >=2 个点时填充
        if len(cum) >= 2:
            ax6.fill_between(xs, 0, cum, color=PRIMARY, alpha=0.10)
        else:
            ax6.annotate(f"{cum[0]:.1f} 分钟", (xs[0], cum[0]), textcoords="offset points",
                         xytext=(10, 8), color=PRIMARY, fontsize=10)
        ax6.set_xlabel("已完成份数", color=INK2, fontsize=10)
        ax6.set_ylabel("累计分钟", color=INK2, fontsize=10)

    fig.text(0.055, 0.032,
             "口径：解析耗时 = 服务端任务实际耗时（含视觉模型排队）；tokens 来自 cost_ledger（本轮补记账）；"
             "CPU/内存为轮询采样峰值，未做系统级隔离。汇总成本为逐文件增量累加，"
             "预算账本口径为全库累计（见交付报告，含首份数学卷未采集部分）。",
             color=MUTED, fontsize=8.5)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] 报告已生成：{out.resolve()}")
    print(f"     资料 {len(parsed)} 份 / 笔记 {len(notes_like)} 篇 / "
          f"总耗时 {parse_s.sum() / 60:.1f} 分钟 / 总 tokens {tok.sum():,.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
