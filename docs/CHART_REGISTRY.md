# Chart Registry — Metadata & Column Requirements

Complete inventory of all 65+ visualizations with column dependencies, data types, analysis patterns, and shared variables for ERD construction and hypothesis testing.

---

## 📊 Legend

- **Required Cols** — must be present (no defaults)
- **Optional Cols** — enhance chart; ignored if missing
- **Data Type** — expected column dtype (numeric, datetime, categorical, geometry)
- **Shared Vars** — columns that appear in multiple charts (linkage points for ERD)
- **Analysis Type** — distributional, temporal, spatial, comparative, relational, quality
- **Hypothesis** — typical research questions the chart answers

---

## 🎯 Core Plotly Charts

### Borough Bar Chart
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `borough_bar_chart()` |
| **Input Cols (Required)** | `borough` (categorical), `violations` \| `repairs` \| metric (numeric) |
| **Input Cols (Optional)** | `date` (for filtering), grouping columns |
| **Data Types** | borough: str, metric: int/float |
| **Output Type** | Plotly Bar Figure |
| **Analysis Type** | Comparative, distributional |
| **Shared Vars** | `borough` (5 distinct: MN, BX, BK, QN, SI) |
| **Typical Hypothesis** | Which borough has highest violation density? Is violation load evenly distributed? |
| **Example Dataset** | `inspection`, `violations`, `ramp_progress` |
| **Dependencies** | plotly.express |

### Metric Gauge
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `metric_gauge()` |
| **Input Cols (Required)** | None (takes scalar values) |
| **Input Params** | `value` (float), `title` (str), `target` (float), `min_val`, `max_val` |
| **Data Types** | numeric |
| **Output Type** | Plotly Indicator (gauge) Figure |
| **Analysis Type** | Comparative (vs target), quality |
| **Shared Vars** | n/a (scalar only) |
| **Typical Hypothesis** | Is current completion rate above/below SLA? Budget variance within threshold? |
| **Example Usage** | Contract progress, SLA breach rate, budget CPI |
| **Dependencies** | plotly.graph_objects |

### Trend Line
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `trend_line()` |
| **Input Cols (Required)** | `date_col` (datetime), `value_col` (numeric) |
| **Input Cols (Optional)** | `group_col` (categorical, for multi-line) |
| **Data Types** | date_col: datetime64, value_col: int/float, group_col: str |
| **Output Type** | Plotly Line Figure |
| **Analysis Type** | Temporal, comparative |
| **Shared Vars** | `date` (temporal anchor), `borough` \| `material_type` (group) |
| **Typical Hypothesis** | Are violations increasing or declining over time? Seasonal patterns? By-borough divergence? |
| **Example Dataset** | `inspection`, `violations`, `ramp_complaints` |
| **Aggregation** | `resample` (D, W, ME, QE, YE), `agg` (sum, mean, count) |

### Correlation Heatmap
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `correlation_heatmap()` |
| **Input Cols (Required)** | 2+ numeric columns (auto-selected) |
| **Data Types** | All numeric (int, float) |
| **Output Type** | Plotly Heatmap Figure (RdBu diverging) |
| **Analysis Type** | Relational, comparative |
| **Shared Vars** | Any numeric pair: `violation_count`, `repair_cost`, `condition_score`, `age_years` |
| **Typical Hypothesis** | Do violations correlate with repair cost? Age with condition decay? |
| **Example Dataset** | `inspection` (profile with all metrics) |
| **Dependencies** | pandas.corr(), plotly |

### Status Donut Chart
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `status_donut()` |
| **Input Cols (Required)** | `status_col` (categorical: Open, Complete, Pending, Dismissed, etc.) |
| **Data Types** | categorical (str) |
| **Output Type** | Plotly Pie Figure (hole=0.45) |
| **Analysis Type** | Distributional, comparative |
| **Shared Vars** | `status` (standard SIM/permit statuses) |
| **Typical Hypothesis** | What % of violations are still open vs completed? Dismissal rate? |
| **Example Dataset** | `violations`, `dismissals`, `ramp_progress` |
| **Dependencies** | plotly.graph_objects |

