# NYC DOT Sidewalk Toolkit

A comprehensive Python toolkit for the NYC Department of Transportation's Sidewalk Inspection & Management unit. Built for project analysts and managers who need to collect, analyze, and report on sidewalk repair data across the five boroughs.

## Quick Start - Choose Your Method

### 🚀 Fastest Path (5 minutes) - All Platforms

```bash
git clone <repo-url>
cd nyc_data

# Option 1: Python Launcher (all platforms)
python launcher.py setup all
python launcher.py docker up
python launcher.py web

# Option 2: Windows PowerShell
.\deploy.ps1 setup
.\deploy.ps1 start

# Option 3: Linux/MacOS Bash
./deploy.sh setup
./deploy.sh start

# Option 4: Make Commands
make setup-all
make deploy
```

### 📚 Traditional Install (if you prefer local Python)

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

## Execution Methods

| Method | Platform | Best For | Command |
|--------|----------|----------|---------|
| **Python Launcher** | All | Unified interface, automation | `python launcher.py ...` |
| **PowerShell Script** | Windows | Native integration | `.\deploy.ps1 ...` |
| **Bash Script** | Linux/MacOS | Unix operations | `./deploy.sh ...` |
| **Make** | All | Development workflow | `make ...` |
| **Docker Compose** | All | Container management | `docker-compose ...` |
| **CLI Tool** | All | Command-line interface | `socrata ...` or `python launcher.py cli ...` |

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup or [docs/EXECUTABLE_PACKAGE.md](docs/EXECUTABLE_PACKAGE.md) for complete package reference.

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
| **Task Board** | Kanban board with color-coded cards, milestones, activity logging |
| **Workflow Engine** | Multi-step pipeline orchestration with triggers and scheduling |
| **Insights Engine** | AI-powered auto-analysis with recommendations and anomaly narratives |
| **NLP Integration** | Construction list enrichment, complaint triage, location extraction |
| **Cost Estimator** | Scope-based cost estimation with borough rates and ADA surcharges |
| **311 Ingestion** | Auto-fetch and triage sidewalk complaints from NYC Open Data |
| **Map View** | Interactive maps with folium (markers, clusters, color-coding) |
| **Change Detection** | Compare data snapshots to surface additions, removals, and modifications |
| **Contractor Scorecards** | Performance profiles with letter grades (A-F) by contractor |
| **Budget Forecasting** | Spend projection, completion dates, workload backlog modeling |
| **SLA Tracking** | Cycle time metrics, SLA violation flagging by borough |
| **Notification Rules** | Configurable alert rules with Teams, Slack, and email delivery |
| **Data Dictionary** | Auto-generated column documentation with types, nulls, and samples |
| **Quantum Optimization** | Crew assignment and route optimization (Qiskit, Cirq, classical) |
| **Quantum Search** | Grover's algorithm function template for database search |
| **PDF Reports** | PDF export via weasyprint with styled tables |
| **QGIS Integration** | Create GeoPackage files for offline field inspection, generate .qgs project files with PostGIS layers |
| **Mobile Field Packages** | Build offline GeoPackage files for field inspection teams with field metadata, styling, and GPS support |
| **DBeaver Profiles** | Connection profiles for DBeaver, pgAdmin, DataGrip |
| **Flask API** | 10-endpoint REST API for programmatic access |
| **Docker** | Full stack with PostGIS, MongoDB, Streamlit, and API |

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

### Quantum Computing

```python
from socrata_toolkit.quantum_search import quantum_search, SearchCriteria, analyze_grover_circuit
from socrata_toolkit.quantum_optimization import optimize_crew_assignment, optimize_repair_route

# Grover's quantum search (classical fallback when Qiskit not installed)
criteria = SearchCriteria(borough="MANHATTAN", min_severity=7, ada_required=True)
result = quantum_search(df, criteria)
print(f"Found {result.match_count} matches via {result.method}")

# Analyze quantum resource requirements
info = analyze_grover_circuit(n_records=10000, n_solutions=50)
print(f"Qubits: {info.num_qubits}, Iterations: {info.num_grover_iterations}")

# Crew assignment optimization
assignment = optimize_crew_assignment(locations_df, n_crews=5)

# Route optimization (TSP with 2-opt)
route = optimize_repair_route(locations_df)
print(f"Route: {route.route}, Distance: {route.total_distance} km")
```

