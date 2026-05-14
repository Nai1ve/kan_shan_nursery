#!/usr/bin/env bash
# 看山小苗圃一键部署脚本。
#
# 默认行为：
#   1. 读取 infra/.env
#   2. 校验当前 Docker 部署实际会读取的环境变量
#   3. docker compose build + up -d
#   4. 等待服务健康
#   5. 验证 OAuth 关键链路
#
# 用法：
#   bash scripts/deploy.sh              # 一键构建并启动
#   bash scripts/deploy.sh --no-build   # 不重新构建，直接启动
#   bash scripts/deploy.sh --check      # 只检查 infra/.env
#   bash scripts/deploy.sh --doctor     # 检查已启动容器和 OAuth 链路
#   bash scripts/deploy.sh --logs       # 查看日志
#   bash scripts/deploy.sh --down       # 停止容器
#   bash scripts/deploy.sh --mirror     # 配置 Docker 镜像加速
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"
ENV_FILE="${INFRA_DIR}/.env"
ENV_TEMPLATE="${INFRA_DIR}/.env.deploy"
COMPOSE_FILE="${INFRA_DIR}/docker-compose.yml"

ACTION="${1:-deploy}"

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

fail() {
  echo "[deploy][ERROR] $*" >&2
  exit 1
}

warn() {
  echo "[deploy][WARN] $*" >&2
}

info() {
  echo "[deploy] $*"
}

ensure_env_file() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ENV_TEMPLATE}" "${ENV_FILE}"
    fail "infra/.env 不存在，已从 infra/.env.deploy 生成。请先填写真实配置后再运行。"
  fi
}

load_env_file() {
  ensure_env_file
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a

  # 兼容旧部署变量名：代码实际读取 OPENAI_COMPAT_*。
  if [[ -z "${OPENAI_COMPAT_BASE_URL:-}" && -n "${LLM_API_BASE_URL:-}" ]]; then
    export OPENAI_COMPAT_BASE_URL="${LLM_API_BASE_URL}"
  fi
  if [[ -z "${OPENAI_COMPAT_API_KEY:-}" && -n "${LLM_API_KEY:-}" ]]; then
    export OPENAI_COMPAT_API_KEY="${LLM_API_KEY}"
  fi
}

has_placeholder() {
  local value="${1:-}"
  [[ -z "${value}" || "${value}" == *"<"* || "${value}" == *">"* || "${value}" == "你的"* ]]
}

require_var() {
  local name="$1"
  local value="${!name:-}"
  if has_placeholder "${value}"; then
    fail "infra/.env 缺少有效配置：${name}"
  fi
}

validate_env() {
  load_env_file

  require_var POSTGRES_PASSWORD
  require_var DATABASE_URL
  require_var KANSHAN_GATEWAY_URL
  require_var PROVIDER_MODE
  require_var STORAGE_BACKEND

  if [[ "${STORAGE_BACKEND}" != "postgres" ]]; then
    warn "当前 STORAGE_BACKEND=${STORAGE_BACKEND}，生产建议使用 postgres。"
  fi

  if [[ "${PROVIDER_MODE}" == "live" ]]; then
    require_var ZHIHU_APP_KEY
    require_var ZHIHU_APP_SECRET
    require_var ZHIHU_ACCESS_SECRET
    require_var ZHIHU_OAUTH_APP_ID
    require_var ZHIHU_OAUTH_APP_KEY
    require_var ZHIHU_OAUTH_REDIRECT_URI

    if [[ "${ZHIHU_OAUTH_REDIRECT_URI}" != */auth/zhihu/callback ]]; then
      fail "ZHIHU_OAUTH_REDIRECT_URI 必须以 /auth/zhihu/callback 结尾，当前=${ZHIHU_OAUTH_REDIRECT_URI}"
    fi

    if [[ "${ZHIHU_OAUTH_REDIRECT_URI}" == *"127.0.0.1"* || "${ZHIHU_OAUTH_REDIRECT_URI}" == *"localhost"* ]]; then
      fail "线上 live 模式不能使用本地 OAuth 回调：${ZHIHU_OAUTH_REDIRECT_URI}"
    fi
  fi

  if [[ "${LLM_PROVIDER_MODE:-mock}" == "openai_compat" ]]; then
    require_var OPENAI_COMPAT_BASE_URL
    require_var OPENAI_COMPAT_API_KEY
    require_var OPENAI_COMPAT_MODEL
  fi

  info "配置检查通过。实际容器配置来源：infra/.env + docker-compose environment。"
}

