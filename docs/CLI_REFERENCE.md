# CLI Reference — socrata Toolkit

Complete reference for the `socrata` command-line interface for NYC DOT data analysis and management.

## Quick Reference

**Installation:**
```bash
pip install -e ".[mission]"
```

**Commands:**
```bash
socrata --help                    # Show all commands
socrata [COMMAND] --help          # Show command help
socrata COMMAND --version         # Show version
```

**Global Options:**
```bash
--debug                           # Enable debug logging
--log-level {DEBUG,INFO,WARNING,ERROR}
--quiet                           # Suppress output
--output {text,json,csv}          # Output format
```

---

## Dataset Management

### dataset health
Analyze dataset freshness, completeness, and SLA compliance.

```bash
# Check single dataset
socrata dataset health --key inspection

# Check all datasets
socrata dataset health --all

# Check datasets stale >7 days
socrata dataset health --all --stale 7

# Sort by staleness (descending)
socrata dataset health --all --sort-by staleness

# JSON output for scripting
socrata dataset health --all --output json
```

**Output:**
- Dataset name, row count, last update
- Age (days since last modified)
- SLA status: ✅ within threshold, ⚠️ at risk, ❌ breached
- Completeness % (null rates by column)

**Exit codes:**
- `0` — All datasets healthy
- `1` — One or more SLA breaches
- `2` — API error

---

### dataset ramp-analysis
Analyze ADA ramp completion rates with confidence intervals.

```bash
# Sample analysis (1000 rows)
socrata dataset ramp-analysis --sample 100

# Full-corpus analysis (requires SOCRATA_APP_TOKEN)
socrata dataset ramp-analysis --full-corpus

# Borough-specific analysis (Manhattan only)
socrata dataset ramp-analysis --borough MN --sample 500

# Include 95% Wilson Score confidence intervals
socrata dataset ramp-analysis --full-corpus --include-ci

# All boroughs with CI
socrata dataset ramp-analysis --full-corpus --include-ci --all-boroughs
```

**Output:**
- Borough, total ramps, completed ramps
- Completion rate %, 95% CI [lower, upper]
- Reliability indicator: "high" (n>100), "medium" (n≥50), "low" (n<50)
- Sample size and data freshness date

---

## Data Fetching & ETL

### fetch
Fetch datasets from Socrata (NYC Open Data).

```bash
# Fetch 1000 rows as JSON
socrata fetch data.cityofnewyork.us dntt-gqwq --max-rows 1000 --format json --out inspections.json

# Fetch with WHERE clause (SOQL syntax)
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --where "borough='BROOKLYN' AND status='OPEN'" \
  --max-rows 50000 \
  --out brooklyn_open.csv

# Fetch to Excel with formatting
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --format xlsx \
  --out inspections.xlsx

# Fetch with column selection
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --select "id,created_date,location,status" \
  --format csv --out subset.csv

# Stream mode (for very large datasets)
socrata fetch data.cityofnewyork.us dntt-gqwq \
  --stream \
  --format parquet \
  --out inspections.parquet
```

**Formats:** `json`, `csv`, `xlsx`, `parquet`  
**Max rows:** Up to 50,000 (or full dataset with `--stream`)

---

### sync
Sync (cache) dataset into local DuckDB for fast queries.

```bash
# Sync single dataset
socrata sync --dataset dntt-gqwq

# Sync multiple datasets
socrata sync --dataset dntt-gqwq --dataset 6kbp-uz6m

# Sync with date filtering
socrata sync --dataset dntt-gqwq \
  --where "created_date > '2026-01-01'"

# Incremental sync (only new/updated rows)
socrata sync --dataset dntt-gqwq --incremental

# Full sync with progress bar
socrata sync --dataset dntt-gqwq --full-corpus --verbose

# List synced tables
socrata db-status
```

**Storage:** `data/local_db/nyc_mission_control.duckdb`

---

### pipeline
ETL pipeline: fetch → clean → deduplicate → load.

```bash
# Complete pipeline (fetch to DuckDB)
socrata pipeline data.cityofnewyork.us dntt-gqwq \
  --table inspections \
  --stream

# Dry-run (show what would happen)
socrata pipeline data.cityofnewyork.us dntt-gqwq \
  --table inspections \
  --dry-run

# Excel output
socrata pipeline data.cityofnewyork.us dntt-gqwq \
  --xlsx-out pipeline_results.xlsx

# With column selection and WHERE filter
socrata pipeline data.cityofnewyork.us dntt-gqwq \
  --select "id,created_date,status,location" \
  --where "borough='MANHATTAN'" \
  --table insp_mn
```

---

## Analysis & Insights

### analyze
Run statistical analysis on a dataset.

```bash
# Profile dataset (null rates, types, distributions)
socrata analyze data.cityofnewyork.us dntt-gqwq --profile

# Anomaly detection (Z-score based)
socrata analyze data.cityofnewyork.us dntt-gqwq --anomalies

# Time-series analysis
socrata analyze data.cityofnewyork.us dntt-gqwq \
  --time-series created_date \
  --aggregate COUNT

# Cohort analysis (by borough)
socrata analyze data.cityofnewyork.us dntt-gqwq \
  --cohort-by borough \
  --metric COUNT
```