### Cost Estimation

```python
from socrata_toolkit.cost_estimator import estimate_costs, summarize_costs

estimated = estimate_costs(construction_df)
summary = summarize_costs(estimated)
print(f"Total estimated: ${summary.total_estimated:,.2f}")
```

### 311 Complaint Ingestion

```python
from socrata_toolkit.complaint_ingestion import ingest_311_complaints

result = ingest_311_complaints(max_rows=500, borough="MANHATTAN", create_tasks=True)
print(f"Ingested {result.total}, {result.critical_count} critical")
```

### SLA Tracking

```python
from socrata_toolkit.sla_tracking import compute_sla_metrics, flag_sla_violations

metrics = compute_sla_metrics(df)
print(f"Avg cycle: {metrics.avg_total_cycle_days} days, Compliance: {metrics.sla_compliance_rate}%")
```

### Change Detection

```python
from socrata_toolkit.change_detection import detect_changes

changes = detect_changes(yesterday_df, today_df, key_col="id")
print(f"Added: {changes.added_count}, Modified: {changes.modified_count}")
```

### Schema Registry & Versioning

The Schema Registry provides production-grade schema versioning, drift detection, and backward compatibility validation. Essential for production data governance and preventing breaking changes.

#### Core Concepts

- **Schema Versions**: Each dataset tracks immutable schema snapshots with version numbers
- **Drift Detection**: Automatically detects schema changes (additions, deletions, type changes)
- **Breaking Changes**: Flags column deletions, type changes, and nullability constraints as breaking
- **Backward Compatibility**: Enforces rules (ALLOW, WARN, BLOCK) for schema evolution
- **Audit Trail**: All operations logged with timestamps, authors, and details

#### Python API

```python
from socrata_toolkit.schema_registry import (
    SchemaRegistry,
    SchemaValidator,
    BackwardCompatibilityChecker,
)
import pandas as pd

# Initialize registry (uses local JSON files by default)
registry = SchemaRegistry(storage_dir="schema_registry/")

# Extract and register schema from DataFrame
df = pd.read_csv("sidewalk_inspections.csv")
schema = SchemaRegistry.extract_schema_from_dataframe(df, "sidewalk-inspections")
registry.register_schema(schema)

# Later, check for drift
df_new = pd.read_csv("sidewalk_inspections_updated.csv")
new_schema = SchemaRegistry.extract_schema_from_dataframe(df_new, "sidewalk-inspections")
changes = registry.detect_drift("sidewalk-inspections", new_schema)
for change in changes:
    print(f"{'BREAKING' if change.is_breaking else 'OK'}: {change.description}")

# Validate records against schema
validator = SchemaValidator(schema)
record = {"id": 1, "borough": "MANHATTAN", "inspection_date": "2024-01-15"}
is_valid, errors = validator.validate_record(record)
if not is_valid:
    print(f"Validation errors: {errors}")

# Check backward compatibility
checker = BackwardCompatibilityChecker(strict_mode=False)
is_compatible, violations = checker.check_compatibility(old_schema, new_schema)
if not is_compatible:
    print(f"Breaking changes: {violations}")
```

#### CLI Commands

```bash
# List all schema versions for a dataset
socrata schema list sidewalk-inspections

# Show the latest schema version
socrata schema current sidewalk-inspections --json-out current_schema.json

# Compare two schema versions
socrata schema diff sidewalk-inspections 1 2

# Validate a JSONL file against a schema
socrata schema validate sidewalk-inspections data.jsonl

# Check backward compatibility
socrata schema check-compatibility sidewalk-inspections data_v2.jsonl --strict
```

