#!/usr/bin/env bash
set -Eeuo pipefail

TYPESCRIPT_VERSION="${IAFFICE_TYPESCRIPT_VERSION:-5.9.3}"
PLAYWRIGHT_VERSION="${IAFFICE_PLAYWRIGHT_VERSION:-1.55.0}"

command -v node >/dev/null || { echo "NODE_REQUIRED" >&2; exit 2; }
command -v npm >/dev/null || { echo "NPM_REQUIRED" >&2; exit 3; }
command -v python3 >/dev/null || { echo "PYTHON3_REQUIRED" >&2; exit 4; }

npm install --global --ignore-scripts "typescript@$TYPESCRIPT_VERSION"
python3 -m pip install --user --disable-pip-version-check "playwright==$PLAYWRIGHT_VERSION"
python3 -m playwright install chromium

echo "TSC=$(tsc --version)"
python3 - <<'PY'
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    print("PLAYWRIGHT_CHROMIUM="+p.chromium.name)
PY
