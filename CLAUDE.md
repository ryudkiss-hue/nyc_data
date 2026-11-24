# CLAUDE.md

Guidance for Claude Code when working with this repository.

## ⚡ MANDATORY REQUIREMENTS (User Directive 2026-06-18)

**CI FAILURE PROTOCOL - NON-NEGOTIABLE**

If GitHub run or test fails or throws warnings:
- ✅ ALWAYS address it automatically
- ✅ NO exceptions
- ✅ NO delays
- ✅ NO justifications

Any CI failure, test failure, warning, linting error, or build failure must be:
1. Immediately investigated for root cause
2. Automatically fixed in code
3. Verified to confirm the fix works
4. Committed and pushed to main

This is the highest priority quality gate. See MANDATORY_CI_FAILURE_PROTOCOL in memory for details.

---

## What this project is

A static GitHub Pages site for NYC DOT's Sidewalk Inspection and Management (SIM) unit, plus a local MCP server. Since 2026-11-24 the project has no backend, database or container: every page reads NYC Open Data (data.cityofnewyork.us, Socrata SODA) and DOT's ArcGIS server (a841-dotweb01.nyc.gov) directly from the browser. The removed platform (Dash Mission Control, Streamlit, `socrata_toolkit`, pipeline, DuckDB, PostgreSQL, MongoDB, Docker, Cloud Run) is on the branch `archive/pre-simplify`; don't bring those back without being asked.

- `site/`: the Pages site. Plain HTML, CSS and ES modules, no build step, no framework. Pages: `index.html` (home), `explore.html` (any dataset: builder or SoQL, profile, map, export), `datasets.html` (freshness board), `layers.html` (DOT ArcGIS layers), `make-safe/` (Make Safe SR brief). Shared code in `site/assets/ui.js` and `site/assets/site.css`.
- `site/data/datasets.json`: the 112 in-scope datasets (keys, Socrata IDs, domains, primary and foreign keys, freshness tiers, known issues). Source of truth for the dataset list.
- `nyc-opendata-mcp/`: Python MCP server and CLI for Claude Desktop and Claude Code. `site/make-safe/brief.js` is a port of `nyc-opendata-mcp/src/nycod`; change both together and run the parity test.
- `data-analytics-skills/`, `.claude/`, `.agents/`, `.remember/`: Claude skills and notes; not part of the site.

## Working on the site

- Serve locally: `python -m http.server 8000 --directory site`.
- Every value from an API or a file goes into the page with `textContent` (the `el()` helper); never `innerHTML` with data.
- Event binding through `addEventListener` only; no inline handlers.
- Palette: white background, black text, `#228BE6` accent for borders and focus rings, `#1864AB` for text and filled buttons (contrast). WCAG 2.1 AA: visible labels, `role="status"` messages, keyboard tabs (`focusgroup`, polyfilled where missing).
- External libraries come from CDNs pinned by version with subresource-integrity hashes (Leaflet, proj4, SheetJS). Recompute the hash when bumping a version.
- Queries: SoQL text values in single quotes with `'` doubled; field names in backticks. ArcGIS where clauses use the layer's field names; outSR=4326.

## Tests (all live; nothing is mocked)

```
pip install -e "nyc-opendata-mcp[test]" ruff playwright openpyxl
ruff check nyc-opendata-mcp site/tests
pytest nyc-opendata-mcp/tests -q                 # msb.py parity tests need MSB_REFERENCE=<path to the skill's assets/msb.py>
python site/tests/make_py_briefs.py && (cd site && npm ci && npm run check && npm run parity)
python site/tests/browser_smoke.py               # every page in headless Chrome; fails on any console error
```

CI (`.github/workflows/ci.yml`) runs the same on every push and pull request; `pages.yml` deploys `site/` (without `tests/` and npm files) on every push to main.

## Data policy

- Never fabricate row counts, dates, statuses or any other value. An unknown stays blank and is labelled; a failed source is reported as failed.
- No synthetic data in site or server code (test fixtures built from live rows are fine, and say so).
- Never put secrets in the repo. The site's optional Socrata app token and Dynamics link prefix live in the user's browser storage only.

## Known dataset issues

Kept per dataset in the `issue` field of `site/data/datasets.json` (shown on the Datasets page and in Explore). Update that field, with the date you checked, when an issue is confirmed or resolved.
