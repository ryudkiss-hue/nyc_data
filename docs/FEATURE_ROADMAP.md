# NYC DOT Advanced Analytics Roadmap
**High-Impact Visualization & Analysis Capabilities**

---

## Executive Summary

This roadmap identifies 6 strategic analysis capabilities that address critical gaps in sidewalk inspection, ramp accessibility, and construction tracking. Each method is evaluated on **impact** (organizational value) and **effort** (implementation complexity), with detailed specifications for the **Pareto zone** (high impact / medium effort).

**Key Constraint:** All methods leverage existing dependencies (scipy, statsmodels, scikit-learn, plotly, folium) already in `pyproject.toml`.

---

## 1. CLUSTERING DIAGNOSTICS ENGINE
**Problem:** Current system lacks cluster quality metrics, forcing manual assessment of sidewalk segments or ramp groupings. No visibility into whether K-means divisions are meaningful or arbitrary.

**Data Source:** Inspection records (violations by block/segment), Ramp Progress data, Street permits (cluster contractors by performance)

**Libraries:** scikit-learn (KMeans, silhouette_score, davies_bouldin_score, calinski_harabasz_score), plotly (interactive elbow curve)

**Visualization Output:**
- Elbow curve with knee detection (plotly line chart + annotation)
- Silhouette plot (horizontal bar chart, colored by cluster)
- Davies-Bouldin Index heatmap (cluster cohesion matrix)
- Cluster composition scatter (PCA/UMAP 2D projection with cluster labels)

**Effort:** 6-8 hours
- Implement elbow/knee detection algorithm (1-2h)
- Build silhouette visualization (1h)
- Quality metric computation & heatmap (2h)
- Integration with existing viz pipeline (2-3h)

**Pareto Fit:** HIGH - Sidewalk managers can now validate segment clustering before resource allocation

---

## 2. INCREMENTAL CONFORMAL PREDICTION ENGINE
**Problem:** Current forecasts lack uncertainty quantification. Inspector wants 90% confidence interval on violation resolution timeline, not just point estimates.

**Data Source:** Violations (CERTI_DATE, VDismissDate, Violation ID) + inspection history

**Libraries:** mapie (MAPIE - Multi-output Adaptive Prediction Interval Estimation), scipy.stats

**Visualization Output:**
- Time series with prediction bands (plotly ribbon chart: mean + 80%, 95% confidence zones)
- Prediction interval width over time (residuals-based calibration plot)
- Coverage diagnostic: how often actual values fall within predicted bands

**Effort:** 8-10 hours
- MAPIE regression wrapper with data prep (2-3h)
- Non-conformity scoring & calibration (2h)
- Plotly ribbon chart + uncertainty visualization (2-3h)
- Backtesting framework (validation metrics) (1-2h)

**Pareto Fit:** HIGH - Direct operational impact on SLA enforcement & budget forecasting

---

## 3. GEOSPATIAL HEATMAP WITH TEMPORAL ANIMATION
**Problem:** Dashboard shows current snapshot; missing trend visualization across 12-24 months. Cannot answer "where is deterioration accelerating?"

**Data Source:** Inspection records (BBLID + location) + temporal dimension (inspectiondate), Violations over time

**Libraries:** folium (base maps + circle/polygon layers), plotly (animated choropleth), geopandas (if available for polygon simplification)

**Visualization Output:**
- Animated borough heatmap (month-over-month violation density by community board)
- "Hot block" timeline slider (show top 10 deteriorating blocks across 24 months)
- Comparison view: violations/km² by month (small multiples of borough maps)

**Effort:** 10-14 hours
- Data aggregation by CB/block + temporal bucketing (2-3h)
- Folium heatmap layer + markers (2-3h)
- Plotly animated choropleth (borough-level aggregates) (2-3h)
- Timeline slider interaction & caching for performance (2-3h)
- Edge cases: sparse months, data quality filtering (1-2h)

**Pareto Fit:** HIGH - Visual storytelling powerful for council members, enables data-driven prioritization

---

## 4. ACCESSIBILITY GAP ANALYSIS (Propensity Score Matching)
**Problem:** Ramp installation disparities between high-need blocks unknown. Hard to separate "where are ramps missing" from "are we installing equitably?"

**Data Source:** Ramp Locations (installed ramps), Ramp Complaints (demand signal), MapPLUTO (infrastructure baseline), Pedestrian Demand (synthetic demand if available)

**Libraries:** statsmodels (logit for propensity scores), scipy (covariate balance diagnostics)

**Visualization Output:**
- Love plot: absolute standardized mean difference before/after matching (forest-style plot)
- Ramp gap map: predicted need vs. installed (folium choropleth by community board)
- Equity metric dashboard: disparity index by income quartile (if demographics available)