### Contract Gantt
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `contract_gantt()` |
| **Input Cols (Required)** | `task_col` (contract ID), `start_col` (date), `end_col` (date) |
| **Input Cols (Optional)** | `color_col` (status: complete, in_progress, delayed, not_started) |
| **Data Types** | task: str, dates: datetime64 |
| **Output Type** | Plotly Timeline Figure |
| **Analysis Type** | Temporal, comparative |
| **Shared Vars** | `contract_id`, `status`, `date` ranges |
| **Typical Hypothesis** | Which contracts are behind schedule? Critical path? |
| **Example Dataset** | Capital projects, street resurfacing schedule |

### Priority Heatmap
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `priority_heatmap()` |
| **Input Cols (Required)** | `row_col` (categorical, e.g., borough), `col_col` (categorical, e.g., status), `value_col` (numeric) |
| **Data Types** | row/col: str, value: int/float |
| **Output Type** | Plotly Heatmap Figure (RdYlGn_r) |
| **Analysis Type** | Comparative, distributional |
| **Shared Vars** | `borough` (rows), `status` (cols) → creates 5×4 grid for allocation view |
| **Typical Hypothesis** | Which borough-status combination has most violations? Priority allocation? |
| **Example Dataset** | `violations` grouped by borough × status |

### Hypothesis Test Results
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `hypothesis_test_results()` |
| **Input Params** | `group_names` (list[str]), `p_values` (list[float]), `effect_sizes` (list[float]) |
| **Data Types** | numeric (p-value 0–1, effect size typically Cohen's d or Cramér's V) |
| **Output Type** | Plotly Bar + Scatter (dual-axis) Figure |
| **Analysis Type** | Statistical inference |
| **Shared Vars** | n/a (aggregated stats only) |
| **Typical Hypothesis** | Is the difference in violation rates across boroughs statistically significant? |
| **Dependencies** | scipy.stats for upstream computation |

### Waterfall Chart
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `waterfall_chart()` |
| **Input Cols (Required)** | `category` (str), `value` (float, signed for up/down) |
| **Data Types** | category: str, value: int/float (positive = increase, negative = decrease) |
| **Output Type** | Plotly Waterfall Figure |
| **Analysis Type** | Temporal decomposition, impact |
| **Shared Vars** | None (flow diagram) |
| **Typical Hypothesis** | What drove the change in open violations from Q1 to Q2? |
| **Example Usage** | Cohort entry/exit flows, budget variance breakdown |

