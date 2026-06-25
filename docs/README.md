# 🗽 NYC DOT Socrata Toolkit — Documentation Hub

Welcome to the unified documentation for the **NYC DOT Sidewalk Data Governance Toolkit**. This repository provides an elite suite of tools for infrastructure asset management, project coordination, and administrative productivity using NYC Open Data.

## 🧭 Documentation Map

| Resource | Purpose |
|----------|---------|
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | **System Design**: DuckDB Spatial foundation, 7-pillar processing layer, and data lineage. |
| [**OPERATIONS.md**](OPERATIONS.md) | **Daily Manual**: Agency runbook, morning checklists, analyst pack workflows, and emergency procedures. |
| [**SETUP.md**](SETUP.md) | **Environment**: Installation, configuration wizard, Docker deployment, and local dev setup. |
| [**INTEGRATION.md**](INTEGRATION.md) | **External Services**: Python API reference, ArcGIS sync, M365 automation, and AI/LLM integration. |
| [**DATASETS.md**](../DATASETS.md) | **Catalog**: Technical reference for all 26 integrated Socrata endpoints and schema definitions. |

---

## 🚀 Quick Access

- **Mission Control**: `python main.py` (Streamlit UI on port 8501)
- **Daily Sync**: `socrata sync -i erm2-nwe9 --table complaints_311`
- **Analyst Pack**: `socrata analyst run --profile config/analyst_profile.yaml`
- **Health Check**: `python launcher.py doctor`

---

## 🛠️ Technical Pillars

1.  **Core**: API client, DuckDB persistence, and a 60+ command CLI.
2.  **Analysis**: Statistical profiling (Four Moments), anomaly detection, and borough Metrics.
3.  **Governance**: Automated lineage tracking and schema drift detection.
4.  **Engineering**: Specialized logic for sidewalk repair lifecycles, ESAL calculations, and ESAL-based deterioration modeling.
5.  **Visualization**: 30+ interactive Plotly, Folium, and Pydeck map layouts.

---

## 🛡️ Support & Maintenance

- **Troubleshooting**: See [SETUP.md#troubleshooting](SETUP.md#troubleshooting).
- **Broken Pipes**: Check `outputs/logs/ingest.jsonl` for ingestion failures.
- **Audit Trails**: Forensic analysis history is stored in `.state/profiles/<name>/decisions.duckdb`.

---

**Version**: 0.3.0 | **License**: MIT | **Classification**: Internal Use Only
© 2026 NYC Department of Transportation