**Effort:** 12-16 hours
- Propensity score model (logit) + data harmonization (3-4h)
- Matching algorithm (nearest neighbor + caliper) (2-3h)
- Balance diagnostics & visualization (2h)
- Gap prediction & mapping (2-3h)
- Fairness metrics computation (1-2h)

**Pareto Fit:** MEDIUM - Policy-facing analysis, high impact if ADA compliance questions arise, but requires careful interpretation training

---

## 5. CONSTRUCTION PERMIT RISK SCORING (Bayesian Hierarchical Model)
**Problem:** Street construction permits vary wildly in execution risk. Current system has no quantified risk model; planners lack confidence intervals on permit delays.

**Data Source:** Street Construction Permits (permit dates, completion status), HIQA Inspections (inspection counts), Capital Projects (actual completion data)

**Libraries:** pymc (Bayesian generalized linear model), arviz (posterior diagnostics + visualization)

**Visualization Output:**
- Risk score distribution by permit type (plotly violin plot with posterior samples)
- Posterior predictive checks: "what's the credible range on permit delays?" (plotly ribbon)
- Contractor-level risk card (small multiples showing contractor-specific delays + uncertainty)

**Effort:** 14-18 hours
- Hierarchical Bayesian model (permit_type ~ contractor + borough + season) (4-5h)
- Data cleaning & covariate engineering (2-3h)
- Posterior predictive simulation & interval extraction (2-3h)
- Risk score aggregation & visualization (2-3h)
- Model validation (posterior predictive checks, convergence diagnostics) (2h)

**Pareto Fit:** MEDIUM - Deep analytical work, but needs subject matter expert buy-in to operationalize

---

## 6. SIDEWALK MATERIAL DEGRADATION PATHWAY ANALYSIS
**Problem:** Some sidewalk materials degrade faster. No visibility into material-specific failure curves. Budget allocation doesn't differentiate by material risk.

**Data Source:** Inspection records (inspectiondate, materialid) + Violations (violation patterns by material), Built dataset (material composition by block)

**Libraries:** statsmodels (survival analysis: Kaplan-Meier curves, Cox proportional hazards), scipy (log-rank tests)

**Visualization Output:**
- Kaplan-Meier survival curves by material (plotly line plot with confidence bands)
- Cumulative hazard by material (competing-risks style visualization)
- Material risk matrix: cost vs. failure rate scatter (bubble chart, size = installation volume)

**Effort:** 10-12 hours
- Time-to-event data preparation (censoring, time window definition) (2-3h)
- Kaplan-Meier estimator + confidence bands (1-2h)
- Cox PH regression (2-3h)
- Plotly visualization (K-M curves + hazard plot) (2h)
- Material economics overlay (1h)

**Pareto Fit:** HIGH - Direct to maintenance budgeting, medium complexity, reusable methodology

---

## PRIORITY MATRIX

```
                       EFFORT (hours)
                   Low (4-8) | Med (8-16) | High (16+)
                   ========================================
Impact    HIGH     |   1,6    |    2,3     |    4,5
          MEDIUM   |          |            |
          LOW      |          |            |
                   ========================================
```

**Quadrant Mapping:**
- **High Impact / Low-Medium Effort (Pareto Zone):**
  1. **Clustering Diagnostics** (6-8h, HIGH impact) → Enables segment-level resource allocation
  2. **Sidewalk Material Degradation** (10-12h, HIGH impact) → Direct budget optimization
  3. **Geospatial Heatmap Animation** (10-14h, HIGH impact) → Executive visibility + public-facing storytelling

- **High Impact / High Effort:**
  4. **Conformal Prediction** (8-10h, HIGH impact) → SLA enforcement, but narrower use case
  5. **Construction Risk Scoring** (14-18h, MEDIUM impact) → Useful, but requires domain expertise to operationalize

- **Medium Impact / High Effort:**
  - **Accessibility Gap Analysis** (12-16h, MEDIUM impact) → Policy-facing, valuable if equity is prioritized

---

## IMPLEMENTATION ROADMAP (Phase 1: Q3 2026)

### Sprint 1 (Weeks 1-2): Clustering Diagnostics
- **Deliverable:** Elbow curve + silhouette plot UI component
- **Integration:** `src/socrata_toolkit/analysis/clustering.py` + `src/socrata_toolkit/viz/clustering_viz.py`
- **Testing:** Unit tests on synthetic K-means data; integration test with violations dataset

### Sprint 2 (Weeks 3-4): Sidewalk Material Analysis
- **Deliverable:** Kaplan-Meier curves for top 4 materials
- **Integration:** `src/socrata_toolkit/analysis/survival.py` + `src/socrata_toolkit/viz/survival_viz.py`
- **Testing:** Validate censoring logic; compare against statsmodels reference

