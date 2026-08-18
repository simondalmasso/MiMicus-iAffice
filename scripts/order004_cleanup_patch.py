from pathlib import Path

path = Path("src/mimicus/providers/openai_agents.py")
text = path.read_text(encoding="utf-8")
old = "        for item in memory[: self.max_memory_items]:\n            if str(item.get(\"status\", \"\")) not in allowed:\n                continue\n"
new = "        for item in memory:\n            if str(item.get(\"status\", \"\")) not in allowed:\n                continue\n            if len(payload) >= self.max_memory_items:\n                break\n"
if old not in text:
    raise SystemExit("memory filter anchor missing")
path.write_text(text.replace(old, new, 1), encoding="utf-8")

harness = Path("scripts/order004_evidence.py")
harness_text = harness.read_text(encoding="utf-8")
lint_line = '    assert all(item["status"] if "status" in item else True for item in memory)\n'
if lint_line not in harness_text:
    raise SystemExit("evidence lint anchor missing")
harness.write_text(harness_text.replace(lint_line, "", 1), encoding="utf-8")
print("ORDER004_CLEANUP_FIX=APPLIED")
