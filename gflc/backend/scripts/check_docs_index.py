# -*- coding: utf-8 -*-
"""开发计划索引校验：防止漏号与死链。

用途：CI 或本地提交前跑一次，确保 `开发计划/README.md` 的索引与磁盘实际文件一致。

检查项：
1. 磁盘上每份 `NN_*.md` 都在 README 索引表里出现（漏号即 FAIL）
2. README 里每个相对链接目标都真实存在（死链即 FAIL）
3. README 里的编号不出现磁盘上不存在的文件（幽灵条目即 FAIL）

用法：
    python scripts/check_docs_index.py            # 在仓库根或 gflc/backend 下均可
    python scripts/check_docs_index.py --quiet    # 只输出失败项
退出码：0 全部通过；1 存在问题。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

def _find_root(start: Path) -> Path:
    """从脚本位置向上找含「开发计划」目录的仓库根，避免硬编码层级。"""
    for p in [start, *start.parents]:
        if (p / "开发计划").is_dir():
            return p
    return start


ROOT = _find_root(Path(__file__).resolve())
DOCS = ROOT / "开发计划"
README = DOCS / "README.md"

# 索引表行形如： | 31 | [31_xxx.md](31_xxx.md) | 说明 | 状态 |
ROW_RE = re.compile(r"^\|\s*(\d{2})\s*\|")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#]+)(?:#[^)]*)?\)")


def main() -> int:
    quiet = "--quiet" in sys.argv
    if not README.exists():
        print(f"[FAIL] 缺少索引文件：{README}")
        return 1

    disk_files = sorted(p.name for p in DOCS.glob("*.md") if p.name != "README.md")
    disk_nums = {name[:2] for name in disk_files if name[:2].isdigit()}

    text = README.read_text(encoding="utf-8")
    lines = text.splitlines()

    # 1. 索引表中的编号
    indexed_nums = []
    for line in lines:
        m = ROW_RE.match(line.strip())
        if m:
            indexed_nums.append(m.group(1))
    indexed_set = set(indexed_nums)

    # 2. 链接目标存在性
    dead_links = []
    for target in LINK_RE.findall(text):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        # mockups/ 等子目录路径同样检查
        if not (DOCS / target).exists():
            dead_links.append(target)

    # 3. 差异
    missing = sorted(disk_nums - indexed_set)       # 磁盘有、索引没有
    ghost = sorted(indexed_set - disk_nums)         # 索引有、磁盘没有
    dup = sorted({n for n in indexed_nums if indexed_nums.count(n) > 1})

    problems = 0
    if missing:
        problems += 1
        print(f"[FAIL] 索引漏掉 {len(missing)} 份：{', '.join(missing)}")
    if ghost:
        problems += 1
        print(f"[FAIL] 索引有幽灵条目 {len(ghost)} 个：{', '.join(ghost)}")
    if dup:
        problems += 1
        print(f"[FAIL] 编号重复：{', '.join(dup)}")
    if dead_links:
        problems += 1
        uniq = sorted(set(dead_links))
        print(f"[FAIL] 死链 {len(uniq)} 个：{', '.join(uniq[:10])}"
              + (" …" if len(uniq) > 10 else ""))

    if not problems:
        if not quiet:
            print(f"[OK] 索引完整：磁盘 {len(disk_files)} 份，索引 {len(indexed_set)} 个编号，"
                  f"链接全部有效")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
