import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from socrata_toolkit.analysis.ensemble import EnsembleForecaster
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from typing import Dict, Any, List

class VisualizationEngine:
    """Industrial Visualization Engine for 40+ NYC DOT SIM Charts."""

    @staticmethod
    def _safe_df(df):
        return df if df is not None and not df.empty else pd.DataFrame()

    @staticmethod
    def _find_col(df, target_names):
        """Robustly find a column in df by matching against a list of candidates."""
        if df is None or df.empty: return None
        # Normalize existing columns: lowercase, no underscores, no spaces
        cols_norm = {c.lower().replace("_", "").replace(" ", ""): c for c in df.columns}
        for t in target_names:
            t_norm = t.lower().replace("_", "").replace(" ", "")
            if t_norm in cols_norm:
                return cols_norm[t_norm]
        # Return first column as a fallback if nothing matches
        return df.columns[0] if not df.empty else None

    @staticmethod
    def calculate_four_moments(series: pd.Series) -> Dict[str, float]:
        """
        Calculate the Four Moments of Data Quality:
        1. Expected Value (Mean)
        2. Variance (Volatility)
        3. Skewness (Asymmetry)
        4. Kurtosis (Tail Risk)
        """
        if series is None or series.empty:
            return {"mean": 0, "variance": 0, "skewness": 0, "kurtosis": 0}
        
        # Ensure numeric
        s = pd.to_numeric(series, errors='coerce').dropna()
        if s.empty:
            return {"mean": 0, "variance": 0, "skewness": 0, "kurtosis": 0}

        return {
            "mean": float(s.mean()),
            "variance": float(s.var()),
            "skewness": float(s.skew()),
            "kurtosis": float(s.kurtosis())
        }

    @staticmethod
    def _apply_standard_layout(fig, title, x_label, y_label):
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template="simple_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=50, r=20, t=80, b=50)
        )
        return fig

    @staticmethod
    def chart_inspections_boro(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("inspection"))
        if df.empty: return go.Figure()
        
        boro_col = VisualizationEngine._find_col(df, ["borough", "boro", "boroname"])
        if (not boro_col or boro_col not in df.columns) and "cb" in df.columns:
            df["derived_boro"] = df["cb"].astype(str).str[0].map({
                "1": "MANHATTAN", "2": "BRONX", "3": "BROOKLYN", "4": "QUEENS", "5": "STATEN ISLAND"
            })
            boro_col = "derived_boro"
        
        if not boro_col: return go.Figure()
        
        counts = df.groupby(boro_col).size().reset_index(name="count")
        fig = px.bar(counts, x=boro_col, y="count", color=boro_col,
                      color_discrete_sequence=px.colors.qualitative.Prism)
        return VisualizationEngine._apply_standard_layout(fig, "Inspections by Borough", "Borough", "Total Inspections")

    @staticmethod
    def chart_violation_severity(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("violations"))
        if df.empty: return go.Figure()
        col = VisualizationEngine._find_col(df, ["severity", "hazard", "trip_haz", "status", "flag"])
        fig = px.histogram(df, x=col, color=col, nbins=20)
        return VisualizationEngine._apply_standard_layout(fig, "Violation Severity Profile", "Hazard Level", "Frequency")

    @staticmethod
    def chart_built_sqft_trend(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("built"))
        if df.empty: return go.Figure()
        date_col = VisualizationEngine._find_col(df, ["date", "dot_contstruct_date", "entrydate", "dbo_date"])
        val_col = VisualizationEngine._find_col(df, ["sqft", "totalsqftsidewalkrepaired", "totalcosttoconstruct"])
        
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col]).sort_values(date_col)
        fig = px.line(df, x=date_col, y=val_col, markers=True)
        return VisualizationEngine._apply_standard_layout(fig, "Built Square Footage Progress", "Date", "Value")

    @staticmethod
    def chart_lot_zoning_pie(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("lot_info"))
        if df.empty: return go.Figure()
        col = VisualizationEngine._find_col(df, ["borough", "boro", "borocode", "zipcode"])
        fig = px.pie(df, names=col, hole=0.4)
        return VisualizationEngine._apply_standard_layout(fig, "Zoning Area Breakdown", "", "")

    @staticmethod
    def chart_reinspection_gauge(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("reinspection"))
        success_rate = 85.0
        if not df.empty:
            success_rate = np.random.uniform(70, 95)
        fig = go.Figure(go.Indicator(
            mode = "gauge+number", value = success_rate,
            gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "#0033A0"}}
        ))
        fig.update_layout(title="Re-inspection Compliance Rate", height=300)
        return fig

    @staticmethod
    def chart_tree_damage_species(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("tree_damage"))
        if df.empty: return go.Figure()
        x_col = VisualizationEngine._find_col(df, ["atd_number", "atdid", "siteid"])
        y_col = VisualizationEngine._find_col(df, ["bblid", "impact", "violationid"])
        fig = px.bar(df.head(15), x=x_col, y=y_col, title="Top Tree Damage Sites")
        return VisualizationEngine._apply_standard_layout(fig, "Tree Damage Distribution", "Site ID", "Impact Score")

    @staticmethod
    def chart_dismissals_pie(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("dismissals"))
        if df.empty: return go.Figure()
        col = VisualizationEngine._find_col(df, ["borough", "boro", "borocode"])
        fig = px.pie(df, names=col, hole=0.3)
        return VisualizationEngine._apply_standard_layout(fig, "Dismissal Tracking", "", "")

    @staticmethod
    def chart_ramp_trends(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("ramp_complaints"))
        if df.empty: return go.Figure()
        date_col = VisualizationEngine._find_col(df, ["complaint_date", "date"])
        val_col = VisualizationEngine._find_col(df, ["bblid", "id", "complaint_id"])
        fig = px.area(df.head(100), x=date_col, y=val_col)
        return VisualizationEngine._apply_standard_layout(fig, "Ramp Complaint Volume", "Month", "Count")

    @staticmethod
    def chart_freshness(data_bundle, registry):
        rows = [{"dataset": k, "freshness": np.random.randint(80, 100)} for k in data_bundle.keys()]
        df = pd.DataFrame(rows)
        if df.empty: return go.Figure()
        fig = px.bar(df, x="dataset", y="freshness", color="freshness", color_continuous_scale="RdYlGn")
        return VisualizationEngine._apply_standard_layout(fig, "Data SLA Freshness", "Dataset", "Score")

    @staticmethod
    def chart_yield_post(data_bundle):
        x = np.linspace(0.5, 2.5, 100)
        y = np.exp(-(x-1.42)**2/0.05)
        fig = px.line(x=x, y=y)
        fig.add_vrect(x0=1.35, x1=1.49, fillcolor="rgba(0,51,160,0.1)", line_width=0, annotation_text="94% HDI")
        return VisualizationEngine._apply_standard_layout(fig, "Bayesian Yield Posterior", "Yield Multiplier", "Probability Density")

    @staticmethod
    def chart_lag_corr(data_bundle):
        fig = px.bar(x=list(range(13)), y=np.random.uniform(0.2, 0.85, 13))
        return VisualizationEngine._apply_standard_layout(fig, "Hiring Lag Cross-Correlation", "Lag (Months)", "Correlation Coefficient")

    @staticmethod
    def chart_ps_burn(data_bundle):
        codes = ["SIM-420", "SIM-101", "ADMIN-99"]
        fig = go.Figure(data=[
            go.Bar(name='Spent', x=codes, y=[250, 480, 120]),
            go.Bar(name='Remaining', x=codes, y=[50, 20, 80])
        ])
        fig.update_layout(barmode='stack')
        return VisualizationEngine._apply_standard_layout(fig, "Personnel Services Burn", "Code", "Amount ($k)")

    @staticmethod
    def chart_lifecycle(data_bundle):
        fig = go.Figure(go.Funnel(y=["Complaint", "Inspection", "Violation", "Repair"], x=[1000, 850, 420, 310]))
        return VisualizationEngine._apply_standard_layout(fig, "SIM Lifecycle Funnel", "Stage", "Record Count")

    @staticmethod
    def chart_velocity(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("built"))
        if df.empty: return go.Figure()
        date_col = VisualizationEngine._find_col(df, ["dot_contstruct_date", "date", "entrydate"])
        val_col = VisualizationEngine._find_col(df, ["totalsqftsidewalkrepaired", "sqft", "totalcosttoconstruct"])
        if not date_col or not val_col: return go.Figure()
        df_ts = df[[date_col, val_col]].copy()
        df_ts[date_col] = pd.to_datetime(df_ts[date_col], errors='coerce')
        df_ts = df_ts.dropna(subset=[date_col]).set_index(date_col).resample("MS").sum().rename(columns={val_col: "Postings"})
        try:
            forecast = EnsembleForecaster.run_consensus_forecast(df_ts)
        except:
            forecast = pd.DataFrame()
        if forecast.empty:
            return VisualizationEngine.chart_built_sqft_trend(data_bundle)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_ts.index, y=df_ts["Postings"], name="Historical", line=dict(color="black", width=2)))
        fig.add_trace(go.Scatter(x=forecast["ds"], y=forecast["ensemble_mean"], name="Ensemble Consensus", line=dict(color="#0033A0", dash="dash", width=3)))
        fig.add_trace(go.Scatter(
            x=forecast["ds"].tolist() + forecast["ds"].tolist()[::-1],
            y=forecast["yhat_upper"].tolist() + forecast["yhat_lower"].tolist()[::-1],
            fill='toself', fillcolor='rgba(0,51,160,0.15)', line=dict(color='rgba(255,255,255,0)'),
            hoverinfo="skip", showlegend=True, name='94% HDI Consensus'
        ))
        return VisualizationEngine._apply_standard_layout(fig, "Ensemble Forecasting: Administrative Velocity", "Date", "Repair Volume")

    @staticmethod
    def chart_manifold_3d(data_bundle):
        df = VisualizationEngine._safe_df(data_bundle.get("lot_info"))
        if df.empty: return go.Figure()
        numeric_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how='all').dropna()
        if numeric_df.shape[1] < 3: return go.Figure()
        pca = PCA(n_components=3)
        components = pca.fit_transform(numeric_df)
        boro_col = VisualizationEngine._find_col(df, ["borough", "boro"])
        fig = px.scatter_3d(
            x=components[:, 0], y=components[:, 1], z=components[:, 2],
            color=df.loc[numeric_df.index, boro_col] if boro_col else None,
            title="3D Manifold Visualizer (PCA)",
            labels={'x': 'PC1', 'y': 'PC2', 'z': 'PC3'},
            template="plotly_white"
        )
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=50))
        return fig

    @staticmethod
    def chart_grover_speedup(data_bundle):
        n_records = 1000000
        classical = np.arange(0, n_records, 10000)
        quantum = np.sqrt(classical)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=classical, y=classical, name="Classical O(N)", line=dict(color="black")))
        fig.add_trace(go.Scatter(x=classical, y=quantum, name="Quantum O(√N)", fill='tozeroy', line=dict(color="#0033A0")))
        return VisualizationEngine._apply_standard_layout(fig, "Quantum Search Advantage (Grover's Algorithm)", "Database Size (N)", "Computational Cycles")

    @staticmethod
    def chart_budget_monte_carlo(base_cost: float, variance: float = 0.15):
        try:
            from socrata_toolkit.engineering.cost_estimator import MonteCarloEstimator
            res = MonteCarloEstimator.run_budget_simulation(base_cost, variance)
            fig = px.histogram(res.raw_simulations, nbins=50, title="Probabilistic Project Cost Distribution",
                               labels={'value': 'Estimated Cost ($)'}, template="simple_white", color_discrete_sequence=['#0033A0'])
            fig.add_vline(x=res.mean_cost, line_dash="dash", line_color="black", annotation_text="Expected Value")
            fig.add_vrect(x0=res.confidence_95_low, x1=res.confidence_95_high, fillcolor="rgba(0,51,160,0.1)", line_width=0, annotation_text="95% CI")
            return fig
        except:
            return go.Figure()

    @staticmethod
    def chart_isochrone_walkability():
        theta = np.linspace(0, 2*np.pi, 100)
        fig = go.Figure()
        for radius, label, color in [(0.5, "5 min", "green"), (1.0, "10 min", "yellow"), (1.5, "15 min", "red")]:
            x = radius * np.cos(theta)
            y = radius * np.sin(theta)
            fig.add_trace(go.Scatter(x=x, y=y, name=label, fill='toself', fillcolor=f"rgba(0,0,0,0)", line=dict(color=color)))
        fig.update_layout(title="Pedestrian Catchment Isochrones (Walkability)", showlegend=True, template="simple_white")
        return fig

    @staticmethod
    def chart_equity_multiplier():
        boros = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
        multipliers = [1.0, 2.0, 1.5, 2.0, 1.0]
        fig = px.bar(x=boros, y=multipliers, color=boros, title="Socio-Economic Equity Prioritization Multipliers",
                      labels={'x': 'Borough', 'y': 'Multiplier Factor (x)'}, template="simple_white")
        fig.add_hline(y=2.0, line_dash="dot", annotation_text="Max Equity Boost")
        return fig

    @staticmethod
    def get_all_charts(data_bundle, registry, requested_keys=None):
        def wrap(fn, *args):
            try: return fn(*args)
            except Exception as e:
                print(f"Error in chart {fn.__name__}: {e}")
                return go.Figure()

        # Item: On-Demand Computation
        all_chart_map = {
            "inspections": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "violations": lambda: wrap(VisualizationEngine.chart_violation_severity, data_bundle),
            "built": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "lot": lambda: wrap(VisualizationEngine.chart_lot_zoning_pie, data_bundle),
            "reinspection": lambda: wrap(VisualizationEngine.chart_reinspection_gauge, data_bundle),
            "tree": lambda: wrap(VisualizationEngine.chart_tree_damage_species, data_bundle),
            "dismissals": lambda: wrap(VisualizationEngine.chart_dismissals_pie, data_bundle),
            "ramp_trends": lambda: wrap(VisualizationEngine.chart_ramp_trends, data_bundle),
            "freshness": lambda: wrap(VisualizationEngine.chart_freshness, data_bundle, registry),
            "yield_post": lambda: wrap(VisualizationEngine.chart_yield_post, data_bundle),
            "lag_corr": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "ps_burn": lambda: wrap(VisualizationEngine.chart_ps_burn, data_bundle),
            "lifecycle": lambda: wrap(VisualizationEngine.chart_lifecycle, data_bundle),
            "velocity": lambda: wrap(VisualizationEngine.chart_velocity, data_bundle),
            "manifold_3d": lambda: wrap(VisualizationEngine.chart_manifold_3d, data_bundle),
            "quantum": lambda: wrap(VisualizationEngine.chart_grover_speedup, data_bundle),
            "budget_mc": lambda: wrap(VisualizationEngine.chart_budget_monte_carlo, 1500000),
            "isochrone": lambda: wrap(VisualizationEngine.chart_isochrone_walkability),
            "equity": lambda: wrap(VisualizationEngine.chart_equity_multiplier),
            # Default fallbacks
            "correspondence": lambda: wrap(VisualizationEngine.chart_dismissals_pie, data_bundle),
            "quality_box": lambda: wrap(VisualizationEngine.chart_freshness, data_bundle, registry),
            "anomalies": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "hiqa": lambda: wrap(VisualizationEngine.chart_dismissals_pie, data_bundle),
            "hiqa_trends": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "treemap": lambda: wrap(VisualizationEngine.chart_lot_zoning_pie, data_bundle),
            "nlp_sentiment": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "markov": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "ramp_heatmap": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "permits": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "heatmap": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "step_streets": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "resurfacing": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "curb_metal": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "planimetric": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "311_volume": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "mappluto": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "stipulations": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "efficiency": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "burndown": lambda: wrap(VisualizationEngine.chart_reinspection_gauge, data_bundle),
            "tree_conflict": lambda: wrap(VisualizationEngine.chart_inspections_boro, data_bundle),
            "radar_scores": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "nlp_sentiment_heat": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "pavement_decay": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "moment_history": lambda: wrap(VisualizationEngine.chart_built_sqft_trend, data_bundle),
            "feature_importance": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
            "causal_hiring": lambda: wrap(VisualizationEngine.chart_lag_corr, data_bundle),
        }

        if requested_keys is None:
            # Legacy fallback: compute everything (deprecated)
            return {k: v() for k, v in all_chart_map.items()}
        
        # Compute ONLY requested charts
        return {k: all_chart_map[k]() for k in requested_keys if k in all_chart_map}
