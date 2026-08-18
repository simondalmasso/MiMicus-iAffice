# ORDER-003 exact evidence commands

```bash
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pip check
ruff format --check .
ruff check .
mypy src/mimicus
pytest tests/unit tests/integration --cov=mimicus --cov-report=term-missing --cov-fail-under=90
python scripts/check_security.py
python scripts/check_ledger.py
python -m mimicus.validation.order003_e2e evidence/ORDER-003
mimicus benchmark --profile offline --episodes 200 --output-dir evidence/ORDER-003
MIMICUS_DATABASE_URL=sqlite:///<clean.db> mimicus db upgrade
MIMICUS_DATABASE_URL=sqlite:///<order002.db> alembic upgrade 0001_order002
MIMICUS_DATABASE_URL=sqlite:///<order002.db> alembic upgrade head
python -m build
python scripts/verify_evidence.py ORDER-003
```

Normal exact-head CI additionally reruns ORDER-002 process compatibility and real MCP transport without an OpenAI key.