### Inspector Performance Boxplot
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/plotly.py` |
| **Function** | `inspector_performance_boxplot()` |
| **Input Cols (Required)** | `inspector_id` (categorical), `metric` (numeric: violations, repairs, score) |
| **Data Types** | inspector_id: str/int, metric: int/float |
| **Output Type** | Plotly Box Figure |
| **Analysis Type** | Comparative, quality |
| **Shared Vars** | `inspector_id` (linkage to `inspection` dataset) |
| **Typical Hypothesis** | Do inspectors have consistent violation-detection rates or scoring bias? |
| **Example Dataset** | `inspection` grouped by `inspector_id` |

---

## 🔢 Advanced Multi-Dimensional Charts

### Parallel Coordinates
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `parallel_coordinates()` |
| **Input Cols (Required)** | 2+ numeric columns (e.g., `violation_count`, `repair_cost`, `condition_score`, `age_years`) |
| **Input Cols (Optional)** | `color_col` (categorical for line coloring, e.g., borough) |
| **Data Types** | numeric cols: int/float, color_col: categorical |
| **Output Type** | Plotly Parcoords Figure (interactive brushing) |
| **Analysis Type** | Multi-variate exploration, filtering |
| **Shared Vars** | `borough`, `violation_count`, `repair_cost`, `condition_score`, `age_years` |
| **Typical Hypothesis** | What block profiles have HIGH violations + HIGH cost + LOW condition? (find problem cases) |
| **Sample Query** | Brush `violation_count` [5–10], `condition_score` [0–40], `repair_cost` [3000–10000] |
| **Dependencies** | plotly.graph_objects (Parcoords) |

### Scatter Plot Matrix (SPLOM)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `scatter_plot_matrix()` |
| **Input Cols (Required)** | 3+ numeric columns (auto-samples if >2000 rows) |
| **Input Cols (Optional)** | `color_col` (categorical, e.g., borough) |
| **Data Types** | numeric: int/float, color_col: str |
| **Output Type** | Plotly SPLOM Figure (N×N grid) |
| **Analysis Type** | Pairwise correlation, outlier detection |
| **Shared Vars** | Any numeric pair in data |
| **Typical Hypothesis** | Are violations driving repair cost? Or is age the primary cost driver? Which pairs show clustering? |
| **Example Cols** | `violation_count`, `repair_cost`, `condition_score`, `age_years`, `inspection_count` |
| **Row Cap** | Default 2000 (random sample for speed) |

### Clustermap (Hierarchical Heatmap)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `clustermap()` |
| **Input Cols (Required)** | `row_key` (categorical: borough, community_board, contractor), 2+ numeric `value_cols` |
| **Data Types** | row_key: str, value_cols: int/float |
| **Output Type** | Plotly Heatmap (Ward-clustered rows/cols) |
| **Analysis Type** | Hierarchical clustering, similarity grouping |
| **Shared Vars** | `borough` (5 clusters), `community_board` (51 clusters) |
| **Typical Hypothesis** | Which boroughs/CBs are most similar in their violation-cost-score profile? Which are outliers? |
| **Dendrograms** | Row & column dendrograms show linkage structure |
| **Z-Score** | Auto-normalized per column for fair comparison |

### Sankey Flow Diagram
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `sankey_flow()` |
| **Input Cols (Required)** | `source_col` (categorical), `target_col` (categorical) |
| **Input Cols (Optional)** | `value_col` (numeric: if None, count rows) |
| **Data Types** | source/target: str, value: int/float |
| **Output Type** | Plotly Sankey Figure |
| **Analysis Type** | Relational flow, state transition |
| **Shared Vars** | `borough` → `violation_type`, `violation_type` → `status`, `material` → `defect_type` |
| **Typical Hypothesis** | Do concrete violations flow to dismissal faster than brick? Which borough-to-status transitions are largest? |
| **Top-N** | Default top 20 source→target pairs (by volume) |

### Radar / Spider Chart
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `radar_chart()` |
| **Input Cols (Required)** | `group_col` (categorical: borough), 2+ numeric `metric_cols` |
| **Data Types** | group: str, metrics: int/float |
| **Output Type** | Plotly Scatterpolar Figure (multiple polygons) |
| **Analysis Type** | Multi-metric comparison across groups |
| **Shared Vars** | `borough` (MN, BX, BK, QN, SI) |
| **Normalize** | Default True (scales each metric 0–1 for fair spoke comparison) |
| **Typical Hypothesis** | Which borough excels in all metrics (highest shape)? Trade-offs: high violations but low cost? |
| **Example Metrics** | `violation_count`, `repair_cost`, `condition_score`, `completion_rate` |

### Crossfilter Layout
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `crossfilter_layout()` |
| **Input Cols (Required)** | `filter_col` (categorical: borough, material), chart specs (x, y per chart) |
| **Data Types** | filter_col: str, x/y: any (parsed by chart type) |
| **Output Type** | List[Plotly Figures], one per (chart × filter_value) combo |
| **Analysis Type** | Multi-chart filtering, slicing |
| **Shared Vars** | `filter_col` (groups data) |
| **Typical Hypothesis** | How does the violation-cost-time relationship differ when filtered to MANHATTAN vs BROOKLYN? |
| **Chart Types** | bar, scatter, histogram, box, violin |
| **Use in Dash** | Wire output figures to dcc.Dropdown; re-render on filter selection |

### Funnel Chart (Inspection Pipeline)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `inspection_funnel()` |
| **Input Params** | `stage_labels` (list[str]), `stage_counts` (list[int]) |
| **Data Types** | labels: str, counts: int |
| **Output Type** | Plotly Funnel Figure |
| **Analysis Type** | Pipeline flow, drop-off |
| **Shared Vars** | None (aggregated stages) |
| **Typical Hypothesis** | What % of violations are dismissed? Reinspected? What's the main leakage point? |
| **Example Stages** | Inspections → Violations → Reinspected → Dismissed → Resolved |
| **Stage Counts** | Should be monotonically decreasing (or increasing if inverted) |

### Bubble Chart (4D Encoding)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/advanced_multidim.py` |
| **Function** | `bubble_chart()` |
| **Input Cols (Required)** | `x_col` (numeric), `y_col` (numeric), `size_col` (numeric) |
| **Input Cols (Optional)** | `color_col` (categorical or numeric), `hover_name_col` (str for tooltip) |
| **Data Types** | x/y/size: int/float, color: categorical/numeric, hover_name: str |
| **Output Type** | Plotly Scatter Figure |
| **Analysis Type** | 4-variate comparison (x, y, size, color) |
| **Shared Vars** | `community_board`, `borough`, `violation_count`, `repair_cost`, `condition_score` |
| **Typical Hypothesis** | Is there a CB with high violation density (size) and high cost (y) but low condition (x)? |
| **Log Axes** | Optional (useful for skewed cost distributions) |