### Sprint 3 (Weeks 5-6): Geospatial Animation
- **Deliverable:** Animated borough heatmap (12-month slider)
- **Integration:** `src/socrata_toolkit/viz/temporal_geospatial.py` (new module)
- **Testing:** Performance benchmarks (data load + render time <2s)

---

## DETAILED SPECS: HIGH IMPACT / MEDIUM EFFORT METHODS

### Method 1: CLUSTERING DIAGNOSTICS ENGINE

**What Problem It Solves:**
Sidewalk segments (blocks or CB clusters) lack validated quality metrics. Planners don't know if their 5-cluster segmentation is optimal or if they should use 3 or 8. This leads to resource misallocation and poor targeting.

**Input Data Format:**
```
DataFrame with numeric features for clustering:
- violation_count (int, >0)
- repair_cost_estimate (float, dollars)
- population_density (float, per_km2)
- material_failure_rate (float, 0-1)
- inspection_frequency_mo (int, months since last)
- years_since_construction (float)

Optional grouping:
- community_board (str, for stratified analysis)
- borough (str, for comparison)
```

**Analysis Steps (Pseudocode):**

```python
# 1. ELBOW DETECTION
def compute_elbow(data, max_k=10):
    """
    Fit K-means for k=1..10, compute inertia.
    Use knee detection algorithm (kneedle) to find inflection point.
    """
    inertias = []
    silhouette_scores = []
    for k in range(1, max_k+1):
        model = KMeans(n_clusters=k, n_init=10, random_state=42)
        inertias.append(model.inertia_)
        silhouette_scores.append(silhouette_score(data, model.labels_))
    
    # Knee detection
    from kneedle import KneeLocator
    knee = KneeLocator(range(1, max_k+1), inertias, curve='convex', direction='decreasing')
    optimal_k = knee.knee or 3  # fallback
    
    return optimal_k, inertias, silhouette_scores

# 2. SILHOUETTE ANALYSIS
def compute_silhouette_full(data, optimal_k):
    """
    Fit final model, compute per-sample silhouette coefficients.
    Return cluster assignments + scores for visualization.
    """
    model = KMeans(n_clusters=optimal_k, n_init=10, random_state=42)
    labels = model.fit_predict(data)
    silhouette_vals = silhouette_samples(data, labels)
    
    return labels, silhouette_vals, model.cluster_centers_

# 3. QUALITY METRICS
def compute_cluster_quality(data, labels):
    """
    Davies-Bouldin Index (lower = better separation)
    Calinski-Harabasz Index (higher = better)
    Gap statistic (if reference distrib available)
    """
    db = davies_bouldin_score(data, labels)
    ch = calinski_harabasz_score(data, labels)
    
    return {"davies_bouldin": db, "calinski_harabasz": ch}

# 4. CLUSTER INTERPRETATION
def interpret_clusters(data_orig, labels, feature_names):
    """
    For each cluster: compute mean feature values.
    Highlight distinguishing features (z-score > 1).
    """
    cluster_profiles = pd.DataFrame()
    for k in range(labels.max() + 1):
        mask = labels == k
        profile = data_orig[mask].mean()
        cluster_profiles[f"Cluster_{k}"] = profile
    
    return cluster_profiles
```

**Output Data Format:**
```json
{
  "optimal_k": 5,
  "elbow_inertias": [1200, 800, 450, 280, 150, 120, 115, 113, 112, 111],
  "silhouette_scores": [0.45, 0.52, 0.58, 0.61, 0.60, 0.55, 0.48, 0.42, 0.35, 0.28],
  "quality_metrics": {
    "davies_bouldin": 0.62,
    "calinski_harabasz": 245.3
  },
  "cluster_profiles": {
    "Cluster_0": {"violation_count": 12.5, "repair_cost": 4500, ...},
    "Cluster_1": {"violation_count": 3.2, "repair_cost": 1200, ...},
    ...
  },
  "cluster_assignments": [0, 2, 1, 0, 3, ...]  // per-row cluster ID
}
```

**Visualization Components:**

1. **Elbow Curve Card** (Plotly):
   - X-axis: k (2-10)
   - Y-axis: inertia (log scale recommended)
   - Vertical line at optimal_k
   - Tooltip shows elbow point + quality metrics at each k

2. **Silhouette Plot** (Plotly horizontal bars):
   - Y-axis: cluster labels (0, 1, 2, ...)
   - X-axis: silhouette coefficient (-1 to 1)
   - Color by cluster
   - Vertical line at mean silhouette score

3. **Quality Metrics Heatmap** (Plotly):
   - Rows: quality metrics (Davies-Bouldin, Calinski-Harabasz, silhouette mean)
   - Cols: k (2-10)
   - Cell color: metric value (normalized 0-1 or -1-1)
   - Hover shows exact values

