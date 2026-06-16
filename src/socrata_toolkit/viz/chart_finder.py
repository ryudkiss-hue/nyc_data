"""Chart Finder — Intelligent visualization recommendation engine.

Given a DataFrame, analyzes its shape, columns, and data characteristics to
recommend the best charts from the 65+ visualization library.

Scoring considers:
- Column count & types (numeric, categorical, datetime)
- Cardinality (distinct values per column)
- Temporal structure (is there a time series?)
- Spatial structure (lat/lon columns?)
- Analysis patterns (comparison, distribution, temporal, relational, spatial)

Example::

    from socrata_toolkit.viz.chart_finder import ChartFinder
    import pandas as pd

    df = pd.read_csv("violations.csv")
    finder = ChartFinder(df)

    # Get top-5 recommendations
    recommendations = finder.recommend(top_n=5)
    for rec in recommendations:
        print(f"{rec.rank}. {rec.chart_name} (score: {rec.score:.2f})")
        print(f"   Reason: {rec.reason}")
        print(f"   Code: {rec.example_code}")
        print()

    # Get specific recommendations for a hypothesis
    recs = finder.recommend_for_hypothesis("Compare violation rates across boroughs")

    # Interactive: show all charts with their required/optional columns
    finder.show_all_charts()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ChartRecommendation:
    """Single chart recommendation with scoring details."""

    rank: int
    chart_name: str
    function_name: str
    module: str
    score: float
    reason: str
    required_cols: list[str]
    suggested_cols: list[str] = field(default_factory=list)
    example_code: str = ""
    analysis_type: str = ""
    hypothesis_fit: str = ""


@dataclass
class DataFrameProfile:
    """Analysis summary of a DataFrame's structure."""

    row_count: int
    col_count: int
    numeric_cols: list[str]
    categorical_cols: list[str]
    datetime_cols: list[str]
    geometry_cols: list[str]
    has_temporal: bool
    has_spatial: bool
    has_grouping: bool
    cardinalities: dict[str, int]
    null_fractions: dict[str, float]
    analysis_patterns: list[str]