---

## 📈 Statistical Visualization Charts

### CUSUM Control Chart
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `cusum_control_chart()` |
| **Input Cols (Required)** | Time-ordered numeric series (index = time or observation order) |
| **Data Types** | series: numeric (int/float), index: ordinal (DatetimeIndex preferred) |
| **Output Type** | Plotly Subplot Figure (2 rows: raw series + CUSUM accumulation) |
| **Analysis Type** | Process control, changepoint detection |
| **Shared Vars** | `date` (temporal anchor for series) |
| **Typical Hypothesis** | Has the violation count process shifted level? When did it happen? |
| **Params** | `k` (allowance, default 0.5σ), `h` (threshold, default 5σ), `annotate_changepoint` (True/False) |
| **Output Markers** | Vertical line at detected shift point (CUSUM max deviation) |

### Bayesian Posterior Strip
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `bayesian_posterior_strip()` |
| **Input Cols (Required)** | DataFrame columns are parameter names, rows are posterior draws (from PyMC/arviz) |
| **Data Types** | numeric (draws from MCMC sampling) |
| **Output Type** | Plotly Scatter Figure (HDI intervals + mean) |
| **Analysis Type** | Bayesian inference, credible intervals |
| **Shared Vars** | Model parameters: Intercept, Borough Effect, Age Effect, Material Effect |
| **Typical Hypothesis** | What are the 89% credible intervals for the borough effect on violation count? |
| **HDI Prob** | Default 0.89 (89% highest density interval) |
| **Plot Elements** | Thin bars (89% HDI), thick bars (50% HDI), white dots (posterior mean) |

### Moran's I Scatter Plot
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `moran_scatter_plot()` |
| **Input Cols (Required)** | `value_col` (numeric: violation_count), `borough_col` (categorical: for spatial lag proxy) |
| **Data Types** | value: int/float, borough: str |
| **Output Type** | Plotly Scatter Figure (4 LISA quadrants colored) |
| **Analysis Type** | Spatial autocorrelation, LISA local indicator |
| **Shared Vars** | `borough` (used to compute borough-mean spatial lag) |
| **Typical Hypothesis** | Do violations cluster spatially (HH + LL quadrants)? Or are outliers isolated? |
| **Quadrants** | HH (red: high-high), LL (blue: low-low), HL (orange: high-isolated), LH (teal: low-surrounded) |
| **Moran's I Statistic** | Slope of z vs Wz line; printed on chart |

### Ridge Plot (KDE Distribution)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `ridge_plot()` |
| **Input Cols (Required)** | `value_col` (numeric), `group_col` (categorical: borough, material_type) |
| **Data Types** | value: int/float, group: str |
| **Output Type** | Plotly Violin Figure (stacked, no overlap) |
| **Analysis Type** | Distributional comparison |
| **Shared Vars** | `borough` (5 distributions), `material_type` (5–7 distributions) |
| **Typical Hypothesis** | Do violation-count distributions differ by borough? Manhattan vs Queens skewness? |
| **Bandwidth** | Param for KDE smoothing (default 0.5 × data std) |

