---
title: Chart Design Workflow — From Spec to Dashboard
version: 1.0
status: OPERATIONAL
created: 2026-06-17
last_updated: 2026-06-17
author: Claude Code
purpose: Standardized workflow for designing, implementing, and integrating Plotly charts into the NYC DOT dashboard
---

# Chart Design Workflow

**Goal:** Add a new interactive chart to the Dash Mission Control dashboard in <30 minutes using the /plotly skill.

**Prerequisites:**
- Dataset is documented in SOCRATA_DATASETS_CONSOLIDATED.md
- Chart type is specified in VISUALIZATION_REGISTRY_57_DATASETS.md
- Sample data has been fetched and validated
- /plotly skill is available in Claude Code

---

## 5-Minute Quick Start

```bash
# 1. Pick a dataset from VISUALIZATION_REGISTRY that's marked "⚠️ Spec only"
#    Example: NYCDOT_Awarded_Contracts → Horizontal Bar chart

# 2. Invoke /plotly with the spec
#    "Design a horizontal bar chart for NYCDOT_Awarded_Contracts.
#     X-axis: Contract Value ($), Y-axis: Contractor.
#     Colors: NYC DOT Blue (#003087)"

# 3. Copy the returned code into src/socrata_toolkit/plotly_charts.py

# 4. Test locally
python -c "
from socrata_toolkit.plotly_charts import chart_name
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', '9u5s-8sd8')
fig = chart_name(df)
fig.show()
"

# 5. Add callback in app/callbacks/visualization_callbacks.py
# 6. Register in app/dash_layouts.py
# 7. Run dashboard: python app/dash_app.py
# 8. Verify in browser at http://localhost:8011
# 9. Commit: git add -A && git commit -m "Add chart for [dataset]"
```

---

## Full Workflow (Step-by-Step)

### PHASE 1: Pre-Design (5 min)

**Goal:** Understand what you're building before writing code.

#### Step 1.1: Check the VISUALIZATION_REGISTRY
```bash
# In docs/VISUALIZATION_REGISTRY_57_DATASETS.md, find your dataset.
# Example: NYCDOT_Awarded_Contracts
# ├─ Chart Type: HORIZONTAL BAR CHART
# ├─ IV (X-Axis): Contract Value ($)
# ├─ DV (Y-Axis): Contractor
# ├─ Colors: NYC DOT Blue (#003087)
# └─ Annotations: Top 15 contractors, sorted by value
```

**Checklist:**
- [ ] Dataset name and fourfour ID found
- [ ] Chart type identified (Bar/Line/Heatmap/etc.)
- [ ] Independent variable (X-axis) noted
- [ ] Dependent variable (Y-axis) noted
- [ ] Color scheme noted (should reference NYC DOT palette)
- [ ] Any special annotations noted

#### Step 1.2: Fetch Sample Data
```bash
# Fetch 100 rows to validate structure
socrata fetch data.cityofnewyork.us <fourfour> --limit 100 --format json > /tmp/sample.json

# Or in Python:
from socrata_toolkit.core.client import SocrataClient, SocrataConfig
client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', '<fourfour>', max_rows=100)
print(df.head())
print(df.dtypes)
print(df.isnull().sum())
```

**Checklist:**
- [ ] DataFrame loads without errors
- [ ] Has columns for IV and DV
- [ ] No major null rates (>50%) in key columns
- [ ] Data types are reasonable (numeric for Y, categorical for X)

#### Step 1.3: Document Design Decisions
```markdown
# Design Notes: [Chart Name]

Dataset: [Dataset name] ([fourfour ID])
Chart type: [Bar/Line/etc]
IV: [X-axis column]
DV: [Y-axis column]
Colors: [NYC colors]
Filtering/Drill-down: [Yes/No, describe]
Expected update frequency: [Daily/Weekly/etc]
Accessibility: [Alt-text plan]
```

**Checklist:**
- [ ] All fields documented
- [ ] Matches VISUALIZATION_REGISTRY spec
- [ ] Team is aware of plan (if relevant)

---

### PHASE 2: Design with /plotly (10 min)

**Goal:** Generate production-ready Plotly code using the /plotly skill.

#### Step 2.1: Invoke /plotly