4. **Cluster Profiles Table** (Dash DataTable):
   - Rows: features
   - Cols: clusters
   - Cell values: mean feature value
   - Conditional formatting (red = high, green = low)

**Edge Cases:**

1. **k=1 or k=n:** Silhouette undefined; skip silhouette plot, show warning
2. **Single-feature data:** PCA projection may be necessary for 2D visualization
3. **Sparse clusters:** Some clusters have <5 members; flag in tooltip
4. **High-dimensional data:** Auto-reduce via PCA to 10 dims before K-means if p>50
5. **Outliers:** Use robust_scaler (IQR-based) instead of StandardScaler if outliers detected (IQR < data range/4)

**Integration Points:**

```python
# In src/socrata_toolkit/analysis/clustering.py
from socrata_toolkit.analysis.clustering import (
    ElbowAnalysis,
    SilhouetteAnalyzer,
    ClusteringDiagnostics,
)

# In src/socrata_toolkit/viz/clustering_viz.py
from socrata_toolkit.viz.clustering_viz import (
    plot_elbow_curve,
    plot_silhouette,
    plot_quality_metrics_heatmap,
)

# In app (Dash callback)
def analyze_clusters(data_path, feature_cols, max_k):
    df = pd.read_parquet(data_path)
    diag = ClusteringDiagnostics(df[feature_cols])
    optimal_k, metrics = diag.diagnose(max_k=max_k)
    
    fig_elbow = plot_elbow_curve(metrics)
    fig_silhouette = plot_silhouette(data, diag.labels_, optimal_k)
    
    return {"optimal_k": optimal_k, "fig_elbow": fig_elbow, "fig_silhouette": fig_silhouette}
```

---

### Method 2: SIDEWALK MATERIAL DEGRADATION PATHWAY ANALYSIS

**What Problem It Solves:**
Some materials (e.g., concrete vs. asphalt) age differently. Without quantified degradation curves, budget allocation treats all materials equally. Goal: identify high-risk materials and prioritize preventive maintenance.

**Input Data Format:**
```
Time-to-event data:
DataFrame with columns:
- block_id (str, unique identifier)
- material_type (str, categorical: "concrete", "asphalt", "stone", "other")
- installation_date (datetime or int, year)
- first_violation_date (datetime or int, year, may be null → censored)
- last_inspection_date (datetime, observation end date)
- borough (str)
- installation_volume (int, count of installations of this material in block)
- surface_area_sqft (float, total area of material)

Derived (computed during preprocessing):
- time_to_event (float, days or months)
- event (bool, 1 if violation observed, 0 if censored)
```

**Analysis Steps (Pseudocode):**

