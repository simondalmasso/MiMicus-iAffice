# Contributing

Use Python 3.12 for the core runtime.

From `core/`:

```bash
python -m pip install -e ".[dev]"
pytest --cov=mimicus --cov-report=term-missing
ruff check src tests
mypy src/mimicus
python -m build
```

From repository root, validate cockpit JavaScript before review:

```bash
node --check public/app.js
```

Changes to trusted falsifier primitives require source review plus compatibility, security, fossil-regression and tamper tests. Runtime mutation must remain declarative.

Do not add an alternate orchestration framework as a transitive control plane without an architecture decision proving MiMicus retains authority over routing, falsification, memory, trust, effects and evidence.

Do not enable a real-world effect adapter without preserving the exact-envelope, one-use approval boundary and adding adversarial tests for tamper, expiry, concurrency and uncertain outcomes.
