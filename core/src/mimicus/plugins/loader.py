from __future__ import annotations

import hashlib
from pathlib import Path


def verify_allowlisted_plugin(path: str | Path, allowlisted_roots: list[str | Path], expected_sha256: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    roots = [Path(root).expanduser().resolve() for root in allowlisted_roots]
    if not any(resolved == root or root in resolved.parents for root in roots):
        raise PermissionError(f"plugin path is not allow-listed: {resolved}")
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest()
    if digest != expected_sha256:
        raise ValueError("plugin source hash mismatch")
    return resolved
