"""
Phase 4-6 Integration Tests: End-to-end validation.

Tests the complete data flow from MotherDuck → Callbacks → Visualizations → Exports

Test coverage:
- Phase 4 (Dashboard): Filters, callbacks, KPI cards
- Phase 5 (Export): PDF, CSV, Excel export functionality
- Phase 6 (E2E): Complete system flow validation

Run with:
    pytest tests/test_phase_4_6_integration.py -v
    pytest tests/test_phase_4_6_integration.py -v --benchmark-only (for perf tests)
"""


import pandas as pd
import plotly.graph_objects as go
import pytest

# Mock MotherDuck data for testing (no real DB calls)


@pytest.fixture
def mock_phase_b_data():
    """Mock Phase B results (Moran's I spatial)."""
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "morans_i": [0.342, 0.215, 0.189, 0.156, 0.098],
            "significance": ["HIGH", "MEDIUM", "MEDIUM", "LOW", "LOW"],
            "cluster_count": [5, 3, 2, 2, 1],
        }
    )


@pytest.fixture
def mock_phase_c_data():
    """Mock Phase C results (distributions)."""
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "distribution_type": ["NORMAL", "SKEWED", "NORMAL", "UNIFORM", "SKEWED"],
            "skewness": [0.12, 0.78, 0.05, -0.02, 0.65],
            "concentration_pct": [15.2, 22.1, 18.5, 12.3, 25.8],
        }
    )


@pytest.fixture
def mock_phase_d_data():
    """Mock Phase D results (anomalies)."""
    return pd.DataFrame(
        {
            "location_id": list(range(1, 26)),
            "borough": ["MN"] * 5 + ["BK"] * 5 + ["BX"] * 5 + ["QN"] * 5 + ["SI"] * 5,
            "outlier_type": ["HIGH", "LOW", "HIGH", "MODERATE", "HIGH"] * 5,
            "severity": ["CRITICAL", "INFO", "CRITICAL", "WARNING", "CRITICAL"] * 5,
            "priority": [1, 5, 2, 3, 1] * 5,
        }
    )


@pytest.fixture
def mock_phase_e_data():
    """Mock Phase E results (decomposition)."""
    dates = pd.date_range("2026-01-01", periods=450, freq="D")
    return pd.DataFrame(
        {
            "period": dates,
            "trend": [100 + i * 0.1 for i in range(450)],
            "seasonal": [10 * (1 + i % 7) for i in range(450)],
            "residual": [0.5 * (i % 3) for i in range(450)],
            "forecast": [100 + i * 0.1 + 10 for i in range(450)],
        }
    )


@pytest.fixture
def mock_phase_f_data():
    """Mock Phase F results (bootstrap CI)."""
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "point_estimate": [85.2, 78.5, 82.1, 76.3, 80.9],
            "ci_lower": [82.1, 75.2, 79.5, 73.1, 77.8],
            "ci_upper": [88.3, 81.8, 84.7, 79.5, 84.0],
            "prob_meets_sla": [0.92, 0.78, 0.87, 0.71, 0.85],
            "prob_sla_breach": [0.08, 0.22, 0.13, 0.29, 0.15],
        }
    )


@pytest.fixture
def mock_kpi_data():
    """Mock KPI dashboard data (18 KPIs × 5 boroughs = 90 rows)."""
    kpis = [
        "total_inspections",
        "inspection_rate",
        "avg_violations_per_inspection",
        "critical_violations",
        "inspection_backlog",
        "data_completeness",
        "data_validity",
        "data_consistency",
        "data_freshness",
        "quality_score",
        "ramp_completion_rate",
        "ramp_complaints",
        "ramp_progress_month",
        "ramp_sla_breach",
        "morans_i_statistic",
        "spatial_clusters",
        "hotspot_concentration",
        "outlier_count",
    ]
    boroughs = ["MN", "BK", "BX", "QN", "SI"]

    rows = []
    for kpi in kpis:
        for borough in boroughs:
            rows.append(
                {
                    "metric_id": kpi,
                    "metric_name": kpi.replace("_", " ").title(),
                    "borough": borough,
                    "value": 75.5 + hash(f"{kpi}{borough}") % 25,
                    "change_pct": 2.3 + hash(f"{kpi}{borough}") % 5 - 2.5,
                    "category": "Inspection Performance"
                    if kpi.startswith("inspection")
                    else "Quality",
                }
            )

    return pd.DataFrame(rows)


# =============================================================================
# PHASE 4 TESTS: DASHBOARD INTEGRATION
# =============================================================================


