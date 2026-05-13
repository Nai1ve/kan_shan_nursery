#!/usr/bin/env bash
# 停止 dev_up.sh 启动的所有后端服务 + 前端 dev server。
#
# 用法：
#   bash scripts/dev_down.sh
set -euo pipefail

killed=0

# 停止 uvicorn 后端进程
for pid in $(pgrep -f "uvicorn app.main:app" 2>/dev/null || true); do
  kill "$pid" 2>/dev/null || true
  killed=$((killed + 1))
done

# 停止 next dev 前端进程
for pid in $(pgrep -f "next-server|next dev" 2>/dev/null || true); do
  kill "$pid" 2>/dev/null || true
  killed=$((killed + 1))
done

# 等待进程退出，超时 3 秒后强制杀
sleep 1
for pid in $(pgrep -f "uvicorn app.main:app|next-server|next dev" 2>/dev/null || true); do
  kill -9 "$pid" 2>/dev/null || true
done

if [[ $killed -gt 0 ]]; then
  echo "[dev_down] stopped ${killed} process(es)"
else
  echo "[dev_down] no running services found"
fi
