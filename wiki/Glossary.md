# 📖 Glossary

Key terms and definitions used throughout Manhattan Mission Control.

---

## A

**ADA** — Americans with Disabilities Act. Federal law requiring accessibility accommodations. In this context: sidewalk ramp compliance tracking.

**App Token** — A free credential from Socrata that identifies your application and removes API rate limits. Get one at [data.cityofnewyork.us](https://data.cityofnewyork.us).

**ARIA** — Accessible Rich Internet Applications. HTML attributes (`aria-label`, `role`, etc.) that make web apps usable with screen readers.

---

## B

**BBL** — Borough-Block-Lot. NYC's unique property identifier (e.g., `1-00001-0001` = Borough 1 (Manhattan), Block 1, Lot 1).

**BIN** — Building Identification Number. A unique ID for each building in NYC.

**Borough** — One of New York City's five counties: Manhattan, Brooklyn, Queens, the Bronx, and Staten Island.

---

## C

**Cart** — The dataset collection feature. Add datasets to the cart to compare, export, or analyze them together. Supports up to 50 datasets.

**CDN** — Content Delivery Network. A network of servers that deliver files (like JavaScript libraries) quickly. The HTML app loads Leaflet.js, QRCode.js, etc. from CDNs.

**COMPLETENESS** — A 24-item agency sign-off checklist tracking whether all required deliverables are complete. Tracked in `docs/COMPLETENESS.md` and the Settings → Completeness tab.

---

## D

**Dataset** — A collection of records (rows and columns) published on NYC Open Data. Each dataset has a unique **fourfour ID** and is accessible via the Socrata API.

**DuckDB** — An embedded analytical database. Used for local storage in the agency dashboard (`data/local_db/`).

**Demo Mode** — A mode where the app loads sample/fixture data instead of making real API calls. Enabled by setting `MISSION_DEMO=1` or when no Socrata token is configured.

---

## E

**Empty State** — The UI shown when no data is loaded. Provides guidance to configure an API token or enable demo mode.

---

## F

**Fourfour ID** — The unique 8-character identifier for a Socrata dataset (e.g., `nc67-uf89`). Named because it's always formatted as four characters, a hyphen, four characters.

**Freshness** — How recently a dataset was last updated. Datasets updated within the last 24 hours are "fresh" (shown in green). Older datasets are "stale" (shown in orange or red).

---

## G

**GeoJSON** — A JSON format for geographic features (points, lines, polygons). Used for exporting map datasets.

**GitHub Pages** — A free static hosting service by GitHub. The HTML app is automatically deployed here on every push to `main`.

---

## H

**Haversine Distance** — The formula for calculating the shortest distance between two points on a sphere (like Earth). Used in the map viewer's distance measurement tool.

**Heatmap** — A map visualization where point density is shown as a color gradient (blue = sparse, red = dense). Available as a layer in the map viewer.

---

## I

**i18n** — Internationalization. The process of making an app support multiple languages. The Streamlit dashboard supports English and Spanish.

**Ingestion** — The process of fetching data from the Socrata API and loading it into the dashboard. Ingestion events are logged to `outputs/logs/ingest.jsonl`.

---

## J

**JSONL** — JSON Lines. A format where each line is a valid JSON object. Used for the ingestion event log (`ingest.jsonl`).

**Jupyter Notebook** — An interactive coding environment (`.ipynb` files). The code generator can produce a complete Jupyter notebook for any dataset.

---

## L

**Leaflet.js** — An open-source JavaScript library for interactive maps. Used in both the HTML app and the Streamlit spatial workflow.

**localStorage** — A browser API for storing data persistently without a server. Used to save themes, favorites, workspaces, and search history.

---

## M

**Marker Clustering** — Grouping nearby map markers into a single marker with a count badge, to avoid visual clutter on dense datasets.

**Mission Control** — The informal name for the Manhattan Mission Control platform.

---

## N

**NYC Open Data** — The City of New York's official open data portal. Hosts thousands of public datasets. URL: [opendata.cityofnewyork.us](https://opendata.cityofnewyork.us/).

---

## P

**Parquet** — A columnar storage format optimized for analytics. The dashboard caches Socrata API responses as `.parquet` files for fast repeated access.

**PII** — Personally Identifiable Information. Data that can identify an individual (names, SSNs, email addresses, etc.). The AI assistant flags columns that may contain PII.

**Productivity ROI** — Return on Investment calculation for analyst productivity. Measured as time saved vs. manual inspection processes.

---

## Q

**SOQL** — Socrata Query Language. An SQL-like language for filtering and aggregating data from the Socrata API. See [[SOQL-Guide]] for the full reference.

**QA/QC** — Quality Assurance / Quality Control. The process of reviewing data for accuracy, completeness, and consistency.

---

## R

**Readiness Score** — A 0–100 score calculated by `socrata readiness` that measures how production-ready the system is across 5 axes: data, code, infrastructure, compliance, and documentation.

**Render.com** — A cloud platform for deploying web services. The Streamlit dashboard can be deployed to Render with one click using the `render.yaml` blueprint.

**ruff** — A fast Python linter and formatter. Used in CI to enforce code quality.

---

## S

**Socrata** — The company (now part of Tyler Technologies) that powers NYC Open Data. Their API and SOQL are the primary data access layer.

**SOQL Studio** — The query editor tab in the HTML app where you can write and run SOQL queries against any dataset.

**Sparkline** — A small inline chart showing a trend. Used in the dataset cards to show value distribution.

**Streamlit** — A Python framework for building data web apps. Used for the agency dashboard backend.

---

## T

**Tile Layer** — The base map imagery in Leaflet (e.g., Street view from OpenStreetMap, Satellite from Esri, Dark mode from CartoDB).

**TTL** — Time To Live. How long a cached item is considered fresh before being re-fetched. Default: 24 hours for parquet caches.

---

## W

**WCAG 2.1 AA** — Web Content Accessibility Guidelines, version 2.1, Level AA. The accessibility standard that Manhattan Mission Control aims to comply with.

**Workflow** — One of the five analytical views in the agency dashboard: QA/QC, Spatial, Contract, Productivity, or Quality.

**Workspace** — A saved session in the HTML app — includes the dataset cart, search state, and SOQL history. Can be named, saved, restored, exported, and shared.

---

*[[Home]] · [[Feature-Reference]] · [[SOQL-Guide]] · [[Changelog]]*
