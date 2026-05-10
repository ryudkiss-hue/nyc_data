# Testing & CI

## Local
```bash
ruff check socrata_toolkit tests
mypy socrata_toolkit
pytest -q
```

## Integration scaffold
```bash
docker compose -f docker-compose.test.yml up -d
export RUN_INTEGRATION=1
pytest -q tests/test_integration_datastores.py
```

## CI
GitHub Actions runs lint, type-checks, and tests across Python 3.10/3.11/3.12.
