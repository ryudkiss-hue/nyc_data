# Visualization Units Standard
## NYC DOT SIM Workflows - Data Science Best Practices

**Date:** 2026-06-11  
**Requirement:** ALL axes, titles, and legends must specify units of measurement  
**Applicability:** CRITICAL before Phase 1 deployment + enforced for Phase 2A Dash migration

---

## MANDATORY UNITS STANDARD

### Rule 1: Axis Labels MUST Include Units

```python
# ❌ WRONG
fig.update_layout(
    xaxis_title="Borough",
    yaxis_title="Violations",
)

# ✅ CORRECT
fig.update_layout(
    xaxis_title="Borough Name",
    yaxis_title="Number of Violations (count)",
)
```

**Common Axis Units:**
| Axis Type | Unit Specification | Example |
|-----------|---|---|
| Count | `(count)` or `(n=)` | "Number of Violations (count)" |
| Percentage | `(%)` or `(percent)` | "Completion Rate (%)" |
| Time | `(days)`, `(hours)`, `(months)` | "Elapsed Time (days)" |
| Currency | `(USD)` or `($)` | "Cost (USD)" |
| Distance | `(meters)`, `(miles)`, `(feet)` | "Buffer Distance (meters)" |
| Score | `(0-100)` or `(score)` | "Quality Score (0-100)" |
| Coordinate | `(degrees)` or `(lat/lon)` | "Latitude (degrees)" |
| Ratio | `(ratio)` or `(per item)` | "Unique Ratio (per item)" |

### Rule 2: Chart Titles MUST Include Context + Unit

```python
# ❌ WRONG
title="Violations"

# ✅ CORRECT
title="Violation Count by Borough (2026-Q2)"
```

**Title Format: `{Metric Name} {by Dimension} ({Time Period})`**

| Component | Purpose | Example |
|-----------|---------|---------|
| Metric Name | What are we measuring? | Violation Count, Completion Rate, Average Cost |
| by Dimension | How is it segmented? | by Borough, by Material Type, by Status |
| Time Period | When is this data from? | (2026-Q2), (Last 30 Days), (2026-06-11) |

### Rule 3: Legends MUST Specify What Each Item Represents

```python
# ❌ WRONG
fig.add_trace(go.Scatter(..., name="Series1"))

# ✅ CORRECT
fig.add_trace(go.Scatter(..., name="Open Violations (count)"))
```

### Rule 4: Color Scales MUST Have Labels + Units

```python
# ❌ WRONG
color_continuous_scale="Viridis"

# ✅ CORRECT
fig.update_layout(
    coloraxis_colorbar=dict(
        title="Quality<br>Score<br>(0-100)",
        thickness=15,
        len=0.7,
    )
)
```

---

## CHECKLIST FOR EVERY VISUALIZATION

Before committing a chart, verify ALL of these:

- [ ] **X-axis**: Has title + explicit units (e.g., "Borough Name", "Days Elapsed")
- [ ] **Y-axis**: Has title + explicit units (e.g., "Count", "Percentage (%)")
- [ ] **Color axis** (if present): Has label + units (e.g., "Quality Score (0-100)")
- [ ] **Title**: Includes metric + dimension + time period
- [ ] **Legend**: Each entry specifies what it is + units (e.g., "Open Violations (count)")
- [ ] **Hover template**: Shows full context with units
- [ ] **Data source**: Includes timestamp (e.g., "Updated 2026-06-11")
- [ ] **All text**: Uses consistent terminology and units across the dashboard

---

## EXAMPLES BY CHART TYPE

### Bar Chart (Categorical)
```python
fig.update_layout(
    title="Violation Count by Borough (2026-Q2)",           # ✓ Metric + dimension + time
    xaxis_title="Borough Name",                             # ✓ Category label
    yaxis_title="Number of Violations (count)",             # ✓ Unit specified
)
fig.add_trace(go.Bar(...,
    name="All Violations (count)",                          # ✓ Legend with unit
    hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",  # ✓ Hover units
))
```

### Line Chart (Time Series)
```python
fig.update_layout(
    title="Violation Trend by Month (2025-2026)",          # ✓ Metric + time range
    xaxis_title="Month (YYYY-MM)",                          # ✓ Date format
    yaxis_title="Monthly Violation Count (count)",          # ✓ Unit + time period
)
fig.add_trace(go.Scatter(...,
    name="Open Violations (count)",                         # ✓ Legend with unit
    hovertemplate="<b>%{x|%Y-%m}</b><br>Count: %{y}<extra></extra>",  # ✓ Time format
))
```

### Pie Chart (Proportion)
```python
fig.update_layout(
    title="Violation Distribution by Material (2026-Q2)",   # ✓ Metric + time
)
fig.add_trace(go.Pie(...,
    labels=["Concrete", "Asphalt", "Other"],
    values=[4500, 2300, 1200],
    hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Pct: %{percent}",  # ✓ Both units
))
fig.update_layout(
    legend=dict(title="Material Type"),                     # ✓ Legend title
)
```

### Geographic Map
```python
fig.update_layout(
    title="Condition Assessment by Block (Manhattan, 2026-Q2)",  # ✓ Location + metric + time
)
fig.update_layout(
    coloraxis_colorbar=dict(
        title="Condition<br>Score<br>(0-100)",              # ✓ Unit (0-100)
    )
)
fig.add_annotation(
    text="Data: NYC Open Data | Updated 2026-06-11 | Map: OpenStreetMap",  # ✓ Source + date
)
```

