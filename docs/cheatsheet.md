# NYC DOT Sidewalk Toolkit -- Quick Reference

## Setup

```bash
pip install -e ".[all]"        # Install everything
python -m socrata_toolkit.install_wizard  # Interactive config
socrata doctor                 # Verify installation
```

## Daily Workflow

### 1. Fetch Inspection Data

```bash
# Search for datasets
socrata search "sidewalk inspections" --domain data.cityofnewyork.us

# Download to JSON
socrata fetch data.cityofnewyork.us h9gi-nx95 --format json --out inspections.json

# Download to Excel with metadata
socrata fetch data.cityofnewyork.us h9gi-nx95 --format xlsx --out inspections.xlsx --include-meta
```

### 2. Build Construction List

```python
from socrata_toolkit.construction_list import *

df = pd.read_csv("inspections.csv")
df = prioritize_construction_list(df)      # Score and rank
df = classify_scope(df)                     # sidewalk/ramp/curb/ada/tree_pit
df = flag_ada_locations(df)                 # Flag ADA compliance needs

# Check for permit conflicts
permits = pd.read_csv("active_permits.csv")
result = detect_construction_conflicts(df, permits)
print(f"Conflicts: {result.conflict_count} ({result.conflict_rate}%)")

# Export clean list
export_construction_list(result.clean, "construction_list.xlsx")
```

### 3. Track Contract Progress

```python
from socrata_toolkit.contract_analytics import *

progress = analyze_contract_progress(contracts_df)
budget = budget_analysis(contracts_df)
productivity = productivity_metrics(contracts_df)

print(f"CPI: {budget.cost_performance_index}")
print(f"Throughput: {productivity.sqft_per_day} sqft/day")
```

### 4. Generate Reports

```python
from socrata_toolkit.reporting import *

# Contract status report
report = generate_contract_report(contracts_df)
report.save("reports/contract_status.html")

# Respond to an inquiry
response = generate_inquiry_response("borough_overview", df, borough="MANHATTAN")
print(response.to_markdown())
```

### 5. Program Dashboard

```python
from socrata_toolkit.program_metrics import *

dashboard = compute_program_dashboard(kpi_data)
print(f"Health: {dashboard.overall_health}")
# green_count, yellow_count, red_count
```

### 6. Export for BI Tools

```python
from socrata_toolkit.bi_integration import *

export_for_tableau(df, "exports/tableau")
export_for_powerbi(df, "exports/powerbi")
```

### 7. Push to Work Management

```python
from socrata_toolkit.work_management import *

# Monday.com
monday = MondayAdapter()
items = monday.construction_list_to_items(df)
monday.export_items("monday_import.json", items)

# MS Project
MSProjectExporter().from_contracts(contracts_df)
```

## CLI Quick Commands

| Command | What it does |
|---------|-------------|
| `socrata search "query"` | Search NYC Open Data |
| `socrata fetch <domain> <4x4> --out file` | Download dataset |
| `socrata analyze <domain> <4x4>` | Profile a dataset |
| `socrata outliers <domain> <4x4>` | Find outliers |
| `socrata correlations <domain> <4x4>` | Find correlations |
| `socrata quality-score <domain> <4x4>` | Quality score |
| `socrata visualize <domain> <4x4> --chart histogram --column col --out img.png` | Make a chart |
| `socrata pipeline <domain> <4x4> --json-out data.json` | Full pipeline |
| `socrata doctor` | Check installation |

## Standard KPIs

| KPI | Target | Formula |
|-----|--------|---------|
| Defect Density | < 2.0 violations/mile | SUM(violations) / SUM(curb_miles) |
| Throughput Velocity | > 200 ft/day | SUM(built_linear_feet) / SUM(days) |
| Budget Burn Variance | Near $0 | SUM(actual_spend) - SUM(planned_spend) |
| First Pass Yield | > 90% | SUM(first_pass) / SUM(total_inspections) |
| Rework Factor | < 5% | SUM(rework_spend) / SUM(actual_spend) |
| ADA Compliance | 100% | ADA-passing ramps / total ramps |
| On-Time Rate | > 90% | On-time contracts / total contracts |

## Borough Codes

| Borough | Code |
|---------|------|
| Manhattan | 1 |
| Bronx | 2 |
| Brooklyn | 3 |
| Queens | 4 |
| Staten Island | 5 |
