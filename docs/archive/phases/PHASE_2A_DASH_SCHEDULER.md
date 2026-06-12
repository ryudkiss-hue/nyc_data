# Phase 2A: Dash Consolidation + Scheduler

**Status:** PLANNING  
**Created:** 2026-06-11  
**Based on:** Phase 1 production-ready main branch (commit 218f52d)  

---

## Overview

Phase 2A focuses on:
1. **Dash Consolidation** — Migrate remaining Streamlit views to Plotly/Dash
2. **Scheduler Integration** — APScheduler for nightly cache refresh (6 AM UTC)
3. **Production Dashboard** — Unified Dash application across all 30+ visualizations

---

## Deliverables

### 2A.1: Unified Dash Application
**Files to create:**
- `src/socrata_toolkit/dashboards/unified_dashboard.py` — Main Dash app
- `src/socrata_toolkit/dashboards/layouts/` — Page layouts
  - `home.py` — Dashboard home/overview
  - `violations.py` — Violation analysis views
  - `ramps.py` — Ramp accessibility views
  - `permits.py` — Permit coordination views
  - `gis.py` — Geographic analysis
  - `analytics.py` — Advanced analytics (hidden methods)
- `src/socrata_toolkit/dashboards/callbacks/` — Dash callbacks
  - `violations_callbacks.py`
  - `ramps_callbacks.py`
  - `permits_callbacks.py`
  - `gis_callbacks.py`
  - `analytics_callbacks.py`

**Specifications:**
- All visualizations use units system (units.py)
- All charts have explicit titles + dimensions + units
- Data source annotations on all maps
- Responsive design (1920x1080+)
- Light/dark theme toggle
- Export to PDF/Excel/PNG

### 2A.2: Nightly Cache Refresh Scheduler
**Files to create:**
- `scripts/scheduler_daemon.py` — APScheduler-based refresh service
- `src/socrata_toolkit/scheduler/` — Scheduler core
  - `__init__.py`
  - `cache_refresh.py` — Refresh logic
  - `notifications.py` — Alert notifications
  - `metrics.py` — Refresh metrics/logging

**Specifications:**
- Cron: 6 AM UTC daily
- Fetch all 24 datasets (incremental delta)
- Classify with spaCy
- Materialize to DuckDB
- Publish success/failure metrics
- Retry on failure with exponential backoff

### 2A.3: Migration from Streamlit
**Actions:**
- Keep `app/app.py` (Streamlit) as legacy support
- Move core logic to Dash:
  - Workflows view → Dash page
  - Studio view → Dash page
  - Settings → Dash page
- Update README to document Dash as primary
- Add `/dashboards` endpoint documentation

### 2A.4: Configuration & Deployment
**Files to create:**
- `config/dash_config.yaml` — Dash app configuration
- `config/scheduler_config.yaml` — Scheduler settings
- `.env.example` — Environment variable template

**Configuration includes:**
- Port binding (default: 8050)
- Debug mode
- Scheduler timezone (UTC)
- Slack webhook for alerts
- DuckDB path
- Socrata token (optional)

---

## Testing

### Unit Tests
- `tests/test_dash_layouts.py` — Layout rendering
- `tests/test_dash_callbacks.py` — Callback logic
- `tests/test_scheduler.py` — Scheduler execution
- `tests/test_cache_refresh.py` — Data refresh logic

### Integration Tests
- Dashboard loads at 127.0.0.1:8050
- All 30+ visualizations render
- Units display correctly on all axes
- GIS maps show data sources
- Export functions work (PDF, Excel, PNG)
- Scheduler cron job executes

### Smoke Tests
- Dash app starts without errors
- SQLite + DuckDB cache initialized
- All 24 datasets accessible
- Sample data displayed in visualizations

---

## Technical Decisions

### 1. Dash over Streamlit
**Why:** 
- More control over layout and styling
- Better for enterprise dashboards
- Native Plotly integration
- Superior performance for large datasets
- Easier to containerize

### 2. APScheduler for Scheduling
**Why:**
- Embedded (no external scheduler needed)
- Flexible cron expressions
- Built-in persistence
- Easy monitoring/metrics

### 3. Keep Streamlit as Legacy
**Why:**
- Zero-downtime migration
- User choice (some prefer Streamlit)
- Gradual deprecation path
- Reduced risk

---

## Dependencies

### New Requirements
```
dash==2.14.0
dash-bootstrap-components==1.5.0
APScheduler==3.10.1
python-dotenv==1.0.0
```

### Existing (from Phase 1)
```
plotly>=5.15.0
pandas>=2.0.0
duckdb>=0.8.0
socrata-py>=0.7.0
spacy>=3.5.0
```

---

## Success Criteria

✅ Dashboard accessible at http://127.0.0.1:8050  
✅ All 30+ visualizations render with units  
✅ Scheduler runs daily at 6 AM UTC  
✅ Data refresh completes in <5 minutes  
✅ Export functions produce valid files  
✅ Zero regression from Phase 1  
✅ All tests pass (109+ core tests)  
✅ Documentation complete  

---

## Next Steps

1. **Design dashboard layout** — Navigation, page structure
2. **Refactor callbacks** — Move from app/callbacks/ to dashboards/callbacks/
3. **Create scheduler daemon** — APScheduler integration
4. **Integration testing** — End-to-end flow
5. **Documentation** — User guide + developer docs
6. **Deploy** — Package as Docker image

---

## Estimated Effort

- Layout design & Dash app: 2 days
- Callback refactoring: 1 day
- Scheduler integration: 1 day
- Testing & QA: 1 day
- Documentation: 1 day
- **Total: ~1 week**

---

**Owner:** Claude (Phase 2A lead)  
**Status:** Ready for implementation  
**Priority:** P0 (production path)