### Heat Map
```python
fig.update_layout(
    title="Violation Density by Week (2026-Q2)",           # ✓ Metric + time
    xaxis_title="Week Number",                             # ✓ X unit
    yaxis_title="Borough Name",                            # ✓ Y unit
)
fig.update_layout(
    coloraxis_colorbar=dict(
        title="Density<br>(count<br>per week)",            # ✓ Unit specification
    )
)
```

### Box Plot / Distribution
```python
fig.update_layout(
    title="Violation Completion Time Distribution (days, 2026-Q2)",  # ✓ Unit in title
    xaxis_title="Material Type",
    yaxis_title="Days to Completion (days)",               # ✓ Unit
)
fig.update_layout(
    boxmean='sd'                                            # Show mean ± std
)
```

### Gauge / Metric
```python
fig.add_trace(go.Indicator(
    title={"text": "Completion Rate (%) — 95% CI"},        # ✓ Unit in title
    value=rate,
    suffix="%",                                             # ✓ Unit displayed
    gauge=dict(
        axis=dict(range=[0, 100]),                          # ✓ Scale is explicit
    )
))
```

---

## UNITS REFERENCE TABLE

### Completeness Metrics
| Metric | Unit | Example |
|--------|------|---------|
| Row count | `(count)` | "Rows Loaded (count)" |
| Completeness | `(%)` | "Completeness (%)" |
| Nullness | `(%)` | "Null Rate (%)" |

### Quality Metrics
| Metric | Unit | Example |
|--------|------|---------|
| Quality score | `(0-100)` | "Quality Score (0-100)" |
| Accuracy | `(%)` | "Classification Accuracy (%)" |
| Confidence interval | `(±%)` | "95% CI (±5%)" |

### Performance Metrics
| Metric | Unit | Example |
|--------|------|---------|
| Latency | `(ms)` | "API Response Time (ms)" |
| Throughput | `(rows/sec)` | "Processing Throughput (rows/sec)" |
| Cache hit rate | `(%)` | "Cache Hit Rate (%)" |

### Spatial Metrics
| Metric | Unit | Example |
|--------|------|---------|
| Coordinates | `(degrees)` or `(lat/lon)` | "Latitude (degrees)" |
| Distance | `(meters)` | "Distance from Intersection (meters)" |
| Density | `(count/km²)` | "Violation Density (count/km²)" |

### Temporal Metrics
| Metric | Unit | Example |
|--------|------|---------|
| Duration | `(days)`, `(hours)` | "Days to Resolution (days)" |
| Frequency | `(per week)`, `(monthly)` | "Inspection Frequency (per month)" |
| Timestamp | `(YYYY-MM-DD)` | "Date (YYYY-MM-DD)" |

---

## AUTOMATION: Units Helper Function

Create this utility to ensure consistency:

```python
# src/socrata_toolkit/viz/units.py
UNITS = {
    # Counts
    'violation_count': 'Number of Violations (count)',
    'inspection_count': 'Number of Inspections (count)',
    'permit_count': 'Number of Permits (count)',
    'sample_size': 'Sample Size (n)',
    
    # Percentages
    'completion_rate': 'Completion Rate (%)',
    'accuracy': 'Classification Accuracy (%)',
    'null_pct': 'Null Rate (%)',
    
    # Scores (0-100)
    'quality_score': 'Quality Score (0-100)',
    'condition_score': 'Condition Score (0-100)',
    'confidence_level': 'Confidence Level (%)',
    
    # Time
    'days_elapsed': 'Days Elapsed (days)',
    'months': 'Month (YYYY-MM)',
    'week': 'Week Number',
    
    # Spatial
    'latitude': 'Latitude (degrees)',
    'longitude': 'Longitude (degrees)',
    'distance': 'Distance (meters)',
    
    # Finance
    'cost': 'Cost (USD)',
    'budget': 'Budget (USD)',
}

def get_unit_label(key: str, default: str = "") -> str:
    """Get the standard unit label for a metric."""
    return UNITS.get(key, default)
```

---

## MIGRATION CHECKLIST (Before Phase 1 Deployment)

- [ ] Audit: All visualizations reviewed for units
- [ ] Fix: Distribution chart — `xaxis_title="Value"`, `yaxis_title="Frequency"`
- [ ] Fix: Bootstrap CI — Title includes `(% CI)`
- [ ] Fix: GIS maps — Add data source + timestamp
- [ ] Fix: Clustering charts — Verify axis units (inertia, coefficient, metric value)
- [ ] Fix: Material charts — Verify y-axis units (lifespan years, cost USD)
- [ ] Fix: All color scales — Add unit label (e.g., "Quality Score (0-100)")
- [ ] Tests: Run full suite — 109/109 passing
- [ ] Verification: Manual check of 5 key visualizations in browser

---

## SUCCESS CRITERIA FOR PHASE 1 DEPLOYMENT

✅ Every axis has label + unit (e.g., "Count", "Days", "%", "USD")  
✅ Every title includes metric + dimension + time period  
✅ Every legend specifies what it represents + unit  
✅ Every color scale has title + unit  
✅ Every hover tooltip shows full context with units  
✅ All 109 tests passing  
✅ Zero linting errors in visualization code  
✅ Visual verification in browser at multiple resolutions

---

**Status: UNITS STANDARD DEFINED**

This standard applies to:
- All 5 areas in Phase 1 deployment
- All 50+ charts in Phase 2A Dash migration
- Any new visualizations added going forward

**Implementation approach:** Create units utility function (UNITS dict), apply to all existing visualizations, then enforce in PR review for future changes.
