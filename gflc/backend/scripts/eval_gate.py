# -*- coding: utf-8 -*-
"""CI 质量门禁：两份相邻版本报告比较，任一指标下降 >3 个百分点即非零退出。

用法：
  # 显式指定两份报告（推荐 CI 绑定「禁止打 tag」时使用）
  python scripts/eval_gate.py --prev evals/reports/v1.0/report.json \
                              --curr evals/reports/v1.1/report.json

  # 自动取 evals/reports/ 下版本号最大的两份
  python scripts/eval_gate.py --reports-dir evals/reports

退出码：0 = 六项指标均未退化超过阈值；1 = 存在退化 >阈值；2 = 参数/报告错误。
"""
import argparse
import json
import re
import sys
from pathlib import Path

METRICS = ["召回率", "命中率", "MRR", "忠实度", "拒答准确率", "卡片可用率"]


def _version_key(name: str):
    nums = re.findall(r"\d+", name)
    return ([int(x) for x in nums], name)


def discover(reports_dir: Path) -> tuple[Path, Path]:
    dirs = [d for d in reports_dir.iterdir()
            if d.is_dir() and (d / "report.json").exists()]
    if len(dirs) < 2:
        raise ValueError(f"报告不足两份：{reports_dir}（找到 {len(dirs)} 份）")
    dirs.sort(key=lambda d: _version_key(d.name))
    prev, curr = dirs[-2], dirs[-1]
    return prev / "report.json", curr / "report.json"


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "metrics" not in data:
        raise ValueError(f"报告缺少 metrics 字段：{path}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="GFLC 评测回归门禁（下降 >3pp 即失败）")
    ap.add_argument("--prev", type=Path, help="上一版本 report.json")
    ap.add_argument("--curr", type=Path, help="当前版本 report.json")
    ap.add_argument("--reports-dir", type=Path, help="报告根目录，自动取最新两版")
    ap.add_argument("--drop-pp", type=float, default=3.0, help="允许的下降百分点，默认 3.0")
    args = ap.parse_args()

    try:
        if args.reports_dir:
            prev_path, curr_path = discover(args.reports_dir)
        elif args.prev and args.curr:
            prev_path, curr_path = args.prev, args.curr
        else:
            raise ValueError("请提供 --prev 与 --curr，或 --reports-dir")
        prev, curr = load(prev_path), load(curr_path)
    except (OSError, ValueError, json.JSONDecodeError) as e:
        print(f"[eval_gate] 参数/报告错误：{e}", file=sys.stderr)
        return 2

    print(f"[eval_gate] {prev.get('version', '?')} → {curr.get('version', '?')}  "
          f"（退化容忍 {args.drop_pp} 个百分点）")
    print(f"{'指标':<10}{'上版':>10}{'本版':>10}{'变化(pp)':>12}  结果")
    failed = []
    for name in METRICS:
        a, b = prev["metrics"].get(name), curr["metrics"].get(name)
        if a is None or b is None:
            print(f"{name:<10}{str(a):>10}{str(b):>10}{'n/a':>12}  跳过（缺指标）")
            continue
        delta = round(float(b) - float(a), 2)
        ok = delta >= -args.drop_pp
        if not ok:
            failed.append((name, delta))
        print(f"{name:<10}{float(a):>10.2f}{float(b):>10.2f}{delta:>+12.2f}  "
              f"{'PASS' if ok else 'FAIL'}")

    if failed:
        print("\n[eval_gate] 门禁未通过：" + "；".join(f"{n} {d:+.2f}pp" for n, d in failed))
        print("[eval_gate] 禁止打 tag / 禁止发布，需回滚或修复后重跑评测。")
        return 1
    print("\n[eval_gate] 门禁通过：六项指标均未退化超过阈值。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