---

### conflict-detect
Detect spatial conflicts between datasets (permits vs. inspections).

```bash
# Manhattan conflicts (within 50m buffer)
socrata conflict-detect --borough MN --buffer 50

# All boroughs, output to GeoJSON
socrata conflict-detect --all-boroughs --output-format geojson --out conflicts.geojson

# Detailed report
socrata conflict-detect --borough BK --buffer 100 --detailed

# Export to Shapefile for GIS
socrata conflict-detect --borough QN --output-format shp --out conflicts.shp
```

**Output:** Conflict geometry, address, overlap percentage, severity

---

### query
Run arbitrary SOQL (Socrata Query Language) queries.

```bash
# Count inspections by borough
socrata query data.cityofnewyork.us dntt-gqwq \
  "SELECT borough, COUNT(*) AS count GROUP BY borough"

# Complex aggregation
socrata query data.cityofnewyork.us dntt-gqwq \
  "SELECT 
     borough, 
     status, 
     AVG(priority) AS avg_priority, 
     COUNT(*) AS total 
   GROUP BY borough, status 
   ORDER BY borough, status"

# Validate SOQL before running
socrata query data.cityofnewyork.us dntt-gqwq \
  "SELECT * FROM table" \
  --validate

# Save results
socrata query data.cityofnewyork.us dntt-gqwq \
  "SELECT * LIMIT 100" \
  --out results.json
```

---

## Quality & Governance

### quality-score
Calculate composite quality score (0–100) for a dataset.

```bash
# Overall score with breakdown
socrata quality-score data.cityofnewyork.us dntt-gqwq

# Score with key column tracking
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --key-column id \
  --date-column created_date

# Freshness threshold (days)
socrata quality-score data.cityofnewyork.us dntt-gqwq \
  --freshness-threshold 30
```

**Dimensions:**
- **Completeness** (35%) — Non-null rates across key columns
- **Validity** (25%) — Data type consistency, range checks
- **Consistency** (25%) — No duplicates, referential integrity
- **Timeliness** (15%) — Freshness (age) vs. SLA threshold

---

### schema-drift
Detect schema changes (added/removed/renamed columns).

```bash
# Check for schema drift
socrata schema-drift data.cityofnewyork.us dntt-gqwq

# Save current schema snapshot
socrata schema-drift data.cityofnewyork.us dntt-gqwq --save-snapshot

# Compare against previous snapshot
socrata schema-drift data.cityofnewyork.us dntt-gqwq --compare-snapshot

# Alert on breaking changes
socrata schema-drift data.cityofnewyork.us dntt-gqwq --alert-on-breaking
```

---

### outliers
Detect statistical outliers.

```bash
# IQR method (default)
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method iqr \
  --column priority

# Z-score method
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method zscore \
  --threshold 3.0

# Isolation Forest (multivariate)
socrata outliers data.cityofnewyork.us dntt-gqwq \
  --method isolation_forest \
  --out outliers.json
```

---

## Reporting

### report
Generate analyst reports.

```bash
# Contract performance report
socrata report contract --output contract_report.xlsx

# Ramp completion report
socrata report ramp --borough all --include-ci --output ramp_report.xlsx

# Inspection health report
socrata report inspection --period 30 --output insp_health.pdf
```

**Formats:** `xlsx`, `pdf`, `pptx`

---

### export
Export data in multiple formats.

```bash
# Export to Excel (with formatting)
socrata export dntt-gqwq --format xlsx --out inspections.xlsx

# Export to Parquet (columnar, compressed)
socrata export dntt-gqwq --format parquet --out inspections.parquet

# Export to CSV
socrata export dntt-gqwq --format csv --out inspections.csv

# Export with filters
socrata export dntt-gqwq \
  --format xlsx \
  --where "borough='MANHATTAN'" \
  --out manhattan.xlsx
```

---

## Natural Language Queries

### nl-query
Translate natural language to SOQL (requires Claude API).

```bash
# Ask a question
socrata nl-query "How many open violations per borough?"

# With dataset hint
socrata nl-query \
  --dataset violations \
  "Show me high-priority cases from last 30 days"

# Validate result before running
socrata nl-query \
  --dataset inspections \
  "Count by status" \
  --validate

# JSON output (for automation)
socrata nl-query \
  --dataset dntt-gqwq \
  "Top 5 boroughs by inspection count" \
  --output json
```

**Requires:** `ANTHROPIC_API_KEY` environment variable set

---

## Observability & Monitoring

### observability
Check monitoring and alerting status.

```bash
# Overall system status
socrata observability status

# SLA compliance report (last 30 days)
socrata observability sla-report --window 30

# Detailed SLA by dataset
socrata observability sla-report --dataset dntt-gqwq

# Alert history
socrata observability alerts --last 7
```

---

### doctor
Diagnose system health.