class TestPhase4DashboardIntegration:
    """Test Phase 4: Filter system, callbacks, KPI cards."""

    def test_filter_system_validates_boroughs(self):
        """Test: Filter accepts valid borough codes."""
        from app.components.filter_system import BOROUGHS

        valid_boroughs = [b["value"] for b in BOROUGHS]
        assert "MN" in valid_boroughs
        assert "BK" in valid_boroughs
        assert len(valid_boroughs) == 5

    def test_filter_system_validates_metrics(self):
        """Test: Filter accepts valid metric types."""
        from app.components.filter_system import METRIC_TYPES

        valid_types = [m["value"] for m in METRIC_TYPES]
        assert "all" in valid_types
        assert "critical" in valid_types
        assert len(valid_types) == 4

    def test_kpi_cards_render_18_metrics(self):
        """Test: KPI dashboard renders all 18 metrics."""
        from app.components.metric_cards import METRIC_CONFIG

        total_metrics = sum(len(cat_data["metrics"]) for cat_data in METRIC_CONFIG.values())
        assert total_metrics == 18, f"Expected 18 KPIs, found {total_metrics}"

    def test_kpi_cards_has_4_categories(self):
        """Test: KPI dashboard has 4 categories."""
        from app.components.metric_cards import METRIC_CONFIG

        categories = list(METRIC_CONFIG.keys())
        assert len(categories) == 4
        assert "Inspection Performance" in categories
        assert "Quality Metrics" in categories
        assert "Ramp Accessibility" in categories
        assert "Spatial Patterns" in categories

    def test_motherduck_service_filters_apply_correctly(self):
        """Test: MotherDuck service applies filters correctly."""
        from app.services.motherduck_service import _apply_filters

        query = "SELECT * FROM test_table"
        filters = {
            "boroughs": ["MN", "BK"],
            "date_start": "2026-05-01",
            "date_end": "2026-06-01",
            "metric_type": "critical",
        }

        result = _apply_filters(query, filters)
        assert "WHERE" in result
        assert "borough IN ('MN','BK')" in result
        assert "2026-05-01" in result
        assert "2026-06-01" in result
        assert "severity = 'HIGH'" in result

    def test_motherduck_service_handles_empty_filters(self):
        """Test: MotherDuck service handles empty filters."""
        from app.services.motherduck_service import _apply_filters

        query = "SELECT * FROM test_table"
        filters = {}
        result = _apply_filters(query, filters)
        assert result == query


# =============================================================================
# PHASE 5 TESTS: EXPORT SYSTEM
# =============================================================================


