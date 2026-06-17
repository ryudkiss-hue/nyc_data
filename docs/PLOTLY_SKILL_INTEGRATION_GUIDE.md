---
title: Plotly Skill Integration Guide
version: 1.0
status: OPERATIONAL
created: 2026-06-17
last_updated: 2026-06-17
author: Claude Code
purpose: Document when and how to use the /plotly Claude Code skill for chart design, implementation, and integration
---

# Plotly Skill Integration Guide — NYC DOT Dashboard

## Quick Reference

**What is /plotly?**
- A Claude Code skill that helps design, specify, and generate Plotly chart code
- Guides you through chart-type selection for a given dataset
- Generates production-ready Python code (Plotly Express or Graph Objects)
- Links interactive charts to the Dash Mission Control dashboard

**When to use /plotly:**
1. Adding a **new visualization** for a dataset not yet charted
2. **Replacing** an existing chart with a better visualization type
3. **Designing** a multi-view dashboard for a new analytical workflow
4. **Troubleshooting** a chart that's not rendering or updating correctly

**When NOT to use /plotly:**
- Styling/theming existing charts (use CSS in `app/assets/` or Mantine config instead)
- Fixing data-loading bugs (use data pipeline debugging instead)
- Exporting charts to static formats (use `plotly.io.write_image()` or `/simplify` instead)

---

## Chart Type Decision Tree

**Use this to decide which chart type to implement before invoking /plotly:**

```
Is your data time-based (dates, timestamps)?
├─ YES → Line Chart (optional: area fill, confidence bands)
│        └─ Multiple series? → Stacked Line or Multi-line
│        └─ Comparing to target? → Add reference line
│        └─ Categorical breakdown? → Faceted/grouped panels
│
├─ NO → Is it categorical (borough, agency, status)?
│      ├─ YES (2D matrix: rows vs columns)?
│      │    ├─ Values? → Heatmap
│      │    └─ Counts? → Grouped Bar Chart
│      │
│      ├─ YES (ranked: top 10, bottom 5)?
│      │    ├─ <10 categories → Horizontal Bar (sorted)
│      │    └─ >10 categories → Horizontal Bar + drill-down
│      │
│      ├─ YES (parts of a whole)?
│      │    ├─ Static snapshot → Donut/Pie
│      │    └─ Time-series parts → Stacked Bar/Area
│      │
│      └─ NO → Is it a single KPI or metric?
│           ├─ YES → Gauge Chart (with threshold zones)
│           └─ NO → Scatter/Bubble (if 2 dimensions); Box Plot (if distribution)
```

---

## How to Use /plotly: 5 Scenarios

### Scenario 1: Adding a New Chart for an Existing Dataset

**Task:** You want to add a **choropleth map** showing ramp locations with density shading.

**Step-by-step:**

1. **Clarify scope** (before invoking /plotly):
   - Dataset: `ramp_progress` (187K rows, has geometry)
   - Chart type: Choropleth map
   - Dimensions: Borough vs completion rate (%)
   - Interactivity: Hover for borough name, rate; click to drill down

2. **Invoke /plotly:**
   ```
   /plotly
   
   I want to add a choropleth map for ramp completion by borough.
   Dataset: ramp_progress (e7gc-ub6z)
   X-axis: Borough geometry (Staten Island, Manhattan, etc.)
   Y-axis: Completion rate (%)
   Desired interactivity: Hover tooltip + click drill-down
   Color scale: Green (high %) → Red (low %)
   ```