### Changepoint Overlay (Time-Series + Shifts)
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `changepoint_overlay()` |
| **Input Cols (Required)** | `date_col` (datetime), `value_col` (numeric) |
| **Input Cols (Optional)** | `group_col` (categorical: borough for multi-series) |
| **Data Types** | date: datetime64, value: int/float, group: str |
| **Output Type** | Plotly Line Figure with vertical dashed markers |
| **Analysis Type** | Temporal changepoint, multi-series comparison |
| **Shared Vars** | `date`, `borough` (one line per borough, one marker per detected shift) |
| **Typical Hypothesis** | Did violation counts shift after the protected streets policy (2026-05)? By borough? |
| **Markers** | Vertical dashed line at CUSUM-detected changepoint per group |

### HDI-Annotated Violin
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/statistical_viz.py` |
| **Function** | `hdi_violin()` |
| **Input Cols (Required)** | `value_col` (numeric), `group_col` (categorical) |
| **Data Types** | value: int/float, group: str |
| **Output Type** | Plotly Violin Figure (with HDI shaded regions) |
| **Analysis Type** | Distributional comparison with Bayesian intervals |
| **Shared Vars** | `borough`, `material_type`, `status` |
| **Typical Hypothesis** | Is the condition-score distribution for brick narrower (more consistent) than concrete? |
| **HDI Shading** | Colored rectangle behind violin marking the 89% HDI band |

---

## 🗺️ D3.js Components (HTML String Output)

### Chord Diagram
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/d3_components.py` |
| **Function** | `chord_diagram()` |
| **Input Params** | `matrix` (NxN list[list[float]]), `groups` (list[str]: group names), `colors` (list[str]: hex codes) |
| **Data Types** | matrix: numeric (flow magnitudes), groups: str, colors: hex strings |
| **Output Type** | str (raw HTML with embedded D3 v7) |
| **Analysis Type** | Relational flow, symmetry |
| **Shared Vars** | `borough`, `violation_type` (for matrix rows/cols) |
| **Typical Hypothesis** | Which borough-to-violation-type flows are bidirectional? Cross-borough coordination patterns? |
| **Matrix Construction** | borough × violation_type contingency table via pd.crosstab() |
| **Browser Embed** | Use `st.components.v1.html()` (Streamlit) or `dcc.Iframe(srcDoc=html)` (Dash) |

### Force-Directed Network
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/d3_components.py` |
| **Function** | `force_network()` |
| **Input Params** | `nodes` (list[dict: id, group, value]), `links` (list[dict: source, target, value]) |
| **Data Types** | node.id: str, node.group: str, node.value: numeric, link.value: numeric |
| **Output Type** | str (raw HTML with embedded D3 v7, interactive dragging) |
| **Analysis Type** | Relational proximity, network structure |
| **Shared Vars** | Node groups: `borough`, `contractor`, `material_type` |
| **Typical Hypothesis** | Which inspectors cluster together (similar violation patterns)? Which contractors are isolated? |
| **Node Construction** | `inspection` → `inspector_id` (nodes), `inspection` pairs with same `block` (links) |
| **Physics** | Charge repulsion (push apart), link distance (pull together), center gravity |

### D3 Treemap
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/d3_components.py` |
| **Function** | `treemap_d3()` |
| **Input Params** | `hierarchy_data` (nested dict in D3 hierarchy format), `width`, `height` |
| **Data Types** | hierarchy: nested structure {name, children: [{name, children: [...] | value}]} |
| **Output Type** | str (raw HTML with embedded D3 v7) |
| **Analysis Type** | Hierarchical decomposition |
| **Shared Vars** | Multi-level grouping: `borough` → `community_board` → `status` |
| **Typical Hypothesis** | Where is the majority of violations (by area size)? Nested structure reveals priority. |
| **Helper Function** | `df_to_hierarchy(df, level_cols, value_col)` builds hierarchy dict from flat DataFrame |
| **Color Scale** | Tableau10; color per top-level node |

