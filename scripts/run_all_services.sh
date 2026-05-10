#!/usr/bin/env bash
# 一次性启动 P0 闭环涉及的 8 个后端服务（mock 模式）。
# 使用方式：
#   bash scripts/run_all_services.sh
# 退出：Ctrl+C 会触发 trap，停掉所有子进程。

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/output/service-logs"
mkdir -p "${LOG_DIR}"

declare -a NAMES=(
  "profile-service"
  "content-service"
  "seed-service"
  "sprout-service"
  "writing-service"
  "feedback-service"
  "zhihu-adapter"
  "llm-service"
  "api-gateway"
)
declare -a PORTS=(8010 8020 8030 8040 8050 8060 8070 8080 8000)

PIDS=()
cleanup() {
  echo
  echo "[run_all_services] stopping ${#PIDS[@]} services..."
  for pid in "${PIDS[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

for i in "${!NAMES[@]}"; do
  name="${NAMES[$i]}"
  port="${PORTS[$i]}"
  log="${LOG_DIR}/${name}.log"
  echo "[run_all_services] starting ${name} on :${port} (log=${log})"
  (
    cd "${ROOT}/services/${name}"
    exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${port}" >"${log}" 2>&1
  ) &
  PIDS+=("$!")
done

echo "[run_all_services] all services launched. Tail logs in ${LOG_DIR}/*.log"
echo "[run_all_services] gateway health: curl http://127.0.0.1:8000/health"
wait
