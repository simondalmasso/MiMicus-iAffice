from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from .config import WRITE_LOCK_ERROR

WRITE_TOKENS = {
    "create-topic", "create_topic", "createnewtopic", "fund-topic", "fund_topic",
    "register", "remove-registration", "remove_registration", "insert-worker-payload",
    "insert_worker_payload", "insert-bulk-worker-payload", "insert_bulk_worker_payload",
    "insert-reputer-payload", "insert_reputer_payload", "insert-bulk-reputer-payload",
    "insert_bulk_reputer_payload", "add-stake", "add_stake", "remove-stake", "remove_stake",
    "delegate-stake", "delegate_stake", "broadcast", "tx", "msgservice", "msgcreate",
    "msgfund", "msgregister", "msgaddstake", "msgdelegatestake",
}

WRITE_PATH_FRAGMENTS = ("/cosmos/tx/", "/txs", "/broadcast_tx", "/emissions/v9/tx", "/emissions/v10/tx")

SECRET_PATTERNS = {
    "private_key_pem": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "bearer_token": re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    "openai_style_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "assigned_private_key": re.compile(r"(?i)\bprivate[_ -]?key\s*[:=]\s*[\"']?[A-Za-z0-9+/=_-]{24,}"),
    "assigned_api_key": re.compile(r"(?i)\bapi[_ -]?key\s*[:=]\s*[\"']?[A-Za-z0-9._-]{20,}"),
    "assigned_mnemonic": re.compile(r"(?i)\bmnemonic\s*[:=]\s*[\"']?(?:[a-z]+\s+){11,23}[a-z]+"),
    "credential_url": re.compile(r"https?://[^\s/@:]+:[^\s/@]+@[^\s/]+"),
}


class LiveExecutionProhibited(RuntimeError):
    pass


def assert_read_only_operation(operation: str) -> None:
    low = operation.lower().strip()
    normalized = re.sub(r"[^a-z0-9_/-]+", "", low)
    if any(token in normalized for token in WRITE_TOKENS):
        raise LiveExecutionProhibited(WRITE_LOCK_ERROR)
    if any(fragment in low for fragment in WRITE_PATH_FRAGMENTS):
        raise LiveExecutionProhibited(WRITE_LOCK_ERROR)
    if re.search(r"\bmsg[a-z0-9_]+\b", low):
        raise LiveExecutionProhibited(WRITE_LOCK_ERROR)


def assert_safe_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError("Only HTTPS read endpoints are allowed")
    if parsed.username or parsed.password:
        raise ValueError("Credential-bearing URL rejected")
    low = parsed.path.lower()
    if any(fragment in low for fragment in WRITE_PATH_FRAGMENTS) or re.search(r"/msg[a-z0-9_/-]*", low):
        raise LiveExecutionProhibited(WRITE_LOCK_ERROR)


def scan_text_for_secrets(text: str) -> list[str]:
    return [name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)]


def scan_tree(root: Path) -> list[tuple[str, str]]:
    findings: list[tuple[str, str]] = []
    ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache", ".allora-edge"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored_parts for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for finding in scan_text_for_secrets(text):
            findings.append((str(path.relative_to(root)), finding))
    return findings
