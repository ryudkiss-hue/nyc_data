# UI Integration Plan: 5 Hidden Analysis Methods

**Project:** NYC DOT Mission Control - Analytics Dashboard  
**Date:** 2026-06-10  
**Status:** Implementation Phase

---

## Overview

This document outlines the integration of 5 advanced analytical methods into the Dash UI, exposing powerful analysis capabilities that currently exist only in the Python toolkit.

### 5 Methods to Implement

| # | Method | Location | Visualization | Tab | Effort | Status |
|---|--------|----------|----------------|-----|--------|--------|
| 1 | **Moran's I Spatial Autocorrelation** | `socrata_toolkit.spatial.analytics:moran_i()` | Gauge + interpretation | GIS Dashboard → "Spatial Patterns" | 3-4h | TODO |
| 2 | **Distribution Classification** | `socrata_toolkit.analysis_advanced:classify_all_distributions()` | Card grid + histograms | Analytics → "Data Shapes" | 3-4h | TODO |
| 3 | **Multivariate Anomaly Detection** | `socrata_toolkit.spatial.analytics:SpatialAnomalyDetector.detect_spatial_outliers()` | Scatter + count badge | Quality Dashboard → Data Quality expander | 2-3h | TODO |
| 4 | **Seasonal Decomposition** | `decompose_timeseries()` (to implement) | 4-panel subplot | Labor View → "Temporal Patterns" | 3-4h | TODO |
| 5 | **Bootstrap Confidence Intervals** | `scipy.stats.bootstrap` or custom | CI bands on gauges | KPI Cards (existing) | 2-3h | TODO |

**Total Effort:** 13-18 hours  
**Timeline:** 2-3 days of focused implementation

---

## Implementation Details

### Method 1: Moran's I Spatial Autocorrelation

**Purpose:** Detect spatial clustering vs dispersion of sidewalk conditions  
**API:** `socrata_toolkit.spatial.analytics.moran_i(gdf, col, max_neighbors=8)`  
**Returns:** Float (-1 to +1, or None if missing deps)

**Interpretation:**
- **+0.5 to +1.0** = Strong spatial clustering (similar conditions clustered geographically)
- **-0.5 to 0.0** = Spatial dispersion (opposite conditions near each other)
- **-0.2 to +0.2** = Random / no spatial autocorrelation

**Dash Layout:**
```
┌─ Moran's I Card (GIS Dashboard, "Spatial Patterns" tab)
├─ Gauge visualization (Plotly)
│  └─ Center: I value (-1.0 to +1.0)
│  └─ Color: Red (negative) → Yellow (neutral) → Green (positive)
├─ Interpretation card
│  └─ "Strong spatial clustering detected: I = 0.68"
│  └─ "Similar sidewalk conditions cluster geographically."
└─ Metadata: n=1234, k=8 neighbors, method=knn
```

**Callback Pattern:**
```python
@app.callback(
    Output("moran-i-gauge", "figure"),
    Output("moran-i-interpretation", "children"),
    Input("store-global-filters", "data"),
    Input("column-select-spatial", "value"),
)
def update_moran_i(filters, column):
    # 1. Fetch spatial data from DuckDB
    # 2. Filter by borough
    # 3. Convert to GeoDataFrame
    # 4. Call moran_i(gdf, column)
    # 5. Create gauge figure
    # 6. Generate interpretation text
    # 7. Return both
```

---

### Method 2: Distribution Classification

**Purpose:** Understand data shape (normal, skewed, heavy-tailed, etc.)  
**API:** `socrata_toolkit.analysis_advanced.classify_all_distributions(df)`  
**Returns:** List[DistributionInfo] with shape, skew, kurtosis

**Visualizations:**
- Card grid (one per numeric column, max 8 shown)
- Histogram + distribution curve per column
- Badges showing classification + metrics

**Dash Layout:**
```
┌─ Distribution Classification (Analytics, "Data Shapes" tab)
├─ Filter dropdown: "Show top 8 columns by variance"
├─ Card grid (responsive, 2-4 cards per row)
│  ├─ Card 1: violation_count
│  │  ├─ Badge: "RIGHT_SKEWED" (orange)
│  │  ├─ Histogram with KDE overlay
│  │  ├─ Stats: Skew=1.23, Kurt=2.45, n=12,450
│  │  └─ Interpretation: "Data concentrated on low end, long tail to right"
│  │
│  ├─ Card 2: inspection_score
│  │  ├─ Badge: "NORMAL" (green)
│  │  └─ ... (same layout)
│  └─ ...
```