```python
# 1. TIME-TO-EVENT DATA PREPARATION
def prepare_survival_data(inspections_df, violations_df, cutoff_date):
    """
    For each block-material pair:
    - Find installation_date from inspections (earliest record)
    - Find first_violation_date (earliest in violations)
    - If no violation by cutoff, mark as censored
    - Compute time_to_event in months
    """
    # Merge inspection + violation history
    df = inspections_df.merge(violations_df, on='BBLID', how='left')
    
    # Compute time-to-event
    df['time_in_months'] = (df['first_violation_date'] - df['installation_date']).dt.days / 30.44
    df['event'] = (~df['first_violation_date'].isna()).astype(int)
    
    # Censor observations with insufficient follow-up (<6 months)
    df.loc[df['time_in_months'] < 6, 'event'] = 0
    df['time_in_months'] = df['time_in_months'].clip(lower=6)
    
    return df[['material_type', 'time_in_months', 'event', 'borough', 'installation_volume']]

# 2. KAPLAN-MEIER SURVIVAL CURVES (BY MATERIAL)
def compute_km_curves(survival_df):
    """
    Stratify by material_type, compute KM estimator + 95% CI.
    Use lifelines library or manual computation.
    """
    from lifelines import KaplanMeierFitter
    
    kmf = KaplanMeierFitter()
    km_results = {}
    
    for material in survival_df['material_type'].unique():
        material_data = survival_df[survival_df['material_type'] == material]
        kmf.fit(material_data['time_in_months'], material_data['event'], label=material)
        
        km_results[material] = {
            'survival_function': kmf.survival_function_.values.flatten(),
            'confidence_interval': kmf.confidence_interval_survival_function_,
            'median_survival_time': kmf.median_survival_time_,
            'event_count': material_data['event'].sum(),
            'n_at_risk': len(material_data),
        }
    
    return km_results

# 3. LOG-RANK TEST (PAIRWISE MATERIAL COMPARISONS)
def compare_materials(survival_df):
    """
    Test null hypothesis: survival curves are equal across materials.
    Bonferroni-corrected alpha (n_comparisons = choose(n_materials, 2))
    """
    from lifelines.statistics import logrank_test
    
    materials = survival_df['material_type'].unique()
    n_comparisons = len(materials) * (len(materials) - 1) / 2
    alpha_corrected = 0.05 / n_comparisons
    
    results = {}
    for i, mat1 in enumerate(materials):
        for mat2 in materials[i+1:]:
            data1 = survival_df[survival_df['material_type'] == mat1]
            data2 = survival_df[survival_df['material_type'] == mat2]
            
            test = logrank_test(
                data1['time_in_months'],
                data2['time_in_months'],
                data1['event'],
                data2['event']
            )
            
            results[(mat1, mat2)] = {
                'test_statistic': test.test_statistic,
                'p_value': test.p_value,
                'significant': test.p_value < alpha_corrected,
            }
    
    return results

# 4. COX PROPORTIONAL HAZARDS REGRESSION (CONFOUNDING ADJUSTMENT)
def fit_cox_model(survival_df):
    """
    Model: log_hazard ~ material_type + borough + installation_volume
    Adjust for confounders (e.g., high-traffic areas → faster failure)
    Return hazard ratios + 95% CI
    """
    from lifelines import CoxPHFitter
    
    # One-hot encode material_type
    df_encoded = pd.get_dummies(survival_df, columns=['material_type'], drop_first=True)
    df_encoded['log_volume'] = np.log1p(df_encoded['installation_volume'])
    
    cph = CoxPHFitter()
    cph.fit(
        df_encoded[['time_in_months', 'event'] + [c for c in df_encoded.columns if 'material_type' in c or 'borough' in c or 'log_volume' in c]],
        duration_col='time_in_months',
        event_col='event'
    )
    
    return cph

# 5. CUMULATIVE HAZARD FUNCTION
def compute_cumulative_hazard(survival_df):
    """
    Nelson-Aalen cumulative hazard by material.
    Useful for comparing failure rates over time.
    """
    from lifelines import NelsonAalenFitter
    
    naf = NelsonAalenFitter()
    ch_results = {}
    
    for material in survival_df['material_type'].unique():
        material_data = survival_df[survival_df['material_type'] == material]
        naf.fit(material_data['time_in_months'], material_data['event'], label=material)
        ch_results[material] = naf.cumulative_hazard_
    
    return ch_results

# 6. COST-BENEFIT SUMMARY BY MATERIAL
def compute_material_economics(km_results, unit_costs, installation_volumes):
    """
    For each material:
    - Median survival time (years)
    - Installation cost per unit
    - Maintenance cost over 20-year horizon
    - ROI: (total_cost / median_lifespan)
    """
    economics = {}
    for material, km in km_results.items():
        median_years = km['median_survival_time'] / 12
        unit_cost = unit_costs.get(material, 100)
        volume = installation_volumes.get(material, 1000)
        
        total_install = volume * unit_cost
        annual_maintenance = (volume / median_years) * 200  # $200/repair
        20yr_cost = total_install + (annual_maintenance * 20)
        
        economics[material] = {
            'median_lifespan_years': median_years,
            'installation_cost': total_install,
            'annual_maintenance': annual_maintenance,
            '20yr_total_cost': 20yr_cost,
            'cost_per_year': 20yr_cost / 20,
        }
    
    return pd.DataFrame(economics).T
```

**Output Data Format:**
```json
{
  "km_curves": {
    "concrete": {
      "time_months": [0, 6, 12, 18, ...],
      "survival_prob": [1.0, 0.95, 0.88, 0.80, ...],
      "ci_lower": [1.0, 0.92, 0.84, 0.75, ...],
      "ci_upper": [1.0, 0.98, 0.92, 0.85, ...],
      "median_survival_months": 156,
      "n_at_risk": 1200,
      "n_events": 340
    },
    "asphalt": {...}
  },
  "log_rank_tests": {
    "concrete_vs_asphalt": {"p_value": 0.003, "significant": true},
    ...
  },
  "cox_hazard_ratios": {
    "asphalt": {"hr": 1.45, "ci_lower": 1.12, "ci_upper": 1.87},
    ...
  },
  "material_economics": {
    "concrete": {"median_lifespan_years": 13, "20yr_cost": 450000},
    "asphalt": {"median_lifespan_years": 9, "20yr_cost": 650000},
    ...
  }
}
```

**Visualization Components:**

1. **Kaplan-Meier Survival Curves** (Plotly line plot):
   - X-axis: time (months)
   - Y-axis: survival probability (0-1)
   - One line per material
   - Shaded confidence bands (95%)
   - Censoring marks on lines (small ticks)
   - Hover shows: time, survival %, n at risk, n events

