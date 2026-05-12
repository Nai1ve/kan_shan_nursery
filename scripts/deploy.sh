#!/usr/bin/env bash
# Kanshan deployment script
#
# Usage:
#   bash scripts/deploy.sh           # Start containers
#   bash scripts/deploy.sh --build   # Rebuild images and start
#   bash scripts/deploy.sh --down    # Stop containers
#   bash scripts/deploy.sh --logs    # View logs
#   bash scripts/deploy.sh --mirror  # Configure Docker mirror (China)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="${ROOT}/infra"

# Ensure .env exists
if [[ ! -f "${INFRA_DIR}/.env" ]]; then
  echo "[deploy] No .env found. Copying from .env.deploy..."
  cp "${INFRA_DIR}/.env.deploy" "${INFRA_DIR}/.env"
fi

# --- Docker mirror configuration (China) ---
configure_mirror() {
  local DAEMON_JSON="/etc/docker/daemon.json"
  echo "[deploy] Configuring Docker mirror for China..."

  if [[ ! -f "$DAEMON_JSON" ]] || ! grep -q "registry-mirrors" "$DAEMON_JSON" 2>/dev/null; then
    sudo mkdir -p /etc/docker
    sudo tee "$DAEMON_JSON" > /dev/null <<'MIRROR'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.m.daocloud.io",
    "https://dockerhub.icu"
  ]
}
MIRROR
    sudo systemctl daemon-reload
    sudo systemctl restart docker
    echo "[deploy] Docker mirror configured. Restarting Docker daemon..."
    sleep 3
    echo "[deploy] Done. Docker daemon restarted."
  else
    echo "[deploy] Docker mirror already configured."
  fi
}

cd "${INFRA_DIR}"

case "${1:-}" in
  --mirror)
    configure_mirror
    ;;
  --build)
    echo "[deploy] Building images and starting containers..."
    docker compose build
    docker compose up -d
    echo "[deploy] Containers started. Use 'bash scripts/deploy.sh --logs' to view logs."
    ;;
  --down)
    echo "[deploy] Stopping containers..."
    docker compose down
    ;;
  --logs)
    docker compose logs -f
    ;;
  "")
    echo "[deploy] Starting containers..."
    docker compose up -d
    echo "[deploy] Containers started. Use 'bash scripts/deploy.sh --logs' to view logs."
    ;;
  *)
    echo "Usage: bash scripts/deploy.sh [--build|--down|--logs|--mirror]"
    exit 1
    ;;
esac