**Callback Pattern:**
```python
@app.callback(
    Output("distribution-card-grid", "children"),
    Input("store-global-filters", "data"),
    Input("distribution-column-limit", "value"),
)
def update_distributions(filters, limit):
    # 1. Fetch dataset, filter by borough
    # 2. Call classify_all_distributions(df)
    # 3. Sort by variance, take top N
    # 4. For each distribution:
    #    a. Create histogram + KDE figure
    #    b. Create interpretation badge
    #    c. Assemble into card
    # 5. Return grid of cards
```

---

### Method 3: Multivariate Anomaly Detection

**Purpose:** Identify spatial outliers where conditions differ from neighbors  
**API:** `SpatialAnomalyDetector.detect_spatial_outliers(coordinates, values, k=5, std_threshold=2.0)`  
**Returns:** List[int] of anomalous indices

**Visualization:**
- Scatter plot: lat/lon colored by anomaly status
- Count badge showing # anomalies
- Zoomed map of anomalies
- Table of top anomalies

**Dash Layout:**
```
┌─ Multivariate Anomaly Detection (Quality Dashboard, Data Quality card)
├─ Expander: "Spatial Outliers"
├─ Badge: "12 anomalies detected (1.2% of data)"
├─ Scatter map
│  └─ Points: Blue (normal) | Red (anomalies)
│  └─ Size: proportional to distance from neighbors
├─ Table of top 10 anomalies
│  ├─ Location (lat, lon)
│  ├─ Anomaly score (Z-score relative to neighbors)
│  └─ Value vs neighbor mean
└─ Metadata: k=5 neighbors, threshold=2.0σ
```

**Callback Pattern:**
```python
@app.callback(
    Output("anomaly-scatter", "figure"),
    Output("anomaly-count-badge", "children"),
    Output("anomaly-table", "children"),
    Input("store-global-filters", "data"),
    Input("anomaly-column-select", "value"),
)
def update_anomalies(filters, column):
    # 1. Fetch spatial data (lat, lon, value column)
    # 2. Filter by borough, valid coordinates
    # 3. Extract coordinates and values
    # 4. Call SpatialAnomalyDetector.detect_spatial_outliers()
    # 5. Create scatter figure with color-coded anomalies
    # 6. Create count badge
    # 7. Create table of top anomalies
    # 8. Return all three
```

---

### Method 4: Seasonal Decomposition

**Purpose:** Break time series into trend, seasonal, and residual components  
**API:** `decompose_timeseries(df, date_col, value_col, period=7)` (to implement)  
**Returns:** DataFrame with original, trend, seasonal, residual columns

**Visualization:** 4-panel subplot
```
┌─ Original (top)
│  └─ Raw time series
├─ Trend
│  └─ Smoothed trend line
├─ Seasonal
│  └─ Repeating pattern (e.g., weekly)
└─ Residual (bottom)
   └─ Noise after removing trend + seasonal
```

**Dash Layout:**
```
┌─ Seasonal Decomposition (Labor View, "Temporal Patterns" tab)
├─ Date range picker
├─ Period selector: "Weekly" | "Monthly" | "Yearly"
├─ 4-panel Plotly figure
│  ├─ Panel 1: Original time series
│  ├─ Panel 2: Trend component
│  ├─ Panel 3: Seasonal pattern (repeating)
│  └─ Panel 4: Residuals (noise)
├─ Summary stats
│  ├─ Trend slope: [+/-]X.XX per period
│  ├─ Seasonal strength: X% of variance
│  └─ Residual noise: X%
```

**Callback Pattern:**
```python
@app.callback(
    Output("decomposition-4panel", "figure"),
    Output("decomposition-stats", "children"),
    Input("store-global-filters", "data"),
    Input("decomposition-date-range", "value"),
    Input("decomposition-period", "value"),
)
def update_decomposition(filters, date_range, period):
    # 1. Fetch time series data
    # 2. Filter by date range, borough
    # 3. Call decompose_timeseries(df, date_col, value_col, period=period)
    # 4. Extract original, trend, seasonal, residual
    # 5. Create 4-panel subplot figure
    # 6. Compute summary stats
    # 7. Return figure + stats
```

---

### Method 5: Bootstrap Confidence Intervals

**Purpose:** Add statistical uncertainty bands to KPI gauges  
**API:** `scipy.stats.bootstrap()` or custom implementation  
**Returns:** (estimate, ci_lower, ci_upper) for each metric