2. **Cumulative Hazard Function** (Plotly line plot):
   - X-axis: time (months)
   - Y-axis: cumulative hazard (0 to max)
   - One line per material
   - Log scale on Y optional
   - Interpretation: steeper = faster failure rate

3. **Material Cost vs. Lifespan Scatter** (Plotly bubble chart):
   - X-axis: median lifespan (years)
   - Y-axis: 20-year total cost ($)
   - Bubble size: installation volume
   - Color: borough (if stratified)
   - Quadrant labels: "premium / long-lived", "cheap / short-lived", etc.

4. **Log-Rank Test Results Table** (Dash):
   - Rows: material pairs
   - Cols: test stat, p-value, significant?
   - Green = significant difference, Gray = no difference

**Edge Cases:**

1. **Few events per material:** If <30 events, use bootstrap confidence intervals (1000 resamples) instead of Greenwood formula
2. **Short follow-up time:** If median observation time <12 months, flag results as preliminary
3. **Installation date unknown:** Use inspection_date as proxy; note in metadata
4. **Multiple violations per block:** Use first violation only (competing risks model requires multi-state framework, out of scope)
5. **Extreme outliers:** Cap follow-up at 25 years; censor longer observations (right-censoring at 300 months)

**Integration Points:**

```python
# In src/socrata_toolkit/analysis/survival.py
from socrata_toolkit.analysis.survival import (
    SurvivalDataPrep,
    KaplanMeierAnalysis,
    CoxRegressionModel,
)

# In src/socrata_toolkit/viz/survival_viz.py
from socrata_toolkit.viz.survival_viz import (
    plot_km_curves,
    plot_cumulative_hazard,
    plot_material_economics,
)

# In app (Dash callback)
def analyze_material_degradation(violations_path, inspections_path):
    df_vio = pd.read_parquet(violations_path)
    df_ins = pd.read_parquet(inspections_path)
    
    prep = SurvivalDataPrep(df_ins, df_vio)
    surv_data = prep.prepare()
    
    km = KaplanMeierAnalysis(surv_data)
    cox = CoxRegressionModel(surv_data)
    
    fig_km = plot_km_curves(km.results)
    fig_econ = plot_material_economics(km.results)
    
    return {"fig_km": fig_km, "fig_econ": fig_econ, "cox_summary": cox.summary()}
```

---

### Method 3: GEOSPATIAL HEATMAP WITH TEMPORAL ANIMATION

**What Problem It Solves:**
Executive and community board members need to see "where is the problem getting worse?" Dashboard static snapshots don't show 12-month trends. Animated maps enable data-driven conversations about neighborhood prioritization and equity.

**Input Data Format:**
```
Temporal geospatial data:
DataFrame with columns:
- date (datetime or YYYY-MM string for bucketing)
- community_board (int, 200-299 for CB IDs)
- borough (str, "MANHATTAN", "BRONX", etc.)
- latitude (float, -74 to -73)
- longitude (float, 40 to 41)
- violation_count (int, violations in this CB-month)
- repair_cost (float, total cost)
- inspections (int, inspection count)

Derived (computed):
- violation_density (violations per km^2)
- year_month (str, YYYY-MM for aggregation)
```

**Analysis Steps (Pseudocode):**

