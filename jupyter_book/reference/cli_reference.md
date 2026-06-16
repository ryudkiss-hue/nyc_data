# CLI Toolkit Reference

Complete command reference for the `socrata` CLI toolkit.

## Installation

```bash
pip install -e .
# or with mission extras:
pip install -e ".[mission]"
```

## Quick Start

```bash
socrata --help                    # Show all commands
socrata dataset health --all      # Check all datasets
socrata dataset health --key inspection  # Check one dataset
```

---

## Dataset Commands

### Health & Status

**Check dataset freshness and quality:**
```bash
# All datasets
socrata dataset health --all

# Single dataset
socrata dataset health --key inspection

# Show only stale datasets (>7 days old)
socrata dataset health --all --stale 7

# Sort by staleness
socrata dataset health --all --sort-by staleness
```

### Fetch & Export

**Fetch data from NYC Open Data:**
```bash
# CSV format
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --format csv --out inspections.csv

# Excel
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --format xlsx --out inspections.xlsx

# JSON
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --format json --out inspections.json

# With filters
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --format csv \
  --where "borough='MANHATTAN'" \
  --out manhattan_inspections.csv

# Limit rows
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --limit 1000 --format csv --out sample.csv
```

### Ramp Analysis

**Analyze ADA ramp completion rates:**
```bash
# Quick sample analysis
socrata dataset ramp-analysis --sample 100

# Full-corpus analysis (requires SOCRATA_APP_TOKEN)
socrata dataset ramp-analysis --full-corpus

# With confidence intervals
socrata dataset ramp-analysis --full-corpus --include-ci

# Single borough
socrata dataset ramp-analysis --full-corpus --borough MN

# Output as JSON
socrata dataset ramp-analysis --full-corpus --output ramps.json
```

---

## Quality & Validation Commands

### Quality Scoring

**Assess data quality (0-100 composite score):**
```bash
# Score a dataset
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --key-column objectid \
  --date-column created_date

# With output
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --output quality_report.json

# Show all dimensions (completeness, validity, consistency, timeliness)
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --verbose
```

### Schema Drift Detection

**Track column/type changes over time:**
```bash
# Save current schema snapshot
socrata schema-drift data.cityofnewyork.us dntt-gqwq \
  --save-snapshot

# Check against previous snapshot
socrata schema-drift data.cityofnewyork.us dntt-gqwq \
  --compare-to snapshot.json
```

### Outlier Detection

**Find anomalous rows:**
```bash
# IQR method
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method iqr \
  --column violation_count \
  --output outliers.json

# Z-score method
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method zscore \
  --threshold 3
```

---

## Spatial & Conflict Commands

### Conflict Detection

**Find overlaps between permits and inspections:**
```bash
# Manhattan, 50m buffer
socrata conflict-detect --borough MN --buffer 50 \
  --output conflicts_mn.geojson

# All boroughs, 100m buffer
socrata conflict-detect --buffer 100 \
  --output all_conflicts.geojson

# Custom extent
socrata conflict-detect \
  --extent "-74.0,40.7,-73.9,40.8" \
  --buffer 75
```

---

## Reporting Commands

### Export Reports

**Generate Excel/PDF/PPTX reports:**
```bash
# Contract/budget report
socrata report contract --output contract_report.xlsx

# Quality scorecard
socrata report quality --output quality_scorecard.pdf

# Borough summary
socrata report borough-summary --output borough_report.pptx

# Custom report (ramp analysis)
socrata report ramp-analysis --borough MN --output ramp_report.xlsx
```

---

## Natural Language Query

### NL → SoQL Translation

**Convert English questions to SQL:**
```bash
# Translate query
socrata nl-query "How many open violations per borough?" \
  --dataset violations

# Translate and execute
socrata nl-query "What's the average time to completion?" \
  --dataset inspection \
  --execute

# Show SoQL only (don't execute)
socrata nl-query "Top 10 violations by count" \
  --dataset violations \
  --dry-run
```