configure_mirror() {
  local daemon_json="/etc/docker/daemon.json"
  info "配置 Docker 镜像加速..."
  sudo mkdir -p /etc/docker
  sudo tee "${daemon_json}" >/dev/null <<'JSON'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.m.daocloud.io",
    "https://dockerhub.icu"
  ],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
JSON
  sudo systemctl daemon-reload
  sudo systemctl restart docker
  info "Docker 已重启。"
}

wait_http() {
  local name="$1"
  local url="$2"
  local timeout="${3:-90}"
  local start
  start="$(date +%s)"
  until curl -fsS "${url}" >/dev/null 2>&1; do
    if (( "$(date +%s)" - start > timeout )); then
      fail "${name} 健康检查超时：${url}"
    fi
    sleep 2
  done
  info "${name} OK: ${url}"
}

wait_services() {
  wait_http "api-gateway" "http://127.0.0.1:${API_GATEWAY_PORT:-8000}/health" 120
  wait_http "profile-service" "http://127.0.0.1:8010/health" 90
  wait_http "content-service" "http://127.0.0.1:8020/health" 90
  wait_http "seed-service" "http://127.0.0.1:8030/health" 90
  wait_http "sprout-service" "http://127.0.0.1:8040/health" 90
  wait_http "writing-service" "http://127.0.0.1:8050/health" 90
  wait_http "feedback-service" "http://127.0.0.1:8060/health" 90
  wait_http "zhihu-adapter" "http://127.0.0.1:8070/health" 90
  wait_http "llm-service" "http://127.0.0.1:8080/health" 90
}

doctor() {
  load_env_file
  info "检查容器状态..."
  compose ps

  wait_services

  info "检查 profile-service -> zhihu-adapter 容器内网络..."
  compose exec -T profile-service python - <<'PY'
import urllib.request
print(urllib.request.urlopen("http://zhihu-adapter:8070/health", timeout=5).read().decode())
PY

  info "检查 OAuth 授权入口..."
  local gateway="${KANSHAN_GATEWAY_URL%/}"
  local auth_url="${gateway}/api/v1/auth/zhihu/authorize"
  local body
  body="$(curl -fsS "${auth_url}")" || fail "OAuth 授权入口不可用：${auth_url}"
  echo "${body}"

  if [[ "${PROVIDER_MODE:-mock}" == "live" ]]; then
    if [[ "${body}" != *"authorize"* || "${body}" != *"redirect_uri"* ]]; then
      fail "OAuth 授权入口返回不像真实知乎授权 URL，请检查 ZHIHU_OAUTH_* 配置。"
    fi
  fi

  info "部署自检完成。"
}

deploy() {
  validate_env

  info "启动 Docker Compose。前端环境变量是构建期写入，默认会重新 build。"
  compose up -d --build
  wait_services
  doctor

  info "部署完成。前端入口：${KANSHAN_GATEWAY_URL%/}"
}

deploy_no_build() {
  validate_env
  compose up -d
  wait_services
  doctor
}

case "${ACTION}" in
  deploy|"")
    deploy
    ;;
  --no-build)
    deploy_no_build
    ;;
  --check)
    validate_env
    ;;
  --doctor)
    doctor
    ;;
  --down)
    ensure_env_file
    compose down
    ;;
  --logs)
    ensure_env_file
    compose logs -f
    ;;
  --mirror)
    configure_mirror
    ;;
  *)
    cat <<'EOF'
Usage:
  bash scripts/deploy.sh              # 一键构建并启动
  bash scripts/deploy.sh --no-build   # 不重新构建
  bash scripts/deploy.sh --check      # 只检查 infra/.env
  bash scripts/deploy.sh --doctor     # 检查已启动服务和 OAuth 链路
  bash scripts/deploy.sh --logs       # 查看日志
  bash scripts/deploy.sh --down       # 停止服务
  bash scripts/deploy.sh --mirror     # 配置 Docker 镜像加速
EOF
    exit 1
    ;;
esac
