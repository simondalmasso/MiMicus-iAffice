from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

from mimicus.falsifiers.spec import FalsifierSpec


FORBIDDEN_DYNAMIC_CALLS = {"exec", "eval", "compile"}


def dynamic_code_execution_findings(paths: Iterable[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        if not path.is_file() or path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_DYNAMIC_CALLS:
                findings.append(f"{path}:{node.lineno}:{node.func.id}")
    return findings


def spec_rejects_source_payload(base: dict[str, object]) -> bool:
    payload = dict(base)
    payload["params"] = {"script": "untrusted generated program"}
    try:
        FalsifierSpec.model_validate(payload)
    except ValidationError:
        return True
    return False