```python
# 1. TEMPORAL BUCKETING & AGGREGATION
def bucket_temporal_data(df, period='month'):
    """
    Aggregate violations/inspections by community_board + time_period.
    Compute density metrics (per km^2).
    """
    df['date'] = pd.to_datetime(df['date'])
    df['year_month'] = df['date'].dt.to_period('M')
    
    # CB-level aggregation
    df_agg = df.groupby(['year_month', 'community_board', 'borough']).agg({
        'violation_count': 'sum',
        'repair_cost': 'sum',
        'inspections': 'sum',
        'latitude': 'mean',
        'longitude': 'mean',
    }).reset_index()
    
    # Compute CB area (NYC CB shapefiles ~ 10-20 km^2 typically)
    cb_areas = {201: 18, 202: 15, 203: 12, ...}  # CB ID -> area km^2
    df_agg['cb_area_km2'] = df_agg['community_board'].map(cb_areas)
    df_agg['violation_density'] = df_agg['violation_count'] / df_agg['cb_area_km2']
    
    return df_agg

# 2. TEMPORAL TREND DETECTION (OPTIONAL)
def compute_trend_per_cb(df_agg):
    """
    For each CB, fit linear trend to violation_density over time.
    Return slope + p-value (trend stat significant?).
    """
    from scipy.stats import linregress
    
    trends = {}
    for cb in df_agg['community_board'].unique():
        cb_data = df_agg[df_agg['community_board'] == cb].sort_values('year_month')
        
        if len(cb_data) < 3:
            trends[cb] = {'slope': 0, 'pval': 1.0}
            continue
        
        x = np.arange(len(cb_data))
        y = cb_data['violation_density'].values
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        trends[cb] = {
            'slope': slope,
            'pval': p_value,
            'direction': 'worsening' if slope > 0 else 'improving'
        }
    
    return trends

# 3. BOROUGH-LEVEL GEOSPATIAL PREPARATION
def prepare_geospatial_geojson(df_agg, shapefile_path):
    """
    Load CB boundaries (GeoJSON or shapefile).
    Join violation_density data.
    Return GeoDataFrame ready for choropleth.
    """
    import geopandas as gpd
    
    gdf = gpd.read_file(shapefile_path)  # CB boundaries
    df_agg['community_board'] = df_agg['community_board'].astype(int)
    gdf = gdf.merge(df_agg, left_on='CB_ID', right_on='community_board', how='left')
    
    # Ensure valid geometries
    gdf = gdf[gdf.geometry.is_valid]
    
    return gdf

# 4. MONTH-BY-MONTH HEATMAP GENERATION
def create_animated_heatmaps(df_agg, output_dir):
    """
    For each month in df_agg, create a borough choropleth.
    Return list of figures (one per month).
    """
    import plotly.express as px
    
    figures = {}
    months = sorted(df_agg['year_month'].unique())
    
    for month in months:
        month_data = df_agg[df_agg['year_month'] == month]
        
        # Create borough subplots (5 total)
        fig = make_subplots(
            rows=2, cols=3,
            subplot_titles=['Manhattan', 'Bronx', 'Brooklyn', 'Queens', 'Staten Island'],
            specs=[[{'type': 'geo'}, {'type': 'geo'}, {'type': 'geo'}],
                   [{'type': 'geo'}, {'type': 'geo'}, None]]
        )
        
        for idx, borough in enumerate(['MANHATTAN', 'BRONX', 'BROOKLYN', 'QUEENS', 'STATEN ISLAND']):
            row, col = (idx // 3) + 1, (idx % 3) + 1
            borough_data = month_data[month_data['borough'] == borough]
            
            # Add choropleth traces per borough
            fig.add_trace(
                go.Choropleth(
                    locations=borough_data['community_board'],
                    z=borough_data['violation_density'],
                    colorscale='Reds',
                    hovertemplate='<b>CB %{locations}</b><br>Violation Density: %{z:.2f}/km²<extra></extra>',
                ),
                row=row, col=col
            )
        
        fig.update_layout(
            title_text=f"Sidewalk Violation Density - {month}",
            height=600,
            showlegend=True,
        )
        
        figures[str(month)] = fig
    
    return figures

# 5. "HOT BLOCK" IDENTIFICATION
def identify_hot_blocks(df, window='month', top_k=10):
    """
    For each month, rank CBs by violation_density.
    Return top-k CBs per month for temporal tracking.
    """
    df_sorted = df.sort_values(['year_month', 'violation_density'], ascending=[True, False])
    
    hot_blocks = {}
    for month in df['year_month'].unique():
        month_data = df[df['year_month'] == month].head(top_k)
        hot_blocks[str(month)] = month_data[['community_board', 'violation_density', 'borough']].to_dict('records')
    
    return hot_blocks

# 6. COMPARISON VIEW: BEFORE VS. AFTER
def compute_month_over_month_change(df_agg):
    """
    Calculate % change in violation_density from month N-1 to N.
    Identify CBs with largest increases/decreases.
    """
    df_agg = df_agg.sort_values(['community_board', 'year_month'])
    df_agg['density_pct_change'] = df_agg.groupby('community_board')['violation_density'].pct_change() * 100
    
    return df_agg
```

**Output Data Format:**
```json
{
  "monthly_aggregates": [
    {
      "year_month": "2025-06",
      "community_board": 201,
      "borough": "MANHATTAN",
      "violation_count": 145,
      "violation_density": 8.06,
      "latitude": 40.715,
      "longitude": -73.980,
      "trend_slope": 0.32,
      "trend_pval": 0.041
    },
    ...
  ],
  "hot_blocks": {
    "2025-06": [
      {"community_board": 201, "violation_density": 12.5},
      {"community_board": 205, "violation_density": 9.8},
      ...
    ],
    "2025-07": [...]
  },
  "month_over_month_change": {
    "2025-06_to_2025-07": {
      "201": 15.3,  // % increase
      "205": -8.2,   // % decrease
      ...
    }
  }
}
```

**Visualization Components:**

1. **Animated Borough Choropleth** (Plotly animated choropleth or folium + slider):
   - Time slider (month-month navigation)
   - 5 subplots (one per borough)
   - Color scale: white → light red → dark red (violation density)
   - Hover shows: CB ID, violation count, density, trend
   - Play/pause button for auto-animation

