"""Flask REST API for DOT Sidewalk Toolkit.

Provides a JSON API for programmatic access to toolkit functionality.
Can be deployed standalone or alongside the Streamlit dashboard.

Endpoints:
    GET  /api/health              -- Health check
    GET  /api/search              -- Search Socrata datasets
    GET  /api/dataset/<4x4>       -- Fetch dataset rows
    GET  /api/metadata/<4x4>      -- Get dataset metadata
    POST /api/analyze             -- Profile uploaded data
    POST /api/quality-score       -- Compute quality score
    POST /api/prioritize          -- Prioritize a construction list
    POST /api/triage              -- Triage complaints via NLP
    GET  /api/board               -- Get task board state
    POST /api/board/task          -- Create a task
    GET  /api/kpis                -- Get program KPI dashboard

Run standalone::

    flask --app socrata_toolkit.core.api run --port 5000

Or with gunicorn::

    gunicorn 'socrata_toolkit.core.api:create_app()' --bind 0.0.0.0:5000
"""

from __future__ import annotations

import json
import os
from typing import Any


def create_app():
    """Flask application factory."""
    try:
        from flask import Flask, jsonify, request
    except ImportError as exc:
        raise ImportError("Install Flask: pip install flask") from exc

    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    # -------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "version": "0.3.0"})

    # -------------------------------------------------------------------
    # Socrata Data Access
    # -------------------------------------------------------------------

    @app.route("/api/search")
    def search():
        from .client import SocrataClient
        query = request.args.get("q", "")
        domain = request.args.get("domain")
        limit = int(request.args.get("limit", 10))
        client = SocrataClient()
        results = client.search(query=query, domain=domain, limit=limit)
        return jsonify([r.__dict__ for r in results])

    @app.route("/api/dataset/<fourfour>")
    def dataset(fourfour):
        from .client import SocrataClient
        domain = request.args.get("domain", "data.cityofnewyork.us")
        max_rows = int(request.args.get("max_rows", 1000))
        client = SocrataClient()
        df = client.fetch_dataframe(domain, fourfour, max_rows=max_rows)
        return jsonify(json.loads(df.to_json(orient="records")))

    @app.route("/api/metadata/<fourfour>")
    def metadata(fourfour):
        from .client import SocrataClient
        domain = request.args.get("domain", "data.cityofnewyork.us")
        client = SocrataClient()
        meta = client.get_metadata(domain, fourfour)
        return jsonify(meta.summary())

    # -------------------------------------------------------------------
    # Analysis
    # -------------------------------------------------------------------

    @app.route("/api/analyze", methods=["POST"])
    def analyze():
        import pandas as pd
        from ..analysis import profile_dataframe
        data = request.get_json()
        if not data or "rows" not in data:
            return jsonify({"error": "POST JSON with 'rows' array"}), 400
        df = pd.DataFrame(data["rows"])
        profile = profile_dataframe(df)
        dtypes = {
            col["name"]: col["type"]
            for col in getattr(profile, "columns", [])
            if isinstance(col, dict) and "name" in col and "type" in col
        }
        return jsonify({
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "null_counts": profile.null_counts,
            "dtypes": dtypes,
        })

    @app.route("/api/quality-score", methods=["POST"])
    def quality_score():
        import pandas as pd
        from ..governance.core import compute_quality_score
        data = request.get_json()
        if not data or "rows" not in data:
            return jsonify({"error": "POST JSON with 'rows' array"}), 400
        df = pd.DataFrame(data["rows"])
        key_columns = data.get("key_columns")
        date_column = data.get("date_column")
        score = compute_quality_score(df, key_columns=key_columns, date_column=date_column)
        return jsonify({
            "overall": score.overall,
            "completeness": score.completeness,
            "validity": score.validity,
            "consistency": score.consistency,
            "freshness": score.freshness,
        })

    # -------------------------------------------------------------------
    # Construction List
    # -------------------------------------------------------------------

    @app.route("/api/prioritize", methods=["POST"])
    def prioritize():
        import pandas as pd
        from ..engineering.construction_list import prioritize_construction_list, classify_scope, flag_ada_locations, summarize_construction_list
        data = request.get_json()
        if not data or "rows" not in data:
            return jsonify({"error": "POST JSON with 'rows' array"}), 400
        df = pd.DataFrame(data["rows"])
        df = prioritize_construction_list(df)
        df = classify_scope(df)
        df = flag_ada_locations(df)
        summary = summarize_construction_list(df)
        return jsonify({
            "summary": {
                "total_locations": summary.total_locations,
                "ada_count": summary.ada_count,
                "high_priority": summary.high_priority_count,
                "avg_priority": summary.avg_priority_score,
            },
            "rows": json.loads(df.to_json(orient="records", default_handler=str)),
        })

    # -------------------------------------------------------------------
    # NLP Triage
    # -------------------------------------------------------------------

    @app.route("/api/triage", methods=["POST"])
    def triage():
        import pandas as pd
        from ..ai import triage_complaints
        data = request.get_json()
        if not data or "rows" not in data:
            return jsonify({"error": "POST JSON with 'rows' array"}), 400
        text_col = data.get("text_column", "complaint_text")
        df = pd.DataFrame(data["rows"])
        result = triage_complaints(df, text_col=text_col)
        return jsonify(json.loads(result.to_json(orient="records", default_handler=str)))

    # -------------------------------------------------------------------
    # Task Board
    # -------------------------------------------------------------------

    @app.route("/api/board")
    def board_state():
        from ..task_board import TaskBoard
        from pathlib import Path
        board_path = Path("outputs/board.json")
        if board_path.exists():
            board = TaskBoard.load(str(board_path))
        else:
            board = TaskBoard()
        return jsonify({
            "name": board.name,
            "stats": board.stats(),
            "tasks": [t.to_dict() for t in board.tasks if t.status != "deleted"],
        })

    @app.route("/api/board/task", methods=["POST"])
    def create_task():
        from ..task_board import TaskBoard, Task
        from pathlib import Path
        board_path = Path("outputs/board.json")
        if board_path.exists():
            board = TaskBoard.load(str(board_path))
        else:
            board = TaskBoard()
        data = request.get_json()
        task = Task(
            title=data.get("title", "Untitled"),
            description=data.get("description", ""),
            assignee=data.get("assignee", ""),
            priority=data.get("priority", "medium"),
            category=data.get("category", "general"),
            borough=data.get("borough", ""),
        )
        tid = board.add_task(task, actor=data.get("actor", "api"))
        board.save(str(board_path))
        return jsonify({"task_id": tid, "title": task.title}), 201

    # -------------------------------------------------------------------
    # KPI Dashboard
    # -------------------------------------------------------------------

    @app.route("/api/kpis")
    def kpis():
        from ..program_metrics import MetricsTracker
        from pathlib import Path
        metrics_path = Path("outputs/metrics.json")
        if metrics_path.exists():
            tracker = MetricsTracker()
            tracker.load(str(metrics_path))
            dashboard = tracker.dashboard()
            return jsonify({
                "health": dashboard.overall_health,
                "metrics": [
                    {"name": m.name, "value": m.value, "target": m.target,
                     "status": m.status, "delta": m.delta_from_target}
                    for m in dashboard.metrics
                ],
                "budget_codes": [b.__dict__ for b in dashboard.budget_codes],
            })
        return jsonify({"health": "unknown", "metrics": [], "budget_codes": []})

    return app
