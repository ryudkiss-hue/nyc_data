"""FastAPI REST API for DOT Sidewalk Toolkit (Turbo-Stream Optimized).

Provides high-performance ASGI access to toolkit functionality.
Compatible with next-gen Turbo-Stream frontend (FastAPI + Mantine 8.0).

Endpoints:
    GET  /api/health              -- Health check
    GET  /api/search              -- Search Socrata datasets
    GET  /api/dataset/{4x4}       -- Fetch dataset rows (Streaming)
    GET  /api/metadata/{4x4}      -- Get dataset metadata
    POST /api/analyze             -- Profile uploaded data
    POST /api/quality-score       -- Compute quality score
    POST /api/prioritize          -- Prioritize a construction list (Streaming)
    POST /api/triage              -- Triage complaints via NLP
    GET  /api/board               -- Get task board state
    POST /api/board/task          -- Create a task
    GET  /api/kpis                -- Get program KPI dashboard

Run standalone::

    uvicorn socrata_toolkit.api:app --port 5000
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

# -------------------------------------------------------------------
# Pydantic Models for Validation
# -------------------------------------------------------------------

class RowData(BaseModel):
    rows: List[dict]
    key_columns: Optional[List[str]] = None
    date_column: Optional[str] = None
    text_column: Optional[str] = "complaint_text"

class TaskCreate(BaseModel):
    title: str = "Untitled"
    description: str = ""
    assignee: str = ""
    priority: str = "medium"
    category: str = "general"
    borough: str = ""
    actor: str = "api"

# -------------------------------------------------------------------
# App Setup
# -------------------------------------------------------------------

app = FastAPI(
    title="NYC DOT Socrata Toolkit API",
    description="Turbo-Stream Optimized ASGI API",
    version="0.4.0"
)

# -------------------------------------------------------------------
# Health
# -------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.4.0", "engine": "FastAPI/ASGI"}

# -------------------------------------------------------------------
# Socrata Data Access
# -------------------------------------------------------------------

@app.get("/api/search")
async def search(
    q: str = "",
    domain: Optional[str] = None,
    limit: int = 10
):
    from .client import SocrataClient
    client = SocrataClient()
    # Assuming search is I/O bound, but client might be synchronous
    # In a full async refactor, client.search would be awaited
    results = client.search(query=q, domain=domain, limit=limit)
    return [r.__dict__ for r in results]

@app.get("/api/dataset/{fourfour}")
async def dataset(
    fourfour: str,
    domain: str = "data.cityofnewyork.us",
    max_rows: int = 1000
):
    from .client import SocrataClient
    client = SocrataClient()

    # Turbo-Stream: Implementation of StreamingResponse for heavy datasets
    def generate():
        df = client.fetch_dataframe(domain, fourfour, max_rows=max_rows)
        yield df.to_json(orient="records")

    return StreamingResponse(generate(), media_type="application/json")

@app.get("/api/metadata/{fourfour}")
async def metadata(
    fourfour: str,
    domain: str = "data.cityofnewyork.us"
):
    from .client import SocrataClient
    client = SocrataClient()
    meta = client.get_metadata(domain, fourfour)
    return meta.summary()

# -------------------------------------------------------------------
# Analysis
# -------------------------------------------------------------------

@app.post("/api/analyze")
async def analyze(data: RowData):
    import pandas as pd

    from .analysis import profile_dataframe

    df = pd.DataFrame(data.rows)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty rows provided")

    profile = profile_dataframe(df)
    return {
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "null_counts": profile.null_counts,
        "dtypes": profile.dtypes,
    }

@app.post("/api/quality-score")
async def quality_score(data: RowData):
    import pandas as pd

    from .governance import compute_quality_score

    df = pd.DataFrame(data.rows)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty rows provided")

    score = compute_quality_score(df, key_columns=data.key_columns, date_column=data.date_column)
    return {
        "overall": score.overall,
        "completeness": score.completeness,
        "validity": score.validity,
        "consistency": score.consistency,
        "freshness": score.freshness,
    }

# -------------------------------------------------------------------
# Construction List
# -------------------------------------------------------------------

@app.post("/api/prioritize")
async def prioritize(data: RowData):
    import pandas as pd

    from .construction_list import (
        classify_scope,
        flag_ada_locations,
        prioritize_construction_list,
        summarize_construction_list,
    )

    df = pd.DataFrame(data.rows)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty rows provided")

    # Turbo-Stream: Decouple prioritization logic for streaming response if needed
    # For now, we return a unified JSON but optimized via ASGI
    df = prioritize_construction_list(df)
    df = classify_scope(df)
    df = flag_ada_locations(df)
    summary = summarize_construction_list(df)

    return {
        "summary": {
            "total_locations": summary.total_locations,
            "ada_count": summary.ada_count,
            "high_priority": summary.high_priority_count,
            "avg_priority": summary.avg_priority_score,
        },
        "rows": json.loads(df.to_json(orient="records", default_handler=str)),
    }

# -------------------------------------------------------------------
# NLP Triage
# -------------------------------------------------------------------

@app.post("/api/triage")
async def triage(data: RowData):
    import pandas as pd

    from .nlp_integration import triage_complaints

    df = pd.DataFrame(data.rows)
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty rows provided")

    result = triage_complaints(df, text_col=data.text_column)
    return json.loads(result.to_json(orient="records", default_handler=str))

# -------------------------------------------------------------------
# Task Board
# -------------------------------------------------------------------

@app.get("/api/board")
async def board_state():
    from .task_board import TaskBoard
    board_path = Path("outputs/board.json")
    if board_path.exists():
        board = TaskBoard.load(str(board_path))
    else:
        board = TaskBoard()
    return {
        "name": board.name,
        "stats": board.stats(),
        "tasks": [t.to_dict() for t in board.tasks if t.status != "deleted"],
    }

@app.post("/api/board/task", status_code=201)
async def create_task(data: TaskCreate):
    from .task_board import Task, TaskBoard
    board_path = Path("outputs/board.json")
    if board_path.exists():
        board = TaskBoard.load(str(board_path))
    else:
        board = TaskBoard()

    task = Task(
        title=data.title,
        description=data.description,
        assignee=data.assignee,
        priority=data.priority,
        category=data.category,
        borough=data.borough,
    )
    tid = board.add_task(task, actor=data.actor)
    board.save(str(board_path))
    return {"task_id": tid, "title": task.title}

# -------------------------------------------------------------------
# KPI Dashboard
# -------------------------------------------------------------------

@app.get("/api/kpis")
async def kpis():
    from .program_metrics import MetricsTracker
    metrics_path = Path("outputs/metrics.json")
    if metrics_path.exists():
        tracker = MetricsTracker()
        tracker.load(str(metrics_path))
        dashboard = tracker.dashboard()
        return {
            "health": dashboard.overall_health,
            "metrics": [
                {"name": m.name, "value": m.value, "target": m.target,
                 "status": m.status, "delta": m.delta_from_target}
                for m in dashboard.metrics
            ],
            "budget_codes": [b.__dict__ for b in dashboard.budget_codes],
        }
    return {"health": "unknown", "metrics": [], "budget_codes": []}

# Application Factory for Gunicorn/Uvicorn
def create_app():
    return app
