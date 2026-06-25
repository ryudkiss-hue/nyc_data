# Visualization Quality Audit & Standard
## NYC DOT SIM Workflows - Phase 1 Deployment

**Date:** 2026-06-11  
**Status:** PRE-DEPLOYMENT AUDIT  
**Scope:** 5 Areas ready for production deployment

---

## AUDIT FINDINGS

### Area 1: Phase 1 Capabilities (Clustering, Material, Geo-Temporal)
**Location:** `src/socrata_toolkit/viz/`
- ✅ `clustering_viz.py` — **COMPLIANT**
  - Elbow Curve: Has title ✓, xaxis_title ✓, yaxis_title ✓
  - Silhouette: Has title ✓, xaxis_title ✓, yaxis_title ✓
  - Quality Heatmap: Has title ✓
- ✅ `material_viz.py` — **COMPLIANT** (Kaplan-Meier curves with proper labels)
- ⚠️ `temporal_maps.py` — **NEEDS REVIEW** (may have parameterized titles)

### Area 2: Hidden Analysis Methods (5 methods)
**Location:** `app/callbacks/hidden_analysis_methods.py`
- ✅ Moran's I — Has title ✓, but needs axes labels (longitude/latitude)
- ⚠️ Distribution Classification — Has title ✓, missing xaxis/yaxis labels
- ✅ Spatial Anomalies — Has title ✓, axes ✓
- ✅ Seasonal Decomposition — Has title ✓, axes ✓
- ⚠️ Bootstrap CI — Metric cards (needs review)

### Area 3: Dash Pilot GIS
**Location:** `app/services/gis_service.py`, `app/callbacks/gis.py`
- ⚠️ Multiple maps with parameterized titles
- ⚠️ Missing data source annotations
- ⚠️ Missing legend clarifications

### Area 4: ACID Fixes & Monitoring
**Status:** No visualization code found (ACID is infrastructure-level)

### Area 5: A/B Test Dashboard
**Location:** `DASH_AB_MONITORING.md`
- ✅ Metrics defined but visualizations not yet built

---

## QUALITY STANDARD (Going Forward)

### Required Elements for ALL Visualizations

**LEVEL 1: Mandatory**
```python
# Every chart MUST have:
fig.update_layout(
    title="Clear, Descriptive Title (Context + Metric)",  # Required
    xaxis_title="X-Axis Label (with units)",              # Required
    yaxis_title="Y-Axis Label (with units)",              # Required if not map
    hovermode="x unified",                                # Better UX
    template="plotly_white",                              # Clean style
)

# Example:
fig.update_layout(
    title="Violation Count by Borough (2026-Q2)",
    xaxis_title="Borough Name",
    yaxis_title="Number of Violations",
)
```

**LEVEL 2: Strong (Highly Recommended)**
```python
fig.update_layout(
    # ... Level 1 above ...
    
    # Add legend if multiple series
    showlegend=True,
    legend=dict(
        title="Legend Title",
        orientation="v",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
    ),
    
    # Data source annotation
    annotations=[
        dict(
            text="Data: Socrata API, Updated 2026-06-11",
            xref="paper", yref="paper",
            x=0.01, y=-0.12,
            showarrow=False,
            font=dict(size=10, color="gray"),
        )
    ],
    
    # Accessibility
    font=dict(family="system-ui", size=12),
)
```

**LEVEL 3: Excellent (Best Practice)**
```python
# All Level 1 + 2, plus:

fig.update_traces(
    # Colorblind-friendly palette
    marker=dict(colorscale="Viridis"),
    hovertemplate="<b>%{x}</b><br>Value: %{y:.2f}<extra></extra>",
)

fig.add_annotation(
    text="95% confidence interval",
    xref="paper",
    yref="paper",
    x=0.5,
    y=1.05,
    showarrow=False,
    font=dict(size=10),
)
```

---

## ACTION ITEMS (Before Phase 1 Deployment)

### CRITICAL (Must Fix Before Deploying)

**1. Hidden Analysis - Distribution Classification**
- File: `app/callbacks/hidden_analysis_methods.py` (around line 330)
- Issue: Chart has title but no axis labels
- Fix: Add `xaxis_title="Value"` and `yaxis_title="Frequency"`
- Est. Time: 5 min