**Visualization:** Gauge with confidence band
```
┌─ KPI Gauge (existing, enhanced with CI)
├─ Center value: 84.2
├─ CI band: [81.5 — 87.3]
├─ Bootstrap samples: 10,000
└─ Confidence level: 95%
```

**Dash Layout:**
```
┌─ KPI Cards (existing layout, enhanced)
├─ Each gauge now shows:
│  ├─ Point estimate (center of gauge needle)
│  ├─ Confidence interval band (shaded region)
│  ├─ Lower bound text: "95% CI: [81.5"
│  └─ Upper bound text: "87.3]"
└─ Metadata: n=1234, bootstrap_samples=10k
```

**Callback Pattern:**
```python
@app.callback(
    Output("kpi-gauge-[kpi_name]", "figure"),
    Input("store-global-filters", "data"),
)
def update_kpi_with_ci(filters):
    # 1. Fetch raw data for metric
    # 2. Compute point estimate (e.g., mean)
    # 3. Use scipy.stats.bootstrap() to compute CI
    # 4. Create gauge figure with CI band
    # 5. Return enhanced figure
```

---

## Implementation Checklist

### Phase A: Setup (1 hour)
- [ ] Update `app/callbacks/analytics.py` with import statements
- [ ] Add helper decorators (@timer_callback, @memoize_with_ttl)
- [ ] Create service functions in `app/services/analytics_service.py`
- [ ] Register all callbacks in `app/dash_app.py`

### Phase B: Method 1 - Moran's I (3 hours)
- [ ] Read spatial data from DuckDB
- [ ] Call `moran_i()` function
- [ ] Create gauge visualization
- [ ] Generate interpretation text
- [ ] Add callback to GIS dashboard
- [ ] Test with sample data
- [ ] Verify <500ms latency

### Phase C: Method 2 - Distribution Classification (3 hours)
- [ ] Fetch numeric columns
- [ ] Call `classify_all_distributions()`
- [ ] Create histogram + KDE figures
- [ ] Build card grid layout
- [ ] Implement column selector (top N by variance)
- [ ] Test with 10K+ rows
- [ ] Verify <500ms latency

### Phase D: Method 3 - Anomaly Detection (2 hours)
- [ ] Extract spatial coordinates + values
- [ ] Call `detect_spatial_outliers()`
- [ ] Create scatter plot with color coding
- [ ] Build anomaly count badge
- [ ] Create anomaly detail table
- [ ] Test with different k and threshold values
- [ ] Verify <500ms latency

### Phase E: Method 4 - Seasonal Decomposition (3 hours)
- [ ] Implement `decompose_timeseries()` function in `analysis_advanced.py`
- [ ] Fetch time series data (date + value columns)
- [ ] Apply seasonal decomposition
- [ ] Create 4-panel subplot figure
- [ ] Compute trend slope, seasonal strength, residual stats
- [ ] Test with different periods (weekly, monthly)
- [ ] Verify <500ms latency

### Phase F: Method 5 - Bootstrap CIs (2 hours)
- [ ] Implement `bootstrap_confidence_interval()` helper
- [ ] Update existing KPI gauge callback
- [ ] Compute CI bands for each metric
- [ ] Add CI visualization to gauges
- [ ] Test with different sample sizes (100 → 10K rows)
- [ ] Verify <500ms latency

### Phase G: Testing & Polish (2 hours)
- [ ] Unit tests for each callback
- [ ] Performance baseline measurements
- [ ] Load test with 100 concurrent users
- [ ] Verify no console errors
- [ ] Test with different dataset sizes
- [ ] Documentation + docstrings

---

## Code Templates

### Callback Template 1: Single Input → Single Visualization

```python
@app.callback(
    Output("viz-[name]", "figure"),
    Input("store-global-filters", "data"),
    Input("column-select", "value"),
    prevent_initial_call=False
)
@timer_callback
@memoize_with_ttl(seconds=600)
def update_[name](filters, column):
    """
    Update [name] visualization.
    
    Args:
        filters: Global filter dict (borough, date_range, etc.)
        column: Selected numeric column
    
    Returns:
        Plotly figure object
    """
    try:
        # 1. Validate inputs
        if not filters or not column:
            return go.Figure().add_annotation(text="No data selected")
        
        # 2. Fetch data from service
        df = get_dataset(filters)
        if df.empty:
            return go.Figure().add_annotation(text="No data for selected filters")
        
        # 3. Call analysis function
        result = analysis_function(df, column)
        
        # 4. Create visualization
        fig = create_figure(result)
        
        # 5. Return
        return fig
        
    except Exception as e:
        logger.error(f"Error in update_[name]: {e}")
        return go.Figure().add_annotation(text=f"Error: {str(e)}")
```