2. **Top-10 Hot Blocks Timeline** (Plotly animated bar chart):
   - Y-axis: community board ID
   - X-axis: violation_density
   - Color: trend direction (red if worsening, green if improving)
   - Animation: month-by-month update
   - Tooltip: CB name, violation count, % change from prior month

3. **Month-over-Month Change Heatmap** (Plotly heatmap):
   - Rows: CBs (sorted by max change)
   - Cols: months (Jun 2025 → Jun 2026)
   - Cell color: % change (-50% → 0% → +50%)
   - Diverging colorscale (blue = improving, red = worsening)

4. **Density Distribution Violin Plot** (Plotly):
   - X-axis: borough
   - Y-axis: violation_density (all CBs in that borough)
   - One violin per month (animated or small multiples)
   - Shows median, quartiles, outliers per month

**Edge Cases:**

1. **Missing months for some CBs:** Treat as 0 violations (no data ≠ no violations); note in legend
2. **Small CB populations:** Flag CBs with <20 total inspections as "unreliable estimate"
3. **Sparse geospatial data:** If <3 CBs have lat/lon, fall back to static borough-level map
4. **Extreme outliers:** Cap violation_density at 95th percentile for color scale (prevents 1 outlier from washing out the map)
5. **Performance:** Pre-compute and cache all figures for quick month navigation; if >24 months, offer "quarterly aggregation" option

**Integration Points:**

```python
# In src/socrata_toolkit/viz/temporal_geospatial.py
from socrata_toolkit.viz.temporal_geospatial import (
    TemporalGeospatialDashboard,
    create_animated_choropleth,
    plot_hot_blocks_timeline,
)

# In app (Dash callbacks + layout)
from dash import dcc, html, Input, Output

app.layout = html.Div([
    dcc.Slider(
        id='month-slider',
        min=0,
        max=len(months)-1,
        step=1,
        marks={i: month for i, month in enumerate(months)},
    ),
    dcc.Graph(id='borough-choropleth'),
    dcc.Graph(id='hot-blocks-timeline'),
])

@app.callback(
    Output('borough-choropleth', 'figure'),
    Input('month-slider', 'value')
)
def update_choropleth(month_idx):
    month = months[month_idx]
    df_month = df_agg[df_agg['year_month'] == month]
    return create_animated_choropleth(df_month)
```

---

## DEPENDENCIES CHECK

All methods use libraries **already in `pyproject.toml`**:

```
✓ scipy (≥1.10.0) - stats, linregress, gaussian_kde
✓ scikit-learn (implied by mapie) - KMeans, silhouette_score, davies_bouldin_score
✓ statsmodels (in survival extras) - KaplanMeierFitter, CoxPHFitter, logrank_test
✓ plotly (≥5.0) - all viz components
✓ folium (≥0.14) - map tiles + markers
✓ geopandas (optional, geo extra) - shapefile handling
✓ pandas (≥2.0) - data manipulation
✓ numpy (≥1.24) - numeric computation
✓ mapie (≥0.8) - conformal prediction
✓ pymc (≥5.0) - Bayesian modeling (already in dependencies)
✓ arviz (≥0.16) - posterior visualization
```

**Note:** lifelines (Kaplan-Meier) **not in dependencies** → add to `[tool.poetry.dependencies]` or use statsmodels alternative.

---

## NEXT STEPS

1. **Validate data availability** for each method with product team (e.g., installation_date in Inspection dataset)
2. **Schedule Sprint Planning** for Phase 1 (Weeks 1-6)
3. **Assign ownership:** Frontend (viz components), Backend (analysis modules), QA (test harness)
4. **Define acceptance criteria** for each deliverable (e.g., "Elbow curve correctly identifies k=5 on synthetic test data")
5. **Plan dashboard integration** (Dash/Streamlit pages, caching strategy for performance)

---

## APPENDIX: COST-BENEFIT SUMMARY

| Method | Impact | Effort | ROI | Primary Use |
|--------|--------|--------|-----|-------------|
| Clustering Diagnostics | HIGH | 6-8h | 1.0 | Segment-level resource allocation |
| Sidewalk Material Analysis | HIGH | 10-12h | 1.2 | Maintenance budget optimization |
| Geospatial Animation | HIGH | 10-14h | 1.1 | Executive/community board storytelling |
| Conformal Prediction | HIGH | 8-10h | 0.9 | SLA enforcement (narrow audience) |
| Construction Risk Scoring | MEDIUM | 14-18h | 0.7 | Permit planning (subject to validation) |
| Accessibility Gap Analysis | MEDIUM | 12-16h | 0.6 | Policy/equity (domain expertise needed) |

**Recommendation:** Prioritize Methods 1, 2, 3 (Q3 2026) for **high ROI + medium effort**. Methods 4-6 are valuable but require stakeholder alignment before development.
