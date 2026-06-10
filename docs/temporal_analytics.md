# Temporal Analytics: Time-Series Analysis with SCD Type 2

## Overview

Temporal analytics enables analyzing how metrics and dimensions change over time using SCD Type 2 historical data. Common use cases include:

- **Trend Analysis**: Track condition scores, material durability over months/years
- **Change Impact**: Measure effects of interventions (e.g., "After repair, condition improved by X%")
- **Deterioration Rates**: Calculate how quickly sidewalk conditions degrade
- **Predictive Maintenance**: Identify patterns predicting failures
- **Performance Reporting**: Report on improvement initiatives

## Key Concepts

### Temporal Granularity

Data can be queried at different time granularities:

```python
from datetime import date, datetime, timedelta

# Point-in-time query
record = tq.get_as_of("sidewalk_123", datetime(2026, 3, 15, 12, 0, 0))

# Daily aggregate
for d in date_range(start_date, end_date):
    record = tq.get_as_of("sidewalk_123", datetime.combine(d, time.min))
    values.append((d, record['data']['condition']))

# Weekly aggregate
for week_start in date_range(start_date, end_date, freq='W'):
    record = tq.get_as_of("sidewalk_123", datetime.combine(week_start, time.min))
    values.append((week_start, record['data']['condition']))

# Monthly aggregate
for month_start in date_range(start_date, end_date, freq='MS'):
    record = tq.get_as_of("sidewalk_123", datetime.combine(month_start, time.min))
    values.append((month_start, record['data']['condition']))
```

### Effective Dating

Each SCD version has an effective date range:

```
Version 1: 2026-01-01 to 2026-03-15 [condition=fair]
Version 2: 2026-03-15 to NULL          [condition=excellent]
```

When querying "as of 2026-03-01", you get Version 1. When querying "as of 2026-04-01", you get Version 2.

## Time-Series Analysis Examples

### 1. Track Metric Over Time

```python
from socrata_toolkit.temporal_queries import TemporalQuery
import pandas as pd
from datetime import date

tq = TemporalQuery(dsn="...", table="sidewalk_conditions_scd")

# Sample dates (e.g., first of each month)
dates = pd.date_range("2026-01-01", "2026-12-31", freq="MS")

# Track ADA compliance for multiple sidewalks
results = tq.track_metric_over_time(
    metric_expr="ada_compliance_score",
    business_keys=["sidewalk_123", "sidewalk_456", "sidewalk_789"],
    dates=[d.date() for d in dates]
)

# Convert to DataFrame
df = pd.DataFrame({
    "date": [d.date() for d in dates],
    "sidewalk_123": [results["sidewalk_123"][i][1] for i in range(len(dates))],
    "sidewalk_456": [results["sidewalk_456"][i][1] for i in range(len(dates))],
    "sidewalk_789": [results["sidewalk_789"][i][1] for i in range(len(dates))],
})

print(df)
# Output:
#        date  sidewalk_123  sidewalk_456  sidewalk_789
# 0 2026-01-01           75.0           80.0           70.0
# 1 2026-02-01           75.0           85.0           75.0
# 2 2026-03-01           90.0           90.0           80.0
```

### 2. Detect Change Patterns

```python
# Analyze which fields change most frequently
pattern = tq.detect_change_patterns("sidewalk_123")

print(f"Total versions: {pattern.total_versions}")
print(f"Fields changed: {pattern.fields_changed}")
print(f"Change frequency: {pattern.change_frequency:.3f} per day")
print(f"Date range: {pattern.date_range[0]} to {pattern.date_range[1]}")
print(f"Changes by type: {pattern.change_types}")

# Example output:
# Total versions: 12
# Fields changed: {'condition', 'material', 'ada_compliance_score'}
# Change frequency: 0.050 per day  (roughly every 20 days)
# Date range: 2026-01-01 to 2026-12-15
# Changes by type: {'INSERT': 1, 'UPDATE': 11}
```

### 3. Calculate Deterioration Rate

```python
def calculate_deterioration_rate(tq, business_key, metric, start_date, end_date):
    """Calculate rate of change per day."""
    versions = tq.get_versions(business_key)
    
    # Filter to date range
    in_range = [v for v in versions 
                if start_date <= v['start_date'] <= end_date]
    
    if len(in_range) < 2:
        return None
    
    first = in_range[-1]['data'].get(metric)
    last = in_range[0]['data'].get(metric)
    
    if first is None or last is None:
        return None
    
    duration_days = (in_range[0]['start_date'] - in_range[-1]['start_date']).days
    if duration_days == 0:
        return None
    
    change_per_day = (last - first) / duration_days
    return change_per_day

# Calculate how condition deteriorates
rate = calculate_deterioration_rate(
    tq,
    business_key="sidewalk_123",
    metric="condition_score",
    start_date=date(2025, 1, 1),
    end_date=date(2026, 1, 1)
)
print(f"Condition deteriorates {rate:.2f} points per day")
```