```bash
# Full system check
socrata doctor

# Check specific components
socrata doctor --check-db      # DuckDB connection
socrata doctor --check-api     # Socrata API access
socrata doctor --check-deps    # Dependencies (pandas, pymc, etc.)
socrata doctor --check-config  # Configuration files

# Detailed output
socrata doctor --verbose
```

---

## Lineage & Impact

### lineage
Track data lineage (sources → transformations → outputs).

```bash
# Show data lineage DAG
socrata lineage dag --format mermaid > lineage.md

# Linear text format
socrata lineage dag --format text

# Save as image (requires Graphviz)
socrata lineage dag --format graphviz --out lineage.png

# Track specific dataset
socrata lineage dataset dntt-gqwq
```

---

## Administrative

### publish
Publish processed data back to Socrata (requires permissions).

```bash
# Publish to existing dataset
socrata publish local.csv --dataset-id a2nx-4u46

# Create new dataset
socrata publish local.csv --new-dataset --name "My Dataset"

# Update with metadata
socrata publish local.csv --dataset-id a2nx-4u46 \
  --description "Updated inspection data" \
  --tags "inspection,quality"
```

---

### meta
Fetch dataset metadata.

```bash
# Dataset info
socrata meta dntt-gqwq

# All columns
socrata meta dntt-gqwq --columns

# Detailed column info (types, descriptions, ranges)
socrata meta dntt-gqwq --columns --detailed

# JSON format
socrata meta dntt-gqwq --output json
```

---

### search
Search Socrata for datasets.

```bash
# Search for "sidewalk" datasets
socrata search -q "sidewalk" --limit 10

# Search for NYC DOT-owned datasets
socrata search -q "DOT" --owner "DOT" --limit 5

# Search with category filter
socrata search -q "inspection" --category "Public Safety" --limit 20

# JSON output
socrata search -q "permit" --output json
```

---

## Configuration

### Configuration Files

**Location:** `~/.socrata/` or `data/config/`

**Files:**
- `.env` or `.env.socrata` — Environment variables
- `socrata_config.yaml` — Default dataset registry, SLA thresholds
- `.socrata-cli.json` — CLI preferences

**Example `.env`:**
```bash
SOCRATA_APP_TOKEN=your_token_here
SOCRATA_DOMAIN=data.cityofnewyork.us
ANTHROPIC_API_KEY=your_claude_key
PG_DSN=postgresql://user:pass@localhost/db
DUCKDB_PATH=data/local_db/nyc_mission_control.duckdb
```

---

## Exit Codes

| Code | Meaning | Example |
|------|---------|---------|
| 0 | Success | `socrata fetch ...` completed successfully |
| 1 | Error | Dataset error, invalid SOQL, SLA breach |
| 2 | API error | Socrata API unavailable, auth failed |
| 3 | Config error | Missing .env, invalid configuration |
| 127 | Command not found | Typo in command name |

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `SOCRATA_APP_TOKEN` | Socrata API token (for high-volume access) | Set from [NYC Open Data tokens page](https://data.cityofnewyork.us/profile/app_tokens) |
| `SOCRATA_DOMAIN` | Socrata portal | `data.cityofnewyork.us` (default) |
| `ANTHROPIC_API_KEY` | Claude API key (for nl-query) | Get from [claude.ai](https://claude.ai) |
| `DUCKDB_PATH` | Local database path | `data/local_db/nyc_mission_control.duckdb` |
| `PG_DSN` | PostgreSQL connection (optional) | `postgresql://user:pass@host/db` |
| `SOCRATA_CACHE_DIR` | Parquet cache directory | `data/cache` |
| `LOG_LEVEL` | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

---

## Common Tasks

### Daily Sync
```bash
# Run this daily to keep DuckDB cache fresh
socrata sync --dataset dntt-gqwq --dataset 6kbp-uz6m --dataset ugc8-s3f6
socrata dataset health --all --sort-by staleness
```

### Weekly Report
```bash
# Generate analyst pack
socrata report contract --output weekly_report.xlsx
socrata report ramp --include-ci --output ramp_status.xlsx

# Check data quality
socrata quality-score data.cityofnewyork.us dntt-gqwq
socrata outliers data.cityofnewyork.us dntt-gqwq --method isolation_forest
```

### Monthly Audit
```bash
# Full health check
socrata doctor

# Schema drift detection
socrata schema-drift data.cityofnewyork.us dntt-gqwq

# Data lineage audit
socrata lineage dag --format text > monthly_lineage.txt

# SLA compliance
socrata observability sla-report --window 30
```

---

## Related Documentation

- [`QUICKSTART.md`](QUICKSTART.md) — Get started in 5 minutes
- [`COMMAND_REFERENCE.md`](COMMAND_REFERENCE.md) — Quick command cheat sheet
- [`MISSION_CONTROL.md`](MISSION_CONTROL.md) — Dashboard reference (alternative to CLI)
- [`CLAUDE.md`](../CLAUDE.md) — Project instructions and context
- [Socrata Query Language (SOQL)](https://dev.socrata.com/docs/queries/) — Write custom queries
