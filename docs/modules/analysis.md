# `socrata_toolkit.analysis` — Analytics & Profiling

**File:** `socrata_toolkit/analysis.py` | **Pillar:** Analytics  
**Dependencies:** `pandas`, `plotly`

---

## Data Profiling

### `profile_dataframe(df) → DataProfile`
Returns a `SimpleNamespace` with row/column counts, null counts, dtypes, unique counts, and numeric summary statistics.

```python
from socrata_toolkit import profile_dataframe
prof = profile_dataframe(df)
print(prof.row_count, prof.column_count)
print(prof.columns["borough"])  # {"dtype": "object", "missing": 12, "unique": 5}
print(prof.numeric_summary)     # pandas describe() as dict
```

### `quality_report(df, key_columns) → dict`
Produces a quality report covering missing values and duplicate rows/keys.
```python
rpt = quality_report(df, key_columns=["id", "complaint_date"])
# → {"row_count": 5000, "missing_values": {...}, "duplicate_rows": 3, "duplicate_keys": {...}}
```

---

## Text Analytics

### `TextInsights` (dataclass)
```python
@dataclass
class TextInsights:
    top_terms: list[tuple[str, int]]  # (term, frequency) pairs
    regex_hits: dict[str, int]        # {"emails": 12, "phones": 3, ...}
    tags: list[str]                   # All unique tags generated
    row_count: int
```

### `generate_text_insights(df, text_columns, regex_patterns, geo_column) → tuple[pd.DataFrame, TextInsights]`
Analyzes text columns for frequent terms, regex patterns, and auto-tags each row.

```python
tagged_df, insights = generate_text_insights(
    df,
    text_columns=["description", "resolution_description"],
    geo_column="location"
)
print(insights.top_terms[:5])  # [("sidewalk", 412), ("repair", 301), ...]
print(insights.regex_hits)     # {"emails": 0, "phones": 2, "urls": 5, "ids": 88}
```

Built-in regex patterns: `emails`, `phones`, `urls`, `ids`. Pass `regex_patterns` dict to customize.

### `extract_term_frequencies(text_list) → dict[str, int]`
Count term frequencies across a list of strings. Returns top 100 terms (≥4 chars).

### `extract_patterns(df, column, pattern_type) → dict[str, int]`
Count `"emails"` or `"phones"` matches in a column.

---

## Validation

### `ValidationReport` (dataclass)
```python
@dataclass
class ValidationReport:
    valid: bool
    errors: list[str]
    warnings: list[str]
    affected_records: int = 0
```

### `validate_required_columns(df, required) → ValidationReport`
Checks that all required columns exist.
```python
rpt = validate_required_columns(df, ["borough", "latitude", "longitude"])
```

### `validate_geospatial_bounds(df, lat_col, lon_col) → ValidationReport`
Validates all lat/lon values fall within NYC bounding box (40.4774–40.9176N, 74.2591–73.7004W).

### `validate_ada_compliance_gates(df, ada_col) → ValidationReport`
Checks ADA compliance column exists and has no nulls.

---

## Anomaly Detection

### `AnomalySeverity` (enum)
`CRITICAL | HIGH | MEDIUM | LOW | INFO`

### `Anomaly` (dataclass)
```python
@dataclass
class Anomaly:
    timestamp: datetime; metric_name: str; anomaly_type: str
    value: float; expected_range: tuple[float,float]
    severity: AnomalySeverity; z_score: float|None; explanation: str
```

### `AnomalyDetector`
Statistical anomaly detection via Z-score.
```python
detector = AnomalyDetector(z_score_threshold=3.0, min_history=5)
anomalies = detector.detect_outliers("defect_density", [(t1, 2.1), (t2, 2.3), ...])
```

### `detect_anomalies(df) → pd.DataFrame`
Returns rows where any numeric column exceeds 3 standard deviations from the mean.

### `flag_anomalies(df) → pd.DataFrame`
Returns the full DataFrame with a `_is_anomaly` boolean column added.

### `detect_outliers_iqr(df, column) → pd.Series`
Returns a boolean mask using IQR (1.5× fence) method.

### `detect_outliers_zscore(df, column, threshold=3.0) → pd.Series`
Returns a boolean mask using Z-score method.

### `detect_all_outliers(df) → list[SimpleNamespace]`
Returns outlier counts for all numeric columns as a list of `{column, outlier_count}` namespaces.

---

## SLA & Freshness

### `SLAMetrics` (dataclass)
```python
@dataclass
class SLAMetrics:
    avg_total_cycle_days: float
    sla_compliance_rate: float   # 0–100
    violation_count: int
    by_borough: dict
```

### `compute_sla_metrics(df, start_col, end_col) → SLAMetrics`
Computes SLA metrics from date columns. Default: `complaint_date` → `repair_date`. SLA threshold: 120 days.

```python
sla = compute_sla_metrics(df, start_col="created_date", end_col="closed_date")
print(f"Compliance: {sla.sla_compliance_rate}%, Violations: {sla.violation_count}")
```

### `flag_sla_violations(df, threshold_days=120) → pd.DataFrame`
Returns only the rows that exceed the SLA threshold.

### `compute_freshness_score(df, date_col) → float`
Returns a 0–100 score: `100 - age_in_days`. Falls to 0 if date column missing or unparseable.

```python
score = compute_freshness_score(df, "updated_at")  # 100.0 if updated today
```

---

## Statistical Functions

### `correlation_analysis(df) → pd.DataFrame`
Returns a correlation matrix for all numeric columns.

### `time_series_summary(df, date_col, value_col) → dict`
Returns `{"mean": ..., "max": ...}` for a numeric column indexed by dates.

### `classify_distribution(series) → str`
Returns `"categorical"` if < 10 unique values, else `"numeric"`.

### `classify_all_distributions(df) → list[SimpleNamespace]`
Returns `{column, best_fit}` for every column.

---

## Program Metrics

### `MetricSnapshot` (dataclass)
```python
@dataclass
class MetricSnapshot:
    name: str; value: float; timestamp: str
    status: str  # "green" | "red"
    target: float; delta_from_target: float
```

### `MetricsTracker`
Records metric history and computes status vs target.
```python
tracker = MetricsTracker()
snap = tracker.record("defect_density", value=2.4, target=2.0)
print(snap.status)  # "red"
```

### `compute_program_dashboard(df) → SimpleNamespace`
Compute KPI dashboard from a violations DataFrame.
Returns: `{metrics, overall_health, green_count, yellow_count, red_count}`.

---

## Reports

### `Report`
```python
report = Report("My Title", "Content text...")
report.to_markdown()   # → "# My Title\n\nContent text..."
report.to_html()
report.save("outputs/reports/my_report.md")
```

### `generate_contract_report(df) → Report`
Generates a summary contract status report.

### `generate_inquiry_response(inquiry_type, df, **kwargs) → Report`
Generates a boilerplate NYC DOT inquiry response.

### `generate_program_report(dashboard) → Report`
Converts a `compute_program_dashboard()` result to a formatted Markdown report.

### `generate_pdf_report(report, path)`
Saves report as a Markdown file (PDF generation stub — extend with `weasyprint`).

---

## Plotly Visualizations

All functions return interactive Plotly figures using `plotly_dark` theme.

### `histogram(df, column, title) → go.Figure`
Histogram with box plot marginal.
```python
fig = histogram(df, "violations")
fig.show()
```

### `bar_chart(df, column, title, top_n=20) → go.Figure`
Value-count bar chart for the top N categories.

### `correlation_heatmap(df, title) → go.Figure`
Interactive correlation heatmap with `RdBu_r` color scale.