#### Backward Compatibility Rules

**ALLOW** (always compatible):
- Adding new optional columns
- Adding columns with default values
- Safe type upgrades (int32 → int64, float32 → float64)

**WARN** (caution, may break):
- Renaming columns
- Making previously optional columns required
- Reordering columns (in strict mode)

**BLOCK** (breaking changes):
- Deleting columns
- Type changes (narrowing conversions)
- Making nullable columns required without migration path

#### PostgreSQL Persistence

For production deployments, schema versions can be persisted to PostgreSQL:

```sql
-- Apply migration to create tables
psql "$PG_DSN" < sql/003_schema_registry_tables.sql

-- Tables created:
-- - public.schemas: Master registry entries
-- - public.schema_versions: All versions with changes
-- - public.schema_audit_log: Audit trail
-- - v_latest_schemas: View for latest versions
-- - v_schema_history: View for change history
```

#### Sample Use Case: Construction List Validation

```python
# Register schema for construction lists
construction_df = pd.read_csv("construction_list.csv")
registry.register_schema(
    SchemaRegistry.extract_schema_from_dataframe(construction_df, "construction-list")
)

# Before accepting updates, validate against schema
updated_df = pd.read_csv("construction_list_updated.csv")
validator = SchemaValidator(registry.get_schema_version("construction-list"))
valid_count, errors = validator.validate_batch(updated_df.to_dict('records'))
print(f"Valid records: {valid_count}/{len(updated_df)}")

# Detect breaking changes before applying
new_schema = SchemaRegistry.extract_schema_from_dataframe(updated_df, "construction-list")
changes = registry.detect_drift("construction-list", new_schema)
if any(c.is_breaking for c in changes):
    print("ERROR: Breaking schema changes detected!")
else:
    registry.register_schema(new_schema)
    print("Schema updated successfully")
```

### Messaging Bot

```python
from socrata_toolkit.messaging import BotAdapter

bot = BotAdapter(default_data=df)
response = bot.handle("manhattan backlog")
print(response.text)  # "MANHATTAN: 245 total, 180 pending repairs"
```

## Airflow Pipeline Stabilization (May 2026)

The orchestrator has been modernized to Airflow 2.x. Key updates include:
- **Provider-based Operators**: Migrated to `apache-airflow-providers` for Postgres, Slack, and HTTP integrations.
- **Improved Discovery**: All Airflow services now use a unified `PYTHONPATH` that correctly resolves the `socrata_toolkit` and local project modules.
- **Enhanced Reliability**: Resolved bitshift operator conflicts and modernized sensor base classes.

## Project Structure

The `socrata_toolkit` has been reorganized into functional submodules for better maintainability:

```
socrata_toolkit/
  core/                # Socrata API client, models, and base classes
  discovery/           # Schema registry, dataset search, and metadata discovery
  analysis/            # Data profiling, metrics, and text analytics
  quality/             # Data validation, freshness tracking, and SLA monitoring
  lineage/             # Data provenance and transformation tracking
  integrations/        # SQL, Excel, BI (Tableau/PowerBI), and Graph adapters
  pipeline/            # Ingestion pipelines (311, complaints, CDC/SCD)
  observability/       # Unified logging, health checks, and tracing
  alerts/              # Alert manager and notification delivery (Slack/Teams)
  reports/             # Automated PDF and Markdown report generation
  viz/                 # Visualization engine (Map, Plotly, Dashboards)
  llm/                 # LLM bridges, chatbots, and SQL-to-NL engines
  spatial/             # Geo-spatial analytics and PostGIS integration
  ops/                 # Workflow orchestration and operation management
  quantum/             # Quantum optimization and search algorithms (Classical fallback)
  tools/               # CLI runner, installation wizard, and dev tools
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run Airflow-specific integration tests
docker exec airflow-scheduler pytest /opt/airflow/project/tests/test_airflow_operators.py

# With coverage
python -m pytest tests/ --cov=socrata_toolkit
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
