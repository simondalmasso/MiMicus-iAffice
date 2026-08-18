from pathlib import Path


def rep(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"missing anchor {path}: {old!r}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")

rep(
    "src/mimicus/orchestration/morphology.py",
    "    agent_parent_ids = (memory.node_id, audition.node_id)\n",
    "    agent_parent_ids: tuple[str, ...] = (memory.node_id, audition.node_id)\n",
)

p = Path("src/mimicus/benchmark.py")
text = p.read_text(encoding="utf-8")
text = text.replace("cost=response.cost,", "cost=float(response.cost or 0.0),")
text = text.replace("cost=sum(response.cost for response in responses),", "cost=sum(float(response.cost or 0.0) for response in responses),")
text = text.replace("cost=response.cost + sum(execution.cost for execution in executions),", "cost=float(response.cost or 0.0) + sum(execution.cost for execution in executions),")
p.write_text(text, encoding="utf-8")

# Preserve the historical domain bankruptcy projection while routing stays capability-scoped.
p = Path("src/mimicus/orchestration/engine.py")
text = p.read_text(encoding="utf-8")
old = '''            state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)\n            if state == "BANKRUPT":\n                lineage_exclusions["bankrupt"].append(candidate.fingerprint)\n'''
new = '''            state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)\n            if state == "BANKRUPT" and self.repository.bankruptcy_state(candidate.fingerprint, domain) != "BANKRUPT":\n                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", f"capability {target_cap}: verified relevant canary bankruptcy")\n            if state == "BANKRUPT":\n                lineage_exclusions["bankrupt"].append(candidate.fingerprint)\n'''
if old not in text:
    raise SystemExit("engine bankruptcy projection anchor missing")
p.write_text(text.replace(old, new, 1), encoding="utf-8")
print("ORDER004_FIX1=APPLIED")
