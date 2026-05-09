# NYC DOT Sidewalk Toolkit

A comprehensive Python toolkit for the NYC Department of Transportation's Sidewalk Inspection & Management unit. Built for project analysts and managers who need to collect, analyze, and report on sidewalk repair data across the five boroughs.

## Quick Start

```bash
# Install core dependencies
pip install -e .

# Install with all optional extras
pip install -e ".[postgres,mongo,xlsx,nlp,dev]"

# Run the interactive setup wizard
python -m socrata_toolkit.install_wizard

# Verify your installation
socrata doctor
```

## What This Toolkit Does

| Module | Purpose |
|--------|---------|
| **Core Client** | Fetch data from NYC Open Data (Socrata API) with pagination, retries, and GeoJSON support |
| **Construction Lists** | Build, prioritize, and export construction lists with conflict detection |
| **Contract Analytics** | Track contract progress, budget (EVM), and productivity metrics |
| **Borough Analysis** | Five-borough comparisons, hotspot identification, and equity analysis |
| **Program Metrics** | KPI tracking with red/yellow/green dashboards and budget code management |
| **Reporting** | Generate Markdown, HTML, and JSON reports for contracts, KPIs, and inquiries |
| **Analysis** | Outlier detection, correlation analysis, time series, distributions |
| **Visualization** | Histograms, heatmaps, time series charts, quality dashboards |
| **Governance** | Data lineage, audit logging, quality scoring, schema drift, retention |
| **Excel Integration** | Pivot tables, VLOOKUP, formulas, multi-sheet workbook builder |
| **SQL Integration** | DDL/DML generation, query builder, analytics views, cross-DB portability |
| **BI Integration** | Tableau, Power BI, and PowerPoint exports |
| **Work Management** | Monday.com, MS Project, Microsoft 365, Google Workspace adapters |

## Installation

### Prerequisites

- Python 3.9 or later
- pip or poetry

### Basic Install

```bash
pip install -e .
```

### Install Extras

```bash
# PostgreSQL support
pip install -e ".[postgres]"

# MongoDB support
pip install -e ".[mongo]"

# Excel export (openpyxl)
pip install -e ".[xlsx]"

# NLP features (spacy)
pip install -e ".[nlp]"

# Everything
pip install -e ".[postgres,mongo,xlsx,nlp,dev]"
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `SOCRATA_APP_TOKEN` | Socrata API app token (optional, increases rate limits) |
| `PG_DSN` | PostgreSQL connection string |
| `MONGO_URI` | MongoDB connection URI |

## CLI Reference

All commands are available via `socrata <command>`. Run `socrata --help` for the full list.

### Data Fetching

```bash
# Search NYC Open Data
socrata search "sidewalk" --domain data.cityofnewyork.us --limit 10

# Fetch dataset metadata
socrata meta data.cityofnewyork.us h9gi-nx95

# Download data as JSON, GeoJSON, or XLSX
socrata fetch data.cityofnewyork.us h9gi-nx95 --format json --out data.json
socrata fetch data.cityofnewyork.us h9gi-nx95 --format xlsx --out data.xlsx --include-meta
```

### Analysis

```bash
# Profile a dataset (column stats, null counts, types)
socrata analyze data.cityofnewyork.us h9gi-nx95 --key-column id

# Detect outliers
socrata outliers data.cityofnewyork.us h9gi-nx95 --method iqr

# Find correlations
socrata correlations data.cityofnewyork.us h9gi-nx95 --threshold 0.5

# Text insights (term frequency, regex patterns, tags)
socrata text-insights data.cityofnewyork.us h9gi-nx95 --text-column description
```

### Quality & Governance

```bash
# Compute data quality score
socrata quality-score data.cityofnewyork.us h9gi-nx95 --key-column id --date-column updated_at

