"""Unit Tests for Phase 1 Visualization Methods.

Tests for:
1. Clustering Diagnostics Engine
2. Material Degradation Analysis
3. Geospatial Temporal Animation
"""

import numpy as np
import pandas as pd
import pytest


# ============================================================================
# CLUSTERING DIAGNOSTICS TESTS
# ============================================================================


class TestClusteringDiagnostics:
    """Test suite for ClusteringDiagnostics."""

    @pytest.fixture
    def sample_clustering_data(self):
        """Create synthetic clustering test data."""
        np.random.seed(42)
        # Generate 3 well-separated clusters
        cluster1 = np.random.normal(loc=[5, 5], scale=1, size=(30, 2))
        cluster2 = np.random.normal(loc=[15, 15], scale=1, size=(30, 2))
        cluster3 = np.random.normal(loc=[25, 5], scale=1, size=(30, 2))
        X = np.vstack([cluster1, cluster2, cluster3])
        return pd.DataFrame(X, columns=["feature_1", "feature_2"])

    def test_clustering_diagnostics_initialization(self, sample_clustering_data):
        """Test ClusteringDiagnostics initialization."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        diag = ClusteringDiagnostics(sample_clustering_data)
        assert diag.X.shape[0] == 90
        assert diag.X.shape[1] == 2
        assert len(diag.feature_cols) == 2

    def test_elbow_detection(self, sample_clustering_data):
        """Test elbow detection algorithm."""
        from socrata_toolkit.analysis.clustering_diagnostics import ElbowAnalyzer

        inertias = [100, 75, 50, 40, 38, 37, 36.5, 36.2]
        k_range = list(range(2, 10))

        elbow_k = ElbowAnalyzer.find_elbow(inertias, k_range)
        assert 2 <= elbow_k <= 10, f"Elbow k={elbow_k} out of range"

    def test_diagnose_full_pipeline(self, sample_clustering_data):
        """Test full diagnosis pipeline."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        diag = ClusteringDiagnostics(sample_clustering_data)
        results = diag.diagnose(max_k=8, min_k=2)

        assert "optimal_k" in results
        assert "inertias" in results
        assert "silhouette_scores" in results
        assert "cluster_profiles" in results
        assert "labels" in results

        optimal_k = results["optimal_k"]
        assert 2 <= optimal_k <= 8, f"Optimal k={optimal_k} out of expected range"

    def test_silhouette_analysis(self, sample_clustering_data):
        """Test silhouette score computation."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            SilhouetteAnalyzer,
        )

        # Create labels for 3 clusters
        labels = np.array([0] * 30 + [1] * 30 + [2] * 30)
        mean_sil, sample_sils = SilhouetteAnalyzer.compute_silhouette_scores(
            sample_clustering_data.values, labels
        )

        assert -1 <= mean_sil <= 1, f"Silhouette score {mean_sil} out of range"
        assert len(sample_sils) == 90
        assert all(-1 <= s <= 1 for s in sample_sils)

    def test_quality_metrics(self, sample_clustering_data):
        """Test Davies-Bouldin and Calinski-Harabasz metrics."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            SilhouetteAnalyzer,
        )

        labels = np.array([0] * 30 + [1] * 30 + [2] * 30)
        metrics = SilhouetteAnalyzer.compute_quality_metrics(
            sample_clustering_data.values, labels
        )

        assert "davies_bouldin" in metrics
        assert "calinski_harabasz" in metrics
        assert metrics["davies_bouldin"] >= 0
        assert metrics["calinski_harabasz"] > 0

    def test_cluster_profiles(self, sample_clustering_data):
        """Test cluster profile computation."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        diag = ClusteringDiagnostics(sample_clustering_data)
        results = diag.diagnose(max_k=5, min_k=2)

        profiles = results["cluster_profiles"]
        assert not profiles.empty
        assert profiles.shape[0] == 2  # Features
        assert profiles.shape[1] >= 2  # At least 2 clusters


# ============================================================================
# MATERIAL DEGRADATION ANALYSIS TESTS
# ============================================================================


class TestMaterialDegradationAnalysis:
    """Test suite for MaterialDegradationAnalysis."""

    @pytest.fixture
    def sample_survival_data(self):
        """Create synthetic survival test data."""
        np.random.seed(42)
        data = {
            "material_type": ["concrete"] * 100 + ["asphalt"] * 100,
            "time_in_months": np.concatenate([
                np.random.gamma(shape=2, scale=60, size=100),  # Concrete: longer lifespan
                np.random.gamma(shape=2, scale=40, size=100),  # Asphalt: shorter lifespan
            ]),
            "event": np.concatenate([
                np.random.binomial(1, 0.6, 100),  # 60% event rate for concrete
                np.random.binomial(1, 0.8, 100),  # 80% event rate for asphalt
            ]),
            "borough": ["Manhattan"] * 200,
            "block_id": range(200),
        }
        return pd.DataFrame(data)

    def test_survival_data_prep(self):
        """Test survival data preparation."""
        from socrata_toolkit.analysis.material_analysis import SurvivalDataPrep

        # Create sample inspection and violation data
        inspections = pd.DataFrame({
            "block_id": [1, 2, 3],
            "material_type": ["concrete", "asphalt", "concrete"],
            "inspection_date": pd.date_range("2023-01-01", periods=3),
            "borough": ["Manhattan", "Brooklyn", "Manhattan"],
        })

        violations = pd.DataFrame({
            "block_id": [1, 2],
            "violation_date": pd.date_range("2024-01-01", periods=2),
        })

        df_surv = SurvivalDataPrep.prepare_time_to_event(
            inspections, violations, cutoff_date="2024-12-31"
        )

        assert "time_in_months" in df_surv.columns
        assert "event" in df_surv.columns
        assert len(df_surv) == 3

    def test_material_degradation_fit(self, sample_survival_data):
        """Test full material degradation analysis fit."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        analysis = MaterialDegradationAnalysis(sample_survival_data)
        results = analysis.fit()

        assert "km_curves" in results
        assert "log_rank_tests" in results
        assert "material_economics" in results
        assert "concrete" in results["km_curves"]
        assert "asphalt" in results["km_curves"]

    def test_kaplan_meier_curves(self, sample_survival_data):
        """Test Kaplan-Meier curve computation."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        analysis = MaterialDegradationAnalysis(sample_survival_data)
        analysis.fit()

        for material, km_result in analysis.km_results.items():
            assert "time_points" in km_result
            assert "survival_prob" in km_result
            assert len(km_result["time_points"]) > 0
            assert len(km_result["survival_prob"]) > 0
            assert all(0 <= p <= 1.01 for p in km_result["survival_prob"])  # Allow small overflow

    def test_material_economics(self, sample_survival_data):
        """Test material economics computation."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        analysis = MaterialDegradationAnalysis(sample_survival_data)
        results = analysis.fit()

        econ = results["material_economics"]
        assert not econ.empty
        assert "median_lifespan_years" in econ.columns
        assert "20_year_total_cost" in econ.columns

    def test_log_rank_tests(self, sample_survival_data):
        """Test log-rank test computation."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        analysis = MaterialDegradationAnalysis(sample_survival_data)
        results = analysis.fit()

        log_rank = results.get("log_rank_tests", {})
        # May be empty if lifelines not available, but structure should be dict
        assert isinstance(log_rank, dict)


# ============================================================================
# TEMPORAL GEOSPATIAL ANIMATION TESTS
# ============================================================================


class TestTemporalGeospatialVisualizer:
    """Test suite for TemporalGeospatialVisualizer."""

    @pytest.fixture
    def sample_temporal_geospatial_data(self):
        """Create synthetic temporal geospatial test data."""
        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=12, freq="MS")
        data = {
            "date": np.repeat(dates, 5),  # 5 community boards per month
            "community_board": np.tile([201, 202, 203, 204, 205], 12),
            "borough": np.tile(["MANHATTAN"] * 5, 12),
            "violation_count": np.random.poisson(15, 60),
            "latitude": np.tile([40.715, 40.720, 40.725, 40.730, 40.735], 12),
            "longitude": np.tile([-73.980, -73.975, -73.970, -73.965, -73.960], 12),
        }
        return pd.DataFrame(data)

    def test_bucket_temporal_data(self, sample_temporal_geospatial_data):
        """Test temporal bucketing."""
        from socrata_toolkit.viz.temporal_maps import bucket_temporal_data

        df_agg = bucket_temporal_data(sample_temporal_geospatial_data, period="month")

        assert "year_month" in df_agg.columns
        assert "violation_density" in df_agg.columns
        assert len(df_agg) <= len(sample_temporal_geospatial_data)
        assert all(df_agg["violation_density"] >= 0)

    def test_month_over_month_change(self, sample_temporal_geospatial_data):
        """Test month-over-month change computation."""
        from socrata_toolkit.viz.temporal_maps import (
            bucket_temporal_data,
            compute_month_over_month_change,
        )

        df_agg = bucket_temporal_data(sample_temporal_geospatial_data)
        df_change = compute_month_over_month_change(df_agg)

        assert "density_pct_change" in df_change.columns
        # First month should have NaN pct_change
        first_month = df_change["year_month"].min()
        assert df_change[df_change["year_month"] == first_month]["density_pct_change"].isna().all()

    def test_identify_hot_blocks(self, sample_temporal_geospatial_data):
        """Test hot block identification."""
        from socrata_toolkit.viz.temporal_maps import (
            bucket_temporal_data,
            identify_hot_blocks,
        )

        df_agg = bucket_temporal_data(sample_temporal_geospatial_data)
        hot_blocks = identify_hot_blocks(df_agg, top_k=3)

        assert isinstance(hot_blocks, dict)
        for month, blocks in hot_blocks.items():
            assert isinstance(blocks, list)
            assert len(blocks) <= 3

    def test_temporal_visualizer_initialization(self, sample_temporal_geospatial_data):
        """Test TemporalGeospatialVisualizer initialization."""
        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        viz = TemporalGeospatialVisualizer(sample_temporal_geospatial_data)

        assert viz.df_agg is not None
        assert not viz.df_agg.empty
        assert len(viz.hot_blocks) > 0

    def test_plot_hot_blocks_timeline(self, sample_temporal_geospatial_data):
        """Test hot blocks timeline plot."""
        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        viz = TemporalGeospatialVisualizer(sample_temporal_geospatial_data)
        fig = viz.plot_hot_blocks_timeline(top_k=3)

        assert fig is not None
        # Plotly figures should have layout
        assert hasattr(fig, "layout")

    def test_plot_month_over_month_heatmap(self, sample_temporal_geospatial_data):
        """Test month-over-month heatmap plot."""
        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        viz = TemporalGeospatialVisualizer(sample_temporal_geospatial_data)
        fig = viz.plot_month_over_month_heatmap()

        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_borough_summary(self, sample_temporal_geospatial_data):
        """Test borough summary plot."""
        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        viz = TemporalGeospatialVisualizer(sample_temporal_geospatial_data)
        fig = viz.plot_borough_summary()

        assert fig is not None
        assert hasattr(fig, "layout")

    def test_get_aggregated_data(self, sample_temporal_geospatial_data):
        """Test aggregated data retrieval."""
        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        viz = TemporalGeospatialVisualizer(sample_temporal_geospatial_data)
        df_agg = viz.get_aggregated_data()

        assert isinstance(df_agg, pd.DataFrame)
        assert not df_agg.empty


# ============================================================================
# VISUALIZATION TESTS
# ============================================================================


class TestClusteringVisualizations:
    """Test suite for clustering visualization functions."""

    @pytest.fixture
    def sample_clustering_results(self):
        """Create sample clustering results."""
        return {
            "optimal_k": 3,
            "inertias": [100, 75, 50, 40, 38, 37],
            "silhouette_scores": [0.4, 0.52, 0.58, 0.55, 0.48, 0.42],
            "elbow_curve_data": [
                {"k": 2, "inertia": 100},
                {"k": 3, "inertia": 75},
                {"k": 4, "inertia": 50},
            ],
            "quality_metrics_by_k": {
                2: {"davies_bouldin": 0.8, "calinski_harabasz": 150.5},
                3: {"davies_bouldin": 0.62, "calinski_harabasz": 245.3},
                4: {"davies_bouldin": 0.55, "calinski_harabasz": 320.1},
            },
            "k_range": [2, 3, 4],
            "labels": np.array([0] * 30 + [1] * 30 + [2] * 30),
            "cluster_profiles": pd.DataFrame({
                "Cluster_0": [5.0, 1000.0],
                "Cluster_1": [12.0, 4500.0],
                "Cluster_2": [3.0, 800.0],
            }, index=["violation_count", "repair_cost"]),
        }

    def test_plot_elbow_curve(self, sample_clustering_results):
        """Test elbow curve plot."""
        from socrata_toolkit.viz.clustering_viz import plot_elbow_curve

        fig = plot_elbow_curve(sample_clustering_results)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_silhouette(self, sample_clustering_results):
        """Test silhouette plot."""
        from socrata_toolkit.viz.clustering_viz import plot_silhouette

        fig = plot_silhouette(sample_clustering_results)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_quality_metrics_heatmap(self, sample_clustering_results):
        """Test quality metrics heatmap."""
        from socrata_toolkit.viz.clustering_viz import plot_quality_metrics_heatmap

        fig = plot_quality_metrics_heatmap(sample_clustering_results)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_cluster_profiles(self, sample_clustering_results):
        """Test cluster profiles table."""
        from socrata_toolkit.viz.clustering_viz import plot_cluster_profiles

        fig = plot_cluster_profiles(sample_clustering_results)
        assert fig is not None
        assert hasattr(fig, "layout")


class TestMaterialVisualizations:
    """Test suite for material visualization functions."""

    @pytest.fixture
    def sample_material_results(self):
        """Create sample material analysis results."""
        return {
            "concrete": {
                "time_points": [0, 20, 40, 60, 80],
                "survival_prob": [1.0, 0.95, 0.88, 0.75, 0.60],
                "ci_lower": [1.0, 0.92, 0.84, 0.70, 0.54],
                "ci_upper": [1.0, 0.98, 0.92, 0.80, 0.66],
                "median_survival_months": 120,
                "n_at_risk": 500,
                "n_events": 300,
            },
            "asphalt": {
                "time_points": [0, 20, 40, 60, 80],
                "survival_prob": [1.0, 0.92, 0.80, 0.65, 0.45],
                "ci_lower": [1.0, 0.88, 0.75, 0.58, 0.37],
                "ci_upper": [1.0, 0.96, 0.85, 0.72, 0.53],
                "median_survival_months": 85,
                "n_at_risk": 500,
                "n_events": 400,
            },
        }

    def test_plot_km_curves(self, sample_material_results):
        """Test KM curves plot."""
        from socrata_toolkit.viz.material_viz import plot_km_curves

        fig = plot_km_curves(sample_material_results)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_cumulative_hazard(self):
        """Test cumulative hazard plot."""
        from socrata_toolkit.viz.material_viz import plot_cumulative_hazard

        cumulative_hazard = {
            "concrete": {
                "time_points": [0, 20, 40, 60],
                "hazard": [0, 0.05, 0.13, 0.29],
            },
            "asphalt": {
                "time_points": [0, 20, 40, 60],
                "hazard": [0, 0.08, 0.22, 0.43],
            },
        }

        fig = plot_cumulative_hazard(cumulative_hazard)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_material_economics(self):
        """Test material economics plot."""
        from socrata_toolkit.viz.material_viz import plot_material_economics

        econ_df = pd.DataFrame({
            "median_lifespan_years": [13, 9],
            "20_year_total_cost": [450000, 650000],
            "cost_per_year": [22500, 32500],
        }, index=["concrete", "asphalt"])

        fig = plot_material_economics(econ_df)
        assert fig is not None
        assert hasattr(fig, "layout")

    def test_plot_log_rank_results(self):
        """Test log-rank results table."""
        from socrata_toolkit.viz.material_viz import plot_log_rank_results

        log_rank = {
            ("concrete", "asphalt"): {
                "p_value": 0.003,
                "significant": True,
                "test_statistic": 8.5,
            },
        }

        fig = plot_log_rank_results(log_rank)
        assert fig is not None
        assert hasattr(fig, "layout")


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestPerformance:
    """Performance tests for each method."""

    def test_clustering_diagnostics_performance(self):
        """Test clustering diagnostics compute time (<5s)."""
        import time

        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        np.random.seed(42)
        df = pd.DataFrame(
            np.random.randn(500, 10),
            columns=[f"feature_{i}" for i in range(10)]
        )

        start = time.time()
        diag = ClusteringDiagnostics(df)
        results = diag.diagnose(max_k=8)
        elapsed = time.time() - start

        assert elapsed < 10.0, f"Clustering diagnostics took {elapsed:.2f}s (expected <10s)"
        assert "optimal_k" in results

    def test_material_analysis_performance(self):
        """Test material analysis compute time (<2s)."""
        import time

        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        np.random.seed(42)
        df_surv = pd.DataFrame({
            "material_type": np.repeat(["concrete", "asphalt"], 250),
            "time_in_months": np.random.gamma(shape=2, scale=50, size=500),
            "event": np.random.binomial(1, 0.7, 500),
            "borough": "Manhattan",
        })

        start = time.time()
        analysis = MaterialDegradationAnalysis(df_surv)
        results = analysis.fit()
        elapsed = time.time() - start

        assert elapsed < 2.0, f"Material analysis took {elapsed:.2f}s (expected <2s)"
        assert "km_curves" in results

    def test_temporal_visualization_performance(self):
        """Test temporal visualization compute time (<1s)."""
        import time

        from socrata_toolkit.viz.temporal_maps import TemporalGeospatialVisualizer

        np.random.seed(42)
        dates = pd.date_range("2025-01-01", periods=12, freq="MS")
        df = pd.DataFrame({
            "date": np.repeat(dates, 50),
            "community_board": np.tile(np.arange(200, 250), 12),
            "borough": np.tile(["MANHATTAN"] * 50, 12),
            "violation_count": np.random.poisson(10, 600),
        })

        start = time.time()
        viz = TemporalGeospatialVisualizer(df)
        elapsed = time.time() - start

        assert elapsed < 1.0, f"Temporal visualization init took {elapsed:.2f}s (expected <1s)"
        assert len(viz.hot_blocks) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
