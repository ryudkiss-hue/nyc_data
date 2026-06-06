# Python API Reference

All modules are importable from `socrata_toolkit`. This guide covers the primary entry points and common patterns.

## Core Module: `socrata_toolkit.core.client`

**Fetch live data:**
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

config = SocrataConfig()
client = SocrataClient(config)

# Fetch DataFrame with optional filtering
df = client.fetch_dataframe(
    domain="data.cityofnewyork.us",
    fourfour="dntt-gqwq",  # inspection dataset
    max_rows=50000,
    where="upper(borough)='MANHATTAN' AND created_date > '2026-01-01'",
    select=["objectid", "borough", "score", "created_date"]
)

# Get dataset metadata
meta = client.get_metadata("data.cityofnewyork.us", "dntt-gqwq")
print(meta.get("rowCount"), meta.get("createdAt"), meta.get("columnsName"))
```

**Key methods:**
- `fetch_dataframe(domain, fourfour, max_rows=None, where=None, select=None)` → `pd.DataFrame`
- `get_metadata(domain, fourfour)` → `dict` with `rowCount`, `createdAt`, `updatedAt`, `license`, `columns`
- `search_datasets(domain, query)` → `list[SearchResult]` with name, description, fourfour, page_views

## Quality Module: `socrata_toolkit.governance.core`

**Compute quality scores (0–100 composite):**
```python
from socrata_toolkit.governance.core import compute_quality_score

score = compute_quality_score(
    df,
    key_columns=["objectid"],         # for uniqueness check
    date_column="created_date",       # for freshness
    freshness_days_threshold=30,      # data older than 30 days = lower freshness
    type_rules={"score": "numeric"}   # optional type validation
)

print(f"Overall: {score.overall}")           # 0–100
print(f"  Completeness: {score.completeness} (weight: 0.35)")
print(f"  Validity:     {score.validity}     (weight: 0.25)")
print(f"  Consistency:  {score.consistency}  (weight: 0.25)")
print(f"  Freshness:    {score.freshness}    (weight: 0.15)")
```

**Weight constants (single source of truth):** src/socrata_toolkit/governance/core.py lines 38–41
```python
QUALITY_WEIGHT_COMPLETENESS = 0.35
QUALITY_WEIGHT_VALIDITY = 0.25
QUALITY_WEIGHT_CONSISTENCY = 0.25
QUALITY_WEIGHT_FRESHNESS = 0.15
```

**Schema drift detection:**
```python
from socrata_toolkit.governance.core import detect_schema_drift, snapshot_schema

baseline = snapshot_schema(df_old)
drift = detect_schema_drift(df_new, baseline)

if not drift.is_compatible:
    print(f"Added: {drift.added_columns}")
    print(f"Removed: {drift.removed_columns}")
    print(f"Type changes: {drift.type_changes}")
```

**Lineage tracking:**
```python
from socrata_toolkit.governance.core import create_lineage

lineage = create_lineage(dataset_id="inspection", run_id="run-20260605-001")
lineage.add_step(
    step_name="fetch_inspection",
    source="data.cityofnewyork.us",
    action="fetch",
    row_count_in=0,
    row_count_out=398000,
    api_endpoint="dntt-gqwq"
)
lineage.save("data/lineage/inspection_run.json")
```

**Audit logging:**
```python
from socrata_toolkit.governance.core import AuditLogger

logger = AuditLogger()
logger.log_event(
    actor="analyst-user-001",
    action="query",
    resource="violations",
    borough="MN",
    row_count=50000
)
count_flushed = logger.flush("data/audit/access_log.json")
```

## Analysis Module: `socrata_toolkit.analysis`

**Outlier detection (IQR or Z-score):**
```python
from socrata_toolkit.analysis import detect_all_outliers

outlier_reports = detect_all_outliers(df, method="iqr")  # or "zscore"
for col, report in outlier_reports.items():
    print(f"{col}: {report['outlier_count']} outliers (bounds: {report['lower']}, {report['upper']})")
```

**Data profiling:**
```python
from socrata_toolkit.analysis import profile_dataframe, quality_report

profile = profile_dataframe(df)
print(profile.summary())

report = quality_report(df)  # Structured assessment
```

**Cohort analysis:**
```python
from socrata_toolkit.analyst.ramp_analysis import compute_borough_completion_rates

df_ramps = client.fetch_dataframe("data.cityofnewyork.us", "e7gc-ub6z")
rates = compute_borough_completion_rates(
    df_ramps,
    borough_col="borough",
    total_col="total_ramps",
    resolved_col="completed_ramps"
)

# → rates["comparison_table"], rates["overall_completion_rate"], rates["ci_95"]
```

## Visualization Module: `socrata_toolkit.viz`

**Primary chart functions:** src/socrata_toolkit/viz/plotly.py

```python
from socrata_toolkit.viz import (
    bar_chart, histogram, time_series_chart, scatter_plot,
    hypothesis_test_results, waterfall_chart, correlation_heatmap,
    inspector_performance_boxplot
)

