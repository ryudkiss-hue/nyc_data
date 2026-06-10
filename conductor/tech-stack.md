# 🗽 Tech Stack - SIM Analyst Mission Control

## 1. Core Languages & Runtimes
*   **Python 3.11+**: Primary language for data ingestion, statistical modeling, and backend logic.

## 2. Web & UI Frameworks
*   **Plotly Dash (Primary)**: The core framework for the high-fidelity analyst workstation.
*   **UI Components**: Mantine v7 (via `dash-mantine-components` v2.7) for high information density and polished interactions.
*   **Icons**: Dash Iconify.

## 3. Data Management & Ingestion
*   **Socrata SODA3 API**: Primary source for live municipal telemetry.
*   **DuckDB**: L2 Parquet cache for high-performance analytical queries.
*   **Zstandard (zstd)**: High-performance compression for serverside state and dataset caching.
*   **Diskcache**: Persistent serverside caching for SODA3 batches.

## 4. Analytical Engines
*   **Pandas & NumPy**: Core data manipulation and matrix operations.
*   **Scipy & Statsmodels**: Frequentist statistical analysis and regression diagnostics.
*   **Shapely**: Spatial geometry operations and GIS intelligence.
*   **PyMC**: Bayesian MCMC modeling for high-uncertainty SLA forecasting.

## 5. Infrastructure & Tooling
*   **Docker**: Containerization for consistent deployment.
*   **GitHub Actions**: CI/CD for automated testing and validation.
