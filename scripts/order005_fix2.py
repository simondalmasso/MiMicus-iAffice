from pathlib import Path


def patch(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing anchor: {path}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


patch(
    "tests/integration/test_order005_runtime.py",
    "from mimicus.agents.bankruptcy import capability_scope\n",
    "from mimicus.agents.calibration import capability_scope\n",
)
patch(
    "src/mimicus/validation/order003_worker.py",
    "    assert write_gate(verified).allowed\n",
    "    assert write_gate(verified).status == MemoryStatus.PRIVATE_VERIFIED\n",
)
print("ORDER005_FIX2=APPLIED")