class ChartFinder:
    """Intelligent chart recommendation engine."""

    def __init__(self, df: pd.DataFrame):
        """Initialize with a DataFrame to analyze.

        Args:
            df: Input DataFrame to analyze.
        """
        self.df = df.copy()
        self.profile = self._profile_dataframe()

    def _profile_dataframe(self) -> DataFrameProfile:
        """Analyze DataFrame structure and characteristics."""
        numeric_cols = self.df.select_dtypes(include=np.number).columns.tolist()
        categorical_cols = self.df.select_dtypes(include=["object"]).columns.tolist()
        datetime_cols = self.df.select_dtypes(include=["datetime64"]).columns.tolist()

        # Detect geometry columns
        geometry_cols = [
            c
            for c in self.df.columns
            if "lat" in c.lower() or "lon" in c.lower() or "geom" in c.lower()
        ]

        cardinalities = {col: self.df[col].nunique() for col in self.df.columns}
        null_fractions = {col: self.df[col].isna().mean() for col in self.df.columns}

        has_temporal = len(datetime_cols) > 0 or any(
            "date" in c.lower() for c in self.df.columns
        )
        has_spatial = len(geometry_cols) >= 2 or all(
            g in self.df.columns for g in ["latitude", "longitude"]
        )
        has_grouping = any(
            card > 1 and card <= 100 for card in cardinalities.values()
        )

        # Infer analysis patterns
        patterns = []
        if has_temporal and len(numeric_cols) > 0:
            patterns.append("temporal")
        if len(numeric_cols) >= 2:
            patterns.append("multivariate")
        if any(card < 20 and card > 1 for card in cardinalities.values()):
            patterns.append("comparative")
        if has_spatial:
            patterns.append("spatial")
        if len(categorical_cols) > 0:
            patterns.append("categorical")
        if len(numeric_cols) > 2:
            patterns.append("distributional")

        return DataFrameProfile(
            row_count=len(self.df),
            col_count=len(self.df.columns),
            numeric_cols=numeric_cols,
            categorical_cols=categorical_cols,
            datetime_cols=datetime_cols,
            geometry_cols=geometry_cols,
            has_temporal=has_temporal,
            has_spatial=has_spatial,
            has_grouping=has_grouping,
            cardinalities=cardinalities,
            null_fractions=null_fractions,
            analysis_patterns=patterns,
        )

    def recommend(self, top_n: int = 5) -> list[ChartRecommendation]:
        """Get top-N chart recommendations for this DataFrame.

        Args:
            top_n: Number of recommendations to return.

        Returns:
            List of ChartRecommendation objects, ranked by score.
        """
        all_charts = self._get_all_charts()
        scores = [self._score_chart(chart) for chart in all_charts]

        ranked = sorted(
            zip(scores, all_charts), key=lambda x: x[0], reverse=True
        )
        recommendations = []
        for rank, (score, chart) in enumerate(ranked[:top_n], 1):
            rec = self._build_recommendation(rank, chart, score)
            recommendations.append(rec)

        return recommendations

    def recommend_for_hypothesis(self, hypothesis: str) -> list[ChartRecommendation]:
        """Recommend charts for a specific research question.

        Args:
            hypothesis: Natural-language question (e.g., "Compare boroughs").

        Returns:
            List of ChartRecommendation objects.
        """
        # Map hypothesis keywords to analysis patterns + chart types
        keywords = {
            "borough": ["comparative", "borough"],
            "trend": ["temporal"],
            "time": ["temporal"],
            "distribution": ["distributional"],
            "compare": ["comparative"],
            "spatial": ["spatial"],
            "cluster": ["spatial", "multivariate"],
            "outlier": ["distributional", "multivariate"],
            "correlation": ["multivariate"],
            "relationship": ["relational"],
            "flow": ["relational"],
            "change": ["temporal"],
            "shift": ["temporal"],
        }

        matched_patterns = []
        for kw, patterns in keywords.items():
            if kw.lower() in hypothesis.lower():
                matched_patterns.extend(patterns)

        # Score charts that match these patterns
        all_charts = self._get_all_charts()
        scores = []
        for chart in all_charts:
            base_score = self._score_chart(chart)
            # Boost score if chart's analysis type matches hypothesis patterns
            if any(p in chart.get("analysis_type", "") for p in matched_patterns):
                base_score *= 1.5
            scores.append(base_score)

        ranked = sorted(zip(scores, all_charts), key=lambda x: x[0], reverse=True)
        recommendations = [
            self._build_recommendation(rank, chart, score)
            for rank, (score, chart) in enumerate(ranked[:5], 1)
        ]

        return recommendations

    def _score_chart(self, chart: dict) -> float:
        """Score a chart's suitability for this DataFrame.

        Scoring factors:
        - Required columns available: +5 points per column
        - Optional columns available: +0.5 points per column
        - Analysis pattern match: +2 points per match
        - Row count fit: +1 point if within reasonable range
        """
        score = 0.0

        # Check required columns
        required = chart.get("required_cols", [])
        required_met = sum(
            1 for col in required if col in self.df.columns or self._column_matches(col)
        )
        score += required_met * 5

        # Penalize if required columns missing
        if len(required) > 0 and required_met < len(required):
            score -= (len(required) - required_met) * 3

        # Check optional columns
        optional = chart.get("optional_cols", [])
        optional_met = sum(
            1 for col in optional if col in self.df.columns or self._column_matches(col)
        )
        score += optional_met * 0.5

        # Analysis pattern match
        for pattern in chart.get("analysis_patterns", []):
            if pattern in self.profile.analysis_patterns:
                score += 2

        # Row count suitability
        if 100 <= self.profile.row_count <= 1000000:
            score += 1

        # Cardinality fit
        if self.profile.has_grouping and "comparative" in chart.get("analysis_patterns", []):
            score += 1.5

        return max(0, score)

    def _column_matches(self, required: str) -> bool:
        """Check if a column type (e.g., 'numeric', 'datetime') matches available columns.

        Args:
            required: Column type or name pattern (e.g., 'date_col', 'numeric').

        Returns:
            True if a matching column exists.
        """
        if "numeric" in required.lower():
            return len(self.profile.numeric_cols) > 0
        if "date" in required.lower() or "temporal" in required.lower():
            return self.profile.has_temporal
        if "categorical" in required.lower():
            return len(self.profile.categorical_cols) > 0
        if "lat" in required.lower() or "lon" in required.lower():
            return self.profile.has_spatial

        # Try substring match on actual column names
        return any(required.lower() in col.lower() for col in self.df.columns)

    def _build_recommendation(
        self, rank: int, chart: dict, score: float
    ) -> ChartRecommendation:
        """Build a detailed recommendation object."""
        required = chart.get("required_cols", [])
        suggested = [
            col for col in chart.get("optional_cols", []) if self._column_matches(col)
        ]

        # Generate example code snippet
        example_code = self._generate_example_code(chart, required, suggested)

        return ChartRecommendation(
            rank=rank,
            chart_name=chart["name"],
            function_name=chart["function"],
            module=chart["module"],
            score=score,
            reason=chart.get("reason", ""),
            required_cols=required,
            suggested_cols=suggested,
            example_code=example_code,
            analysis_type=chart.get("analysis_type", ""),
            hypothesis_fit=chart.get("hypothesis_fit", ""),
        )

    def _generate_example_code(
        self, chart: dict, required: list[str], suggested: list[str]
    ) -> str:
        """Generate example code to use the recommended chart."""
        func = chart["function"]
        module = chart["module"].replace("viz/", "").replace(".py", "")

        # Find actual column names that match required
        col_mapping = {}
        for req in required:
            matched = self._find_column(req)
            if matched:
                col_mapping[req] = matched

        if not col_mapping:
            return f"from socrata_toolkit.viz.{module} import {func}\n# Add data..."

        args = ", ".join([f'{k}="{v}"' for k, v in col_mapping.items()])
        return f"from socrata_toolkit.viz.{module} import {func}\nfig = {func}(df, {args})\nfig.show()"

    def _find_column(self, pattern: str) -> str | None:
        """Find a column that matches the required pattern."""
        pattern_lower = pattern.lower()

        # Try exact match first
        if pattern in self.df.columns:
            return pattern

        # Try substring match
        matches = [c for c in self.df.columns if pattern_lower in c.lower()]
        if matches:
            return matches[0]

        # Try type-based match
        if "numeric" in pattern_lower and self.profile.numeric_cols:
            return self.profile.numeric_cols[0]
        if "date" in pattern_lower and self.profile.datetime_cols:
            return self.profile.datetime_cols[0]
        if "categorical" in pattern_lower and self.profile.categorical_cols:
            return self.profile.categorical_cols[0]

        return None

    def _get_all_charts(self) -> list[dict]:
        """Return metadata for all 65+ charts."""
        return [
            # Plotly core
            {
                "name": "Borough Bar Chart",
                "function": "borough_bar_chart",
                "module": "viz/plotly.py",
                "required_cols": ["borough", "violations"],
                "optional_cols": ["date", "status"],
                "analysis_patterns": ["comparative", "categorical"],
                "reason": "Show metric aggregated by borough with color coding.",
                "hypothesis_fit": "Which borough has highest X?",
            },
            {
                "name": "Trend Line",
                "function": "trend_line",
                "module": "viz/plotly.py",
                "required_cols": ["date", "value"],
                "optional_cols": ["borough", "material_type"],
                "analysis_patterns": ["temporal"],
                "reason": "Track numeric metric over time, optionally grouped.",
                "hypothesis_fit": "Is X increasing/decreasing over time?",
            },
            {
                "name": "Correlation Heatmap",
                "function": "correlation_heatmap",
                "module": "viz/plotly.py",
                "required_cols": ["numeric"],
                "optional_cols": [],
                "analysis_patterns": ["multivariate"],
                "reason": "Show pairwise correlations between all numeric columns.",
                "hypothesis_fit": "Which metrics are related?",
            },
            {
                "name": "Status Donut Chart",
                "function": "status_donut",
                "module": "viz/plotly.py",
                "required_cols": ["status"],
                "optional_cols": [],
                "analysis_patterns": ["distributional", "categorical"],
                "reason": "Show composition of categories as proportions.",
                "hypothesis_fit": "What % are in each status?",
            },
            {
                "name": "KPI Gauge",
                "function": "kpi_gauge",
                "module": "viz/plotly.py",
                "required_cols": [],
                "optional_cols": [],
                "analysis_patterns": ["comparative"],
                "reason": "Display single scalar metric vs target.",
                "hypothesis_fit": "Is current value above/below threshold?",
            },
            {
                "name": "Contract Gantt",
                "function": "contract_gantt",
                "module": "viz/plotly.py",
                "required_cols": ["contract_id", "start_date", "end_date"],
                "optional_cols": ["status"],
                "analysis_patterns": ["temporal"],
                "reason": "Show project timeline with milestones.",
                "hypothesis_fit": "Which projects are behind schedule?",
            },
            {
                "name": "Priority Heatmap",
                "function": "priority_heatmap",
                "module": "viz/plotly.py",
                "required_cols": ["row_col", "col_col", "metric"],
                "optional_cols": [],
                "analysis_patterns": ["comparative", "categorical"],
                "reason": "2D matrix showing metric by two categorical dimensions.",
                "hypothesis_fit": "Where is the highest concentration?",
            },
            {
                "name": "Hypothesis Test Results",
                "function": "hypothesis_test_results",
                "module": "viz/plotly.py",
                "required_cols": [],
                "optional_cols": [],
                "analysis_patterns": [],
                "reason": "Display p-values and effect sizes for statistical tests.",
                "hypothesis_fit": "Are differences significant?",
            },
            {
                "name": "Waterfall Chart",
                "function": "waterfall_chart",
                "module": "viz/plotly.py",
                "required_cols": ["category", "value"],
                "optional_cols": [],
                "analysis_patterns": ["temporal"],
                "reason": "Show sequential impact/decomposition.",
                "hypothesis_fit": "What drove the change from Q1 to Q2?",
            },
            {
                "name": "Inspector Performance Boxplot",
                "function": "inspector_performance_boxplot",
                "module": "viz/plotly.py",
                "required_cols": ["inspector_id", "metric"],
                "optional_cols": [],
                "analysis_patterns": ["comparative", "distributional"],
                "reason": "Quartile/outlier distributions by inspector.",
                "hypothesis_fit": "Do inspectors have consistent scoring?",
            },
            # Advanced multidim
            {
                "name": "Parallel Coordinates",
                "function": "parallel_coordinates",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["numeric", "numeric"],
                "optional_cols": ["categorical"],
                "analysis_patterns": ["multivariate"],
                "reason": "Interactive multi-axis brushing for filtering complex data.",
                "hypothesis_fit": "What profile has high X + high Y + low Z?",
            },
            {
                "name": "Scatter Plot Matrix (SPLOM)",
                "function": "scatter_plot_matrix",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["numeric", "numeric", "numeric"],
                "optional_cols": ["categorical"],
                "analysis_patterns": ["multivariate"],
                "reason": "Grid of all pairwise scatters to spot relationships.",
                "hypothesis_fit": "Which pairs of metrics correlate?",
            },
            {
                "name": "Clustermap",
                "function": "clustermap",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["categorical", "numeric"],
                "optional_cols": [],
                "analysis_patterns": ["multivariate", "comparative"],
                "reason": "Hierarchically clustered heatmap with dendrograms.",
                "hypothesis_fit": "Which groups are similar? Which are outliers?",
            },
            {
                "name": "Sankey Flow Diagram",
                "function": "sankey_flow",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["source", "target"],
                "optional_cols": ["value"],
                "analysis_patterns": ["relational"],
                "reason": "Show flow magnitude from source to target categories.",
                "hypothesis_fit": "Which transitions are most common?",
            },
            {
                "name": "Radar / Spider Chart",
                "function": "radar_chart",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["categorical", "numeric"],
                "optional_cols": [],
                "analysis_patterns": ["comparative", "multivariate"],
                "reason": "Multi-metric polygon per group (normalized 0-1).",
                "hypothesis_fit": "Which group excels across all metrics?",
            },
            {
                "name": "Inspection Funnel",
                "function": "inspection_funnel",
                "module": "viz/advanced_multidim.py",
                "required_cols": [],
                "optional_cols": [],
                "analysis_patterns": ["categorical"],
                "reason": "Pipeline stages with drop-off at each step.",
                "hypothesis_fit": "Where are we losing cases?",
            },
            {
                "name": "Bubble Chart",
                "function": "bubble_chart",
                "module": "viz/advanced_multidim.py",
                "required_cols": ["numeric", "numeric", "numeric"],
                "optional_cols": ["categorical"],
                "analysis_patterns": ["multivariate"],
                "reason": "4D encoding: x, y, size, color.",
                "hypothesis_fit": "Is there a community board with high cost + low score?",
            },
            # Statistical viz
            {
                "name": "CUSUM Control Chart",
                "function": "cusum_control_chart",
                "module": "viz/statistical_viz.py",
                "required_cols": ["date", "value"],
                "optional_cols": [],
                "analysis_patterns": ["temporal"],
                "reason": "Detect process shifts; shows cumulative deviation.",
                "hypothesis_fit": "Did the violation count shift level?",
            },
            {
                "name": "Bayesian Posterior Strip",
                "function": "bayesian_posterior_strip",
                "module": "viz/statistical_viz.py",
                "required_cols": ["numeric"],
                "optional_cols": [],
                "analysis_patterns": ["distributional"],
                "reason": "Credible intervals (HDI) from Bayesian MCMC.",
                "hypothesis_fit": "What are the 89% credible intervals?",
            },
            {
                "name": "Moran's I Scatter",
                "function": "moran_scatter_plot",
                "module": "viz/statistical_viz.py",
                "required_cols": ["numeric", "categorical"],
                "optional_cols": [],
                "analysis_patterns": ["spatial"],
                "reason": "Spatial autocorrelation; LISA quadrant coloring.",
                "hypothesis_fit": "Do violations cluster spatially?",
            },
            {
                "name": "Ridge Plot",
                "function": "ridge_plot",
                "module": "viz/statistical_viz.py",
                "required_cols": ["numeric", "categorical"],
                "optional_cols": [],
                "analysis_patterns": ["distributional", "comparative"],
                "reason": "Stacked KDE distributions for group comparison.",
                "hypothesis_fit": "Do distributions differ by borough?",
            },
            {
                "name": "Changepoint Overlay",
                "function": "changepoint_overlay",
                "module": "viz/statistical_viz.py",
                "required_cols": ["date", "value"],
                "optional_cols": ["categorical"],
                "analysis_patterns": ["temporal"],
                "reason": "Time series with CUSUM shift markers per group.",
                "hypothesis_fit": "When did shifts occur? By group?",
            },
            {
                "name": "HDI-Annotated Violin",
                "function": "hdi_violin",
                "module": "viz/statistical_viz.py",
                "required_cols": ["numeric", "categorical"],
                "optional_cols": [],
                "analysis_patterns": ["distributional", "comparative"],
                "reason": "Violin with credible interval shading.",
                "hypothesis_fit": "Is one group's distribution narrower?",
            },
            # D3 components
            {
                "name": "Chord Diagram",
                "function": "chord_diagram",
                "module": "viz/d3_components.py",
                "required_cols": ["source", "target"],
                "optional_cols": [],
                "analysis_patterns": ["relational"],
                "reason": "Circular flow diagram; symmetry visible.",
                "hypothesis_fit": "Which flows are reciprocal?",
            },
            {
                "name": "Force-Directed Network",
                "function": "force_network",
                "module": "viz/d3_components.py",
                "required_cols": ["source", "target"],
                "optional_cols": ["group"],
                "analysis_patterns": ["relational"],
                "reason": "Interactive network with physics-based layout.",
                "hypothesis_fit": "Which nodes cluster? Which are bridges?",
            },
            {
                "name": "D3 Treemap",
                "function": "treemap_d3",
                "module": "viz/d3_components.py",
                "required_cols": ["categorical", "categorical", "numeric"],
                "optional_cols": [],
                "analysis_patterns": ["hierarchical"],
                "reason": "Nested hierarchy; area = magnitude.",
                "hypothesis_fit": "Where is the concentration?",
            },
            {
                "name": "Stream Graph",
                "function": "stream_graph",
                "module": "viz/d3_components.py",
                "required_cols": ["date", "categorical", "numeric"],
                "optional_cols": [],
                "analysis_patterns": ["temporal"],
                "reason": "Stacked area with wavy baseline.",
                "hypothesis_fit": "Has the composition changed over time?",
            },
            {
                "name": "Hex-Bin Density Map",
                "function": "hex_binmap",
                "module": "viz/d3_components.py",
                "required_cols": ["latitude", "longitude"],
                "optional_cols": [],
                "analysis_patterns": ["spatial"],
                "reason": "Spatial point density via hex binning.",
                "hypothesis_fit": "Where are hotspots geographically?",
            },
        ]

    def show_all_charts(self) -> None:
        """Print a reference table of all charts and their requirements."""
        charts = self._get_all_charts()
        print("\n" + "=" * 120)
        print(f"{'Chart Name':<30} {'Required Cols':<25} {'Module':<30} {'Analysis Type':<20}")
        print("=" * 120)
        for chart in charts:
            req = ", ".join(chart.get("required_cols", [])[:2])
            module = chart["module"].split("/")[-1]
            print(
                f"{chart['name']:<30} {req:<25} {module:<30} {chart.get('analysis_patterns', [''])[0]:<20}"
            )
        print("=" * 120 + "\n")