### Stream Graph
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/d3_components.py` |
| **Function** | `stream_graph()` |
| **Input Cols (Required)** | `date_col` (datetime), `category_col` (categorical: violation_type), `value_col` (numeric: count) |
| **Data Types** | date: datetime64, category: str, value: int/float |
| **Output Type** | str (raw HTML with embedded D3 v7) |
| **Analysis Type** | Temporal composition, stacked area |
| **Shared Vars** | `date` (temporal anchor), `violation_type` (stacked streams) |
| **Typical Hypothesis** | Have trip-hazard violations increased relative to cracked-slab? Composition shift over time? |
| **Aggregation** | Pivot: date × violation_type (auto-sums `value_col`) |
| **Offset** | d3.stackOffsetWiggle (wavy baseline, easier on eyes than stacked) |

### Hex-Bin Density Map
| Attribute | Value |
|-----------|-------|
| **Module** | `viz/d3_components.py` |
| **Function** | `hex_binmap()` |
| **Input Cols (Required)** | `lat_col` (numeric: latitude), `lon_col` (numeric: longitude) |
| **Data Types** | lat/lon: float |
| **Output Type** | str (raw HTML with embedded D3 v7 + d3-hexbin plugin) |
| **Analysis Type** | Spatial density, hotspot |
| **Shared Vars** | `latitude`, `longitude` (geographic coordinates) |
| **Typical Hypothesis** | Where are violation hotspots geographically? Are they clustered or dispersed? |
| **Projection** | Equirectangular, centered on NYC (40.71, -73.98) |
| **NYC Bounds** | Hard-coded to filter lat 40.47–40.93, lon -74.26–-73.70 |
| **Hex Color** | Sequential OrRd (white to red); density encoded in color |

---

## 🔗 Shared Variables & ERD Linkage Points

### Common Categorical Dimensions (Join Keys)

| Variable | Possible Values | Appears In Charts | Datasets | Notes |
|----------|-----------------|-------------------|----------|-------|
| `borough` | MN, BX, BK, QN, SI | All comparative, radar, Sankey, clustermap, ridge | inspection, violations, permits, ramp_progress, all | Primary geographic grouping (5 values) |
| `community_board` | 101–518 (NYC BBL format) | Clustermap, bubble, funnel detail, Sankey, parallel coords | inspection, violations, lot_info | Finer geographic resolution (51+ boards) |
| `material_type` | Concrete, Brick, Asphalt, Granite, Stone | Ridge plot, radar (if grouped), clustermap, Sankey | inspection, violations, built | Defect type driver |
| `violation_type` | Trip Hazard, Cracked Slab, ADA, Raised Lip, Depression | Sankey, stream graph, chord, treemap | violations, built | Primary defect classification |
| `status` | Open, Complete, Pending, Dismissed, Closed | Donut, priority heatmap, Sankey, funnel | violations, dismissals, ramp_progress, permits | Work item state machine |
| `inspector_id` | A001–Z999 (example) | Inspector performance boxplot, network (as node) | inspection | Quality check (detection bias) |
| `contractor_id` | String ID | Network node, clustermap row | built, street_construction_inspections | Vendor performance |
| `date` | YYYY-MM-DD | Trend line, CUSUM, changepoint, stream graph, temporal heatmap | All datasets with temporal data | Temporal anchor for all time-series |

### Common Numeric Measures (Metric Linkages)

| Metric | Units | Appears In Charts | Datasets | Notes |
|--------|-------|-------------------|----------|-------|
| `violation_count` | count | Bar, heatmap, parallel coords, SPLOM, bubble, funnel | inspection, violations | Primary outcome (volume) |
| `repair_cost` | USD | Bubble, SPLOM, parallel coords, radar (if metric) | inspection, built | Financial impact |
| `condition_score` | 0–100 | SPLOM, parallel coords, radar, ridge, violin | inspection | Quality metric (inverse of violations) |
| `age_years` | years | SPLOM, parallel coords, bubble | inspection | Predictive feature |
| `completion_rate` | 0–1 or 0–100% | Metric gauge, radar, status donut | ramp_progress, capital_blocks | Progress tracking |
| `inspections` | count | Parallel coords, SPLOM (if in dataset) | inspection | Volume of inspection effort |
| `dismissals` | count | Funnel, status donut | dismissals | Rejection rate |

---

## 🎯 Analysis Patterns & Hypothesis-Testing Workflows

### Pattern 1: Identify Problem Cases (High Violations, High Cost)

**Charts in Sequence:**
1. **Parallel Coordinates** — Brush `violation_count` [8–20], `repair_cost` [5000–∞], `condition_score` [0–40]
2. **Clustermap** — Show which blocks cluster with these outliers
3. **Bubble Chart** — Overlay to confirm (y=repair_cost, x=condition_score, size=violation_count, color=borough)
4. **Sankey** — From borough → violation_type to understand defect composition

**Output:** List of blocks to prioritize for intervention

---

### Pattern 2: Process Control & Shift Detection

**Charts in Sequence:**
1. **CUSUM Control Chart** — Detect when daily violation counts shift significantly
2. **Changepoint Overlay** — By-borough breakdown; identify which boroughs shift when
3. **Trend Line** — Overlay long-term trend to separate shift from noise
4. **Funnel** — If shift coincides with policy change, track downstream pipeline effects (dismissals, repairs)

**Output:** Confirmation of policy impact (e.g., "Protected streets reduced violations on 2026-05-15 by 12%")

---

### Pattern 3: Comparative Borough Analysis

**Charts in Sequence:**
1. **Borough Bar Chart** — Raw counts
2. **Radar Chart** — Multi-metric normalization (all metrics 0–1 scale)
3. **Ridge Plot** — Distribution shapes (skewness, outliers)
4. **Moran's I Scatter** — Geographic clustering (do high-violation boroughs neighbor each other?)

**Output:** Borough typology (which boroughs are similar, which unique)

---

### Pattern 4: Root-Cause Investigation (Drilling Down)

**Charts in Sequence:**
1. **Priority Heatmap** — Show borough × status (e.g., MN has high open violations)
2. **Sankey: Borough → Violation Type** — Drill into MN; see if one defect type dominates
3. **Clustermap: Material Type × Metrics** — Is concrete worse than brick in MN?
4. **Funnel: By Material + Borough** — What's the dismissal rate for MN concrete trip hazards?

**Output:** Root cause identified (e.g., "MN concrete trip hazards have 8% dismissal rate vs 35% for brick")

---

### Pattern 5: Spatial Hotspot Identification

**Charts in Sequence:**
1. **Hex-Bin Density Map** — Visual hotspot location
2. **Bubble Chart** — Community board level (size=violation_count, color=condition_score)
3. **Stream Graph: By Date** — Are hotspots persistent or transient?
4. **Network: Inspector → Block** — Which inspectors cover hotspot blocks?

**Output:** Geospatial investment recommendation (e.g., "CB 207 (Manhattan-Upper West) needs 20 additional inspections/month")

---

### Pattern 6: Quality Assessment (Bayesian + HDI)

**Charts in Sequence:**
1. **Bayesian Posterior Strip** — 89% credible intervals for borough effect on condition
2. **HDI-Annotated Violin** — Posterior predictive for each borough
3. **Ridge Plot** — Bootstrap resampling distribution (if using frequentist CI)

**Output:** Credible intervals: "Borough effect for BK is [-12%, 8%] at 89% certainty" (overlaps zero → not significant)

---

## 🔄 Common Data Prep Pipelines for Charts

### For Comparative Charts (Borough Bar, Radar, Heatmap)
```python
# Aggregate to borough level
agg_df = df.groupby('borough').agg({
    'violation_count': 'sum',
    'repair_cost': 'mean',
    'condition_score': 'mean',
    'age_years': 'mean',
    'dismissals': 'count',
}).reset_index()

