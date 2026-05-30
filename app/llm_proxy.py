"""Standalone LLM proxy server for Mission Control v2.

Keeps API keys server-side — the browser SPA sends messages here instead of
directly to Gemini/OpenAI, so keys are never exposed in the client.

Usage::

    # Development
    python app/llm_proxy.py

    # Production (gunicorn)
    gunicorn app.llm_proxy:create_proxy_app --bind 0.0.0.0:5001

Environment variables:

    GEMINI_API_KEY    Google AI Studio key (starts with AIza)
    OPENAI_API_KEY    OpenAI secret key (starts with sk-)
    PROXY_PORT        Port to listen on (default: 5001)
    PROXY_ORIGIN      CORS allowed origin (default: * for dev; restrict in prod)

Endpoints:

    GET  /api/ai/status   → {"gemini": bool, "openai": bool}
    POST /api/ai/chat     → {"reply": str}
        Body: {"provider": "gemini"|"openai",
               "messages": [{"role": "user"|"assistant", "content": str}, ...],
               "context": str}

Notes:

    This module is intentionally stdlib-only for the proxy logic so it can run
    without any extra dependencies (just Flask for the HTTP layer).  The full
    Flask API at ``socrata_toolkit.core.api`` also exposes these two endpoints
    when Flask is available — use whichever fits your deployment.
"""

from __future__ import annotations

import json
import os
import urllib.request


def create_proxy_app():
    """Flask application factory — returns a WSGI app with the two AI endpoints."""
    try:
        from flask import Flask, jsonify, request
        from flask_cors import CORS  # type: ignore[import]
    except ImportError:
        # flask_cors is optional — fall back to manual header injection
        CORS = None  # type: ignore[assignment]
        from flask import Flask, jsonify, request

    app = Flask(__name__)
    allowed_origin = os.environ.get("PROXY_ORIGIN", "*")

    if CORS is not None:
        CORS(app, origins=allowed_origin)
    else:
        # Inject CORS headers manually on every response
        @app.after_request
        def _add_cors(response):
            response.headers["Access-Control-Allow-Origin"] = allowed_origin
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
            return response

        @app.route("/api/ai/<path:_>", methods=["OPTIONS"])
        def _options_handler(_):
            from flask import Response
            return Response(status=204, headers={
                "Access-Control-Allow-Origin": allowed_origin,
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
            })

    @app.route("/api/ai/status")
    def ai_status():
        return jsonify({
            "gemini": bool(os.environ.get("GEMINI_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
        })

    @app.route("/api/ai/chat", methods=["POST"])
    def ai_chat():
        data = request.get_json(silent=True) or {}
        provider = data.get("provider", "gemini")
        messages = data.get("messages", [])
        context = data.get("context", "")

        if provider == "gemini":
            key = os.environ.get("GEMINI_API_KEY", "")
            if not key:
                return jsonify({"error": "GEMINI_API_KEY not configured"}), 503
            reply = _call_gemini(key, messages, context)

        elif provider == "openai":
            key = os.environ.get("OPENAI_API_KEY", "")
            if not key:
                return jsonify({"error": "OPENAI_API_KEY not configured"}), 503
            reply = _call_openai(key, messages, context)

        else:
            return jsonify({"error": f"Unknown provider: {provider}"}), 400

        if isinstance(reply, dict) and "error" in reply:
            return jsonify(reply), 502
        return jsonify({"reply": reply})

    return app


def _call_gemini(key: str, messages: list[dict], context: str) -> str | dict:
    system_prompt = (
        "You are a data engineering expert. "
        + (f"Context:\n{context}\n\n" if context else "")
        + "Help with SOQL queries, SQL, data pipelines, and analysis."
    )
    user_text = (
        system_prompt
        + "\n\n---\n\n"
        + "\n".join(
            f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['content']}"
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
        return (
            result.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "No response from Gemini")
        )
    except Exception as exc:
        return {"error": f"Gemini error: {exc}"}


def _call_openai(key: str, messages: list[dict], context: str) -> str | dict:
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
        return (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "No response from OpenAI")
        )
    except Exception as exc:
        return {"error": f"OpenAI error: {exc}"}


if __name__ == "__main__":
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    port = int(os.environ.get("PROXY_PORT", 5001))
    print(f"Starting LLM proxy on http://localhost:{port}")
    print(f"  Gemini key: {'✓ set' if os.environ.get('GEMINI_API_KEY') else '✗ not set'}")
    print(f"  OpenAI key: {'✓ set' if os.environ.get('OPENAI_API_KEY') else '✗ not set'}")
    proxy = create_proxy_app()
    proxy.run(host="0.0.0.0", port=port, debug=False)
