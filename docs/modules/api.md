# `socrata_toolkit.api` — REST Interface

**File:** `socrata_toolkit/api.py` | **Pillar:** API  
**Dependencies:** `fastapi`, `uvicorn`

---

The `api` module provides a RESTful interface to the toolkit and the underlying DuckDB data, allowing external systems (or mobile apps) to programmatic access the NYC sidewalk datasets.

## Quick Start

```bash
# Run the API server
python -m socrata_toolkit.api
```
Server runs at `http://localhost:8000`.

---

## Endpoints

### `GET /`
Basic root info.

### `GET /health`
Returns `{"status": "healthy"}`.

### `GET /tables`
Lists all tables in the configured DuckDB database.

### `GET /data/{table}?limit=100`
Returns the first N records of a table as JSON.

### `POST /analyze/costs`
Accepts a JSON list of records and returns a cost summary + enriched records.

### `POST /analyze/quality`
Accepts a JSON list of records and returns quality metrics (completeness, consistency).

---

## Integration Example

```python
import requests

# Send data for quality check
data = [{"borough": "MANHATTAN", "block": 1234}, {"borough": "BROOKLYN"}]
resp = requests.post("http://localhost:8000/analyze/quality", json=data)
print(resp.json())
# → {"overall": 75.0, "completeness": 83.3, "consistency": 100.0}
```
