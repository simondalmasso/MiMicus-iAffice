# ORDER-002 validation commands

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
python -m mimicus.validation.e2e evidence/ORDER-002/E2E_RESULTS.json
mimicus benchmark --profile offline --episodes 200 --output-dir evidence/ORDER-002
mimicus db upgrade
python -m build
python scripts/verify_evidence.py
```
