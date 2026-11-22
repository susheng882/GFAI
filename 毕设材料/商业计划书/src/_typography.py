# -*- coding: utf-8 -*-
"""全局字号治理：消除 7 px 级小字，使 A4 册页内文字可读。
规则：字号 <10 px 统一 +1.2 px，下限 8.8、上限 9.8；≥10 px 的标题/图题保持不动。
图例行（frame 模板 y=878）保持原字号，避免长图例溢出；处理带幂等标记，可重复执行。
注意：本脚本必须作为流水线最后一步运行（在 _build_figs_* / _normalize 之后）。
"""
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).parent
MARK = "typography-v2"


def bump(v: float) -> float:
    if v >= 10.0:
        return v
    return max(8.8, min(9.8, round(v + 1.2, 2)))


def main():
    n_file, n_text = 0, 0
    for f in sorted(ROOT.glob("*.svg")):
        s = f.read_text(encoding="utf-8")
        if MARK in s:
            print("  skip (already processed):", f.name)
            continue
        root = etree.fromstring(s.encode("utf-8"))
        cnt = 0
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            if etree.QName(el).localname == "text" and el.get("y") == "878":
                continue                      # 长图例行不放大
            fs = el.get("font-size")
            if fs:
                try:
                    nv = bump(float(fs))
                except ValueError:
                    continue
                if abs(nv - float(fs)) > 1e-6:
                    el.set("font-size", f"{nv:g}")
                    cnt += 1
        out = etree.tostring(root, encoding="unicode")
        f.write_text(f"<!-- {MARK} -->\n" + out, encoding="utf-8")
        n_file += 1
        n_text += cnt
        print(f"  {f.name[:36]:<38} bumped {cnt}")
    print(f"TOTAL: {n_file} files, {n_text} text nodes")


if __name__ == "__main__":
    main()
