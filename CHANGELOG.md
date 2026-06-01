# Changelog

All notable changes to this project will be documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.4.0] - 2026-06-01

### Added

- 6 analyst CLI commands (`conflict-detect`, `report`, `dataset health`, `cache refresh`, `export`, `nl-query`)
- Advanced Analytics view with 13 charts (CUSUM, Bayesian CI, KMeans, survival curves, Moran's I autocorrelation, etc.)
- GIS Dashboard with 10 charts (DBSCAN, TSP, conflict buffers, animated bar, etc.)
- Spatial conflict detection engine with Moran's I autocorrelation
- Contract analytics dashboard with Gantt, burn-down, defect recurrence
- DuckDB L2 cache with schema-drift detection
- NL query interface via Claude API (claude-haiku-4-5)
- PDF/Excel/PPTX report generation (WeasyPrint + openpyxl + python-pptx)
- Nightly prefetch scheduler with APScheduler
- Data quality scorecard (0–100 with completeness/uniqueness/validity/timeliness)
- SLA breach forecasting (PyMC Bayesian credible intervals)
- Settings UI with scheduler config, SLA sliders, Slack/ArcGIS testing
- 30 interactive visualizations (up from 6)

### Fixed

- MapPLUTO dataset fourfour corrected (6fi9-q3ta)
- CI unified ignore list for known-optional test files

## [0.3.0] - 2026-03-01

### Added

- Initial Streamlit Mission Control with 6 visualizations
- Core Python library (`socrata_toolkit`)
- Data lineage and governance modules
- 31 data analytics skills library

## [0.2.0] - 2025-12-01

### Added

- CLI toolkit (`socrata` command)
- Socrata SODA API integration
- Basic data quality checks
