# socrata_toolkit/api.py
"""
REST API for Socrata Toolkit (FastAPI version).
Provides endpoints for data, analysis, and system health.
"""

from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException

from ..core import DuckDBManager
from ..engineering import estimate_costs, summarize_costs
from ..governance import compute_quality_score

app = FastAPI(title="Socrata Toolkit API", version="0.3.0")

# In-memory storage or DB path
DB_PATH = "nyc_dash.db"


@app.get("/")
def read_root():
    return {"name": "Socrata Toolkit API", "status": "active"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/tables")
def list_tables():
    mgr = DuckDBManager(DB_PATH)
    try:
        tables = mgr.query("SHOW TABLES").fetchall()
        return {"tables": [t[0] for t in tables]}
    finally:
        mgr.close()


@app.get("/data/{table}")
def get_table_data(table: str, limit: int = 100):
    mgr = DuckDBManager(DB_PATH)
    try:
        df = mgr.query(f"SELECT * FROM {table} LIMIT {limit}").df()
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Table {table} not found or query failed: {e}")
    finally:
        mgr.close()


@app.post("/analyze/costs")
def analyze_costs(data: list[dict[str, Any]]):
    df = pd.DataFrame(data)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty data provided")

    df_with_costs = estimate_costs(df)
    summary = summarize_costs(df_with_costs)
    return {
        "summary": {
            "total": summary.total_estimated,
            "avg": summary.avg_cost_per_location,
            "count": summary.location_count,
        },
        "records": df_with_costs.to_dict(orient="records"),
    }


@app.post("/analyze/quality")
def analyze_quality(data: list[dict[str, Any]]):
    df = pd.DataFrame(data)
    score = compute_quality_score(df)
    return {
        "overall": score.overall,
        "completeness": score.completeness,
        "consistency": score.consistency,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