---

## Cache & Sync Commands

### Data Caching

**Manage local Parquet cache (L2 layer):**
```bash
# Refresh cache for one dataset
socrata cache refresh inspection

# Refresh multiple datasets
socrata cache refresh inspection violations ramp_progress

# Refresh all
socrata cache refresh --all

# Check cache size
socrata cache status
```

### Sync Operations

**Sync data to PostgreSQL or Delta Lake:**
```bash
# Sync to PostgreSQL (requires PG_DSN)
socrata sync --dataset inspection \
  --domain data.cityofnewyork.us \
  --target postgres

# Dry run (show plan, don't execute)
socrata sync --dataset inspection --dry-run

# Incremental sync (delta only)
socrata sync --dataset inspection --incremental
```

---

## Observability Commands

### Status & Health

**Monitor system health:**
```bash
# Overall status
socrata observability status

# SLA report (last 30 days)
socrata observability sla-report --window 30

# Audit log
socrata observability audit-log --limit 100

# Data lineage
socrata lineage dag --format mermaid
```

---

## Database Commands

### DuckDB Management

**Query local cache or database:**
```bash
# Check DuckDB status
socrata db-status

# Query cache directly
socrata db-query "SELECT borough, COUNT(*) FROM inspection GROUP BY borough"

# List cached tables
socrata db-list-tables

# Export table
socrata db-export inspection --format parquet --out inspection.parquet
```

---

## Doctor (Diagnostic) Commands

### Pre-flight Checks

**Verify environment and configuration:**
```bash
# Full diagnostic
socrata doctor --checklist

# Check specific systems
socrata doctor --check database
socrata doctor --check socrata-api
socrata doctor --check file-permissions
socrata doctor --check envvars
```

---

## Environment Variables

Set these before running commands:

| Variable | Purpose | Example |
|----------|---------|---------|
| `SOCRATA_APP_TOKEN` | API authentication (required for >2K rows) | `ABC123XYZ...` |
| `ANTHROPIC_API_KEY` | Claude API (for nl-query) | `sk-ant-...` |
| `SOCRATA_DOMAIN` | Socrata portal | `data.cityofnewyork.us` |
| `SOCRATA_CACHE_DIR` | Parquet cache location | `/data/cache` |
| `DUCKDB_PATH` | DuckDB database file | `data/local_db/nyc_mission_control.duckdb` |
| `PG_DSN` | PostgreSQL connection | `postgresql://user:pass@host:5432/db` |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (invalid input, API failure) |
| 2 | Data not found |
| 3 | Configuration missing (e.g., SOCRATA_APP_TOKEN) |
| 4 | Permission denied |
| 5 | Timeout |

---

## Common Workflows

### Daily Dataset Refresh
```bash
# Check health
socrata dataset health --all --stale 7

# Refresh caches
socrata cache refresh --all

# Generate quality report
socrata quality-score data.cityofnewyork.us dntt-gqwq --output daily_quality.json
```

### Ramp Program Analysis
```bash
# Full borough analysis
socrata dataset ramp-analysis --full-corpus --include-ci

# Export as report
socrata report ramp-analysis --output ramp_status.xlsx

# Check SLA compliance
socrata observability sla-report --window 30
```

### Conflict Detection
```bash
# Detect spatial overlaps
socrata conflict-detect --buffer 100 --output conflicts.geojson

# Export as map layers
socrata db-export conflicts --format geojson --out conflicts.geojson
```

---

## Tips & Tricks

**Speed up large queries:**
- Set `SOCRATA_APP_TOKEN` for full-corpus access
- Use `--limit` to sample before full fetch
- Leverage `--where` filters to reduce payload

**Avoid common errors:**
- Always set `SOCRATA_APP_TOKEN` before fetching >2K rows
- Check `socrata dataset health` before analyzing stale datasets
- Use `--dry-run` to preview reports before generating

**Integrate with Python:**
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', 'dntt-gqwq', max_rows=50000)
```

