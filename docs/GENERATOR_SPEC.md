# Generator Specification: NYC DOT Socrata Swiss Army Knife

This document provides a detailed technical specification for an AI-driven code generator to reconstruct or extend the **NYC DOT Data Assistant**. The application is designed as a universal, portable Socrata open data workbench.

## 1. Core Architecture (Pillar System)
The application must follow a **Pillar Architecture**, where functionality is partitioned into lazy-loaded modules under the `socrata_toolkit` package.

### Toolkit Pillars:
1.  **Core (`core.py`)**:
    - `SocrataClient`: High-performance HTTP client with pagination, retries, and parallel fetching (Dask integration).
    - `SoQLBuilder`: Fluent query builder for Socrata Query Language, including geo-operators (`within_circle`, `within_box`).
    - `DuckDBManager`: Thread-safe database management with `:memory:` fallback for Windows file-locking resilience.
    - `SchemaRegistry`: Versioned JSON persistence for dataset schemas.
2.  **Analytics (`analysis.py`)**:
    - Automated profiling (`profile_dataframe`).
    - Statistical anomaly detection (Z-score and IQR).
    - SLA Tracking (cycle days, compliance rates).
    - Text Insights (term frequency, regex pattern extraction).
3.  **Engineering (`engineering.py`)**:
    - Cost Estimation: Square-foot based rates with borough-specific multipliers.
    - Construction Management: Priority scoring, scope classification, and ADA flagging.
    - Performance: Contractor scorecards and productivity metrics.
    - **Budgeting**: Spending projections, burndown calculations, and completion modeling.
4.  **Pipeline (`pipeline.py`)**:
    - Change Data Capture (CDC): Record-level diffing between dataset versions.
    - **Workflow Engine**: Multi-step `Workflow` and `WorkflowStep` classes with Airflow DAG export.
    - BI Export: Fluent `ExcelWorkbookBuilder`, Tableau/PowerBI CSV exporters.
5.  **Governance (`governance.py`)**:
    - Composite Quality Scoring (Completeness, Consistency, Validity, Freshness).
    - Data Lineage: JSON-based tracking of every pipeline run.
    - Audit Logging: Actor-based event trail.
6.  **Spatial (`spatial.py`)**:
    - Geo-Intersection Joins: Buffer-aware joining of disparate datasets (e.g., Projects vs. Complaints).
    - Clustering: KMeans-based geographic grouping.
    - **Interoperability**: Create/Load GeoPackage (`.gpkg`) and generate QGIS project files (`.qgs`).
7.  **AI (`ai.py`)**:
    - Socrata Chatbot: LLM-driven conversational interface (GPT-4o integration).
    - NL→SQL: Translate natural language questions into SoQL/DuckDB queries.
    - **Quantum Optimization**: Simulated Grover search and TSP route/crew assignment optimization.
8.  **Cleaning (`cleaning.py`)**:
    - Standardized mappings for NYC Boroughs and BBL (Borough-Block-Lot).
    - Type inference and outlier removal.
9.  **API (`api.py`)**:
    - RESTful FastAPI interface for all toolkit functions.

---

## 2. Dash UI Design System
The UI must be **Premium, Responsive, and Interactive**, built with `dash`, `dash-bootstrap-components`, and `Dash AG Grid`.

### Aesthetic Requirements:
- **Rich Palette**: Support for **Dark**, **Light**, and **Sepia** modes via CSS custom properties.
- **Micro-Animations**: Smooth transitions for hover states, sidebar toggles, and data updates.
- **Glassmorphism**: Subtle translucency on cards and sidebars in Dark mode.
- **Interactive Grids**: Every data table should use `dash-ag-grid` with filtering, sorting, and conditional styling enabled.

### Page Ecosystem (14+ Pages):
- **Dashboard**: Central ingest hub with DuckDB browser.
- **SoQL Maestro**: Advanced SQL/SoQL editor with template library.
- **Quantum Workbench**: Visualizations for Grover search and route optimization maps.
- **Task Board**: Persistent Kanban system stored in DuckDB.
- **Dev Tools**: SQL REPL and system performance monitoring.

---

## 3. Deployment & Portability
- **DuckDB-Native**: Direct data ingestion via `httpfs` extension (e.g., `SELECT * FROM read_json_auto('url')`).
- **MotherDuck**: Seamless cloud synchronization when `MOTHERDUCK_TOKEN` is present.
- **Containerization**: Full `docker-compose.yml` for multi-stage production deployment (Gunicorn-backed).
- **Environment Driven**: Configurable via `.env` (Socrata tokens, DB paths, OpenAI keys).

## 4. Reconciliation Protocol
The generator must incorporate specific "Sidewalk Toolkit" logic:
- **Borough Multipliers**: Manhattan (1.35), Brooklyn (1.15), Queens (1.10), Bronx (1.05), SI (1.00).
- **Construction Priority**: `hazardous > severe > moderate > minor`.
- **BBL Generation**: `boro_digit + block(5) + lot(4)`.
- **QGIS XML Structure**: Standard `.qgs` template for PostGIS connections.
