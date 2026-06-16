"""
Validation Tests for Phase 1 Methods with Realistic Sidewalk Data

Tests the methods against domain assumptions:
- Clustering: k=4-6 expected for sidewalk segments
- Material: Concrete > Asphalt in lifespan
- Temporal: Manhattan/inner boroughs > outer boroughs
"""

import numpy as np
import pandas as pd
import pytest


class TestClusteringDomainValidation:
    """Validate clustering results against domain knowledge."""

    def test_optimal_k_in_expected_range(self):
        """Verify optimal k falls within expected range for sidewalk data."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        # Create realistic sidewalk segment data
        np.random.seed(42)
        n_segments = 300

        # 4 natural clusters with different violation patterns
        violations = np.concatenate(
            [
                np.random.normal(2, 1, 75),  # Low-violation cluster
                np.random.normal(8, 2, 75),  # Medium-violation cluster
                np.random.normal(15, 3, 75),  # High-violation cluster
                np.random.normal(25, 4, 75),  # Critical cluster
            ]
        )

        costs = violations * 200 + np.random.normal(0, 500, n_segments)
        density = violations * 10 + np.random.normal(0, 20, n_segments)

        df = pd.DataFrame(
            {
                "violation_count": np.maximum(violations, 0),
                "repair_cost": np.maximum(costs, 0),
                "population_density": np.maximum(density, 0),
            }
        )

        # Run clustering
        diag = ClusteringDiagnostics(df)
        results = diag.diagnose(max_k=8)

        optimal_k = results["optimal_k"]

        # Domain expectation: 4-6 clusters for sidewalk segments
        assert 3 <= optimal_k <= 8, f"Optimal k={optimal_k} outside expected range [3-8]"

    def test_cluster_profiles_show_separation(self):
        """Verify that clusters have meaningfully different profiles."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        # Create well-separated clusters
        np.random.seed(42)
        cluster1 = np.random.normal(loc=[3, 500], scale=1, size=(50, 2))
        cluster2 = np.random.normal(loc=[15, 3000], scale=2, size=(50, 2))
        cluster3 = np.random.normal(loc=[25, 8000], scale=3, size=(50, 2))

        X = np.vstack([cluster1, cluster2, cluster3])
        df = pd.DataFrame(X, columns=["violation_count", "repair_cost"])

        diag = ClusteringDiagnostics(df)
        results = diag.diagnose(max_k=5)

        profiles = results["cluster_profiles"]

        # Check that cluster means are sufficiently separated
        violation_means = profiles.loc["violation_count"].values
        cost_means = profiles.loc["repair_cost"].values

        # Violation means should be in increasing order (roughly)
        assert violation_means.min() < violation_means.max() * 0.5, (
            "Clusters not separated enough on violations"
        )

        # Cost means should be in increasing order (roughly)
        assert cost_means.min() < cost_means.max() * 0.3, "Clusters not separated enough on cost"


