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

        from ..engineering.construction_list import (
            classify_scope,
            flag_ada_locations,
            prioritize_construction_list,
            summarize_construction_list,
        )
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
        from pathlib import Path

        from ..task_board import TaskBoard
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
        from pathlib import Path

        from ..task_board import Task, TaskBoard
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
        from pathlib import Path

        from ..program_metrics import MetricsTracker
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

    # -------------------------------------------------------------------
    # AI Proxy  (Issue 2 — keeps API keys server-side)
    # -------------------------------------------------------------------

    @app.route("/api/ai/status")
    def ai_status():
        """Return which AI providers have keys configured (never expose the keys)."""
        import os
        return jsonify({
            "gemini": bool(os.environ.get("GEMINI_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        })

    @app.route("/api/ai/chat", methods=["POST"])
    def ai_chat():
        """Proxy AI chat requests — API keys stay on the server."""
        import os
        import urllib.request

        data = request.get_json(silent=True) or {}
        provider = data.get("provider", "gemini")
        messages = data.get("messages", [])  # [{role, content}, ...]
        context = data.get("context", "")

        if provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY", "")
            if not key:
                return jsonify({"error": "GEMINI_API_KEY not configured on server"}), 503

            system_prompt = (
                "You are a data engineering expert. "
                + (f"Context:\n{context}\n\n" if context else "")
                + "Help with SOQL queries, SQL, data pipelines, and analysis."
            )
            # Flatten to a single user turn (Gemini doesn't have a system role)
            user_text = (
                system_prompt
                + "\n\n---\n\n"
                + "\n".join(
                    f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
                    for m in messages
                )
            )
            payload = json.dumps(
                {"contents": [{"role": "user", "parts": [{"text": user_text}]}]}
            ).encode()
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemini-1.5-flash:generateContent?key={key}"
            )
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                reply = (
                    result.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "No response from Gemini")
                )
                return jsonify({"reply": reply})
            except Exception as exc:
                return jsonify({"error": f"Gemini error: {exc}"}), 502

        elif provider == "openai":
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                return jsonify({"error": "OPENAI_API_KEY not configured on server"}), 503

            system_msg = {
                "role": "system",
                "content": (
                    "You are a data engineering expert. "
                    + (f"Context:\n{context}" if context else "")
                ),
            }
            openai_messages = [system_msg] + [
                {"role": m["role"], "content": m["content"]} for m in messages
            ]
            payload = json.dumps(
                {"model": "gpt-4o", "messages": openai_messages, "max_tokens": 2000}
            ).encode()
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                reply = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "No response from OpenAI")
                )
                return jsonify({"reply": reply})
            except Exception as exc:
                return jsonify({"error": f"OpenAI error: {exc}"}), 502

        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400

    return app
