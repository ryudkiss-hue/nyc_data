# Installation & Environment Matrix

## Base
```bash
pip install .
```

## Extras
```bash
pip install ".[postgres]"
pip install ".[mongo]"
pip install ".[all]"
```

## Full developer environment
```bash
pip install -r requirements-dev.txt
```

## Required env vars
- `SOCRATA_APP_TOKEN`
- `PG_DSN` (optional)
- `MONGO_URI` (optional)
