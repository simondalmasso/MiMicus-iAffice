# Runbook

1. Install Python 3.11+ and `python -m pip install -e .`.
2. Run `allora-edge safety-check --root .`.
3. Run `allora-edge scan` to verify chain ID, dynamically enumerate topics, persist SQLite, and regenerate evidence.
4. Inspect `evidence/QUALIFYING_TOPICS.json`. Empty list is normal.
5. Start `allora-edge watch --interval 60` for persistent change detection.
6. Use `allora-edge health` for last block/scan, topic/active/eligible counts and schema version.
7. If `QUALIFYING_TOPIC_FOUND` appears, stop before any financial action and send evidence to independent AUD + owner.

No operational step includes wallet setup or a chain transaction.
