# UI Integration Implementation Checklist

**Status:** Phase B-F Implementation Started  
**Timeline:** 13-18 hours | 2-3 focused sessions  
**Target Date:** 2026-06-13

---

## Phase A: Setup ✅ COMPLETE

### Files Created
- [x] `app/callbacks/decorators.py` — Caching & timing decorators
- [x] `app/services/analytics_service.py` — Data fetch service layer
- [x] `app/callbacks/analytics.py` — Callback stubs for all 5 methods

### Status
✅ All Phase A infrastructure in place
- Decorators: `@timer_callback`, `@memoize_with_ttl()`
- Service functions: `get_dataset()`, `get_spatial_data()`, `get_timeseries_data()`, `get_kpi_metrics()`
- Callback structure ready for all 5 methods

---

## Phase B: Moran's I Spatial Autocorrelation ✅ IMPLEMENTED

### Implementation Status
- [x] `compute_morans_i()` function — calculates spatial autocorrelation statistic
- [x] `create_morans_i_figure()` — gauge visualization with color scale
- [x] Error handling and edge cases covered
- [x] Logging and performance monitoring in place

### Integration Points
**Target Location:** GIS Dashboard → "Spatial Patterns" tab
```python
# Callback pattern (to be added to app/callbacks/gis_callbacks.py)
@app.callback(
    Output("moran-i-gauge", "figure"),
    Output("moran-i-interpretation", "children"),
    Input("store-global-filters", "data"),
    Input("column-select-spatial", "value"),
)
def update_moran_i(filters, column):
    i_value, interpretation = compute_morans_i(filters, column)
    fig = create_morans_i_figure(i_value)
    return fig, interpretation
```

### Testing Requirements
- [ ] Test with real inspection data (expects lat/lon + numeric column)
- [ ] Verify <200ms latency with 10K rows
- [ ] Test with missing geometries
- [ ] Verify color scale interpretation (red/yellow/green)