```
/plotly

I want to design a horizontal bar chart for contractor award amounts.

Dataset: NYCDOT_Awarded_Contracts (9u5s-8sd8)
X-axis (independent variable): Contract Value ($)
Y-axis (dependent variable): Contractor (name)
Chart type: Horizontal Bar
Colors: NYC DOT Blue (#003087) for bars; gray for reference
Sorting: Descending by contract value
Top N: Top 15 contractors
Interactivity:
  - Hover: Show contractor name, contract value, award date
  - Exclude: Hidden until expanded
Reference line: Median contract value in gray dashed line
Annotations: Value labels on bars, formatted as $millions
Update frequency: Weekly (or trigger on data refresh)
```

**Checklist:**
- [ ] Prompt includes all dimensions from registry spec
- [ ] Colors explicitly reference NYC DOT palette
- [ ] Interactivity requirements stated
- [ ] Edge cases mentioned (empty data, outliers, etc.)

#### Step 2.2: Review /plotly Output

/plotly will return code like:

```python
def contractor_awards_chart(df: pd.DataFrame, top_n: int = 15) -> Any:
    """Horizontal bar chart of top contractors by award amount."""
    go, px = _get_plotly()
    
    top_contractors = df.nlargest(top_n, 'contract_value')
    
    fig = px.bar(
        top_contractors,
        x='contract_value',
        y='contractor_name',
        orientation='h',
        color_discrete_sequence=['#003087'],
        title='Top Contractors by Award Amount'
    )
    
    # Median reference line
    median = df['contract_value'].median()
    fig.add_vline(x=median, line_dash='dash', line_color='gray')
    
    fig.update_layout(
        xaxis_title='Contract Value ($)',
        yaxis_title='Contractor',
        template='plotly_white',
        height=600
    )
    
    return fig
```

