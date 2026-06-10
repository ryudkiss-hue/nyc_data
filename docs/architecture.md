# 🏗️ NYC Sidewalk Toolkit Architecture

## 1. High-Level Design

The toolkit follows a **local-first, DuckDB-driven** architecture designed for high-performance spatial analysis and rigorous data governance.

```
DATA LAYER
  NYC Socrata (26 datasets) → DuckDB L2 Cache (Parquet) → Spatial Extensions

PROCESSING LAYER (7 Pillars)
  1. Core: API client, DuckDB persistence, CLI (Click)
  2. Analysis: Profiling (Four Moments), Anomaly detection
  3. Analyst: Weekly packs, role-based workflows, publishing
  4. Quality: SLA tracking, Freshness, Validation rules
  5. Visualization: 30+ chart types (Plotly, Folium, Pydeck)
  6. Governance: Data Lineage (NetworkX), Audit logs, Schema Drift
  7. Engineering: Contract analytics, Budget forecasting

INTERFACE LAYER
  ↓ CLI (socrata tool)
  ↓ Streamlit Mission Control (Port 8501)
  ↓ REST API (FastAPI, Port 8000)
```

---

## 2. Spatial Foundation (DuckDB Spatial)

The project leverages **DuckDB Spatial** for high-speed geographic queries, replacing legacy PostGIS requirements for local analysis.

### Coordinate Systems
- **Primary**: WGS84 (SRID 4326) for web mapping.
- **Secondary**: NAD83 NY Long Island (SRID 2263) for feet-based engineering metrics.

### Key Spatial Tables
- `sidewalk_segments`: LineString geometries with condition scores.
- `inspections`: Point-based defect records.
- `blocks`: Polygon boundaries for spatial aggregation.

---

## 3. Data Governance & Lineage

The toolkit implements a production-grade provenance system to track data from ingestion to executive reports.

### Lineage System
- **Tracking**: Uses `@track_transformation` decorators to record execution metrics.
- **Persistence**: Lineage DAGs are stored in DuckDB, capturing input/output row counts, duration, and data quality scores.
- **Impact Analysis**: Answers "what breaks if dataset X changes?" by tracing downstream dependencies.

### Schema Drift Detection
- Compares incoming SODA3 schemas against local baselines.
- Logs events to `docs/SCHEMA_DRIFT.md` and triggers alerts on breaking changes (column removal/type shifts).

---

## 4. Pillar Details

### Core (API & Persistence)
- **SocrataClient**: Robust SODA API wrapper with exponential backoff and 50k-row pagination.
- **DuckDB Store**: L2 cache utilizing Parquet for efficient, column-oriented analysis.

### Analysis & Quality
- **Four Moments**: Mandatory reporting of Expected Value, Variance, Skewness, and Kurtosis.
- **SLA Tracker**: Monitors dataset age against thresholds (HIGH=14d, MEDIUM=30d, LOW=60d).

### Visualization
- **Plotly**: Interactive dashboards for KPI tracking and hypothesis testing.
- **Folium**: Map-based visualization for spatial conflict detection.

---

## 5. Key Decisions
- **DuckDB over Postgres**: Prioritizes local speed and ease of setup for individual analysts.
- **Parquet Persistence**: Ensures portable, efficient data storage.
- **Bayesian Modeling**: Uses MCMC for asset degradation and deterioration modeling where OLS fails.