### 4. Compare Before/After Intervention

```python
def compare_before_after(tq, business_key, intervention_date, metric, window_days=30):
    """Compare metric before and after intervention."""
    before_date = intervention_date - timedelta(days=window_days)
    after_date = intervention_date + timedelta(days=window_days)
    
    before = tq.get_as_of(business_key, before_date)
    after = tq.get_as_of(business_key, after_date)
    
    if not before or not after:
        return None
    
    before_val = before['data'].get(metric)
    after_val = after['data'].get(metric)
    
    if before_val is None or after_val is None:
        return None
    
    improvement = after_val - before_val
    percent_change = (improvement / before_val * 100) if before_val != 0 else 0
    
    return {
        "before": before_val,
        "after": after_val,
        "improvement": improvement,
        "percent_change": percent_change,
    }

# Measure repair impact
result = compare_before_after(
    tq,
    business_key="sidewalk_123",
    intervention_date=date(2026, 3, 15),
    metric="condition_score",
    window_days=30
)

print(f"Before repair: {result['before']}")
print(f"After repair: {result['after']}")
print(f"Improvement: {result['percent_change']:.1f}%")
```

## Statistical Analysis

### 1. Trend Analysis

```python
import numpy as np
from scipy import stats

# Get time series data
dates = pd.date_range("2026-01-01", "2026-12-31", freq="M")
results = tq.track_metric_over_time(
    "condition_score",
    ["sidewalk_123"],
    [d.date() for d in dates]
)

# Convert to values
values = [v[1] for v in results["sidewalk_123"]]
x = np.arange(len(values))
y = np.array(values)

# Calculate trend line
slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

print(f"Trend: {slope:.2f} points/month")
print(f"R²: {r_value**2:.3f}")
print(f"Significance: p={p_value:.4f}")

if p_value < 0.05:
    direction = "improving" if slope > 0 else "deteriorating"
    print(f"Significant {direction} trend detected")
```

### 2. Seasonal Decomposition

```python
from statsmodels.tsa.seasonal import seasonal_decompose

# Create time series
ts_data = pd.Series(
    [v[1] for v in results["sidewalk_123"]],
    index=pd.date_range("2026-01-01", periods=12, freq="MS")
)

# Decompose
decomposition = seasonal_decompose(ts_data, model='additive', period=4)

# Plot components
import matplotlib.pyplot as plt
fig, axes = plt.subplots(4, 1, figsize=(12, 8))

ts_data.plot(ax=axes[0], title="Condition Score")
decomposition.trend.plot(ax=axes[1], title="Trend")
decomposition.seasonal.plot(ax=axes[2], title="Seasonal")
decomposition.resid.plot(ax=axes[3], title="Residual")

plt.tight_layout()
plt.show()
```

### 3. Anomaly Detection

```python
def detect_anomalies(series, threshold=2.0):
    """Detect values deviating from mean by threshold std devs."""
    mean = series.mean()
    std = series.std()
    
    anomalies = []
    for i, value in enumerate(series):
        z_score = abs((value - mean) / std)
        if z_score > threshold:
            anomalies.append((i, value, z_score))
    
    return anomalies

# Get condition scores over time
ts_data = pd.Series([v[1] for v in results["sidewalk_123"]])
anomalies = detect_anomalies(ts_data, threshold=2.0)

for idx, value, z_score in anomalies:
    print(f"Anomaly at index {idx}: value={value:.1f} (z={z_score:.2f})")
```

## Cohort Analysis

### Compare Groups of Records

```python
def cohort_analysis(tq, business_keys_by_cohort, metric, dates):
    """Compare metric across cohorts over time."""
    results = {}
    
    for cohort_name, business_keys in business_keys_by_cohort.items():
        cohort_results = tq.track_metric_over_time(
            metric,
            business_keys,
            dates
        )
        
        # Calculate average per cohort
        values = []
        for date_idx in range(len(dates)):
            cohort_values = [
                cohort_results[bk][date_idx][1] 
                for bk in business_keys
                if cohort_results[bk][date_idx][1] is not None
            ]
            avg = np.mean(cohort_values) if cohort_values else None
            values.append(avg)
        
        results[cohort_name] = values
    
    return results

# Compare condition by borough
dates = pd.date_range("2026-01-01", "2026-12-31", freq="M").date
cohorts = {
    "manhattan": ["sw_m_001", "sw_m_002", "sw_m_003"],
    "brooklyn": ["sw_b_001", "sw_b_002", "sw_b_003"],
    "queens": ["sw_q_001", "sw_q_002", "sw_q_003"],
}

results = cohort_analysis(tq, cohorts, "condition_score", dates)

# Plot
import matplotlib.pyplot as plt
for cohort, values in results.items():
    plt.plot(dates, values, marker='o', label=cohort)

plt.xlabel("Date")
plt.ylabel("Condition Score")
plt.legend()
plt.show()
```