# Use agg_df → bar_chart, radar_chart, priority_heatmap
```

### For Temporal Charts (Trend, CUSUM, Changepoint)
```python
# Group by date, aggregate metrics
ts = df.groupby('date').agg({
    'violation_count': 'sum',
}).sort_index()

# Use ts.sort_index() → trend_line, cusum_control_chart, changepoint_overlay
```

### For Relational Charts (Sankey, Chord, Network)
```python
# Build contingency or edge list
import pandas as pd
flow = df.groupby(['source_col', 'target_col']).size().reset_index(name='value')

# Use flow → sankey_flow, chord_diagram, force_network
```

### For Hierarchical Charts (Treemap, D3 Treemap, Clustermap)
```python
# For treemap: nested hierarchy
hierarchy = {
    'name': 'root',
    'children': [
        {'name': 'MN', 'children': [
            {'name': 'CB101', 'value': 340},
            ...
        ]},
        ...
    ]
}

# Use hierarchy → treemap_d3, clustermap (pivot-based)
```

---

## 📊 Metadata Table (CSV-Ready Export)

For reference, here's a condensed version suitable for CSV/Excel export:

```
chart_name,module,function,required_cols,optional_cols,data_types,analysis_type,shared_vars,hypothesis_example,dependencies
Borough Bar Chart,viz/plotly.py,borough_bar_chart,borough;metric_col,date;group_col,str;numeric,Comparative,borough,Which borough has highest violations?,plotly.express
Parallel Coordinates,viz/advanced_multidim.py,parallel_coordinates,numeric_cols (2+),color_col,numeric;categorical,Multi-variate,any numeric pair,What profiles have high violations+high cost+low score?,plotly.graph_objects
CUSUM Control Chart,viz/statistical_viz.py,cusum_control_chart,time_series,k;h;annotate_changepoint,numeric,Process Control,date,Has violation count shifted level?,scipy.stats
Hex-Bin Density Map,viz/d3_components.py,hex_binmap,latitude;longitude,,float,Spatial Density,lat/lon,Where are violation hotspots?,d3-hexbin CDN
Sankey Flow,viz/advanced_multidim.py,sankey_flow,source_col;target_col,value_col,str;numeric,Relational Flow,borough;violation_type,Which borough-to-violation flows dominate?,plotly.graph_objects
```

---

## 🧮 Example ERD (Entity-Relationship Diagram)

```
┌─────────────────┐
│   INSPECTION    │
├─────────────────┤
│ objectid (PK)   │◄──┐
│ borough*        │   │ 1:N
│ community_board*│   │
│ material_type   │   ├─── VIOLATIONS
│ condition_score │   │   ├─────────────────┐
│ age_years       │   │   │ objectid (PK)   │
│ inspection_id   │   │   │ inspection_id*  │───→ INSPECTION (FK)
│ date*           │   │   │ violation_type* │
│ inspector_id    │   │   │ status*         │
└─────────────────┘   │   │ date*           │
         │            │   └─────────────────┘
         │            │
         └────────────┘

