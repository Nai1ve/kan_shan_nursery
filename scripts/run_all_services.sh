#!/usr/bin/env bash
# 启动 9 个后端服务（mock 默认；live 由 services/config.yaml 控制）。
#
# 用法：
#   bash scripts/run_all_services.sh          # 前台启动，Ctrl+C 退出
#   bash scripts/run_all_services.sh --check  # 只做依赖体检，不启动
#
# 依赖（首次跑前请确认）：
#   1) Python 3.10+
#   2) pip install -r services/<svc>/requirements.txt （首次安装见下方）
#   3) services/config.yaml 已存在；模板见 services/config.example.yaml
#
# 注意：脚本会把每个服务的 stdout/stderr 写到 output/service-logs/<svc>.log，
# 控制台只看到启动条目；评测/调试请 tail 对应 log 文件，或直接看
# output/logs/<svc>-YYYY-MM-DD.jsonl。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT}/output/service-logs"
mkdir -p "${LOG_DIR}"

# ---- preflight ---------------------------------------------------------------

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[preflight] python3 not found in PATH" >&2
    exit 1
  fi
  python3 -c 'import sys; assert sys.version_info >= (3, 10), sys.version_info'
}

check_fastapi() {
  if ! python3 -c "import fastapi, uvicorn" >/dev/null 2>&1; then
    echo "[preflight] fastapi/uvicorn not importable. Install with:" >&2
    echo "  for s in services/*/; do pip install -r \"\$s/requirements.txt\"; done" >&2
    exit 1
  fi
}

check_config() {
  if [[ ! -f "${ROOT}/services/config.yaml" ]]; then
    echo "[preflight] services/config.yaml missing. Copy services/config.example.yaml first." >&2
    echo "  cp services/config.example.yaml services/config.yaml" >&2
    exit 1
  fi
}

check_python
check_fastapi
check_config

if [[ "${1:-}" == "--check" ]]; then
  echo "[preflight] OK (python3 + fastapi + services/config.yaml)"
  exit 0
fi

# ---- launch -----------------------------------------------------------------

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

echo
echo "[run_all_services] all 9 services launched."
echo "  - tail logs: tail -f ${LOG_DIR}/*.log"
echo "  - structured: tail -f output/logs/<service>-$(date +%F).jsonl"
echo "  - gateway health: curl -s http://127.0.0.1:8000/health | python3 -m json.tool"
echo
wait