# Check for schema drift
socrata schema-drift data.cityofnewyork.us h9gi-nx95 --baseline schema.json --save-snapshot current.json
```

### Visualization

```bash
# Generate charts
socrata visualize data.cityofnewyork.us h9gi-nx95 --chart histogram --column violations --out hist.png
socrata visualize data.cityofnewyork.us h9gi-nx95 --chart heatmap --out corr.png
socrata visualize data.cityofnewyork.us h9gi-nx95 --chart quality --out quality.png
```

### Pipeline & Export

```bash
# Full pipeline: fetch, analyze, export to multiple targets
socrata pipeline data.cityofnewyork.us h9gi-nx95 \
  --json-out data.json \
  --xlsx-out data.xlsx \
  --pg-dsn "$PG_DSN" --pg-table inspections --pg-conflict-col id

# Streaming mode (low memory)
socrata pipeline data.cityofnewyork.us h9gi-nx95 --stream --pg-dsn "$PG_DSN" --pg-table data --pg-conflict-col id

# Batch search with a file of IDs
socrata batch-search data.cityofnewyork.us h9gi-nx95 --field id --file ids.txt --out results.json
```

### Operations

```bash
# Detect spatial conflicts
socrata conflict --proposed-file proposed.json --ref-file permits.json --buffer-meters 20

# Run health checks
socrata doctor --check-db

# Apply database migrations
socrata migrate --dsn "$PG_DSN"

# Generate and dispatch alerts
socrata alerts --pg-dsn "$PG_DSN" --preview
```

## Python API Examples

### Construction List Management

```python
from socrata_toolkit.construction_list import (
    prioritize_construction_list,
    detect_construction_conflicts,
    classify_scope,
    flag_ada_locations,
    export_construction_list,
)

# Load and prioritize inspection data
inspections = pd.read_csv("inspections.csv")
prioritized = prioritize_construction_list(inspections)
prioritized = classify_scope(prioritized)
prioritized = flag_ada_locations(prioritized)

# Check for conflicts with active permits
permits = pd.read_csv("permits.csv")
result = detect_construction_conflicts(prioritized, permits)
print(f"{result.conflict_count} conflicts found ({result.conflict_rate}%)")

# Export the clean list
export_construction_list(result.clean, "construction_list.xlsx")
```

### Contract Analytics

```python
from socrata_toolkit.contract_analytics import (
    analyze_contract_progress,
    budget_analysis,
    productivity_metrics,
)

progress = analyze_contract_progress(contracts_df)
for p in progress:
    print(f"{p.contract_id}: {p.pct_complete}% complete, {p.status}")

budget = budget_analysis(contracts_df)
print(f"CPI: {budget.cost_performance_index}, Forecast: ${budget.forecast_at_completion:,.0f}")

prod = productivity_metrics(contracts_df)
print(f"Throughput: {prod.sqft_per_day} sqft/day, Efficiency: {prod.crew_efficiency}")
```

### Program KPI Dashboard

```python
from socrata_toolkit.program_metrics import MetricsTracker, compute_program_dashboard

# Quick dashboard from raw data
dashboard = compute_program_dashboard(df)
print(f"Program health: {dashboard.overall_health}")

# Or build a custom tracker
tracker = MetricsTracker()
tracker.load_standard_kpis()
tracker.record("defect_density", 1.8)
tracker.record("throughput_velocity", 220)
tracker.add_budget_code("PS-001", description="Personnel", allocated=100000, spent=60000)
dashboard = tracker.dashboard()
tracker.save("metrics_state.json")
```

### Report Generation

```python
from socrata_toolkit.reporting import generate_contract_report, generate_inquiry_response

report = generate_contract_report(contracts_df)
report.save("reports/contract_status.md")
report.save("reports/contract_status.html")

# Respond to an inquiry
response = generate_inquiry_response("borough_overview", df, borough="MANHATTAN")
print(response.to_markdown())
```

### Excel Integration

```python
from socrata_toolkit.excel_integration import ExcelWorkbookBuilder, vlookup, create_pivot_table

# Build a multi-sheet workbook
builder = ExcelWorkbookBuilder()
builder.add_data_sheet("Inspections", inspections_df)
builder.add_pivot_sheet("Borough Summary", inspections_df, rows="borough", values="violations")
builder.add_vlookup_sheet("Enriched", inspections_df, contracts_df, "contract_id", "contract_id", ["contractor_name"])
builder.add_formula_column("Inspections", "severity_class", '=IF(B{row}>7,"HIGH","LOW")')
builder.save("report.xlsx")
```

### BI Platform Exports

```python
from socrata_toolkit.bi_integration import export_for_tableau, export_for_powerbi, create_presentation
from socrata_toolkit.bi_integration import SlideContent

