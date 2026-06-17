"""
Phase 1 Dash Callback Integration Examples

This module demonstrates how to integrate the 3 Phase 1 visualization methods
into the existing Dash application. Copy these patterns into app/callbacks/analytics.py
and app/dash_layouts.py as needed.

Author: Claude Code
Date: 2026-06-10
"""


import numpy as np
import pandas as pd
from dash import Input, Output, dcc, html

# Import analysis modules
from socrata_toolkit.analysis.clustering_diagnostics import ClusteringDiagnostics
from socrata_toolkit.analysis.material_analysis import MaterialDegradationAnalysis
from socrata_toolkit.viz.clustering_viz import (
    plot_cluster_profiles,
    plot_elbow_curve,
    plot_quality_metrics_heatmap,
    plot_silhouette,
)
from socrata_toolkit.viz.material_viz import (
    plot_cumulative_hazard,
    plot_km_curves,
    plot_log_rank_results,
    plot_material_economics,
)
from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

# ============================================================================
# LAYOUT EXAMPLES
# ============================================================================

def create_clustering_diagnostics_tab() -> html.Div:
    """Create Clustering Diagnostics tab layout."""
    return html.Div([
        html.H2("Clustering Diagnostics: Optimal Sidewalk Segmentation"),
        html.P(
            "Determine the optimal number of clusters (k) for sidewalk segments "
            "using elbow detection, silhouette analysis, and quality metrics."
        ),

        # Controls
        html.Div([
            html.Label("Select Features for Clustering:"),
            dcc.Dropdown(
                id="clustering-features-dropdown",
                options=[
                    {"label": "Violations + Cost + Density", "value": "default"},
                    {"label": "Violations Only", "value": "violations"},
                    {"label": "Custom Selection", "value": "custom"},
                ],
                value="default",
            ),
            html.Label("Max Clusters to Test:"),
            dcc.Slider(
                id="max-k-slider",
                min=4,
                max=15,
                step=1,
                value=8,
                marks={i: str(i) for i in range(4, 16)},
            ),
        ], style={"marginBottom": "20px"}),

        # Loading indicator
        dcc.Loading([
            # Visualizations
            html.Div([
                html.Div(
                    dcc.Graph(id="elbow-curve-graph"),
                    style={"width": "48%", "display": "inline-block", "marginRight": "2%"}
                ),
                html.Div(
                    dcc.Graph(id="silhouette-graph"),
                    style={"width": "48%", "display": "inline-block", "marginLeft": "2%"}
                ),
            ]),

            html.Div([
                dcc.Graph(id="quality-metrics-heatmap"),
            ]),

            html.Div([
                html.H3("Cluster Profiles (Mean Feature Values)"),
                dcc.Graph(id="cluster-profiles-table"),
            ]),

            # Summary stats
            html.Div([
                html.H3("Summary"),
                html.Div(id="clustering-summary", style={
                    "backgroundColor": "#f0f0f0",
                    "padding": "15px",
                    "borderRadius": "5px"
                }),
            ]),
        ], type="default"),
    ])

