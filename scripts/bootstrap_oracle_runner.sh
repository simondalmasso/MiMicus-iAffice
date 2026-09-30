#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${GITHUB_REPOSITORY_URL:-https://github.com/simondalmasso/the-iAffice}"
RUNNER_DIR="${IAFFICE_RUNNER_DIR:-/opt/actions-runner}"
RUNNER_USER="${IAFFICE_RUNNER_USER:-iaffice-runner}"
RUNNER_NAME="${IAFFICE_RUNNER_NAME:-iaffice-oracle-free}"
RUNNER_LABELS="oracle-free,iaffice"

if [[ "${EUID}" -ne 0 ]]; then
  echo "ROOT_REQUIRED" >&2
  exit 2
fi
if [[ -z "${GITHUB_RUNNER_TOKEN:-}" ]]; then
  echo "GITHUB_RUNNER_TOKEN_REQUIRED" >&2
  exit 3
fi
command -v curl >/dev/null || { echo "CURL_REQUIRED" >&2; exit 4; }
command -v python3 >/dev/null || { echo "PYTHON3_REQUIRED" >&2; exit 5; }

arch="$(uname -m)"
case "$arch" in
  x86_64|amd64) runner_arch="x64" ;;
  aarch64|arm64) runner_arch="arm64" ;;
  *) echo "UNSUPPORTED_ARCH:$arch" >&2; exit 6 ;;
esac

meta="$(mktemp)"
trap 'rm -f "$meta"' EXIT
curl --fail --silent --show-error --location   -H 'Accept: application/vnd.github+json'   https://api.github.com/repos/actions/runner/releases/latest > "$meta"

read -r version asset_url digest < <(python3 - "$meta" "$runner_arch" <<'PY'
import json,sys
data=json.load(open(sys.argv[1],encoding='utf-8'))
arch=sys.argv[2]
name=f"actions-runner-linux-{arch}-{data['tag_name'].lstrip('v')}.tar.gz"
asset=next((a for a in data.get('assets',[]) if a.get('name')==name),None)
if not asset:
    raise SystemExit("RUNNER_ASSET_NOT_FOUND")
digest=asset.get('digest') or ''
if not digest.startswith('sha256:'):
    raise SystemExit("RUNNER_DIGEST_UNAVAILABLE")
print(data['tag_name'],asset['browser_download_url'],digest)
PY
)

if ! id "$RUNNER_USER" >/dev/null 2>&1; then
  useradd --system --create-home --shell /bin/bash "$RUNNER_USER"
fi
install -d -m 0755 -o "$RUNNER_USER" -g "$RUNNER_USER" "$RUNNER_DIR"

tarball="$(mktemp --suffix=.tar.gz)"
trap 'rm -f "$meta" "$tarball"' EXIT
curl --fail --silent --show-error --location "$asset_url" -o "$tarball"
actual="sha256:$(sha256sum "$tarball" | awk '{print $1}')"
if [[ "$actual" != "$digest" ]]; then
  echo "RUNNER_DIGEST_MISMATCH" >&2
  exit 7
fi

rm -rf "$RUNNER_DIR"/*
tar -xzf "$tarball" -C "$RUNNER_DIR"
chown -R "$RUNNER_USER:$RUNNER_USER" "$RUNNER_DIR"

sudo -u "$RUNNER_USER" "$RUNNER_DIR/config.sh"   --url "$REPO_URL"   --token "$GITHUB_RUNNER_TOKEN"   --name "$RUNNER_NAME"   --labels "$RUNNER_LABELS"   --unattended   --replace

"$RUNNER_DIR/svc.sh" install "$RUNNER_USER"
"$RUNNER_DIR/svc.sh" start

echo "RUNNER_READY:$RUNNER_NAME"
echo "LABELS=self-hosted,linux,$RUNNER_LABELS"
