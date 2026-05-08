# Quickstart

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
socrata doctor --check-db
```

Run Streamlit:
```bash
streamlit run socrata_toolkit/app.py
```

Run CLI search:
```bash
socrata search "sidewalk" --domain data.cityofnewyork.us --limit 10
```