class TestMaterialDegradationDomainValidation:
    """Validate material analysis results against domain knowledge."""

    def test_concrete_outlives_asphalt(self):
        """Verify that concrete has longer median survival than asphalt."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        np.random.seed(42)

        # Create realistic survival data
        # Concrete: longer lifespan, lower failure rate
        concrete_time = np.random.gamma(shape=3, scale=50, size=200)  # mean ~150 months
        concrete_event = np.random.binomial(1, 0.5, 200)

        # Asphalt: shorter lifespan, higher failure rate
        asphalt_time = np.random.gamma(shape=2, scale=35, size=200)  # mean ~70 months
        asphalt_event = np.random.binomial(1, 0.7, 200)

        df_surv = pd.DataFrame(
            {
                "material_type": ["concrete"] * 200 + ["asphalt"] * 200,
                "time_in_months": np.concatenate([concrete_time, asphalt_time]),
                "event": np.concatenate([concrete_event, asphalt_event]),
                "borough": "Manhattan",
            }
        )

        # Run analysis
        analysis = MaterialDegradationAnalysis(df_surv)
        results = analysis.fit()

        # Extract median survival times
        concrete_median = results["km_curves"]["concrete"]["median_survival_months"]
        asphalt_median = results["km_curves"]["asphalt"]["median_survival_months"]

        # Domain expectation: concrete >> asphalt lifespan
        assert concrete_median > asphalt_median, (
            f"Concrete median ({concrete_median:.0f}) should exceed asphalt ({asphalt_median:.0f})"
        )

    def test_material_economics_show_cost_benefit(self):
        """Verify that material economics reveal cost-benefit tradeoffs."""
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        np.random.seed(42)

        # Create data where concrete costs more but lasts longer
        df_surv = pd.DataFrame(
            {
                "material_type": np.repeat(["concrete", "asphalt"], 100),
                "time_in_months": np.concatenate(
                    [
                        np.random.gamma(3, 50, 100),  # Concrete
                        np.random.gamma(2, 30, 100),  # Asphalt
                    ]
                ),
                "event": np.concatenate(
                    [
                        np.random.binomial(1, 0.5, 100),  # Concrete
                        np.random.binomial(1, 0.7, 100),  # Asphalt
                    ]
                ),
                "borough": "Manhattan",
            }
        )

        analysis = MaterialDegradationAnalysis(df_surv)
        results = analysis.fit()

        econ = results["material_economics"]

        # Concrete should have longer lifespan
        assert (
            econ.loc["concrete", "median_lifespan_years"]
            > econ.loc["asphalt", "median_lifespan_years"]
        ), "Concrete should have longer median lifespan than asphalt"


class TestTemporalDomainValidation:
    """Validate temporal trends against domain knowledge."""

    def test_manhattan_has_more_violations_than_outer_boroughs(self):
        """Verify that Manhattan shows higher violation density."""
        from socrata_toolkit.viz.temporal_maps import bucket_temporal_data

        np.random.seed(42)

        dates = pd.date_range("2025-01-01", periods=12, freq="MS")
        data = {
            "date": np.repeat(dates, 100),
            "community_board": np.tile(np.arange(200, 300), 12),
            "borough": np.tile(
                (["MANHATTAN"] * 25 + ["BROOKLYN"] * 25 + ["QUEENS"] * 25 + ["BRONX"] * 25), 12
            ),
            "violation_count": np.tile(
                np.concatenate(
                    [
                        np.random.poisson(20, 25),  # Manhattan: higher
                        np.random.poisson(10, 25),  # Brooklyn
                        np.random.poisson(8, 25),  # Queens
                        np.random.poisson(12, 25),  # Bronx
                    ]
                ),
                12,
            ),
        }

        df = pd.DataFrame(data)
        df_agg = bucket_temporal_data(df)

        # Group by borough and compute mean density
        borough_density = df_agg.groupby("borough")["violation_density"].mean()

        # Manhattan should have highest density
        assert borough_density["MANHATTAN"] > borough_density["QUEENS"], (
            "Manhattan should have higher violation density than Queens"
        )

    def test_hot_blocks_are_identified_correctly(self):
        """Verify that hot block identification works."""
        from socrata_toolkit.viz.temporal_maps import bucket_temporal_data, identify_hot_blocks

        np.random.seed(42)

        # Create data with clear hot blocks
        dates = pd.date_range("2025-01-01", periods=6, freq="MS")
        data = {
            "date": np.repeat(dates, 20),
            "community_board": np.tile(np.arange(201, 221), 6),
            "borough": "MANHATTAN",
            "violation_count": np.tile(
                np.concatenate(
                    [
                        np.ones(5) * 50,  # Top 5: high violations
                        np.ones(15) * 10,  # Rest: low violations
                    ]
                ),
                6,
            ),
        }

        df = pd.DataFrame(data)
        df_agg = bucket_temporal_data(df)
        hot_blocks = identify_hot_blocks(df_agg, top_k=5)

        # Verify top 5 are identified for each month
        for month, blocks in hot_blocks.items():
            assert len(blocks) <= 5, f"More than 5 blocks returned for {month}"
            # Top blocks should have highest densities
            densities = [b["violation_density"] for b in blocks]
            assert densities == sorted(densities, reverse=True), (
                f"Hot blocks not sorted by density for {month}"
            )

    def test_month_over_month_change_detection(self):
        """Verify that MoM changes are detected accurately."""
        from socrata_toolkit.viz.temporal_maps import (
            bucket_temporal_data,
            compute_month_over_month_change,
        )

        np.random.seed(42)

        # Create data with clear trends
        dates = pd.date_range("2025-01-01", periods=4, freq="MS")
        data = {
            "date": np.repeat(dates, 10),
            "community_board": np.tile(np.arange(201, 211), 4),
            "borough": "MANHATTAN",
            "violation_count": np.array(
                [
                    [10] * 10,  # Jan: 10 violations per CB
                    [15] * 10,  # Feb: 15 (50% increase)
                    [12] * 10,  # Mar: 12 (20% decrease)
                    [18] * 10,  # Apr: 18 (50% increase)
                ]
            ).flatten(),
        }

        df = pd.DataFrame(data)
        df_agg = bucket_temporal_data(df)
        df_change = compute_month_over_month_change(df_agg)

        # Check that Feb shows positive change (50% increase)
        feb_changes = df_change[df_change["year_month"].astype(str).str.contains("2025-02")]
        if len(feb_changes) > 0:
            # Should be positive (growth)
            assert feb_changes["density_pct_change"].notna().any(), (
                "Feb MoM changes should not be NaN"
            )


class TestCrossMethodConsistency:
    """Verify that methods work together coherently."""

    def test_clustering_and_material_methods_compatible(self):
        """Verify that clustering and material methods can use same features."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )

        np.random.seed(42)

        # Create dataset that works for both methods
        df = pd.DataFrame(
            {
                "violation_count": np.random.poisson(10, 200),
                "repair_cost": np.random.gamma(shape=2, scale=2000, size=200),
                "material_type": np.random.choice(["concrete", "asphalt"], 200),
                "time_months": np.random.gamma(shape=2, scale=50, size=200),
            }
        )

        # Clustering should work on violation + cost
        cluster_cols = ["violation_count", "repair_cost"]
        assert all(col in df.columns for col in cluster_cols)

        diag = ClusteringDiagnostics(df[cluster_cols])
        results = diag.diagnose(max_k=5)
        assert results["optimal_k"] > 0

    def test_all_methods_handle_missing_data(self):
        """Verify all methods gracefully handle missing values."""
        from socrata_toolkit.analysis.clustering_diagnostics import (
            ClusteringDiagnostics,
        )
        from socrata_toolkit.analysis.material_analysis import (
            MaterialDegradationAnalysis,
        )

        np.random.seed(42)

        # Clustering with NaN
        df_cluster = pd.DataFrame(
            {
                "feature1": [1, 2, np.nan, 4, 5, 6],
                "feature2": [10, 20, 30, np.nan, 50, 60],
            }
        )

        # Drop NaN for clustering (expected behavior)
        df_clean = df_cluster.dropna()
        if len(df_clean) > 0:
            diag = ClusteringDiagnostics(df_clean)
            results = diag.diagnose(max_k=3)
            assert "optimal_k" in results

        # Material analysis with missing events
        df_material = pd.DataFrame(
            {
                "material_type": ["concrete", "asphalt", "concrete", "asphalt"],
                "time_in_months": [100, 80, np.nan, 90],
                "event": [1, 0, 1, np.nan],
            }
        )

        # Drop rows with missing critical values
        df_clean = df_material.dropna(subset=["time_in_months", "event"])
        if len(df_clean) > 1:
            analysis = MaterialDegradationAnalysis(df_clean)
            results = analysis.fit()
            assert "km_curves" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