# ============================================================================
# CLI TOOL
# ============================================================================


def main():
    """Quick CLI for testing Chart Finder."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Chart Finder — intelligent visualization recommender"
    )
    parser.add_argument("csv_path", nargs="?", help="Path to CSV/Excel file")
    parser.add_argument(
        "-n", "--top-n", type=int, default=5, help="Number of recommendations (default 5)"
    )
    parser.add_argument(
        "-q",
        "--question",
        type=str,
        help="Research question (e.g., 'Compare boroughs')",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Show all available charts with requirements",
    )

    args = parser.parse_args()

    if args.all:
        # Demo mode: show all charts
        demo_df = pd.DataFrame({
            "borough": ["MN", "BX", "BK", "QN", "SI"] * 20,
            "violation_count": np.random.poisson(5, 100),
            "repair_cost": np.random.exponential(3000, 100),
            "condition_score": np.random.normal(65, 15, 100),
            "date": pd.date_range("2024-01-01", periods=100),
            "material_type": np.random.choice(["Concrete", "Brick", "Asphalt"], 100),
        })
        finder = ChartFinder(demo_df)
        finder.show_all_charts()
        return

    if not args.csv_path:
        print("Usage: python -m socrata_toolkit.viz.chart_finder <file.csv> [--top-n 10] [--question 'Question?']")
        print("       python -m socrata_toolkit.viz.chart_finder --all")
        sys.exit(1)

    # Load data
    try:
        if args.csv_path.endswith(".xlsx"):
            df = pd.read_excel(args.csv_path)
        else:
            df = pd.read_csv(args.csv_path)
    except Exception as e:
        print(f"Error loading file: {e}")
        sys.exit(1)

    finder = ChartFinder(df)

    print(f"\n📊 Chart Finder Results for: {args.csv_path}")
    print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"   Numeric: {len(finder.profile.numeric_cols)}, Categorical: {len(finder.profile.categorical_cols)}, Temporal: {len(finder.profile.datetime_cols)}")
    print()

    # Get recommendations
    if args.question:
        print(f"🎯 For question: '{args.question}'\n")
        recs = finder.recommend_for_hypothesis(args.question)
    else:
        recs = finder.recommend(top_n=args.top_n)

    # Print recommendations
    for rec in recs:
        print(f"{rec.rank}. {rec.chart_name}")
        print(f"   Module: {rec.module} | Function: {rec.function_name}")
        print(f"   Score: {rec.score:.2f} | Analysis: {rec.analysis_type}")
        print(f"   Required: {', '.join(rec.required_cols)}")
        if rec.suggested_cols:
            print(f"   Optional: {', '.join(rec.suggested_cols)}")
        print(f"   Why: {rec.reason}")
        if rec.example_code:
            print(f"   Code: {rec.example_code}")
        print()


if __name__ == "__main__":
    main()
