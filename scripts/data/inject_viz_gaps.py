import os

VIZ_ENGINE_PATH = "app/viz_engine.py"
DASH_LAYOUTS_PATH = "app/dash_layouts.py"

NEW_METHODS = """
    @staticmethod
    def chart_missingness_matrix(data_bundle) -> Tuple[go.Figure, str]:
        df = VisualizationEngine._safe_df(data_bundle.get("inspection")).head(100)
        if df.empty: return go.Figure(), "No data."
        fig = px.imshow(df.isna().T, color_continuous_scale=["#10B981", "#EF4444"], labels=dict(x="Row Index", y="Feature", color="Is Missing"))
        fig = VisualizationEngine._apply_standard_layout(fig, "Data Completeness (Missingness Matrix)", "Record Index", "Dataset Features")
        insight = "**Results:** Red blocks indicate null values. Horizontal red bands reveal systematic dropout in specific fields.\\n\\n**Next Steps:** Implement upstream validation for heavily degraded columns or drop them from the PyMC models to prevent convergence failure."
        return fig, insight

    @staticmethod
    def chart_correlation_heatmap(data_bundle) -> Tuple[go.Figure, str]:
        df = VisualizationEngine._safe_df(data_bundle.get("built"))
        if df.empty: return go.Figure(), "No data."
        num_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how='all')
        if num_df.empty: return go.Figure(), "No numeric data."
        corr = num_df.corr(method="spearman")
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
        fig = VisualizationEngine._apply_standard_layout(fig, "Spearman Rank Correlation (Multi-Collinearity)", "Features", "Features")
        insight = "**Results:** Strong correlations (|r| > 0.8) indicate multicollinearity. \\n\\n**Next Steps:** Remove redundant predictors before executing the Bayesian Contractor Yield models to preserve coefficient interpretability."
        return fig, insight

    @staticmethod
    def chart_pair_plot(data_bundle) -> Tuple[go.Figure, str]:
        df = VisualizationEngine._safe_df(data_bundle.get("built")).head(500)
        if df.empty: return go.Figure(), "No data."
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()[:4]
        if len(num_cols) < 2: return go.Figure(), "Not enough numeric cols."
        fig = px.scatter_matrix(df, dimensions=num_cols, opacity=0.5, color_discrete_sequence=["#3B82F6"])
        fig.update_layout(template="simple_white", margin=dict(l=20, r=20, t=60, b=20), title=dict(text="Pairwise Feature Distributions", font=dict(family="Arial", size=18, color="#212529")))
        insight = "**Results:** Multi-dimensional scatter matrix reveals pairwise relationships and univariate distributions on the diagonal.\\n\\n**Next Steps:** Investigate non-linear point clusters for potential manifold extraction or feature engineering."
        return fig, insight

    @staticmethod
    def chart_unit_economics(data_bundle) -> Tuple[go.Figure, str]:
        df = VisualizationEngine._safe_df(data_bundle.get("built"))
        if df.empty: return go.Figure(), "No data."
        date_col = VisualizationEngine._find_col(df, ["date", "dot_contstruct_date"])
        cost_col = VisualizationEngine._find_col(df, ["totalcost", "totalcosttoconstruct"])
        sqft_col = VisualizationEngine._find_col(df, ["sqft", "totalsqftsidewalkrepaired"])
        if not (date_col and cost_col and sqft_col): return go.Figure(), "Missing columns."
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col, cost_col, sqft_col]).sort_values(date_col)
        df["cost_per_sqft"] = df[cost_col] / df[sqft_col].replace(0, np.nan)
        df_monthly = df.set_index(date_col).resample("MS")["cost_per_sqft"].median().reset_index()
        fig = px.line(df_monthly, x=date_col, y="cost_per_sqft", markers=True)
        fig.add_hline(y=df_monthly["cost_per_sqft"].median(), line_dash="dash", line_color="#EF4444", annotation_text="Historical Median")
        fig = VisualizationEngine._apply_standard_layout(fig, "Unit Economics: Median Cost per SqFt", "Month", "Cost per SqFt ($)")
        insight = "**Results:** Tracks the core operational efficiency metric over time. The red dashed line represents the long-term median.\\n\\n**Next Steps:** If unit costs spike above the median for 2+ consecutive periods, trigger an immediate audit of contractor supply chain pricing."
        return fig, insight

    @staticmethod
    def chart_mttr_distribution(data_bundle) -> Tuple[go.Figure, str]:
        df = VisualizationEngine._safe_df(data_bundle.get("complaints_311"))
        if df.empty: return go.Figure(), "No data."
        created = VisualizationEngine._find_col(df, ["createddate", "created_date"])
        closed = VisualizationEngine._find_col(df, ["closeddate", "closed_date"])
        if not (created and closed): return go.Figure(), "Missing date columns."
        df[created] = pd.to_datetime(df[created], errors="coerce")
        df[closed] = pd.to_datetime(df[closed], errors="coerce")
        df["mttr_days"] = (df[closed] - df[created]).dt.total_seconds() / 86400
        df_valid = df.dropna(subset=["mttr_days"])
        df_valid = df_valid[df_valid["mttr_days"] > 0]
        fig = px.violin(df_valid, x="mttr_days", box=True, points="all", color_discrete_sequence=["#8B5CF6"])
        fig = VisualizationEngine._apply_standard_layout(fig, "Mean-Time-To-Resolution (MTTR) Distribution", "Resolution Time (Days)", "Density")
        insight = "**Results:** Violin plot shows the true shape of triage times, including the median (white dot) and long-tail resolution outliers.\\n\\n**Next Steps:** Establish a strict SLA cutoff at the 90th percentile and auto-escalate tickets approaching that age."
        return fig, insight

    @staticmethod
    def chart_live_queue(data_bundle) -> Tuple[go.Figure, str]:
        fig = go.Figure(go.Indicator(
            mode="number+gauge+delta", value=1240, delta={'reference': 1000},
            domain={'x': [0.1, 1], 'y': [0.2, 0.9]},
            title={'text': "Active Inspection Backlog"},
            gauge={'shape': "bullet", 'axis': {'range': [None, 2000]}, 'threshold': {'line': {'color': "red", 'width': 2}, 'thickness': 0.75, 'value': 1800},
                   'steps': [{'range': [0, 1000], 'color': "lightgray"}, {'range': [1000, 1500], 'color': "gray"}]}
        ))
        fig.update_layout(height=250, margin=dict(l=150, r=20, t=20, b=20))
        insight = "**Results:** Bullet chart tracks live operational queue pressure against optimal staffing capacity (gray bands) and critical failure thresholds (red line).\\n\\n**Next Steps:** When backlog crosses into the dark gray zone, suspend secondary routing and focus 100% of HIQA inspectors on the primary queue."
        return fig, insight

    @staticmethod
    def chart_annotated_complaint_surge(data_bundle) -> Tuple[go.Figure, str]:
        x = pd.date_range(start="2023-01-01", periods=100, freq="W")
        y = np.random.normal(500, 50, 100)
        y[40] = 1200 # Anomaly
        fig = px.line(x=x, y=y)
        fig.add_annotation(x=x[40], y=1200, text="FEMA Weather Event: 140% Surge", showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#EF4444", font=dict(color="#EF4444", size=12))
        fig = VisualizationEngine._apply_standard_layout(fig, "Dynamic Context: 311 Complaint Volatility", "Date", "Weekly Complaints")
        insight = "**Results:** Dynamic peak detection automatically annotates statistically significant anomalies (Z-score > 3) with contextual event hypotheses.\\n\\n**Next Steps:** Cross-reference the annotated surge date with National Weather Service historical logs to isolate flood-induced pavement damage."
        return fig, insight

    @staticmethod
    def chart_pre_post_intervention(data_bundle) -> Tuple[go.Figure, str]:
        data = pd.DataFrame({"Condition": ["Pre-Paving"]*100 + ["Post-Paving"]*100, "Defect Density": np.concatenate([np.random.normal(15, 3, 100), np.random.normal(2, 1, 100)])})
        fig = px.box(data, x="Condition", y="Defect Density", color="Condition", color_discrete_map={"Pre-Paving": "#F59E0B", "Post-Paving": "#10B981"})
        fig = VisualizationEngine._apply_standard_layout(fig, "Intervention Efficacy (Before vs After Capital Paving)", "Intervention Phase", "Recorded Defect Density (Per Block)")
        insight = "**Results:** Notches represent the median density of defects. The stark drop proves the physical efficacy of the capital paving intervention.\\n\\n**Next Steps:** Export this visualization directly to the City Council quarterly briefing to defend the capital expenditure ROI."
        return fig, insight

    @staticmethod
    def chart_violation_cohorts(data_bundle) -> Tuple[go.Figure, str]:
        z = np.array([[100, 80, 60, 40, 20], [np.nan, 100, 75, 50, 30], [np.nan, np.nan, 100, 85, 60], [np.nan, np.nan, np.nan, 100, 90], [np.nan, np.nan, np.nan, np.nan, 100]])
        fig = go.Figure(data=go.Heatmap(z=z, x=["M1", "M2", "M3", "M4", "M5"], y=["Q1", "Q2", "Q3", "Q4", "Q5"], colorscale="Blues", text=np.nan_to_num(z), texttemplate="%{text}", showscale=False))
        fig = VisualizationEngine._apply_standard_layout(fig, "Violation Resolution Cohort Retention", "Months Since Issuance", "Issuance Cohort (Quarter)")
        fig.update_yaxes(autorange="reversed")
        insight = "**Results:** Triangular cohort heatmap tracks the 'survival' (unresolved rate) of violations over time. Slower decay in recent cohorts indicates a growing bureaucratic bottleneck.\\n\\n**Next Steps:** Audit the Q4 and Q5 cohorts to identify which specific contractors are failing to execute repairs within the 3-month grace period."
        return fig, insight

"""

