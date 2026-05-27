# Architecture

## System Overview

The project ships two distinct user-facing surfaces that share the same Python library core:

| Surface | Technology | Entry point |
|---------|-----------|-------------|
| **Streamlit Dashboard** | Python/Streamlit (server-side rendering) | `python main.py` |
| **Mission Control v2 SPA** | Vanilla JS + Tailwind (browser) | `app/static/mission_control_v2.html` |

Both surfaces are **hybrid**: most data fetching goes directly from the browser to public
Socrata APIs, but AI features are routed through a lightweight backend proxy that keeps
API keys out of the browser.

---

## Backend Layers (Python library — `src/socrata_toolkit/`)

1. **Ingestion** — `client.py`  
   Fetches from Socrata Discovery API and individual dataset endpoints.

2. **Transformation / Analysis** — `analysis.py`, `text_analytics.py`,
   `nlp_advanced.py`, `spatial.py`, `dot_sidewalk.py`, `llm_duck_bridge.py`

3. **Persistence** — `exporters.py` + CLI pipeline  
   DuckDB local cache, Parquet/Excel exports.

4. **Flask REST API** — `src/socrata_toolkit/core/api.py`  
   Optional thin HTTP layer; exposes `/api/*` endpoints consumed by the SPA.  
   Run with: `flask --app socrata_toolkit.core.api run --port 5000`

5. **UX** — `cli.py` (CLI) and `app/app.py` (Streamlit)

6. **Ops** — `validation.py`, `state.py`, `logging_utils.py`, CI

---

## Mission Control v2 SPA — Data Flow

```
Browser (mission_control_v2.html)
  │
  ├─ Dataset search / metadata
  │     └─ DIRECT → api.us.socrata.com/api/catalog/v1  (CORS-safe, no key needed)
  │
  ├─ Dataset row fetch / column schema
  │     └─ DIRECT → https://{domain}/api/views/{id}.json  (Socrata app token optional)
  │
  ├─ AI chat (Gemini / GPT-4o)
  │     └─ PROXY → /api/ai/chat  →  generativelanguage.googleapis.com  (key server-side)
  │                              →  api.openai.com                      (key server-side)
  │
  └─ State persistence
        └─ localStorage: cart, favorites, recent searches, Socrata token, dark mode
```

### Why Hybrid?

| Concern | Decision |
|---------|----------|
| Socrata data is public | Direct browser→Socrata fetch avoids a proxy bottleneck |
| AI API keys are secret | Routed through `/api/ai/chat`; keys live in env vars only |
| No forced server dependency | SPA degrades gracefully when backend is offline (AI tab shows offline notice) |

---

## AI Proxy

The SPA never stores or transmits AI API keys through the browser. Keys are configured
via environment variables on the server:

```bash
export GEMINI_API_KEY="AIza..."
export OPENAI_API_KEY="sk-..."
```

Two deployment options:

1. **Standalone proxy** — `python app/llm_proxy.py` (port 5001 by default)
2. **Bundled with Flask API** — `flask --app socrata_toolkit.core.api run` (port 5000)  
   The Flask app exposes `GET /api/ai/status` and `POST /api/ai/chat`.

When the proxy is unreachable the AI tab shows a yellow "Proxy offline" notice and
the send button shows a warning toast — no silent failures.

---

## Security Boundaries

| Component | Stored where | Accessible to |
|-----------|-------------|---------------|
| Socrata app token | `localStorage` (browser) | Browser JS only |
| Gemini API key | Server env var | Python process only |
| OpenAI API key | Server env var | Python process only |
| Cart / favorites | `localStorage` (browser) | Browser JS only |

> **The browser never sees AI API keys** — this is enforced at the architecture level,
> not by convention.

---

## Directory Map

```
nyc_data/
├── app/
│   ├── app.py               # Streamlit dashboard entry point
│   ├── llm_proxy.py         # Standalone AI proxy server
│   ├── static/
│   │   └── mission_control_v2.html  # SPA (self-contained)
│   ├── views/               # Streamlit page modules
│   ├── services/            # Shared service helpers
│   └── ui/                  # Theme, empty states, i18n
├── src/socrata_toolkit/
│   ├── core/
│   │   ├── api.py           # Flask REST API (includes /api/ai/*)
│   │   ├── client.py        # Socrata API client
│   │   └── ...
│   ├── analyst/             # Analysis modules
│   ├── governance/          # Audit, lineage, compliance
│   └── ...
├── config/
│   └── datasets.yaml        # Dataset registry
├── docs/                    # All documentation
├── tests/                   # pytest suite
└── pyproject.toml
```