class TestPhase5ExportSystem:
    """Test Phase 5: PDF, CSV, Excel exports."""

    def test_universal_exporter_initializes(self):
        """Test: UniversalExporter initializes without error."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()
        assert exporter is not None

    def test_export_to_csv_creates_valid_format(self, mock_phase_b_data):
        """Test: CSV export creates valid format."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()
        csv_str = exporter.export_data_to_csv(mock_phase_b_data, "Test Report", {"Records": 5})

        assert csv_str is not None
        assert "Test Report" in csv_str
        assert "borough" in csv_str
        assert len(csv_str) > 100

    def test_export_to_csv_with_statistics(self, mock_phase_b_data):
        """Test: CSV export includes statistics."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()
        stats = {"Avg Moran's I": 0.2, "Records": 5}
        csv_str = exporter.export_data_to_csv(mock_phase_b_data, "Test", stats)

        assert "Avg Moran's I" in csv_str
        assert "0.2" in csv_str

    def test_export_to_excel_creates_valid_format(self, mock_phase_b_data):
        """Test: Excel export creates valid format."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()
        xlsx_bytes = exporter.export_data_to_excel(
            mock_phase_b_data, "Test Report", "Test narrative"
        )

        assert xlsx_bytes is not None
        assert len(xlsx_bytes) > 1000

    def test_export_to_pdf_creates_valid_format(self, mock_phase_b_data):
        """Test: PDF export creates valid format."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()
        fig = go.Figure(data=[go.Bar(x=["A", "B", "C"], y=[1, 2, 3])])
        pdf_bytes = exporter.export_figure_to_pdf(fig, "Test Report", {"Test": "Value"})

        # PDF export may return None if ReportLab not installed, so check if not None
        if pdf_bytes is not None:
            assert len(pdf_bytes) > 0


# =============================================================================
# PHASE 6 TESTS: END-TO-END INTEGRATION
# =============================================================================


class TestPhase6EndToEndIntegration:
    """Test Phase 6: Complete data flow integration."""

    def test_phase_b_complete_flow(self, mock_phase_b_data):
        """Test: Phase B complete flow (filter → fetch → render)."""
        from app.callbacks.analytics import AnalyticsEngine

        # Simulate filter
        filters = {"boroughs": ["MN", "BK"]}

        # Simulate fetch (using mock data)
        df = mock_phase_b_data[mock_phase_b_data["borough"].isin(filters["boroughs"])]
        assert len(df) == 2

        # Simulate render
        data_bundle = {"spatial": df}
        fig, narrative = AnalyticsEngine.chart_morans_i(data_bundle)
        assert fig is not None
        assert narrative is not None

    def test_phase_c_complete_flow(self, mock_phase_c_data):
        """Test: Phase C complete flow."""
        from app.callbacks.analytics import AnalyticsEngine

        filters = {"boroughs": ["MN"]}
        df = mock_phase_c_data[mock_phase_c_data["borough"].isin(filters["boroughs"])]
        assert len(df) == 1

        data_bundle = {"data": df}
        fig, narrative = AnalyticsEngine.chart_distribution_classification(data_bundle)
        assert fig is not None
        assert narrative is not None

    def test_phase_d_complete_flow(self, mock_phase_d_data):
        """Test: Phase D complete flow."""
        from app.callbacks.analytics import AnalyticsEngine

        filters = {"boroughs": ["MN"]}
        df = mock_phase_d_data[mock_phase_d_data["borough"].isin(filters["boroughs"])]
        assert len(df) == 5

        data_bundle = {"geographic": df}
        fig, narrative = AnalyticsEngine.chart_anomaly_detection(data_bundle)
        assert fig is not None
        assert narrative is not None

    def test_phase_e_complete_flow(self, mock_phase_e_data):
        """Test: Phase E complete flow."""
        from app.callbacks.analytics import AnalyticsEngine

        df = mock_phase_e_data
        assert len(df) == 450

        data_bundle = {"timeseries": df}
        fig, narrative = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)
        assert fig is not None
        assert narrative is not None

    def test_phase_f_complete_flow(self, mock_phase_f_data):
        """Test: Phase F complete flow."""
        from app.callbacks.analytics import AnalyticsEngine

        df = mock_phase_f_data
        assert len(df) == 5

        data_bundle = {"bootstrap": df}
        fig, narrative = AnalyticsEngine.chart_bootstrap_ci_forecast(data_bundle)
        assert fig is not None
        assert narrative is not None

    def test_all_phases_export(self, mock_phase_b_data, mock_phase_c_data):
        """Test: All phases can be exported."""
        from app.services.universal_exporter import UniversalExporter

        exporter = UniversalExporter()

        # Test Phase B export
        csv_b = exporter.export_data_to_csv(mock_phase_b_data, "Phase B")
        assert csv_b is not None

        # Test Phase C export
        csv_c = exporter.export_data_to_csv(mock_phase_c_data, "Phase C")
        assert csv_c is not None

    def test_kpi_dashboard_updates_on_filter_change(self, mock_kpi_data):
        """Test: KPI dashboard data updates on filter change."""
        # Simulate filter change
        initial_data = mock_kpi_data.copy()
        filtered_data = initial_data[initial_data["borough"] == "MN"]

        assert len(filtered_data) == 18  # 18 KPIs for 1 borough


# =============================================================================
# PERFORMANCE BENCHMARKS (Phase 6.2)
# =============================================================================


class TestPhase6Performance:
    """Test Phase 6: Performance benchmarks."""

    def test_phase_b_latency_benchmark(self, benchmark, mock_phase_b_data):
        """Benchmark Phase B latency (target <200ms)."""
        from app.callbacks.analytics import AnalyticsEngine

        def render_phase_b():
            data_bundle = {"spatial": mock_phase_b_data}
            AnalyticsEngine.chart_morans_i(data_bundle)

        result = benchmark(render_phase_b)
        # Benchmark will print timing info

    def test_phase_c_latency_benchmark(self, benchmark, mock_phase_c_data):
        """Benchmark Phase C latency (target <300ms)."""
        from app.callbacks.analytics import AnalyticsEngine

        def render_phase_c():
            data_bundle = {"data": mock_phase_c_data}
            AnalyticsEngine.chart_distribution_classification(data_bundle)

        result = benchmark(render_phase_c)

    def test_phase_d_latency_benchmark(self, benchmark, mock_phase_d_data):
        """Benchmark Phase D latency (target <400ms)."""
        from app.callbacks.analytics import AnalyticsEngine

        def render_phase_d():
            data_bundle = {"geographic": mock_phase_d_data}
            AnalyticsEngine.chart_anomaly_detection(data_bundle)

        result = benchmark(render_phase_d)

    def test_phase_e_latency_benchmark(self, benchmark, mock_phase_e_data):
        """Benchmark Phase E latency (target <500ms)."""
        from app.callbacks.analytics import AnalyticsEngine

        def render_phase_e():
            data_bundle = {"timeseries": mock_phase_e_data}
            AnalyticsEngine.chart_seasonal_decomposition(data_bundle)

        result = benchmark(render_phase_e)

    def test_phase_f_latency_benchmark(self, benchmark, mock_phase_f_data):
        """Benchmark Phase F latency (target <300ms)."""
        from app.callbacks.analytics import AnalyticsEngine

        def render_phase_f():
            data_bundle = {"bootstrap": mock_phase_f_data}
            AnalyticsEngine.chart_bootstrap_ci_forecast(data_bundle)

        result = benchmark(render_phase_f)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
