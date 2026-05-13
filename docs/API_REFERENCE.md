# `socrata_toolkit` — API Reference

**Version:** 0.3.0 | **License:** MIT | **Author:** Richard Yudkiss

The `socrata_toolkit` is a modular, Pillar-Architecture Python library for ingesting, analyzing, and governing NYC municipal datasets via the Socrata SODA API. It is the engine behind the **NYC Data Assistant** Dash application.

---

## Module Index

| Module | File | Pillar | Description |
|--------|------|--------|-------------|
| [`core`](./modules/core.md) | `socrata_toolkit/core.py` | Core | Socrata client, SoQL builder, DuckDB management, schema registry, exporters |
| [`analysis`](./modules/analysis.md) | `socrata_toolkit/analysis.py` | Analytics | Profiling, anomaly detection, SLA, text analytics, visualizations |
| [`engineering`](./modules/engineering.md) | `socrata_toolkit/engineering.py` | Engineering | Cost estimation, sidewalk KPIs, construction list management, task board |
| [`pipeline`](./modules/pipeline.md) | `socrata_toolkit/pipeline.md` | Pipeline | CDC, ingestion, deduplication, BI export, sync, streaming |
| [`governance`](./modules/governance.md) | `socrata_toolkit/governance.py` | Governance | Quality scoring, audit logging, lineage, alerting, compliance |
| [`spatial`](./modules/spatial.md) | `socrata_toolkit/spatial.py` | Spatial | Clustering, spatial joins, conflict detection, hotspot analysis |
| [`ai`](./modules/ai.md) | `socrata_toolkit/ai.py` | AI | NL→SQL, sentiment, quantum search, route/crew optimization |
| [`cleaning`](./modules/cleaning.md) | `socrata_toolkit/cleaning.py` | Cleaning | Borough normalization, BBL, column standardization, outlier removal |

---

## Quick Installation

```bash
pip install -e ".[all]"          # All extras
pip install -e ".[geo,nlp,xlsx]" # Specific extras
```

### Extras

| Extra | Packages |
|-------|---------|
| `xlsx` | `openpyxl` |
| `nlp` | `spacy` |
| `viz` | `matplotlib` |
| `geo` | `shapely` |
| `ui` | `streamlit` |
| `all` | Everything above + core deps |

---

## Architecture Overview

```
socrata_toolkit/
├── core.py        ← SocrataClient, SoQLBuilder, DuckDB layer, Schema Registry
├── analysis.py    ← Profiling, anomalies, SLA, visualizations
├── engineering.py ← KPIs, cost estimation, task board
├── pipeline.py    ← CDC, ingestion, BI export
├── governance.py  ← Quality scoring, audit, lineage
├── spatial.py     ← Clustering, joins, hotspots
├── ai.py          ← LLM, NL→SQL, quantum-inspired optimization
└── cleaning.py    ← Data normalization utilities
```

All symbols are lazy-loaded via `__init__.py`. Import directly:

```python
from socrata_toolkit import SocrataClient, SoQLBuilder, compute_quality_score
# or
import socrata_toolkit as st
client = st.SocrataClient()
```

---

## Environment Variables

| Variable | Module | Purpose |
|----------|--------|---------|
| `SOCRATA_APP_TOKEN` | `core` | Socrata API rate-limit bypass token |
| `DUCKDB_PATH` | `core`, `pipeline` | Path to local DuckDB file (default: `nyc_mission_control.db`) |
| `OPENAI_API_KEY` | `ai` | OpenAI key for GPT-4o NL→SQL |
| `MOTHERDUCK_TOKEN` | `dash_app/data/db` | MotherDuck cloud DuckDB token |

---

## Dash Application Pages

The Dash app at `dash_app/` exposes these toolkit modules via 14 interactive pages:

| Page | Route | Toolkit modules used |
|------|-------|---------------------|
| Dashboard | `/` | `pipeline.ingest_311_complaints`, `core.DuckDBManager` |
| Analytics | `/analytics` | `analysis.*`, `governance.compute_quality_score` |
| Geospatial | `/geospatial` | `spatial.*` |
| Task Board | `/tasks` | `engineering.Task`, `engineering.TaskBoard` |
| Data Pipeline | `/pipeline` | `pipeline.*`, `cleaning.*` |
| AI Assistant | `/ai` | `ai.SocrataLLMChatbot`, `ai.SQLQueryEngine` |
| Quantum | `/quantum` | `ai.quantum_search`, `ai.optimize_repair_route`, `ai.optimize_crew_assignment` |
| Governance | `/governance` | `governance.*` |
| Engineering | `/engineering` | `engineering.*` |
| SoQL Maestro | `/soql` | `core.SoQLBuilder`, `core.SocrataClient` |
| Reports | `/reports` | `analysis.Report`, `analysis.generate_program_report` |
| Export | `/export` | `pipeline.ExcelWorkbookBuilder`, `pipeline.export_for_tableau` |
| Dev Tools | `/devtools` | `core.DuckDBManager`, raw DuckDB SQL |
| Settings | `/settings` | All modules (health check) |

---

*See individual module docs in [`docs/modules/`](./modules/) for full signatures and examples.*
