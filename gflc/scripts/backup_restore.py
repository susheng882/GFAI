# -*- coding: utf-8 -*-
"""GFLC 备份 / 校验 / 恢复工具（SQLite 数据库 + 对象存储目录）。

对象存储目录口径：
  - 开发环境：LOCAL_STORAGE_DIR（本地磁盘上传目录）；
  - 生产环境：挂载 MinIO 数据卷（miniodata:/data）到本机目录后再备份，
    或用 `mc mirror` 先把桶同步到该目录。本脚本只处理「目录」，不直接连 MinIO API。

命令：
  python scripts/backup_restore.py backup   --db-path D --storage-dir S --backup-dir B [--dry-run]
  python scripts/backup_restore.py verify   --backup-dir B --backup-id <时间戳> [--dry-run]
  python scripts/backup_restore.py restore  --backup-dir B --backup-id <时间戳> \
                                             --db-path D --storage-dir S --confirm [--dry-run]

安全约定：
  - restore 必须显式带 --confirm 才写盘；--dry-run 只打印计划。
  - 恢复前会把当前 db 另存为 <db>.pre-restore-<时间戳>，避免误覆盖后无法回溯。
  - 不联网、不上传备份到第三方；异地保存由运维人工完成。
"""
import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def storage_fingerprint(root: Path) -> dict:
    """目录内容指纹：相对路径 → {size, sha256}，按路径排序保证确定性。"""
    items = {}
    if not root.exists():
        return {"count": 0, "bytes": 0, "files": {}}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = p.relative_to(root).as_posix()
            items[rel] = {"size": p.stat().st_size, "sha256": sha256(p)}
    return {"count": len(items), "bytes": sum(v["size"] for v in items.values()), "files": items}


