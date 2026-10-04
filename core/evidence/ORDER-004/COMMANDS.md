# ORDER-004 exact validation commands

`ruff format --check .`; `ruff check .`; `mypy src/mimicus`; `pytest tests/unit tests/integration --cov=mimicus --cov-report=term-missing --cov-fail-under=90`; `python scripts/check_security.py`; `python scripts/check_ledger.py`; `python -m mimicus.validation.order003_e2e`; `python scripts/order004_evidence.py`; `mimicus benchmark --profile offline --episodes 200`; SQLite migration from clean and ORDER-002 baseline; PostgreSQL schema compile; `python -m build`; final manifest verification.
