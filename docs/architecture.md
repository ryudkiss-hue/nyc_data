# 🏗️ NYC Sidewalk Toolkit Architecture

## 1. High-Level Design

The toolkit follows a **hybrid DuckLake architecture**, integrating local DuckDB L2 caches with MotherDuck for cloud persistence, collaborative sharing, and industrial-grade data engineering.

```
DATA LAYER
  NYC Socrata (26 datasets) → DuckDB L2 Cache (Parquet) → MotherDuck (DuckLake)

PROCESSING LAYER (7 Pillars)
  1. Core: SODA3 Client, DuckLake Manager, DuckDBRepository
  2. Analysis: Profiling (Four Moments), Bayesian MCMC (PyMC)
  3. Analyst: Weekly packs, MotherDuck Data Shares, Role-based workflows
  4. Quality: SLA tracking, Freshness, Validation rules
  5. Visualization: Plotly Dash (Enterprise), Streamlit (Mission Control)
  6. Governance: Data Lineage (NetworkX), Audit logs, Schema Drift
  7. Engineering: Contract analytics, Budget forecasting

INTERFACE LAYER
  ↓ CLI (socrata tool)
  ↓ Streamlit Mission Control (Port 8501)
  ↓ Dash Workstation (Port 8011)
  ↓ REST API (FastAPI, Port 8000)
```

---

## 2. DuckLake & MotherDuck Integration

The project leverages a **DuckLake** pattern to bridge high-performance local analysis with cloud-scale persistence.

### Hybrid Execution
- **Local (Hot)**: L2 Parquet caches for ultra-fast, feet-on-the-ground spatial analysis.
- **Cloud (Cold/Shared)**: MotherDuck persistence for executive reporting, cross-agency coordination, and long-term trend analysis.
- **Bridging**: The `DuckDBManager` supports transparent `ATTACH 'md:'` operations and `publish_to_motherduck()` data promotion flows.

### Spatial Foundation (Native DuckDB Spatial)
The project utilizes native DuckDB `GEOMETRY` types, replacing legacy WKT/Lat-Lon strings with high-speed geographic objects.

- **Automated Detection**: Ingestion pipelines detect spatial columns and convert to native `GEOMETRY` during upserts.
- **Coordinate Systems**: 
    - **WGS84 (4326)**: Default for ingestion and web mapping.
    - **NAD83 NY Long Island (2263)**: For precision feet-based engineering metrics.

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
