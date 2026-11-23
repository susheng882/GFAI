#!/usr/bin/env bash
# GFLC V6 备份恢复演练：备份 → 破坏 → 恢复 → 校验 → 输出 RPO/RTO 计时模板
#
# 用法：bash gflc/scripts/drill.sh            （可设 PYTHON=/path/to/python 指定解释器）
# 口号：本演练在临时目录用样本数据进行，所有输出仅为「本机参考值」，
#       不得据此判定 G4 已通过；生产环境必须用真实三容器栈复演并记录 RTO/RPO。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOL="$SCRIPT_DIR/backup_restore.py"
PYTHON="${PYTHON:-python}"
WORK="$(mktemp -d)"

# 跨平台秒差计算（不依赖 bc）
elapsed() { "$PYTHON" -c "print(f'{$2 - $1:.2f}')"; }

echo "============================================================"
echo "GFLC 备份恢复演练（本机参考值 · 生产需复演 · 不判定 G4 通过）"
echo "============================================================"
echo "临时演练目录：$WORK  （演练结束后可人工清理，脚本不执行递归删除）"
echo

# ---------- 0. 造样本数据（仅临时目录，绝不触碰真实 db / 上传目录）----------
DB="$WORK/app.db"
ST="$WORK/storage"
mkdir -p "$ST"
"$PYTHON" - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute("create table docs(id integer primary key, title text)")
con.executemany("insert into docs(title) values(?)", [("资料A",), ("资料B",), ("资料C",)])
con.commit(); con.close()
PY
printf 'sample object payload 1\n' > "$ST/obj-1.txt"
printf 'sample object payload 2\n' > "$ST/obj-2.txt"
BEFORE_ROWS=$("$PYTHON" - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); print(con.execute("select count(*) from docs").fetchone()[0]); con.close()
PY
)
echo "样本：db 初始 $BEFORE_ROWS 行，storage 2 个文件"

# ---------- 1. 备份 ----------
T_BK_START="$(date +%s.%N)"
"$PYTHON" "$TOOL" backup --db-path "$DB" --storage-dir "$ST" --backup-dir "$WORK/backups"
T_BK_END="$(date +%s.%N)"
BID="$(ls -1 "$WORK/backups" | tail -n 1)"
echo "备份 id=$BID，耗时 $(elapsed "$T_BK_START" "$T_BK_END") s"

# ---------- 2. 校验备份 ----------
"$PYTHON" "$TOOL" verify --backup-dir "$WORK/backups" --backup-id "$BID"

# ---------- 3. 破坏（仅临时目录）----------
T_DESTROY="$(date +%s.%N)"
"$PYTHON" - "$DB" "$ST" <<'PY'
import os, sqlite3, sys
db, st = sys.argv[1], sys.argv[2]
con = sqlite3.connect(db); con.execute("drop table docs"); con.commit(); con.close()
for name in os.listdir(st):
    os.remove(os.path.join(st, name))
print("已模拟破坏：drop table + 清空对象存储")
PY
AFTER_DESTROY=$("$PYTHON" - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); print(con.execute("select count(*) from sqlite_master where type='table' and name='docs'").fetchone()[0]); con.close()
PY
)
echo "破坏后 docs 表数量=$AFTER_DESTROY（期望 0）"

# ---------- 4. 恢复（显式 --confirm）----------
T_RS_START="$(date +%s.%N)"
"$PYTHON" "$TOOL" restore --backup-dir "$WORK/backups" --backup-id "$BID" \
    --db-path "$DB" --storage-dir "$ST" --confirm
T_RS_END="$(date +%s.%N)"

# ---------- 5. 恢复后校验 ----------
"$PYTHON" "$TOOL" verify --backup-dir "$WORK/backups" --backup-id "$BID"
RESTORE_ROWS=$("$PYTHON" - "$DB" <<'PY'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1]); print(con.execute("select count(*) from docs").fetchone()[0]); con.close()
PY
)
RESTORE_FILES=$(find "$ST" -type f | wc -l | tr -d ' ')
if [ "$RESTORE_ROWS" != "$BEFORE_ROWS" ] || [ "$RESTORE_FILES" != "2" ]; then
    echo "[drill] 失败：恢复后 db 行数=$RESTORE_ROWS、文件数=$RESTORE_FILES"; exit 1
fi

# ---------- 6. RPO / RTO 计时模板 ----------
RTO="$(elapsed "$T_DESTROY" "$T_RS_END")"
echo
echo "============================================================"
echo "演练结果：备份校验通过 / 破坏成功 / 恢复后 $RESTORE_ROWS 行 + $RESTORE_FILES 文件，一致 ✔"
echo "------------------------------------------------------------"
echo "RPO/RTO 输出模板（本机参考值，生产必须复演后重填）："
echo "| 指标 | 定义 | 本机参考值 | 生产实测值（待填） | 门禁 |"
echo "|---|---|---|---|---|"
echo "| RPO | 故障点距最近一次可用备份的时间 | 同一时刻备份，≈0（不代表生产） | ______ | ≤24h |"
echo "| RTO | 确认破坏 → 恢复并校验完成 | ${RTO} 秒（样本 db） | ______ | ≤4h（回滚场景 ≤10min） |"
echo "------------------------------------------------------------"
echo "注意：本机样本 db 远小于生产库；生产 RTO 需在三容器栈上实测。此结果不构成 G4 通过证据。"
echo "============================================================"