**2. Hidden Analysis - Bootstrap CI**
- File: `app/callbacks/hidden_analysis_methods.py` (around line 896)
- Issue: Metric card missing context
- Fix: Add descriptive title with metric and confidence level
- Est. Time: 5 min

**3. GIS Service - Multiple Maps**
- File: `app/services/gis_service.py`
- Issue: Maps use parameterized titles, missing data source annotations
- Fix: Ensure all maps have data source footer
- Est. Time: 15 min

### HIGH PRIORITY (Do Before Week 2)

**4. Add Data Source Annotations Everywhere**
- All visualizations should cite source: "Data: Socrata API, Updated [DATE]"
- Est. Time: 30 min (batch across all files)

**5. Accessibility Check**
- Verify all color scales use colorblind-friendly palettes
- Currently: Some use default Plotly colors (may not be accessible)
- Est. Time: 20 min (batch review)

---

## COMPLIANCE CHECKLIST

Use this for every visualization going forward:

```markdown
## [Chart Name]

- [ ] Has descriptive title (shows context + metric)
- [ ] X-axis has label with units
- [ ] Y-axis has label with units (if applicable)
- [ ] Hover tooltips show full context
- [ ] Uses colorblind-friendly palette
- [ ] Includes data source annotation
- [ ] Has legend (if multiple series)
- [ ] Clean, professional layout
- [ ] Tested in browser at different screen sizes
```

---

## IMPLEMENTATION PLAN

### Phase 1: Fix Critical Issues (Before Deployment)
1. ✅ Identify all visualizations (Done above)
2. 🔄 Fix hidden analysis (5 + 5 + 15 = 25 min)
3. 🔄 Fix GIS annotations (15 min)
4. **Total Time: ~40 minutes**

### Phase 2: Enhance All Visualizations (Week 1-2)
- Add data source annotations (30 min)
- Audit color palettes (20 min)
- Test accessibility (15 min)
- **Total Time: ~65 minutes**

### Phase 3: Template for Phase 2A Dash Migration
- Create `src/socrata_toolkit/viz/quality_standards.py` with:
  - Base chart templates (bar, line, pie, scatter, etc.)
  - Pre-built layouts with all required elements
  - Color palette definitions (colorblind-friendly)
- **Time: 1-2 hours**

---

## SUCCESS CRITERIA FOR PHASE 1 DEPLOYMENT

✅ All 5 areas have visualizations with:
1. Descriptive titles
2. Labeled axes (with units)
3. Data source citations
4. Hover tooltips showing full context
5. Accessible color palettes

✅ 109/109 tests still passing  
✅ No performance regressions  
✅ Verified in browser at multiple screen sizes

---

## Template Code (Copy-Paste Ready)

### Basic Bar Chart
```python
import plotly.express as px

def create_violations_by_borough(df):
    """Create violations bar chart with proper labels."""
    fig = px.bar(
        df,
        x="borough",
        y="violation_count",
        title="Violation Count by Borough (2026-Q2)",
        labels={"borough": "Borough", "violation_count": "Number of Violations"},
        color_discrete_sequence=["#1f77b4"],
    )
    
    fig.update_layout(
        xaxis_title="Borough",
        yaxis_title="Number of Violations",
        showlegend=False,
        template="plotly_white",
        height=500,
    )
    
    fig.add_annotation(
        text="Data: Socrata API, Updated 2026-06-11",
        xref="paper", yref="paper",
        x=0.01, y=-0.15,
        showarrow=False,
        font=dict(size=9, color="gray"),
    )
    
    return fig
```

### Map with Data Source
```python
def create_condition_map(gdf):
    """Create GIS condition map with proper annotation."""
    fig = px.scatter_map(
        gdf,
        lat="latitude",
        lon="longitude",
        hover_name="block_id",
        title="Condition Assessment Map - Manhattan (2026-Q2)",
        zoom=11,
    )
    
    fig.update_layout(
        mapbox_style="carto-positron",
        height=600,
    )
    
    fig.add_annotation(
        text="Data: NYC Open Data (Socrata), Updated 2026-06-11 | Map: OpenStreetMap contributors",
        xref="paper", yref="paper",
        x=0.5, y=-0.05,
        showarrow=False,
        font=dict(size=9, color="gray"),
        xanchor="center",
    )
    
    return fig
```

---

**Status: READY FOR FIXES**

Once critical issues are fixed, Phase 1 deployment can proceed with full visualization quality assurance.
