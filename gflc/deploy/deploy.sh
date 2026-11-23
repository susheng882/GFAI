#!/usr/bin/env bash
# GFLC 服务器一键部署（Linux）
# 用法：cd /opt/gflc/deploy && chmod +x deploy.sh && ./deploy.sh
set -euo pipefail

echo "=== GFLC 服务器部署 ==="

command -v docker >/dev/null || { echo "未安装 docker"; exit 1; }
docker info >/dev/null 2>&1 || { echo "Docker daemon 未运行"; exit 1; }

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env，请填写所有 CHANGE_ME 项后重新运行。"
  exit 1
fi
if grep -q "CHANGE_ME" .env; then
  echo ".env 仍有 CHANGE_ME 占位符，请先填写真实值。"
  exit 1
fi

echo ">>> 构建 React 前端并落进镜像上下文"
(
  cd ../web
  if [ ! -d node_modules ]; then npm install; fi
  npm run build
)
rm -rf ../backend/frontend/dist
cp -r ../web/dist ../backend/frontend/dist
echo "[OK] 前端产物 -> backend/frontend/dist"

echo ">>> 构建并启动"
docker compose build
docker compose up -d

echo ">>> 等待服务健康（最长 180s）"
for i in $(seq 1 60); do
  if docker compose exec -T app curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "[OK] 服务已就绪"
    break
  fi
  sleep 3
  if [ "$i" -eq 60 ]; then
    echo "服务未就绪，请查看：docker compose logs -f app"
    exit 1
  fi
done

echo ">>> 当前状态"
docker compose ps
echo "访问地址：http://$(hostname -I | awk '{print $1}')"