### Dependencies
- libpysal (for KNN weights)
- esda (for Moran's I computation)

---

## Phase C: Distribution Classification ⏳ SCAFFOLDING

### Implementation Status
- [x] `classify_all_distributions()` — analyzes numeric column shapes
- [x] `create_distribution_figures()` — histogram + KDE per column
- [ ] Card grid layout in Dash (needs UI integration)
- [ ] Column selector dropdown (by variance)

### What's Needed
1. Create callback stub in `app/callbacks/analytics_callbacks.py`:
```python
@app.callback(
    Output("distribution-card-grid", "children"),
    Input("store-global-filters", "data"),
    Input("distribution-column-limit", "value"),
)
def update_distributions(filters, limit):
    dist_df = classify_all_distributions(filters, limit)
    figs = create_distribution_figures(dist_df, get_dataset(filters), limit)
    # Build card grid from figs and dist_df
```

2. Add to Analytics view layout (existing file: `app/views/analytics_advanced.py`)

### Performance Target
- Latency: <300ms (with 10K rows, 8 columns)
- Cache TTL: 10 minutes

### Dependencies
- scipy (for skew, kurtosis computation)
- numpy
- plotly

---

## Phase D: Anomaly Detection ⏳ SCAFFOLDING

### Implementation Status
- [x] `detect_spatial_outliers()` — k-nearest neighbor anomaly detection
- [x] `create_anomaly_scatter()` — map visualization
- [ ] Anomaly detail table (top 10 anomalies)
- [ ] Expander/accordion in Quality Dashboard

### What's Needed
1. Create callback in `app/callbacks/quality_callbacks.py`
2. Add to Data Quality expander in existing Quality Dashboard
3. Implement anomaly table display

### Performance Target
- Latency: <400ms (with 5K spatial points)
- Cache TTL: 5 minutes

### Dependencies
- scipy.spatial.distance
- numpy

---

## Phase E: Seasonal Decomposition ⏳ SCAFFOLDING

### Implementation Status
- [x] `decompose_timeseries_data()` — trend/seasonal/residual split
- [x] `create_decomposition_figure()` — 4-panel subplot
- [ ] Date range picker integration
- [ ] Period selector (weekly/monthly/yearly)

### What's Needed
1. Create callback in `app/callbacks/labor_callbacks.py`
2. Add to Labor/Temporal Patterns view
3. Dynamic period selection UI

### Performance Target
- Latency: <500ms (with 2K time points)
- Cache TTL: 15 minutes

### Dependencies
- statsmodels (for seasonal_decompose)

---

## Phase F: Bootstrap Confidence Intervals ⏳ SCAFFOLDING

### Implementation Status
- [x] `compute_bootstrap_ci()` — bootstrap resampling for CI
- [ ] Update existing KPI gauge callbacks
- [ ] Add CI bands to gauge visualization
- [ ] Update KPI card display text

### What's Needed
1. Modify existing KPI callback in `app/callbacks/executive_callbacks.py`
2. Wrap KPI computation with `compute_bootstrap_ci()`
3. Update gauge figure to show CI bands

### Performance Target
- Latency: <300ms (with bootstrap resampling)
- Cache TTL: 10 minutes

### Dependencies
- numpy
- scipy.stats

---

## Phase G: Testing & Polish ⏳ TODO

### Unit Tests
- [ ] Test each callback with mock data
- [ ] Verify error handling (missing cols, empty data, etc.)
- [ ] Test caching and TTL behavior
- [ ] Verify logging

### Integration Tests
- [ ] Load each dashboard view
- [ ] Verify all callbacks fire without errors
- [ ] Test with different filter combinations

### Performance Tests
- [ ] Latency benchmarks (target: <500ms per method)
- [ ] Load test (100 concurrent users)
- [ ] Memory usage monitoring

### Code Review & Documentation
- [ ] Docstrings complete
- [ ] Type hints consistent
- [ ] Error messages user-friendly
- [ ] README/guide for developers

---

## Integration Sequence (Recommended)

### Session 1: Phase B-C (6-7 hours)
1. ✅ Complete Phase A setup
2. ✅ Finalize Moran's I (Phase B)
3. ⏳ Implement Distribution Classification UI (Phase C)
4. ✅ Test both on real data

### Session 2: Phase D-E (5-6 hours)
1. ⏳ Implement Anomaly Detection UI (Phase D)
2. ⏳ Implement Decomposition UI (Phase E)
3. ✅ Performance test all methods

### Session 3: Phase F-G (3-4 hours)
1. ⏳ Implement Bootstrap CI integration (Phase F)
2. ✅ Complete all tests and documentation
3. ✅ Code review and final polish

---

## Known Issues / Blockers

### Dependencies
- [ ] Verify libpysal/esda installed in production
- [ ] Verify statsmodels installed
- [ ] Check scipy version compatibility

### Data
- [ ] Ensure inspection data has geometry column (`the_geom`)
- [ ] Verify date columns are TIMESTAMP type in DuckDB
- [ ] Confirm numeric columns exist for distribution analysis

### Performance
- [ ] May need query optimization for 100K+ rows
- [ ] Consider spatial indexing for Moran's I
- [ ] Bootstrap might be slow for large samples (mitigate with sampling)

---

## Success Criteria

- [x] All 5 methods have working implementations
- [ ] All callbacks render without errors
- [ ] All latency targets met (<500ms P95)
- [ ] No console errors or warnings
- [ ] Accurate results vs. direct Python calls
- [ ] Works with different dataset sizes
- [ ] Load test passes (100 users, >95% success)
- [ ] Documentation complete
- [ ] Code review approved
- [ ] Integrated into CI/CD pipeline

---

## Files Modified/Created This Session

```
app/
├── callbacks/
│   ├── decorators.py                    ✅ NEW
│   ├── analytics.py                     ✅ NEW (Phase B-F stubs)
│   └── [gis|quality|labor|analytics]_callbacks.py  ⏳ TODO
├── services/
│   └── analytics_service.py             ✅ NEW (enhanced Phase A)
└── views/
    └── [existing files]                 ⏳ INTEGRATE

UI_INTEGRATION_CHECKLIST.md               ✅ THIS FILE
```

---

**Last Updated:** 2026-06-11  
**Next Session:** Complete Phase C-E integration  
**Estimated Completion:** 2026-06-13