def _copy_storage(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        print(f"[storage] 源目录不存在，跳过：{src}")
        return
    print(f"[storage] {src} → {dst}")
    if not dry_run:
        shutil.copytree(src, dst, dirs_exist_ok=True)


def cmd_backup(args) -> int:
    bid = args.backup_id or stamp()
    out = Path(args.backup_dir).resolve() / bid
    db_src = Path(args.db_path).resolve() if args.db_path else None
    st_src = Path(args.storage_dir).resolve() if args.storage_dir else None
    print(f"[backup] id={bid} 目标={out}" + ("（dry-run）" if args.dry_run else ""))

    manifest = {"backup_id": bid, "created_at": datetime.now().isoformat(timespec="seconds"),
                "db": None, "storage": None}

    if db_src and db_src.exists():
        db_dst = out / "db" / db_src.name
        print(f"[db] {db_src} → {db_dst}")
        if not args.dry_run:
            db_dst.parent.mkdir(parents=True, exist_ok=True)
            src_con = sqlite3.connect(f"file:{db_src}?mode=ro", uri=True)
            dst_con = sqlite3.connect(str(db_dst))
            try:
                src_con.backup(dst_con)  # 在线安全备份，避开 WAL 拷贝不一致
            finally:
                dst_con.close()
                src_con.close()
        if not args.dry_run:
            manifest["db"] = {"source": str(db_src), "file": str(db_dst.relative_to(out)),
                              "size": db_dst.stat().st_size, "sha256": sha256(db_dst)}
    else:
        print(f"[db] 未提供或不存在，跳过：{db_src}")

    if st_src and st_src.exists():
        st_dst = out / "storage"
        _copy_storage(st_src, st_dst, args.dry_run)
        if not args.dry_run:
            fp = storage_fingerprint(st_dst)
            manifest["storage"] = {"source": str(st_src), "file": "storage", **fp}
    else:
        print(f"[storage] 未提供或不存在，跳过：{st_src}")

    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[backup] 完成，清单：{out / 'manifest.json'}")
    else:
        print("[backup] dry-run 结束，未写任何文件")
    return 0


def cmd_verify(args) -> int:
    out = Path(args.backup_dir).resolve() / args.backup_id
    mpath = out / "manifest.json"
    if not mpath.exists():
        print(f"[verify] 清单不存在：{mpath}", file=sys.stderr)
        return 2
    m = json.loads(mpath.read_text(encoding="utf-8"))
    ok = True

    db = m.get("db")
    if db:
        p = out / db["file"]
        actual = sha256(p) if p.exists() else None
        good = actual == db["sha256"]
        ok &= good
        print(f"[verify] db {p.name}: {'一致' if good else '不一致'} ({actual})")
    else:
        print("[verify] db: 清单中无数据库记录，跳过")

    st = m.get("storage")
    if st:
        actual = storage_fingerprint(out / "storage")
        good = (actual["count"] == st["count"] and actual["files"] == st["files"])
        ok &= good
        print(f"[verify] storage: {'一致' if good else '不一致'} "
              f"({actual['count']} 文件 / {actual['bytes']} 字节)")
    else:
        print("[verify] storage: 清单中无对象存储记录，跳过")

    print(f"[verify] {'通过' if ok else '失败'}（backup_id={args.backup_id}）")
    return 0 if ok else 1


def cmd_restore(args) -> int:
    if not args.confirm and not args.dry_run:
        print("[restore] 拒绝执行：真实恢复必须显式带 --confirm（或用 --dry-run 预览）", file=sys.stderr)
        return 2
    out = Path(args.backup_dir).resolve() / args.backup_id
    mpath = out / "manifest.json"
    if not mpath.exists():
        print(f"[restore] 清单不存在：{mpath}", file=sys.stderr)
        return 2
    m = json.loads(mpath.read_text(encoding="utf-8"))
    tag = stamp()

    db = m.get("db")
    if db:
        src = out / db["file"]
        dst = Path(args.db_path).resolve() if args.db_path else Path(db["source"])
        print(f"[restore] db {src} → {dst}")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                safety = dst.with_name(dst.name + f".pre-restore-{tag}")
                shutil.copy2(dst, safety)
                print(f"[restore] 已保留恢复前副本：{safety}")
            shutil.copy2(src, dst)
    else:
        print("[restore] db: 清单中无记录，跳过")

    st = m.get("storage")
    if st:
        src = out / "storage"
        dst = Path(args.storage_dir).resolve() if args.storage_dir else Path(st["source"])
        print(f"[restore] storage {src} → {dst}")
        if not args.dry_run:
            if dst.exists():
                safety = dst.with_name(dst.name + f".pre-restore-{tag}")
                shutil.copytree(dst, safety, dirs_exist_ok=True)
                print(f"[restore] 已保留恢复前副本：{safety}")
            shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        print("[restore] storage: 清单中无记录，跳过")

    print(f"[restore] {'dry-run 结束，未写盘' if args.dry_run else '完成'}（backup_id={args.backup_id}）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="GFLC 备份/校验/恢复（SQLite + 对象存储目录）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("backup", help="创建备份")
    b.add_argument("--db-path", help="SQLite 数据库文件路径")
    b.add_argument("--storage-dir", help="对象存储目录（本地上传目录 / 挂载的 MinIO 数据目录）")
    b.add_argument("--backup-dir", required=True, help="备份根目录")
    b.add_argument("--backup-id", help="备份 ID，默认当前时间戳")
    b.add_argument("--dry-run", action="store_true")
    b.set_defaults(func=cmd_backup)

    v = sub.add_parser("verify", help="按清单校验备份完整性")
    v.add_argument("--backup-dir", required=True)
    v.add_argument("--backup-id", required=True)
    v.add_argument("--dry-run", action="store_true")
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("restore", help="从备份恢复（需 --confirm）")
    r.add_argument("--backup-dir", required=True)
    r.add_argument("--backup-id", required=True)
    r.add_argument("--db-path", help="恢复目标 db 路径，默认取清单里的 source")
    r.add_argument("--storage-dir", help="恢复目标存储目录，默认取清单里的 source")
    r.add_argument("--confirm", action="store_true", help="确认真实写盘")
    r.add_argument("--dry-run", action="store_true")
    r.set_defaults(func=cmd_restore)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
