# NYC DOT SIM · Open Data

Browser tools for NYC DOT's Sidewalk Inspection and Management (SIM) unit, published at **https://ryudkiss-hue.github.io/nyc_data/**. The site is static: every page reads NYC Open Data and DOT's ArcGIS server directly from the browser, so there is no server, database or container to run, and files you open in it stay on your machine.

| Page | What it does |
|---|---|
| [Explore data](https://ryudkiss-hue.github.io/nyc_data/explore.html) | Open any NYC Open Data dataset (search the whole catalog or pick one of the 112 Sidewalk Program datasets), filter it with a builder or plain SoQL, count rows by a column, profile the columns, map the rows and download CSV or JSON. Each query has a shareable link. |
| [Datasets](https://ryudkiss-hue.github.io/nyc_data/datasets.html) | The Sidewalk Program's datasets with live update dates against their freshness tier (HIGH 14, MEDIUM 30, LOW 60 days), row counts, joins and known issues. |
| [DOT map layers](https://ryudkiss-hue.github.io/nyc_data/layers.html) | Browse and query DOT's ArcGIS layers: PRISM corners and ramps, GAZETTEER LION, AddressPoint, MapPLUTO and any other folder. Filter by attribute or distance from a point; map the features and export GeoJSON or CSV. |
| [Make Safe brief](https://ryudkiss-hue.github.io/nyc_data/make-safe/) | Everything public data says about one Make Safe SR, or every SR on a tab of the weekly workbook: corners, ramps, ramp program, complaint and temporary-repair history, permits, capital projects and nearby 311. |

## Repository

```
site/                 the GitHub Pages site (plain HTML, CSS and ES modules; no build step)
  index.html          home and quick start
  explore.html        Explore data
  datasets.html       Datasets board
  layers.html         DOT map layers
  make-safe/          Make Safe brief (brief.js is the browser port of the MCP server's brief)
  assets/             shared ui.js and site.css, one script per page
  data/datasets.json  the 112 in-scope datasets: keys, joins, freshness tiers, known issues
  tests/              JS/Python parity test and a headless-browser smoke test of every page
nyc-opendata-mcp/     local MCP server and CLI for Claude Desktop and Claude Code (same Make Safe brief, plus SoQL and ArcGIS tools)
data-analytics-skills/, .claude/, .agents/, .remember/   Claude skills and notes for analysis work
```

The Dash Mission Control app, Streamlit app, `socrata_toolkit` library, ingest pipeline, DuckDB/PostgreSQL/MongoDB stores, Docker images and Cloud Run deployment were removed on 2026-11-24 to keep the project to one static site. They remain on the branch [`archive/pre-simplify`](https://github.com/ryudkiss-hue/nyc_data/tree/archive/pre-simplify).

## Running the site locally

Any static file server works, for example from the repo root:

```
python -m http.server 8000 --directory site
```

then open http://localhost:8000/.

## Tests

CI runs these on every push and pull request; all of them read the live services.

```
pip install -e "nyc-opendata-mcp[test]" ruff playwright openpyxl
ruff check nyc-opendata-mcp site/tests
pytest nyc-opendata-mcp/tests -q
python site/tests/make_py_briefs.py && (cd site && npm ci && npm run check && npm run parity)
python site/tests/browser_smoke.py        # needs Chrome; set CHROME to its path if it is not /usr/bin/google-chrome
```

## Updating the dataset list

`site/data/datasets.json` holds each dataset's key, Socrata ID, domain, primary key, foreign keys, freshness tier and any known issue. Names, update dates and row counts are read live, so the file only changes when a dataset is added or dropped, a join or tier changes, or an issue is found or resolved. Edit it by hand and keep `sla_rule` in step with any tier change.