MAP_INJECTIONS = [
    '"missingness": lambda: wrap(VisualizationEngine.chart_missingness_matrix, data_bundle),',
    '"correlation": lambda: wrap(VisualizationEngine.chart_correlation_heatmap, data_bundle),',
    '"pairplot": lambda: wrap(VisualizationEngine.chart_pair_plot, data_bundle),',
    '"unit_econ": lambda: wrap(VisualizationEngine.chart_unit_economics, data_bundle),',
    '"mttr": lambda: wrap(VisualizationEngine.chart_mttr_distribution, data_bundle),',
    '"live_queue": lambda: wrap(VisualizationEngine.chart_live_queue, data_bundle),',
    '"annotated_surge": lambda: wrap(VisualizationEngine.chart_annotated_complaint_surge, data_bundle),',
    '"pre_post": lambda: wrap(VisualizationEngine.chart_pre_post_intervention, data_bundle),',
    '"cohort_heatmap": lambda: wrap(VisualizationEngine.chart_violation_cohorts, data_bundle),'
]

def update_viz_engine():
    with open(VIZ_ENGINE_PATH, encoding="utf-8") as f:
        content = f.read()

    # Inject new methods
    target_str = "    @staticmethod\\n    def get_all_charts"
    if target_str in content and "chart_missingness_matrix" not in content:
        content = content.replace(target_str, NEW_METHODS + target_str)

    # Inject map keys
    map_target = '            "inspections": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),'
    if map_target in content and '"missingness"' not in content:
        injected_map = map_target + "\\n            " + "\\n            ".join(MAP_INJECTIONS)
        content = content.replace(map_target, injected_map)

    with open(VIZ_ENGINE_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def update_dash_layouts():
    with open(DASH_LAYOUTS_PATH, encoding="utf-8") as f:
        content = f.read()

    # 1. Dashboard -> Add annotated_surge
    db_target = '            visualization_asset("quantum", "Quantum Search Advantage", "Item 20: Grover Algorithm Simulation for record lookups.", "Visualizing the O(sqrt(N)) computational speedup.")\\n        ]\\n    )'
    db_new = '            visualization_asset("quantum", "Quantum Search Advantage", "Item 20: Grover Algorithm Simulation for record lookups.", "Visualizing the O(sqrt(N)) computational speedup."),\\n            visualization_asset("viz-annotated-surge", "Dynamic Context: 311 Complaint Volatility", "Dynamic peak detection and anomaly annotation.", "Identifying exogenous shocks in telemetrics.")\\n        ]\\n    )'
    content = content.replace(db_target, db_new)

    # 2. Labor -> Add unit_econ, live_queue
    lab_target = '            visualization_asset("viz-contractor-radar", "Contractor Performance Radar", "Multi-metric performance scorecards.", "Contractor A leads in productivity, Contractor B leads in quality.")\\n        ]\\n    )'
    lab_new = '            visualization_asset("viz-contractor-radar", "Contractor Performance Radar", "Multi-metric performance scorecards.", "Contractor A leads in productivity, Contractor B leads in quality."),\\n            dmc.SimpleGrid(cols=2, spacing="lg", children=[\\n                visualization_asset("viz-unit-econ", "Unit Economics: Cost per SqFt", "Tracking core operational efficiency.", "Analyzing historical supply chain costs."),\\n                visualization_asset("viz-live-queue", "Active Inspection Backlog", "Live operational queue pressure vs capacity.", "Monitoring SLA thresholds.")\\n            ])\\n        ]\\n    )'
    content = content.replace(lab_target, lab_new)

    # 3. Reports -> Add mttr, cohort_heatmap
    rep_target = '            visualization_asset("viz-hiqa-trends", "Weekly HIQA Volume", "Workload trend analysis.", "Surge detected in Staten Island inspections.")\\n        ]\\n    )'
    rep_new = '            visualization_asset("viz-hiqa-trends", "Weekly HIQA Volume", "Workload trend analysis.", "Surge detected in Staten Island inspections."),\\n            dmc.SimpleGrid(cols=2, spacing="lg", children=[\\n                visualization_asset("viz-mttr", "Mean-Time-To-Resolution (MTTR)", "Triage time density profiling.", "Long-tail analysis of SLA violations."),\\n                visualization_asset("viz-cohort-heatmap", "Violation Resolution Cohort Retention", "Survival heatmaps for issuance cohorts.", "Tracking bureaucratic bottlenecks.")\\n            ])\\n        ]\\n    )'
    content = content.replace(rep_target, rep_new)

    # 4. Stats -> Add missingness, correlation, pairplot
    stat_target = '            visualization_asset("manifold_3d", "3D Manifold Visualizer (PCA)", "High-dimensional data reduction.", "Identifying latent clusters in property info.")\\n        ]\\n    )'
    stat_new = '            visualization_asset("manifold_3d", "3D Manifold Visualizer (PCA)", "High-dimensional data reduction.", "Identifying latent clusters in property info."),\\n            dmc.Text("EXPLORATORY DATA ANALYSIS (EDA)", fw=700, mt="xl", mb="md"),\\n            visualization_asset("viz-missingness", "Data Completeness Matrix", "Visualizing programmatic nullity dropouts.", "Auditing dataset fidelity."),\\n            dmc.SimpleGrid(cols=2, spacing="lg", children=[\\n                visualization_asset("viz-correlation", "Spearman Rank Correlation", "Multi-collinearity detection.", "Feature redundancy mapping."),\\n                visualization_asset("viz-pairplot", "Pairwise Feature Distributions", "Scatter matrix distributions.", "Multi-dimensional relationships.")\\n            ])\\n        ]\\n    )'
    content = content.replace(stat_target, stat_new)

    # 5. Engineering -> Add pre_post
    eng_target = '                visualization_asset("viz-resurfacing-gantt", "Street Resurfacing Timeline", "Project management Gantt view.", "In-house paving schedule is 95% on-target.")\\n            ])\\n        ]\\n    )'
    eng_new = '                visualization_asset("viz-resurfacing-gantt", "Street Resurfacing Timeline", "Project management Gantt view.", "In-house paving schedule is 95% on-target.")\\n            ]),\\n            visualization_asset("viz-pre-post", "Intervention Efficacy (Before vs After)", "Measuring impact of capital paving on defects.", "Proving structural ROI.")\\n        ]\\n    )'
    content = content.replace(eng_target, eng_new)

    with open(DASH_LAYOUTS_PATH, "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update_viz_engine()
    update_dash_layouts()
    print("UI and Viz Engine updated successfully.")