def create_material_degradation_tab() -> html.Div:
    """Create Material Degradation Analysis tab layout."""
    return html.Div([
        html.H2("Sidewalk Material Degradation: Kaplan-Meier Survival Analysis"),
        html.P(
            "Analyze failure curves by material type (concrete, asphalt, etc.) "
            "to quantify lifespan and optimize maintenance budgets."
        ),

        # Controls
        html.Div([
            html.Label("Select Borough:"),
            dcc.Dropdown(
                id="borough-filter",
                options=[
                    {"label": "All Boroughs", "value": "all"},
                    {"label": "Manhattan", "value": "MANHATTAN"},
                    {"label": "Brooklyn", "value": "BROOKLYN"},
                    {"label": "Queens", "value": "QUEENS"},
                    {"label": "Bronx", "value": "BRONX"},
                    {"label": "Staten Island", "value": "STATEN ISLAND"},
                ],
                value="all",
            ),
        ], style={"marginBottom": "20px"}),

        dcc.Loading([
            # KM Curves
            html.Div([
                html.H3("Kaplan-Meier Survival Curves"),
                dcc.Graph(id="km-curves-graph"),
                html.P(
                    "Shaded bands represent 95% confidence intervals. "
                    "Dashed lines indicate median survival time per material.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Cumulative Hazard
            html.Div([
                html.H3("Cumulative Hazard (Nelson-Aalen)"),
                dcc.Graph(id="cumulative-hazard-graph"),
                html.P(
                    "Steeper slopes indicate faster failure rates.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Economics
            html.Div([
                html.H3("Material Cost-Benefit Analysis"),
                dcc.Graph(id="material-economics-graph"),
                html.P(
                    "Bubble size represents cost-per-year. "
                    "Upper-right = premium long-lived; lower-left = cheap short-lived.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Log-Rank Tests
            html.Div([
                html.H3("Log-Rank Test Results"),
                dcc.Graph(id="log-rank-table"),
                html.P(
                    "Green cells indicate significant differences in survival (p < 0.05).",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Summary
            html.Div([
                html.H3("Economic Summary"),
                html.Div(id="material-summary", style={
                    "backgroundColor": "#f0f0f0",
                    "padding": "15px",
                    "borderRadius": "5px"
                }),
            ]),
        ], type="default"),
    ])

def create_temporal_geospatial_tab() -> html.Div:
    """Create Temporal Geospatial Animation tab layout."""
    return html.Div([
        html.H2("Violation Trends: 12-Month Month-over-Month Animation"),
        html.P(
            "Track deterioration acceleration across community boards. "
            "Identify 'hot blocks' and emerging problem areas."
        ),

        # Controls
        html.Div([
            html.Label("Date Range:"),
            dcc.DatePickerRange(
                id="date-range-picker",
                start_date="2025-06-01",
                end_date="2026-06-01",
                display_format="YYYY-MM-DD",
            ),
            html.Br(),
            html.Label("Top K Hot Blocks:"),
            dcc.Slider(
                id="top-k-slider",
                min=5,
                max=20,
                step=1,
                value=10,
                marks={i: str(i) for i in range(5, 21, 5)},
            ),
        ], style={"marginBottom": "20px"}),

        dcc.Loading([
            # Hot Blocks Timeline (animated)
            html.Div([
                html.H3("Top Hot Blocks Over Time (Animated)"),
                dcc.Graph(id="hot-blocks-timeline-graph"),
                html.P(
                    "Play to see month-by-month ranking changes. Red = worsening, Green = improving.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Month-over-Month Heatmap
            html.Div([
                html.H3("Month-over-Month % Change in Violation Density"),
                dcc.Graph(id="month-over-month-heatmap"),
                html.P(
                    "Blue = improving, Red = worsening. White = no data.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Borough Distribution
            html.Div([
                html.H3("Violation Distribution by Borough"),
                dcc.Graph(id="borough-distribution-graph"),
                html.P(
                    "Violin plots show median, quartiles, and outliers per borough × month.",
                    style={"fontSize": "12px", "color": "#666"}
                ),
            ]),

            # Summary
            html.Div([
                html.H3("Trend Summary"),
                html.Div(id="temporal-summary", style={
                    "backgroundColor": "#f0f0f0",
                    "padding": "15px",
                    "borderRadius": "5px"
                }),
            ]),
        ], type="default"),
    ])

# ============================================================================
# CALLBACK EXAMPLES
# ============================================================================

# Note: In a real application, you'd need to:
# 1. Register these callbacks in your Dash app
# 2. Load violations/inspections data from DuckDB or cache
# 3. Handle data filtering and caching for performance

def register_clustering_callbacks(app):
    """Register clustering diagnostics callbacks."""

    @app.callback(
        Output("elbow-curve-graph", "figure"),
        Output("silhouette-graph", "figure"),
        Output("quality-metrics-heatmap", "figure"),
        Output("cluster-profiles-table", "figure"),
        Output("clustering-summary", "children"),
        Input("clustering-features-dropdown", "value"),
        Input("max-k-slider", "value"),
    )
    def update_clustering_analysis(features_mode: str, max_k: int):
        """Update clustering visualizations."""
        try:
            # Load violations data (from cache or DuckDB)
            # In production, this would load from persistent storage
            df = load_violations_data()  # Placeholder

            # Select features based on mode
            if features_mode == "default":
                feature_cols = ["violation_count", "repair_cost", "population_density"]
            elif features_mode == "violations":
                feature_cols = ["violation_count"]
            else:
                feature_cols = ["violation_count", "repair_cost"]

            # Filter to available columns
            feature_cols = [col for col in feature_cols if col in df.columns]
            if not feature_cols:
                feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()

            # Run clustering diagnostics
            diag = ClusteringDiagnostics(df[feature_cols])
            results = diag.diagnose(max_k=max_k)

            # Create visualizations
            fig_elbow = plot_elbow_curve(results)
            fig_silhouette = plot_silhouette(results)
            fig_metrics = plot_quality_metrics_heatmap(results)
            fig_profiles = plot_cluster_profiles(results)

            # Create summary
            optimal_k = results["optimal_k"]
            quality = results["quality_metrics_by_k"].get(optimal_k, {})

            summary = html.Div([
                html.P(f"Optimal Number of Clusters: {optimal_k}", style={"fontSize": "16px", "fontWeight": "bold"}),
                html.P(f"Davies-Bouldin Index: {quality.get('davies_bouldin', 'N/A'):.3f} (lower is better)"),
                html.P(f"Calinski-Harabasz Index: {quality.get('calinski_harabasz', 'N/A'):.1f} (higher is better)"),
                html.P(f"Silhouette Score: {results['silhouette_scores'][optimal_k - 2]:.3f}"),
            ])

            return fig_elbow, fig_silhouette, fig_metrics, fig_profiles, summary

        except Exception as e:
            return {}, {}, {}, {}, html.Div(f"Error: {str(e)}", style={"color": "red"})

def register_material_callbacks(app):
    """Register material degradation callbacks."""

    @app.callback(
        Output("km-curves-graph", "figure"),
        Output("cumulative-hazard-graph", "figure"),
        Output("material-economics-graph", "figure"),
        Output("log-rank-table", "figure"),
        Output("material-summary", "children"),
        Input("borough-filter", "value"),
    )
    def update_material_analysis(selected_borough: str):
        """Update material degradation visualizations."""
        try:
            # Load survival data
            df_surv = load_survival_data(borough=selected_borough)  # Placeholder

            if df_surv.empty:
                return {}, {}, {}, {}, html.Div("No data available for selected borough")

            # Run material analysis
            analysis = MaterialDegradationAnalysis(df_surv)
            results = analysis.fit()

            # Create visualizations
            fig_km = plot_km_curves(results["km_curves"])
            cumulative_hazard = analysis.get_cumulative_hazard()
            fig_hazard = plot_cumulative_hazard(cumulative_hazard)
            fig_econ = plot_material_economics(results["material_economics"])
            fig_logrank = plot_log_rank_results(results["log_rank_tests"])

            # Create summary
            econ_df = results["material_economics"]
            summary = html.Div([
                html.Table([
                    html.Tr([
                        html.Th("Material"),
                        html.Th("Median Lifespan"),
                        html.Th("20-Year Cost"),
                        html.Th("Cost/Year"),
                    ]),
                    *[
                        html.Tr([
                            html.Td(material.capitalize()),
                            html.Td(f"{row['median_lifespan_years']:.1f} years"),
                            html.Td(f"${row['20_year_total_cost']:,.0f}"),
                            html.Td(f"${row['cost_per_year']:,.0f}"),
                        ])
                        for material, row in econ_df.iterrows()
                    ],
                ], style={"width": "100%", "borderCollapse": "collapse"}),
            ])

            return fig_km, fig_hazard, fig_econ, fig_logrank, summary

        except Exception as e:
            return {}, {}, {}, {}, html.Div(f"Error: {str(e)}", style={"color": "red"})

def register_temporal_callbacks(app):
    """Register temporal geospatial callbacks."""

    @app.callback(
        Output("hot-blocks-timeline-graph", "figure"),
        Output("month-over-month-heatmap", "figure"),
        Output("borough-distribution-graph", "figure"),
        Output("temporal-summary", "children"),
        Input("date-range-picker", "start_date"),
        Input("date-range-picker", "end_date"),
        Input("top-k-slider", "value"),
    )
    def update_temporal_analysis(start_date: str, end_date: str, top_k: int):
        """Update temporal geospatial visualizations."""
        try:
            # Load violations within date range
            df = load_violations_by_date(start_date, end_date)  # Placeholder

            if df.empty:
                return {}, {}, {}, html.Div("No data available for selected date range")

            # Create visualizer
            viz = TemporalGeospatialVisualizer(df, period="month")

            # Generate visualizations
            fig_timeline = viz.plot_hot_blocks_timeline(top_k=top_k)
            fig_heatmap = viz.plot_month_over_month_heatmap()
            fig_borough = viz.plot_borough_summary()

            # Create summary
            hot_blocks = viz.get_hot_blocks_data()
            latest_month = max(hot_blocks.keys()) if hot_blocks else "N/A"

            if latest_month != "N/A":
                top_block = hot_blocks[latest_month][0] if hot_blocks[latest_month] else {}
                summary = html.Div([
                    html.P(f"Date Range: {start_date} to {end_date}"),
                    html.P(f"Latest Month: {latest_month}"),
                    html.P(f"Top Hot Block: CB {top_block.get('community_board', 'N/A')} ({top_block.get('borough', 'N/A')})"),
                    html.P(f"Violation Density: {top_block.get('violation_density', 'N/A'):.2f} per km²"),
                ])
            else:
                summary = html.Div("No temporal data available")

            return fig_timeline, fig_heatmap, fig_borough, summary

        except Exception as e:
            return {}, {}, {}, html.Div(f"Error: {str(e)}", style={"color": "red"})

# ============================================================================
# PLACEHOLDER DATA LOADING FUNCTIONS
# ============================================================================

def load_violations_data() -> pd.DataFrame:
    """Load violations data from DuckDB or cache.

    This is a placeholder. In production, implement actual data loading.
    """
    # TODO: Load from DuckDB
    # import duckdb
    # conn = duckdb.connect(":memory:")
    # df = conn.execute("""
    #     SELECT violation_count, repair_cost, population_density, ...
    #     FROM violations
    # """).df()
    # return df

    return pd.DataFrame()  # Placeholder

def load_survival_data(borough: str | None = None) -> pd.DataFrame:
    """Load survival data (prepared from inspections + violations).

    This is a placeholder. In production, implement actual data loading.
    """
    # TODO: Implement with SurvivalDataPrep
    # df_insp = load_inspections(borough=borough)
    # df_vio = load_violations(borough=borough)
    # prep = SurvivalDataPrep()
    # df_surv = prep.prepare_time_to_event(df_insp, df_vio)
    # return df_surv

    return pd.DataFrame()  # Placeholder

def load_violations_by_date(start_date: str, end_date: str) -> pd.DataFrame:
    """Load violations within date range for temporal analysis.

    This is a placeholder. In production, implement actual data loading.
    """
    # TODO: Load from DuckDB with date filter
    # import duckdb
    # df = duckdb.execute("""
    #     SELECT date, community_board, borough, violation_count, latitude, longitude
    #     FROM violations
    #     WHERE date >= ? AND date <= ?
    # """, [start_date, end_date]).df()
    # return df

    return pd.DataFrame()  # Placeholder

# ============================================================================
# HOW TO INTEGRATE
# ============================================================================

"""
To integrate these callbacks into your Dash app:

1. Add imports to app/callbacks/analytics.py:
   from app.phase1_callbacks_example import (
       register_clustering_callbacks,
       register_material_callbacks,
       register_temporal_callbacks,
   )

2. Call registration functions in app initialization:
   if __name__ == "__main__":
       register_clustering_callbacks(app)
       register_material_callbacks(app)
       register_temporal_callbacks(app)
       app.run_server(debug=True)

3. Update app/dash_layouts.py to include tabs:
   import dcc
   from app.phase1_callbacks_example import (
       create_clustering_diagnostics_tab,
       create_material_degradation_tab,
       create_temporal_geospatial_tab,
   )

   app.layout = dcc.Tabs([
       dcc.Tab(label="Clustering Diagnostics", children=create_clustering_diagnostics_tab()),
       dcc.Tab(label="Material Analysis", children=create_material_degradation_tab()),
       dcc.Tab(label="Temporal Trends", children=create_temporal_geospatial_tab()),
   ])

4. Implement data loading functions with real DuckDB queries

5. Add error handling and caching for production performance
"""