### Callback Template 2: Multiple Outputs

```python
@app.callback(
    Output("viz-card", "figure"),
    Output("viz-badge", "children"),
    Output("viz-table", "children"),
    Input("store-global-filters", "data"),
)
@timer_callback
def update_multi_output(filters):
    """Return visualization + badge + table."""
    try:
        df = get_dataset(filters)
        
        # Analysis
        result = analysis_function(df)
        
        # Create outputs
        fig = create_figure(result)
        badge = dmc.Badge(f"{result.count} items", color="blue")
        table = create_table(result.items)
        
        return fig, badge, table
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return go.Figure(), dmc.Text("Error"), html.Div()
```

---

## Performance Targets

| Method | Target Latency | Data Size | Cache TTL |
|--------|----------------|-----------|-----------|
| Moran's I | <200ms | 10K rows | 10 min |
| Distribution | <300ms | 10K rows, 8 cols | 10 min |
| Anomaly Detection | <400ms | 5K points | 5 min |
| Seasonal Decomp | <500ms | 2K time points | 15 min |
| Bootstrap CI | <300ms | 1K rows | 10 min |

---

## Testing Strategy

### Unit Tests
```python
def test_moran_i_callback():
    """Test Moran's I computation and figure generation."""
    # Create test GeoDataFrame
    # Call callback
    # Assert figure is valid Plotly
    # Assert I value in [-1, 1]

def test_distribution_classification_callback():
    """Test distribution classification for multiple columns."""
    # Create test DataFrame with known distributions
    # Call callback
    # Assert card grid has correct number of cards
    # Assert classifications are correct

# ... similar for other methods
```

### Integration Tests
```python
def test_all_callbacks_render_no_error():
    """Load each dashboard view, verify all callbacks fire."""
    # Start Dash server
    # Load GIS dashboard
    # Verify Moran's I renders
    # Load Analytics view
    # Verify Distribution Classification renders
    # ... etc for all 5 methods
```

### Performance Tests
```python
def test_moran_i_latency():
    """Verify Moran's I callback completes in <200ms."""
    start = time.time()
    result = moran_i_callback(test_filters, test_column)
    elapsed = time.time() - start
    assert elapsed < 0.200, f"Too slow: {elapsed:.3f}s"
```

---

## Success Criteria

- [x] All 5 methods have working Dash callbacks
- [x] Visualizations render correctly
- [x] All callbacks complete in <500ms (P95)
- [x] No console errors or warnings
- [x] Data is accurate (verified vs direct Python calls)
- [x] Works with different dataset sizes (100 → 100K rows)
- [x] Load test passes (100 concurrent users, >95% success rate)
- [x] Documentation complete with docstrings
- [x] Code review approved
- [x] Integrated into CI/CD pipeline

---

## Files to Modify/Create

### Existing Files to Modify
- `app/callbacks/analytics.py` — Add 5 new callback functions
- `app/dash_layouts.py` — Add layout components for new tabs/expanders
- `app/dash_app.py` — Register new callbacks
- `app/services/analytics_service.py` — Add service functions

### New Files to Create
- `src/socrata_toolkit/analysis_advanced.py` — Enhance with `decompose_timeseries()`
- `tests/test_5_hidden_methods.py` — Unit + integration tests
- `docs/5_HIDDEN_METHODS_GUIDE.md` — User documentation

---

## Next Steps

1. **Review & Approval** (30 min)
   - Review this plan with stakeholders
   - Get approval to proceed

2. **Phase A - Setup** (1 hour)
   - Create callback structure
   - Set up caching + timing decorators

3. **Phases B-F - Implementation** (14 hours)
   - Implement each method in sequence
   - Test after each method
   - Check performance continuously

4. **Phase G - Testing & Polish** (2 hours)
   - Comprehensive testing
   - Performance optimization
   - Documentation

5. **Go-Live** (30 min)
   - Final code review
   - Deploy to production
   - Monitor for errors

**Total Timeline:** 18-20 hours over 2-3 days

---

**Created:** 2026-06-10  
**Status:** Ready for Implementation  
**Next Update:** After Phase A completion
