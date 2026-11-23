#!/usr/bin/env bash
# N4 生产栈冒烟：静态校验（daemon 未启动也能跑）+ 可选在线健康检查清单 + 20 并发压测
#
# 用法：
#   bash gflc/deploy/smoke.sh static                  # 仅 docker compose config 静态校验
#   bash gflc/deploy/smoke.sh live   [BASE_URL]       # 容器起来后做健康检查 + 接口冒烟
#   bash gflc/deploy/smoke.sh stress [BASE_URL]       # 20 并发压测（默认 10min，可覆盖）
# 注意：本脚本不执行 docker compose up；启动由运维在确认 .env 与证书后手动进行。
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"
MODE="${1:-static}"
BASE="${2:-http://127.0.0.1}"

CREATED_ENV=0
static_check() {
    if [ ! -f .env ]; then
        cp .env.example .env
        sed -i -E 's/CHANGE_ME[A-Za-z0-9_]*/DUMMYVALUE/g' .env
        CREATED_ENV=1
        trap 'if [ "$CREATED_ENV" = 1 ]; then rm -f .env; fi' EXIT
        echo "[static] 已用 .env.example 生成临时 .env（校验后自动删除）"
    fi
    docker compose config --quiet
    echo "[static] docker compose config（基础栈）通过"
    docker compose -f docker-compose.yml -f docker-compose.ssl.yml config --quiet
    echo "[static] docker compose config（HTTPS 覆盖层）通过"
    echo "[static] 说明：静态校验不代表容器可启动；daemon 未启动时不得强行 up。"
}

live_check() {
    echo "=== 三容器/五服务健康检查清单 ==="
    echo "[清单] data 层：db(pgvector) / redis / minio；app 层：app；网关层：nginx"
    if ! docker compose ps >/dev/null 2>&1; then
        echo "[live] Docker daemon 未启动或 compose 不可用，跳过容器检查"; return 0
    fi
    docker compose ps
    for svc in db redis minio app nginx; do
        local cid health
        cid="$(docker compose ps -q "$svc" | head -n1)"
        if [ -z "$cid" ]; then echo "  [FAIL] $svc 未运行"; continue; fi
        health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}running{{end}}' "$cid")"
        echo "  [$([ "$health" = healthy ] || [ "$health" = running ] && echo OK || echo FAIL)] $svc: $health"
    done
    echo "=== 接口冒烟 ==="
    echo -n "  /health         -> "; curl -s -o /dev/null -w '%{http_code}\n' "$BASE/health"
    echo -n "  / (前端 HTML)   -> "; curl -s "$BASE/" | grep -o '<html' | head -n1 || echo '非 HTML（需排查）'
    echo -n "  /docs (应 403)  -> "; curl -s -o /dev/null -w '%{http_code}\n' "$BASE/docs"
}

stress_check() {
    python "$DIR/stress_20.py" --url "$BASE/health" --concurrency 20 --seconds 600
}

case "$MODE" in
    static) static_check ;;
    live)   live_check ;;
    stress) stress_check ;;
    *) echo "用法：$0 {static|live|stress} [BASE_URL]" >&2; exit 2 ;;
esac