┌──────────────────┐      ┌──────────────┐
│   BUILT (Repairs)│      │  DISMISSALS  │
├──────────────────┤      ├──────────────┤
│ objectid (PK)    │      │ objectid (PK)│
│ inspection_id*   │──────│ violation_id*│
│ repair_cost      │      │ reason       │
│ contractor_id    │      │ date*        │
│ date*            │      └──────────────┘
│ status*          │
└──────────────────┘

       * = Dimension column (appears in multiple charts)
     (PK) = Primary key
      (FK) = Foreign key
```

---

## 🎬 Quick Start: Which Chart for Your Question?

| Research Question | Start With | Then Compare With |
|---|---|---|
| "Which borough has the most violations?" | Borough Bar | Radar (multi-metric view) |
| "Are violations declining over time?" | Trend Line | CUSUM (formal shift test) |
| "What drives high repair costs?" | SPLOM | Parallel Coords (multivariable filtering) |
| "Which blocks are problematic?" | Bubble Chart | Hex-Bin Density (geographic) |
| "How consistent are inspectors?" | Boxplot | Bayesian Posterior (credible intervals) |
| "Is there spatial clustering?" | Moran's I | Hex-Bin + Network (geography + flow) |
| "What's the dismissal rate by type?" | Funnel | Sankey (borough × type breakdown) |
| "Which borough differs from others?" | Radar | Clustermap (hierarchical grouping) |

---

**Generated:** 2026-06-12  
**Version:** v0.5.0 (Expanded viz library: 65+ charts)  
**Next Steps:**  
- Populate this registry with live dataset column names (run schema-mapper skill)
- Build auto-generated visualization suggestions based on DataFrame shape
- Create a dashboard "chart finder" UI (input columns → recommend visualizations)