# Hypothesis testing results (dual-axis: p-value bars + effect size line)
fig = hypothesis_test_results(
    group_names=["Manhattan", "Brooklyn", "Bronx"],
    p_values=[0.001, 0.05, 0.45],
    effect_sizes=[0.8, 0.5, 0.1]
)

# Waterfall decomposition (SLA breach drivers)
fig = waterfall_chart(
    categories=["Critical Inspections", "Low Scores", "Volume", "Coverage", "Net"],
    values=[30, -15, 20, -5, 30],
    measure=["relative", "relative", "relative", "relative", "total"]
)

# Correlation heatmap
fig = correlation_heatmap(df, numeric_cols=["score", "age_days", "inspector_count"])

# Inspector performance distribution
fig = inspector_performance_boxplot(df, inspector_col="inspector_id", metric_col="score")
```

## Spatial Module: `socrata_toolkit.spatial.core`

**Spatial intersection joins (GIS conflict detection):**
```python
from socrata_toolkit.spatial.core import spatial_intersects_join

result = spatial_intersects_join(
    left_df=permits_df,
    right_df=inspection_df,
    left_geom_col="the_geom",
    right_geom_col="the_geom",
    buffer_meters=50
)

print(f"Conflicts: {result.overlap_count} / {len(permits_df)} ({result.conflict_rate*100:.1f}%)")
print(result.joined.head())
```

## NL Query Module: `app.services.nl_query`

**Translate natural language to SOQL:**
```python
from app.services.nl_query import nl_to_soql, validate_soql

question = "How many open violations per borough in the last 90 days?"
dataset_key = "violations"
columns = ["objectid", "borough", "status", "created_date", ...]

params = nl_to_soql(question, dataset_key, columns)
# → {"where": "...", "select": "...", "$limit": "..."}

errors = validate_soql(params, valid_columns=columns)
if errors:
    print(f"Invalid SOQL: {errors}")
```

## DuckDB Cache Module: `socrata_toolkit.core.duckdb_store`

**Query the L2 Parquet cache (no API calls):**
```python
from socrata_toolkit.core.duckdb_store import query_parquet_cache

result = query_parquet_cache(
    "SELECT borough, COUNT(*) as count FROM violations GROUP BY borough ORDER BY count DESC"
)
print(result)  # Returns list[dict]

# Delta-aware refresh
from socrata_toolkit.core.duckdb_store import fetch_and_update_cache
df = fetch_and_update_cache("violations", incremental=True)
```

---

## Configuration Files

**SLA Thresholds** (data/sla_config.json):
```json
{
  "sla_thresholds": {
    "HIGH": {"days": 14, "description": "Critical datasets"},
    "MEDIUM": {"days": 30, "description": "Important datasets"},
    "LOW": {"days": 60, "description": "Reference datasets"}
  }
}
```

**Filter Presets** (data/filter_presets.json):
```json
{
  "presets": {
    "last_7_days": {"date_range": ["-7d", "today"]},
    "manhattan": {"borough": "MANHATTAN"},
    "critical_only": {"priority": "CRITICAL"}
  }
}
```

---

## Import Patterns (Best Practices)

**1. Fetch & analyze:**
```python
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.governance.core import compute_quality_score
from socrata_toolkit.analysis import detect_all_outliers

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe(domain, fourfour)
score = compute_quality_score(df, key_columns=["id"])
outliers = detect_all_outliers(df, method="iqr")
```

**2. Visualize:**
```python
from socrata_toolkit.viz import bar_chart, histogram, correlation_heatmap
import streamlit as st

fig = bar_chart(df, column="borough", title="Count by Borough")
st.plotly_chart(fig, use_container_width=True)
```

**3. Govern & audit:**
```python
from socrata_toolkit.governance.core import create_lineage, AuditLogger

lineage = create_lineage("inspection")
logger = AuditLogger()
logger.log_event("analyst-001", "query", "violations")
lineage.save("lineage.json")
logger.flush("audit.json")
```

**4. Advanced analytics:**
```python
from socrata_toolkit.analyst.ramp_analysis import compute_borough_completion_rates
from socrata_toolkit.analysis import time_series_analysis

rates = compute_borough_completion_rates(df, borough_col="borough", ...)
trend = time_series_analysis(df, date_col="date", value_col="count")
```

---

## Type Signatures

All functions use type hints. Key types:

```python
pd.DataFrame         # pandas DataFrame (primary data structure)
dict[str, Any]       # config dicts, metadata, lineage
list[str]            # column names, filter values
float                # quality scores (0–100), probabilities (0–1)
datetime             # timestamps (always UTC)
QualityScore         # dataclass: overall, completeness, validity, consistency, freshness
SchemaDiff           # dataclass: added_columns, removed_columns, type_changes, is_compatible
LineageRecord        # dataclass: dataset_id, run_id, created_at, steps
AuditEvent           # dataclass: timestamp, actor, action, resource, details
```

---

## Error Handling

**At system boundaries only** (API calls, file I/O):

```python
try:
    df = client.fetch_dataframe(domain, fourfour)
except Exception as e:
    logger.error(f"Failed to fetch {fourfour}: {e}")
    return None
```

**Do NOT validate inside the toolkit.** Trust the caller's inputs and pandas' error messages.