## Custom Aggregations

### Borough-Level Statistics

```python
def borough_aggregate(tq, borough_sidewalks, metric, as_of_date):
    """Calculate borough-level aggregates."""
    values = []
    
    for sidewalk_id in borough_sidewalks:
        record = tq.get_as_of(sidewalk_id, as_of_date)
        if record and metric in record['data']:
            values.append(record['data'][metric])
    
    return {
        "count": len(values),
        "mean": np.mean(values),
        "median": np.median(values),
        "std": np.std(values),
        "min": np.min(values),
        "max": np.max(values),
        "p25": np.percentile(values, 25),
        "p75": np.percentile(values, 75),
    }

# Manhattan borough statistics as of March 2026
brooklyn_sidewalks = [
    "sw_b_" + str(i).zfill(4) 
    for i in range(1, 1001)  # 1000 sidewalks
]

stats = borough_aggregate(
    tq,
    brooklyn_sidewalks,
    "condition_score",
    datetime(2026, 3, 15)
)

print(f"Brooklyn condition on 2026-03-15:")
print(f"  Mean: {stats['mean']:.1f}")
print(f"  Median: {stats['median']:.1f}")
print(f"  Std Dev: {stats['std']:.1f}")
print(f"  Range: {stats['min']:.1f} - {stats['max']:.1f}")
```

## Performance Tips

### 1. Use Materialized Views for Common Aggregations

```sql
-- Create materialized view for monthly borough aggregates
CREATE MATERIALIZED VIEW mv_borough_monthly_stats AS
SELECT 
    DATE_TRUNC('month', st.start_date) as month,
    'brooklyn' as borough,
    AVG((st.data_values->>'condition_score')::float) as avg_condition,
    COUNT(DISTINCT st.business_key) as sidewalk_count
FROM sidewalk_conditions_scd st
WHERE st.business_key LIKE 'sw_b_%'
GROUP BY DATE_TRUNC('month', st.start_date);

-- Create index
CREATE INDEX idx_mv_borough_monthly ON mv_borough_monthly_stats(month, borough);

-- Query becomes much faster
SELECT * FROM mv_borough_monthly_stats
WHERE month >= '2026-01-01' AND borough = 'brooklyn'
ORDER BY month DESC;
```

### 2. Pre-Sample Time Series Data

```python
# Instead of querying every day, sample monthly
dates = pd.date_range("2026-01-01", "2026-12-31", freq="MS")  # Monthly
results = tq.track_metric_over_time("condition_score", keys, dates)
# Much faster than daily sampling
```

### 3. Use Batch Queries

```python
# Inefficient: multiple queries
for key in sidewalk_ids:
    record = tq.get_as_of(key, target_date)
    process(record)

# Better: batch if available
records = tq.batch_get_as_of(sidewalk_ids, target_date)
for record in records:
    process(record)
```

## Reporting

### Generate Time-Series Report

```python
def generate_temporal_report(tq, business_key, start_date, end_date):
    """Generate comprehensive temporal analytics report."""
    
    # Get versions
    versions = tq.get_versions(business_key)
    in_range = [v for v in versions 
                if start_date <= v['start_date'] <= end_date]
    
    # Get timeline
    timeline = tq.get_change_timeline(business_key)
    
    # Detect pattern
    pattern = tq.detect_change_patterns(business_key)
    
    # Generate report
    report = {
        "business_key": business_key,
        "period": f"{start_date} to {end_date}",
        "total_versions": len(in_range),
        "fields_changed": list(pattern.fields_changed) if pattern else [],
        "change_frequency": f"{pattern.change_frequency:.3f} per day" if pattern else "N/A",
        "operations": pattern.change_types if pattern else {},
        "timeline": timeline,
    }
    
    return report

report = generate_temporal_report(
    tq,
    "sidewalk_123",
    date(2026, 1, 1),
    date(2026, 12, 31)
)

import json
print(json.dumps(report, indent=2, default=str))
```

## Integration with Lineage Tracking

Link temporal changes to data lineage:

```python
from socrata_toolkit.lineage_core import TransformationNode, NodeType

# Create lineage node for temporal analysis
temporal_analysis = TransformationNode(
    node_id="temporal_analysis_sidewalk_123",
    name="Temporal Condition Analysis: Sidewalk 123",
    node_type=NodeType.TRANSFORMATION,
    owner="analytics@nyc.gov"
)

# Record that this analysis depended on historical versions
for version in versions:
    # Link to SCD version
    pass

# Record output as materialized view
output_view = TransformationNode(
    node_id="mv_sidewalk_conditions",
    name="Materialized Sidewalk Condition View",
    node_type=NodeType.MATERIALIZATION,
    owner="analytics@nyc.gov"
)
```

## See Also

- `docs/cdc_guide.md` for CDC fundamentals
- `docs/audit_compliance.md` for audit-based analysis
- `socrata_toolkit/temporal_queries.py` for API reference
