#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${IAFFICE_REPO_DIR:-/opt/iaffice}"
SERVICE_USER="${IAFFICE_EXECUTOR_USER:-iaffice}"
STATE_DIR="${IAFFICE_EXECUTOR_ROOT:-/var/lib/iaffice-executor}"
ENV_DIR="/etc/iaffice"
UNIT_SRC="$REPO_DIR/apps/oracle-executor/iaffice-executor.service"
ENV_SRC="$REPO_DIR/apps/oracle-executor/executor.env.example"
UNIT_DST="/etc/systemd/system/iaffice-executor.service"
ENV_DST="$ENV_DIR/executor.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ROOT_REQUIRED" >&2
  exit 2
fi
if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "REPO_NOT_FOUND:$REPO_DIR" >&2
  exit 3
fi
command -v python3 >/dev/null || { echo "PYTHON3_REQUIRED" >&2; exit 4; }
python3 -m py_compile "$REPO_DIR/apps/oracle-executor/iaffice_executor.py"

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$STATE_DIR" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -m 0750 -o "$SERVICE_USER" -g "$SERVICE_USER" "$STATE_DIR"
install -d -m 0750 "$ENV_DIR"
install -m 0644 "$UNIT_SRC" "$UNIT_DST"

if [[ ! -f "$ENV_DST" ]]; then
  install -m 0600 "$ENV_SRC" "$ENV_DST"
  echo "CONFIG_CREATED:$ENV_DST"
  echo "SET_IAFFICE_EXECUTOR_SIGNING_KEY_AND_HTTPS_ENDPOINT_BEFORE_START"
fi

chown root:root "$ENV_DST"
chmod 0600 "$ENV_DST"
systemctl daemon-reload
systemctl enable iaffice-executor.service >/dev/null

echo "INSTALLED_NOT_STARTED"
echo "NEXT=configure $ENV_DST, expose 127.0.0.1:8788 through trusted HTTPS, then systemctl start iaffice-executor"