# Tableau
export_for_tableau(df, "exports/tableau", geo_columns={"borough": "State/Province"})

# Power BI
export_for_powerbi(df, "exports/powerbi", date_columns=["inspection_date"])

# PowerPoint / Google Slides
slides = [
    SlideContent(title="Program Overview", body="Q1 2025 results", data={"Contracts": 12, "Completion": "78%"}),
    SlideContent(title="Borough Breakdown", body="Performance by borough"),
]
create_presentation(slides, "exports/report.pptx", title="DOT Sidewalk Program")
```

### Work Management Integration

```python
from socrata_toolkit.work_management import MondayAdapter, MSProjectExporter, M365Adapter

# Monday.com
monday = MondayAdapter()
items = monday.construction_list_to_items(construction_df)
monday.export_items("monday_import.json", items)

# Microsoft Project
exporter = MSProjectExporter()
exporter.from_contracts(contracts_df)
exporter.save("schedule.xml")

# Teams notification
msg = M365Adapter.teams_notification("5 new conflicts detected", "Construction conflicts found in Manhattan",
    facts={"Borough": "Manhattan", "Conflicts": 5})
M365Adapter().export_payloads("teams_alert.json", msg)
```

### SQL Generation

```python
from socrata_toolkit.sql_integration import SQLQueryBuilder, dataframe_to_create_table, export_as_sql_file

# Generate DDL + DML
export_as_sql_file(df, "inspections", "setup.sql", dialect="postgres", primary_key="id")

# Fluent query builder
query = (SQLQueryBuilder("inspections")
    .select("borough", "COUNT(*) as cnt", "AVG(severity) as avg_sev")
    .where("status = 'Pending Repair'")
    .group_by("borough")
    .order_by("cnt DESC")
    .limit(10)
    .build())
```

## Project Structure

```
socrata_toolkit/
  __init__.py              # Lazy-loading public API
  client.py                # Socrata API client
  models.py                # Data models (DatasetMetadata, SearchResult)
  cli.py                   # Click-based CLI (20+ commands)
  analysis.py              # Basic profiling and quality reports
  analysis_advanced.py     # Outliers, correlations, time series, distributions
  visualization.py         # Chart generation (matplotlib)
  governance.py            # Lineage, audit, quality scoring, schema drift, retention
  construction_list.py     # Construction list management
  contract_analytics.py    # Contract progress, budget, productivity
  borough_analysis.py      # Five-borough analysis and equity scoring
  program_metrics.py       # KPI tracking and dashboards
  reporting.py             # Automated report generation
  excel_integration.py     # Excel workbook builder, pivot tables, VLOOKUP
  sql_integration.py       # SQL generation and query builder
  bi_integration.py        # Tableau, Power BI, PowerPoint exports
  work_management.py       # Monday.com, MS Project, M365, Google Workspace
  alerts.py                # Alert management and notification
  compliance.py            # DCWP license and Parks permit checks
  conflict.py              # Spatial conflict resolution
  dot_sidewalk.py          # Sidewalk-specific KPIs and SQL templates
  exporters.py             # Postgres, MongoDB, XLSX exporters
  ops.py                   # Grace period, permit lookahead, burndown
  spatial.py               # Shapely-based spatial operations
  text_analytics.py        # Text insights and tagging
  nlp_advanced.py          # NLP (spacy, textblob, transformers)
  llm_duck_bridge.py       # LLM classification bridge

tests/                     # 163 tests covering all modules
scripts/                   # Nightly jobs, migrations, build helpers
sql/migrations/            # Database migration files
docs/                      # Extended documentation
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run a specific module's tests
python -m pytest tests/test_construction_list.py -v

# With coverage
python -m pytest tests/ --cov=socrata_toolkit
```

## License

MIT