3. **Review output:**
   - /plotly returns Plotly code (Plotly Express or Graph Objects)
   - Check: Does it match the VISUALIZATION_REGISTRY spec?
   - Check: Are colors aligned with NYC DOT palette (#003087, #FF6319, #C60C30)?

4. **Integrate into Dash:**
   - Copy the function into `src/socrata_toolkit/plotly_charts.py`
   - Add callback in `app/callbacks/visualization_callbacks.py`
   - Register dcc.Graph in `app/dash_layouts.py`
   - Test with live data: `python app/dash_app.py`

---

### Scenario 2: Redesigning a Chart (Type Change)

**Task:** Current bar chart for `inspection` (borough counts) is static. You want **interactive filtering**.

**Current approach:**
```python
# In plotly_charts.py
def borough_bar_chart(df, ...):
    fig = go.Figure(go.Bar(...))
    return fig
```

**Step-by-step:**

1. **Clarify the new requirement:**
   - Keep data (borough inspection counts) — same
   - Add interactivity: Dropdown to filter by date range or status
   - Add visual improvements: animations, hover templates

2. **Invoke /plotly:**
   ```
   /plotly
   
   Redesign this bar chart to add interactivity:
   Current chart: Vertical bar (borough vs inspection count)
   New requirement: Add date-range dropdown filter
   Dataset: inspection (dntt-gqwq)
   Desired animation: Smooth transitions on filter change
   Framework: Dash callbacks (not just static Plotly)
   ```

3. **Review and integrate:**
   - /plotly returns enhanced code with Dash callback pattern
   - Update `app/callbacks/visualization_callbacks.py`
   - Test interactive filtering in browser

---

### Scenario 3: Building a Multi-Chart Dashboard

**Task:** Create a new "Equity Overview" dashboard with 4 linked charts.

**Step-by-step:**

1. **Define the dashboard structure** (before /plotly):
   - Chart 1: Population by borough (bar) — controls filter
   - Chart 2: Demographic breakdown by community district (stacked bar)
   - Chart 3: Housing density trend (line with forecast)
   - Chart 4: Census tract heatmap (choropleth)

2. **Invoke /plotly once per chart:**
   ```
   /plotly
   
   Design Chart 1 (Population by Borough):
   Dataset: Demographics_by_Borough (6khm-nrue)
   Type: Vertical bar
   X: Borough
   Y: Population count
   Color by: Income level (if available)
   ```
   
   (Repeat for Charts 2, 3, 4 with their own dataset + design)

3. **Create dashboard layout** in `app/dash_layouts.py`:
   ```python
   @callback(Output('demographic-chart-2', 'figure'),
             Input('demographic-chart-1', 'clickData'))
   def on_borough_click(click_data):
       borough = click_data['points'][0]['x']
       # Filter chart 2 by borough
       return update_chart_2(borough)
   ```

4. **Test linked interactions** in browser

---

### Scenario 4: Fixing a Non-Rendering Chart

**Task:** Choropleth map in GIS dashboard shows blank (no data points).

**Step-by-step:**

1. **Debug first (without /plotly):**
   - Check data: Does the DataFrame have geometry?
   - Run: `print(df[['geometry', 'borough', 'completion_rate']].head())`
   - Validate GeoJSON: Are coordinates in `[lon, lat]` format (not `[lat, lon]`)?

2. **If geometry is correct, invoke /plotly for fix:**
   ```
   /plotly
   
   My choropleth map isn't rendering data.
   Geometry is valid (GeoDataFrame, verified with gdf.head())
   Data has 5 rows (one per borough)
   Issue: Map shows blank/empty
   What's the correct Plotly configuration for this data?
   ```

3. **Review fix** and apply to code

---

### Scenario 5: Adding a New KPI Gauge to Dashboard

**Task:** Add a single gauge showing current ramp completion rate.

**Step-by-step:**

1. **Clarify KPI spec:**
   - Metric: Ramp completion rate (%)
   - Target: 80%
   - Threshold zones: Green (>80%), Yellow (60-80%), Red (<60%)
   - Update frequency: Daily

2. **Invoke /plotly:**
   ```
   /plotly
   
   Design a gauge chart for ramp completion rate.
   Metric: Ramp completion % (0–100)
   Target threshold: 80%
   Color zones: Green >80%, Yellow 60-80%, Red <60%
   Data source: ramp_progress (e7gc-ub6z)
   Update: Daily (6 AM)
   ```

3. **Review and integrate:**
   - /plotly returns gauge code using `plotly.graph_objects.Indicator`
   - Add to `app/visualization_engine/kpi_cards.py`
   - Link to scheduler for daily updates

---

## Integration Points: Where Plotly Fits in the Pipeline

```
VISUALIZATION REGISTRY (docs/VISUALIZATION_REGISTRY_37_DATASETS.md)
    ↓ [Specifies chart type, dimensions, colors for all 57 datasets]
    ↓
/PLOTLY SKILL [Generates code from spec]
    ↓ [Returns Plotly Express or Graph Objects function]
    ↓
src/socrata_toolkit/plotly_charts.py [Store all chart functions here]
    ↓ [Also: D3 charts in viz/d3_components.py; GIS charts in spatial/]
    ↓
app/callbacks/visualization_callbacks.py [Dash callbacks for interactivity]
    ↓ [Handles filter changes, drill-downs, linked interactions]
    ↓
app/dash_layouts.py [Register dcc.Graph components]
    ↓ [Bind callbacks to UI elements]
    ↓
DASHBOARD (http://localhost:8011) [Live interactive charts]
```

---

## Workflow: Adding a New Chart (Checklist)

**Before invoking /plotly:**
- [ ] Check VISUALIZATION_REGISTRY for dataset — what chart type is specified?
- [ ] Fetch sample data: `socrata fetch <fourfour> --limit 100`
- [ ] Validate shape: Do you have independent + dependent variables?
- [ ] Check colors: NYC DOT palette = #003087 (blue), #FF6319 (orange), #C60C30 (red)

**Invoke /plotly with:**
- [ ] Dataset name + fourfour ID
- [ ] Chart type (from registry)
- [ ] Independent variable (X-axis)
- [ ] Dependent variable (Y-axis)
- [ ] Any special requirements (animation, multi-series, drill-down, etc.)
- [ ] Color scheme + branding expectations

**After /plotly returns code:**
- [ ] Review for NYC DOT colors + styling
- [ ] Check for import statements (what Plotly modules does it use?)
- [ ] Test with live data: `python -c "from socrata_toolkit.plotly_charts import chart_func; fig = chart_func(df); fig.show()"`
- [ ] Verify accessibility: alt-text, high-contrast labels

**Integration:**
- [ ] Add to `src/socrata_toolkit/plotly_charts.py`
- [ ] Create callback in `app/callbacks/visualization_callbacks.py` (if interactive)
- [ ] Register in `app/dash_layouts.py` with `dcc.Graph(id=...)`
- [ ] Test in browser: `python app/dash_app.py`
- [ ] Update VISUALIZATION_REGISTRY if chart differs from spec
- [ ] Commit: `git add -A && git commit -m "Add [chart name] for [dataset]"`

---

## Current Plotly Charts (Implemented)

| Chart | Dataset | Type | Location | Status |
|-------|---------|------|----------|--------|
| borough_bar_chart | inspection, violations, etc. | Bar | `plotly_charts.py:43` | ✅ Active |
| kpi_gauge | Multiple (KPIs) | Gauge | `plotly_charts.py:78` | ✅ Active |
| contract_gantt | Built/permits | Gantt | `plotly_charts.py:117` | ✅ Active |
| priority_heatmap | By status/borough | Heatmap | `plotly_charts.py:151` | ✅ Active |
| trend_line | Time-series data | Line | `plotly_charts.py:177` | ✅ Active |
| status_donut | Status distribution | Donut | `plotly_charts.py:211` | ✅ Active |

**To add more:** Use /plotly to generate functions, add to this module.

---

## Common Patterns & Tips

### Pattern 1: Interactive Filter + Chart Update
```python
@callback(
    Output('chart-id', 'figure'),
    Input('filter-dropdown', 'value')
)
def update_chart(selected_value):
    df_filtered = df[df['category'] == selected_value]
    fig = borough_bar_chart(df_filtered, ...)
    return fig
```

### Pattern 2: Drill-Down on Click
```python
@callback(
    Output('detail-chart', 'figure'),
    Input('summary-chart', 'clickData')
)
def on_bar_click(click_data):
    if click_data is None:
        return go.Figure()
    borough = click_data['points'][0]['x']
    # Fetch + chart data for selected borough
```

### Pattern 3: Multi-Series Line Chart
```python
# /plotly will generate this pattern:
fig = px.line(
    df.groupby(['date', 'borough']).size().reset_index(name='count'),
    x='date', y='count', color='borough',
    title='Trend by Borough'
)
```

### Pattern 4: Animated Bar Chart (Ranked)
```python
# /plotly can generate animation frames for ranked data:
fig = px.bar(
    df, x='count', y='borough',
    animation_frame='year',
    range_x=[0, df['count'].max()],
    title='Borough Inspection Counts Over Time'
)
```

---

## Troubleshooting: When /plotly Output Doesn't Work

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| ImportError: No module named 'plotly' | Plotly not installed | `pip install plotly` (check requirements.txt) |
| Figure shows blank/empty | DataFrame is empty or columns misnamed | Check `df.columns`, `df.head()`, verify dataset freshness |
| Colors don't match brand | /plotly used default colors | Specify color map in /plotly prompt: "Use NYC blue (#003087)" |
| Hover tooltip shows wrong values | Column names in code don't match data | Verify column names, update `borough_col`, `value_col` params |
| Chart renders but callback not firing | Callback ID mismatch | Check `dcc.Graph(id=...)` matches `@callback(Output('...', ...))` |
| Animation not smooth | Frame interval too long | Reduce `animation_duration_ms` or add more frames |

---

## Resources

- **Plotly Docs:** https://plotly.com/python/
- **Plotly Express API:** https://plotly.com/python-api-reference/generated/plotly.express.html
- **Dash Callbacks:** https://dash.plotly.com/basic-callbacks
- **NYC DOT Color Palette:** `#003087` (blue), `#FF6319` (orange), `#C60C30` (red)
- **Visualization Registry:** See `docs/VISUALIZATION_REGISTRY_37_DATASETS.md` for all 57 datasets + specs

---

## Next Steps

1. **Review existing charts** in `src/socrata_toolkit/plotly_charts.py` — understand patterns
2. **Pick a dataset** from VISUALIZATION_REGISTRY without a chart yet
3. **Invoke `/plotly`** with dataset + desired chart type
4. **Integrate** using checklist above
5. **Test** in browser before committing

When in doubt, use `/plotly` — it's faster and more accurate than manual Plotly syntax.
