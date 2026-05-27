# Manhattan Mission Control

The project ships two user-facing surfaces built on the same Python library core.

---

## Surface 1 — Streamlit Dashboard (`app/app.py`)

SIM Project Analyst workspace: 15 Socrata datasets, four workflow views, and
Productivity ROI telemetry.

### Layout

| Path | Role |
|------|------|
| `app/app.py` | Streamlit entry point |
| `app/views/` | Home, workflows, publish, settings pages |
| `app/ui/` | Theme, empty states, i18n |
| `app/services/` | Shared service helpers |
| `config/datasets.yaml` | Socrata registry (single source of truth) |
| `src/socrata_toolkit/` | CLI, analyst pack, publish, readiness |
| `legacy_archive/dash_app/` | Archived Dash UI (optional) |

### Navigation

| Page | Purpose |
|------|---------|
| **Home** | Onboarding, quick status |
| **Analyst Workflows** | QA, Spatial, Contract, Productivity |
| **Publish & Pack** | Run pack + publish (dry-run default) |
| **Settings & Quality** | Readiness, completeness, health, ingest log |

### Run

```bash
pip install -e ".[mission]"
export SOCRATA_APP_TOKEN="your-token"   # omit for demo/offline mode
python main.py
# or: mission
```

Dataset registry: `config/datasets.yaml` (loaded by `app/data_loader.py`).  
Local parquet cache: `data/local_db/socrata_cache/` (24h TTL).  
Ingestion telemetry: `outputs/logs/ingest.jsonl` (local only, gitignored).

---

## Surface 2 — Mission Control v2 SPA (`app/static/mission_control_v2.html`)

A self-contained single-page application for dataset discovery, SOQL query building,
multi-dataset joins, GIS mapping, and AI-assisted analysis.

> **Architecture**: Hybrid — Socrata API calls go browser-direct; AI calls route through
> a backend proxy so API keys never enter the browser.

### Features

| Tab | What it does |
|-----|-------------|
| **Discovery** | Search across 5 Socrata domains, live filters, sort, cart |
| **Profiles** | Column profiling, sample values, quality score |
| **SOQL Builder** | Visual query builder + template library |
| **Join Builder** | Cross-dataset JOIN SQL/Python generator |
| **Visualize** | ERD, ER diagram, Mermaid, bar/scatter charts |
| **GIS Map** | Multi-layer Leaflet map with bounding-box filter |
| **AI Assistant** | Chat with Gemini or GPT-4o about your datasets |
| **Export** | Generate Docker Compose, Python pipeline, Airflow DAG, dbt model |

### Run with AI enabled

```bash
# Terminal 1 — Start the AI proxy (keeps keys server-side)
export GEMINI_API_KEY="AIza..."   # or OPENAI_API_KEY="sk-..."
python app/llm_proxy.py           # listens on :5001

# Terminal 2 — Open the SPA
open app/static/mission_control_v2.html
# or serve via: python -m http.server 8080 --directory app/static
```

Alternatively, run the full Flask API which bundles the same proxy endpoints:

```bash
flask --app socrata_toolkit.core.api run --port 5000
```

### Run without AI (browse-only)

The SPA works without any backend:

```bash
open app/static/mission_control_v2.html
```

The AI tab will show "Proxy offline" — all other tabs work normally.

### Configuration (Config modal)

| Setting | Where stored |
|---------|-------------|
| Socrata app token | `localStorage` (browser) |
| AI API keys | Server env vars (`GEMINI_API_KEY`, `OPENAI_API_KEY`) — **never in browser** |

> See [security.md](security.md) for the full API key policy.

---

## CLI (unchanged entry point)

```bash
pip install -e ".[xlsx,postgres]"
socrata analyst run --profile config/analyst_profile.yaml
socrata readiness
```

## Databases

Local DuckDB files live under `data/local_db/` (see `config/analyst_profile.example.yaml`).

## More documentation

- [architecture.md](architecture.md) — system layers and data flow diagrams
- [security.md](security.md) — key management, credential rotation
- [USER_FRIENDLY_FEATURES.md](USER_FRIENDLY_FEATURES.md) — i18n, empty states, Docker