**Code Review Checklist:**
- [ ] Imports are correct (`import plotly.express as px`, `import plotly.graph_objects as go`)
- [ ] Function signature matches pattern: `def chart_name(df, **kwargs) -> Any`
- [ ] Uses `_get_plotly()` helper for lazy imports
- [ ] Colors are NYC DOT palette (#003087, #FF6319, #C60C30)
- [ ] Hover templates are included (if /plotly generated them)
- [ ] Layout is responsive (height specified, readable labels)
- [ ] Error handling not needed (trust data quality upstream)

#### Step 2.3: Ask Questions if Needed

If /plotly output doesn't match your needs:

```
/plotly

The code you generated uses orientation='h', but I need:
- Sorted descending by contract value
- Value labels on each bar
- Median reference line at 50th percentile
Can you update the code to include these?
```

**Common Refinements:**
- Sorting (ascending/descending)
- Value labels and formatting (currency, percentages)
- Reference lines (targets, benchmarks, averages)
- Drill-down/click events (requires Dash callback, can't auto-generate)
- Custom tooltips

---

### PHASE 3: Integration (10 min)

**Goal:** Wire the chart into the dashboard.

#### Step 3.1: Add to plotly_charts.py

```bash
# Copy /plotly output into src/socrata_toolkit/plotly_charts.py
# at the end of the file (before or after existing functions)

# Example location:
# ├─ borough_bar_chart (line 43)
# ├─ kpi_gauge (line 78)
# ├─ contract_gantt (line 117)
# ├─ priority_heatmap (line 151)
# ├─ trend_line (line 177)
# ├─ status_donut (line 211)
# └─ contractor_awards_chart (line NEW)  ← YOUR FUNCTION HERE
```

**Checklist:**
- [ ] Function pasted into `src/socrata_toolkit/plotly_charts.py`
- [ ] No syntax errors (run `python -m py_compile src/socrata_toolkit/plotly_charts.py`)
- [ ] Function docstring describes IV, DV, and output
- [ ] Type hints match existing functions

#### Step 3.2: Test Function Locally

```python
# In Python shell or script:
from socrata_toolkit.plotly_charts import contractor_awards_chart
from socrata_toolkit.core.client import SocrataClient, SocrataConfig

client = SocrataClient(SocrataConfig())
df = client.fetch_dataframe('data.cityofnewyork.us', '9u5s-8sd8', max_rows=5000)
fig = contractor_awards_chart(df)
fig.show()  # Opens in browser
```

**Checklist:**
- [ ] No import errors
- [ ] No runtime errors (null values, missing columns)
- [ ] Chart renders in browser
- [ ] Colors, labels, and layout match spec

#### Step 3.3: Create Callback in app/callbacks/visualization_callbacks.py

```python
# If your chart doesn't need filtering, you can skip this step.
# Just register the static figure in the layout (Step 3.4).

# If you DO need filtering (e.g., by borough, date range):

from dash import callback, Input, Output
from socrata_toolkit.plotly_charts import contractor_awards_chart

@callback(
    Output('contractor-chart', 'figure'),
    Input('contractor-filter', 'value')
)
def update_contractor_chart(selected_contractor=None):
    """Update contractor awards chart on filter change."""
    df = fetch_contractor_data()  # Implement based on your needs
    if selected_contractor:
        df = df[df['contractor_name'] == selected_contractor]
    return contractor_awards_chart(df)
```

**Checklist:**
- [ ] Callback input/output IDs are defined
- [ ] Function name is descriptive
- [ ] Data fetch logic is implemented (or use existing utility)
- [ ] Handles edge cases (empty filter, null data)

#### Step 3.4: Register in app/dash_layouts.py

Find the appropriate page/section and add:

```python
# In app/dash_layouts.py, under the relevant section (e.g., "Contractor Management"):

dcc.Graph(
    id='contractor-chart',
    figure=contractor_awards_chart(df_contractors)  # initial data
)

# Or with callback:
dcc.Graph(id='contractor-chart')  # callback will populate

# Don't forget to import at top of file:
from socrata_toolkit.plotly_charts import contractor_awards_chart
```

**Checklist:**
- [ ] `dcc.Graph` component created with unique ID
- [ ] ID matches callback Output/Input if using callback
- [ ] Imported from `plotly_charts`
- [ ] Positioned logically in layout (near related charts)
- [ ] HTML structure is valid (check for missing commas, brackets)

#### Step 3.5: Test in Dashboard

```bash
# Start the dashboard
python app/dash_app.py

# Open browser: http://localhost:8011
# Navigate to the page with your new chart
# Test:
# - Chart renders without errors
# - Hover tooltips work
# - Click interactions work (if applicable)
# - Colors match spec
# - Labels are readable
```

**Checklist:**
- [ ] Chart appears on page
- [ ] No console errors (check browser DevTools → Console)
- [ ] Data loads correctly (no blank chart)
- [ ] Interactivity works (hover, click, filter)
- [ ] Responsive on mobile (if applicable)

#### Step 3.6: Commit to Git

```bash
# Stage changes
git add -A

# Commit with clear message
git commit -m "Add contractor awards horizontal bar chart (9u5s-8sd8)

- Implements VISUALIZATION_REGISTRY spec for NYCDOT_Awarded_Contracts
- Uses Plotly Express with NYC DOT color palette
- Displays top 15 contractors by award value
- Includes median reference line and hover tooltips
- Integrated into contractor management dashboard"

# Push (if applicable)
git push origin feature/contractor-awards-chart
```

**Commit Message Best Practices:**
- [ ] One-line summary (under 72 chars)
- [ ] Blank line, then detailed description
- [ ] Reference dataset fourfour ID
- [ ] Note if it fulfills VISUALIZATION_REGISTRY spec
- [ ] Mention any special considerations (filtering, GIS, etc.)

---

### PHASE 4: Documentation (5 min)

**Goal:** Record what you built for future maintenance.

#### Step 4.1: Update VISUALIZATION_REGISTRY (if spec changed)

If your implementation differs from the spec (different colors, added drill-down, etc.):

```markdown
# In docs/VISUALIZATION_REGISTRY_57_DATASETS.md, find the dataset section:

#### X.X `contractor_awards` (9u5s-8sd8)
```
Title: "Top Contractors by Award Value"
Implementation Status: ✅ IMPLEMENTED (2026-06-17)
File: src/socrata_toolkit/plotly_charts.py:contractor_awards_chart()
Callback: app/callbacks/visualization_callbacks.py:update_contractor_chart()
Dashboard Location: app/dash_layouts.py ~ Contractor Management section
Chart Type: HORIZONTAL BAR CHART ✅ (matches spec)
Interactivity: ✅ Hover + reference line (added beyond spec)
```
```

**Checklist:**
- [ ] Status changed from "⚠️ Spec only" to "✅ Implemented"
- [ ] Implementation file path noted
- [ ] Dashboard location documented
- [ ] Date added

#### Step 4.2: Update VISUALIZATION_AUDIT

In `docs/VISUALIZATION_AUDIT_PLOTLY_VS_OTHER.md`, update the dataset status:

```markdown
| NYCDOT_Awarded_Contracts | 9u5s-8sd8 | Horizontal Bar | Plotly Express | ✅ IMPLEMENTED | plotly_charts.py:contractor_awards_chart() |
```

**Checklist:**
- [ ] Status field updated to "✅ IMPLEMENTED"
- [ ] File location updated

#### Step 4.3: Add Docstring Notes (Optional)

If the chart has non-obvious features:

```python
def contractor_awards_chart(df: pd.DataFrame, top_n: int = 15) -> Any:
    """
    Horizontal bar chart of top contractors by awarded contract value.
    
    Args:
        df: DataFrame with columns: contractor_name, contract_value, award_date
        top_n: Number of top contractors to display (default: 15)
    
    Returns:
        Plotly figure object
    
    Notes:
        - Sorted descending by contract value
        - Median reference line added at 50th percentile
        - Hover shows contractor name, value, and award date
        - Empty data returns blank chart (not an error)
    
    Example:
        from socrata_toolkit.plotly_charts import contractor_awards_chart
        df = client.fetch_dataframe('data.cityofnewyork.us', '9u5s-8sd8')
        fig = contractor_awards_chart(df)
        fig.show()
    """
```

**Checklist:**
- [ ] Docstring includes purpose
- [ ] Args and return types documented
- [ ] Edge cases noted
- [ ] Usage example included

---

## Decision Tree: Which Phase Am I In?

```
Do I have a spec in VISUALIZATION_REGISTRY?
├─ NO  → Create spec first (requires analyst/PM review)
│        └─ Then return to PHASE 1
│
├─ YES, already implemented?
│  └─ Update existing chart? → Skip to PHASE 2 (redesign)
│     └─ Different chart type → Go to PHASE 1
│
└─ YES, not implemented?
   └─ Follow full workflow PHASE 1–4
```

---

## Common Workflows

### Adding a Simple Bar Chart (5 min)

1. Invoke /plotly: "Vertical bar chart, [dataset], X=[column], Y=[count/sum of column]"
2. Copy code to `plotly_charts.py`
3. Register in `dash_layouts.py` as static: `dcc.Graph(figure=chart_func(df))`
4. Test + commit

**Example:** Contractor count by trade code (no filtering needed)

---

### Adding a Time Series with Filtering (15 min)

1. Invoke /plotly: "Line chart with date on X, metric on Y, optionally grouped by [category]"
2. Copy code to `plotly_charts.py`
3. Create callback in `visualization_callbacks.py` for date-range filter
4. Register in `dash_layouts.py` with callback wiring
5. Test + commit

**Example:** Violations trend over last 90 days, filtered by borough

---

### Adding a KPI Gauge (10 min)

1. Invoke /plotly: "Gauge chart, [metric], target=[value], zones=[thresholds]"
2. Copy code to `plotly_charts.py` (or `kpi_cards.py` if using Dash cards)
3. Link to scheduler/pipeline if metric needs daily refresh
4. Register in `kpi_cards.py`
5. Test + commit

**Example:** Current ramp completion rate (%) with target 80%

---

### Replacing an Existing Chart (10 min)

1. Find function in `plotly_charts.py` or `viz/` modules
2. Invoke /plotly with current spec + desired changes
3. Replace function body with new code
4. Test with same callback setup
5. Commit with note: "Refactor: [old chart type] → [new chart type]"

**Example:** Dismissal bar chart → dismissal gauge (to emphasize single metric)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| /plotly output doesn't match registry spec | Ask /plotly to adjust; or file PR to update registry if spec is wrong |
| Chart shows blank/no data | Check DataFrame columns match function params; validate data freshness |
| Callback not firing | Verify ID match between `dcc.Graph(id=...)` and `@callback(Output('...')` |
| Colors are wrong | Verify #003087, #FF6319, #C60C30 are in use; check color_discrete_sequence param |
| Chart too slow | Reduce rows with `.sample()` or limit time window; use `scattergl` for 1M+ points |
| Hover tooltip shows wrong data | Check hover_data param or custom hover_template in /plotly output |
| Mobile layout broken | Add `responsive=True` to `fig.update_layout()`; test on small screen |

---

## Checklists

### Pre-/plotly Checklist
- [ ] Dataset in SOCRATA_DATASETS_CONSOLIDATED.md
- [ ] Chart spec in VISUALIZATION_REGISTRY_57_DATASETS.md
- [ ] Sample data fetched and validated
- [ ] Column names and data types confirmed
- [ ] No critical null rates (>50%)
- [ ] NYC DOT color palette accessible (#003087, #FF6319, #C60C30)

### Post-/plotly Integration Checklist
- [ ] Code tested locally (no errors)
- [ ] Chart renders in browser
- [ ] Callback wired (if applicable)
- [ ] Layout registration updated
- [ ] Dashboard loads without errors
- [ ] Hover/click interactions work
- [ ] Colors match spec
- [ ] Labels are readable
- [ ] Responsive on mobile (if applicable)
- [ ] Committed with clear message
- [ ] VISUALIZATION_REGISTRY updated
- [ ] VISUALIZATION_AUDIT updated

---

## Templates

### /plotly Prompt Template

```
/plotly

I want to design a [CHART_TYPE] chart for [DATASET_NAME].

Dataset: [dataset] ([fourfour ID])
X-axis (independent variable): [column name]
Y-axis (dependent variable): [column name or aggregation]
Chart type: [Bar/Line/Heatmap/etc]
Colors: [NYC DOT palette: Blue #003087, Orange #FF6319, Red #C60C30]
Sorting: [ascending/descending by value, or by category]
Top N: [show top/bottom 10/15/etc, or all]
Interactivity: [Hover tooltips / Click drill-down / Filter dropdown / Reference line]
Special features: [Stacking / Grouping / Facets / Confidence intervals / etc]
Update frequency: [Daily/Weekly/Static]
```

### Callback Template

```python
from dash import callback, Input, Output
from socrata_toolkit.plotly_charts import chart_function_name

@callback(
    Output('chart-id', 'figure'),
    Input('filter-id', 'value')
)
def update_chart_name(filter_value):
    """Update chart on [filter] change."""
    df = fetch_data()  # Implement based on data source
    if filter_value:
        df = df[df['column'] == filter_value]
    return chart_function_name(df)
```

### Layout Registration Template

```python
dcc.Graph(
    id='chart-id',
    figure=chart_function_name(df_initial_data)
)
```

---

## References

- **Plotly Skill Guide:** `docs/PLOTLY_SKILL_INTEGRATION_GUIDE.md`
- **Visualization Audit:** `docs/VISUALIZATION_AUDIT_PLOTLY_VS_OTHER.md`
- **Visualization Registry:** `docs/VISUALIZATION_REGISTRY_57_DATASETS.md`
- **Plotly API:** https://plotly.com/python-api-reference/
- **Dash Callbacks:** https://dash.plotly.com/basic-callbacks
- **NYC DOT Dataset Consolidation:** `docs/SOCRATA_DATASETS_CONSOLIDATED.md`

---

## Summary

| Phase | Time | Output | Key Action |
|-------|------|--------|-----------|
| 1. Pre-Design | 5 min | Design notes + sample data | Check registry, fetch data, doc plan |
| 2. /plotly Design | 10 min | Plotly code | Invoke skill, review output, refine |
| 3. Integration | 10 min | Wired dashboard | Add to `plotly_charts.py`, callback, layout |
| 4. Documentation | 5 min | Updated registry | Mark "✅ Implemented", add notes |
| **Total** | **30 min** | **Live chart** | **From spec to dashboard** |

**Your goal: Get from "I want to add a chart" to "It's live on the dashboard" in <30 minutes using /plotly.**

The workflow is designed to be fast, repeatable, and maintainable. Use it for every new Plotly chart in the NYC DOT dashboard.
