#!/usr/bin/env bash
# 同时启动后端 9 个服务 + 前端 dev server，并把前端切到 gateway 模式。
#
# 用法：
#   bash scripts/dev_up.sh
#
# 启动后：
#   - http://127.0.0.1:3000             前端
#   - http://127.0.0.1:8000/health      gateway
#   - 各服务日志见 output/service-logs/*.log 与 output/logs/*.jsonl
#
# Ctrl+C 同时停掉所有子进程。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/output/service-logs"
mkdir -p "${LOG_DIR}"

if ! command -v npm >/dev/null 2>&1; then
  echo "[dev_up] npm not found; please install Node.js 20+" >&2
  exit 1
fi

if [[ ! -d "${ROOT}/frontend/node_modules" ]]; then
  echo "[dev_up] frontend deps missing. Run: (cd frontend && npm install)" >&2
  exit 1
fi

# Run preflight + start backend in background.
bash "${ROOT}/scripts/run_all_services.sh" --check
echo "[dev_up] starting backend stack..."
bash "${ROOT}/scripts/run_all_services.sh" &
BACKEND_PID=$!

cleanup() {
  echo
  echo "[dev_up] stopping backend (pid ${BACKEND_PID}) and frontend..."
  kill "${BACKEND_PID}" 2>/dev/null || true
  if [[ -n "${FRONTEND_PID:-}" ]]; then
    kill "${FRONTEND_PID}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

# Give backend a chance to bind sockets.
sleep 3

echo "[dev_up] starting frontend (gateway mode)"
(
  cd "${ROOT}/frontend"
  NEXT_PUBLIC_KANSHAN_BACKEND_MODE=gateway \
  NEXT_PUBLIC_KANSHAN_GATEWAY_URL="http://127.0.0.1:8000" \
  NEXT_PUBLIC_ZHIHU_ADAPTER_URL="http://127.0.0.1:8070" \
  npm run dev
) &
FRONTEND_PID=$!

echo
echo "[dev_up] frontend  http://127.0.0.1:3000"
echo "[dev_up] gateway   http://127.0.0.1:8000/health"
echo "[dev_up] adapter   http://127.0.0.1:8070/health"
echo
wait
