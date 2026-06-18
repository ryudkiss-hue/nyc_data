"""
Unit tests for KPI Registry module.

Tests cover:
- KPIDefinition validation and immutability
- ThresholdConfig and threshold level determination
- TimeSeriesMetadata validation
- DimensionConfig validation
- KPIRegistry loading from YAML
- Query methods (get_kpi, by_category, by_dataset)
- Registry validation and health checks
"""

import pytest
import tempfile
from datetime import datetime, timezone, timezone
from pathlib import Path

from socrata_toolkit.kpi.models import (
    DimensionConfig,
    KPIDefinition,
    KPIResult,
    KPIValue,
    ThresholdConfig,
    ThresholdLevel,
    TimeSeriesMetadata,
    Trend,
)
from socrata_toolkit.kpi.registry import KPIRegistry


class TestThresholdConfig:
    """Tests for ThresholdConfig."""

    def test_threshold_config_creation(self):
        """Test creating threshold configuration."""
        config = ThresholdConfig()
        assert config.bronze_min == 0.0
        assert config.silver_min == 60.0
        assert config.gold_min == 80.0

    def test_get_level_bronze(self):
        """Test determining bronze level."""
        config = ThresholdConfig()
        assert config.get_level(50.0) == ThresholdLevel.BRONZE

    def test_get_level_silver(self):
        """Test determining silver level."""
        config = ThresholdConfig()
        assert config.get_level(70.0) == ThresholdLevel.SILVER

    def test_get_level_gold(self):
        """Test determining gold level."""
        config = ThresholdConfig()
        assert config.get_level(90.0) == ThresholdLevel.GOLD

    def test_get_color(self):
        """Test getting color for value."""
        config = ThresholdConfig()
        assert config.get_color(50.0) == "#ffcccc"  # Bronze/red
        assert config.get_color(70.0) == "#ffffcc"  # Silver/yellow
        assert config.get_color(90.0) == "#ccffcc"  # Gold/green

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        config = ThresholdConfig(bronze_min=0, silver_min=50, gold_min=75)
        assert config.get_level(49.9) == ThresholdLevel.BRONZE
        assert config.get_level(60.0) == ThresholdLevel.SILVER
        assert config.get_level(80.0) == ThresholdLevel.GOLD


class TestTimeSeriesMetadata:
    """Tests for TimeSeriesMetadata."""

    def test_creation_with_defaults(self):
        """Test creating with default values."""
        ts = TimeSeriesMetadata()
        assert ts.enabled is True
        assert ts.forecast_method == "exponential_smoothing"
        assert ts.forecast_periods == 3
        assert ts.confidence_interval == 0.95

    def test_validation_success(self):
        """Test valid configuration."""
        ts = TimeSeriesMetadata(
            forecast_method="linear",
            confidence_interval=0.95,
            anomaly_threshold=3.0,
        )
        errors = ts.validate()
        assert len(errors) == 0

    def test_validation_invalid_method(self):
        """Test invalid forecast method."""
        ts = TimeSeriesMetadata(forecast_method="invalid")
        errors = ts.validate()
        assert any("forecast_method" in e for e in errors)

    def test_validation_invalid_confidence(self):
        """Test invalid confidence interval."""
        ts = TimeSeriesMetadata(confidence_interval=1.5)
        errors = ts.validate()
        assert any("confidence_interval" in e for e in errors)

    def test_validation_invalid_anomaly_threshold(self):
        """Test invalid anomaly threshold."""
        ts = TimeSeriesMetadata(anomaly_threshold=-1.0)
        errors = ts.validate()
        assert any("anomaly_threshold" in e for e in errors)


class TestDimensionConfig:
    """Tests for DimensionConfig."""

    def test_creation(self):
        """Test creating dimension config."""
        dim = DimensionConfig(name="borough", values=["MN", "BK", "QN"])
        assert dim.name == "borough"
        assert len(dim.values) == 3
        assert dim.aggregation == "sum"

    def test_validation_success(self):
        """Test valid dimension."""
        dim = DimensionConfig(name="borough", aggregation="avg")
        errors = dim.validate()
        assert len(errors) == 0

    def test_validation_missing_name(self):
        """Test validation requires name."""
        dim = DimensionConfig(name="")
        errors = dim.validate()
        assert any("name" in e for e in errors)

    def test_validation_invalid_aggregation(self):
        """Test invalid aggregation."""
        dim = DimensionConfig(name="borough", aggregation="invalid")
        errors = dim.validate()
        assert any("aggregation" in e for e in errors)

    def test_valid_aggregations(self):
        """Test all valid aggregations."""
        for agg in ["sum", "avg", "count", "max", "min"]:
            dim = DimensionConfig(name="test", aggregation=agg)
            errors = dim.validate()
            assert len(errors) == 0


class TestKPIDefinition:
    """Tests for KPIDefinition."""

    def test_creation(self):
        """Test creating KPI definition."""
        kpi = KPIDefinition(
            kpi_id="PRM-001",
            name="Permit Fee Revenue",
            category="permits",
            target=100.0,
        )
        assert kpi.kpi_id == "PRM-001"
        assert kpi.name == "Permit Fee Revenue"
        assert kpi.category == "permits"
        assert kpi.is_valid()

    def test_validation_missing_kpi_id(self):
        """Test validation requires kpi_id."""
        kpi = KPIDefinition(
            kpi_id="",
            name="Test",
            category="permits",
        )
        assert not kpi.is_valid()
        errors = kpi.validate()
        assert any("kpi_id" in e for e in errors)

    def test_validation_missing_category(self):
        """Test validation requires category."""
        kpi = KPIDefinition(
            kpi_id="TEST-001",
            name="Test",
            category="",
        )
        assert not kpi.is_valid()
        errors = kpi.validate()
        assert any("category" in e for e in errors)

    def test_validation_invalid_direction(self):
        """Test invalid direction."""
        kpi = KPIDefinition(
            kpi_id="TEST-001",
            name="Test",
            category="permits",
            direction="invalid",
        )
        assert not kpi.is_valid()
        errors = kpi.validate()
        assert any("direction" in e for e in errors)

    def test_with_dimensions(self):
        """Test KPI with dimensions."""
        kpi = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
            dimensions=[
                DimensionConfig(name="borough", values=["MN", "BK"]),
            ],
        )
        assert len(kpi.dimensions) == 1
        assert kpi.dimensions[0].name == "borough"

    def test_with_thresholds(self):
        """Test KPI with custom thresholds."""
        thresholds = ThresholdConfig(bronze_min=0, silver_min=50, gold_min=80)
        kpi = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
            threshold_config=thresholds,
        )
        assert kpi.threshold_config.gold_min == 80


class TestKPIValue:
    """Tests for KPIValue."""

    def test_creation(self):
        """Test creating KPI value."""
        now = datetime.now(timezone.utc)
        val = KPIValue(value=85.5, timestamp=now, period="current")
        assert val.value == 85.5
        assert val.timestamp == now
        assert val.period == "current"

    def test_with_dimension(self):
        """Test KPI value with dimension."""
        val = KPIValue(
            value=90.0,
            timestamp=datetime.now(timezone.utc),
            dimension_name="borough",
            dimension_value="MN",
        )
        assert val.dimension_name == "borough"
        assert val.dimension_value == "MN"


class TestTrend:
    """Tests for Trend."""

    def test_creation(self):
        """Test creating trend."""
        trend = Trend(
            period_over_period=5.0,
            anomaly_flagged=False,
        )
        assert trend.period_over_period == 5.0
        assert trend.anomaly_flagged is False

    def test_with_forecast(self):
        """Test trend with forecast."""
        trend = Trend(
            forecast_next_period=105.0,
            forecast_ci_lower=100.0,
            forecast_ci_upper=110.0,
        )
        assert trend.forecast_next_period == 105.0
        assert trend.forecast_ci_lower == 100.0
        assert trend.forecast_ci_upper == 110.0

    def test_with_anomaly(self):
        """Test trend with anomaly."""
        trend = Trend(
            anomaly_flagged=True,
            anomaly_severity="high",
            anomaly_z_score=3.5,
        )
        assert trend.anomaly_flagged is True
        assert trend.anomaly_severity == "high"
        assert trend.anomaly_z_score == 3.5


class TestKPIResult:
    """Tests for KPIResult."""

    def test_creation(self):
        """Test creating KPI result."""
        kpi_def = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
        )
        result = KPIResult(
            kpi_id="PRM-001",
            kpi_definition=kpi_def,
            current_value=85.0,
            target=100.0,
            status="yellow",
        )
        assert result.kpi_id == "PRM-001"
        assert result.current_value == 85.0

    def test_to_dict(self):
        """Test converting to dictionary."""
        kpi_def = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
        )
        result = KPIResult(
            kpi_id="PRM-001",
            kpi_definition=kpi_def,
            current_value=85.0,
            target=100.0,
        )
        result_dict = result.to_dict()
        assert result_dict["kpi_id"] == "PRM-001"
        assert result_dict["current_value"] == 85.0
        assert "computed_at" in result_dict

    def test_status_color_gold(self):
        """Test status color for gold level."""
        kpi_def = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
        )
        result = KPIResult(
            kpi_id="PRM-001",
            kpi_definition=kpi_def,
            current_value=90.0,
            target=100.0,
        )
        assert result.get_status_color() == "#2ecc71"  # Green


class TestKPIRegistry:
    """Tests for KPIRegistry singleton."""

    def test_singleton_instance(self):
        """Test singleton pattern."""
        reg1 = KPIRegistry.instance()
        reg2 = KPIRegistry.instance()
        assert reg1 is reg2

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file."""
        registry = KPIRegistry()
        with pytest.raises(FileNotFoundError):
            registry.load_definitions("/nonexistent/path.yaml")

    def test_get_kpi_not_found(self):
        """Test getting non-existent KPI."""
        registry = KPIRegistry()
        registry._loaded = True  # Fake loaded state
        assert registry.get_kpi("NONEXISTENT-001") is None

    def test_get_all_kpis_empty(self):
        """Test getting all KPIs when none loaded."""
        registry = KPIRegistry()
        registry._loaded = True
        assert len(registry.get_all_kpis()) == 0

    def test_validate_registry_empty(self):
        """Test validating empty registry."""
        registry = KPIRegistry()
        registry._loaded = True
        validation = registry.validate_registry()
        assert validation["total_kpis"] == 0
        assert len(validation["duplicate_ids"]) == 0

    def test_len_operation(self):
        """Test len() on registry."""
        registry = KPIRegistry()
        registry._loaded = True
        assert len(registry) == 0

    def test_iteration(self):
        """Test iterating over registry."""
        registry = KPIRegistry()
        registry._loaded = True
        kpis = list(registry)
        assert len(kpis) == 0


class TestKPIRegistryIntegration:
    """Integration tests for KPI Registry with YAML loading."""

    def test_manual_kpi_creation(self):
        """Test manually creating KPIs in registry."""
        registry = KPIRegistry()
        registry._loaded = True

        kpi = KPIDefinition(
            kpi_id="TEST-001",
            name="Test KPI",
            category="permits",
            target=100.0,
        )
        registry._kpis["TEST-001"] = kpi

        assert registry.get_kpi("TEST-001") is not None
        assert registry.get_kpi("TEST-001").name == "Test KPI"

    def test_get_kpis_by_category(self):
        """Test filtering KPIs by category."""
        registry = KPIRegistry()
        registry._loaded = True

        registry._kpis["PRM-001"] = KPIDefinition(
            kpi_id="PRM-001",
            name="Permits 1",
            category="permits",
        )
        registry._kpis["PED-001"] = KPIDefinition(
            kpi_id="PED-001",
            name="Pedestrian 1",
            category="pedestrian",
        )

        permits = registry.get_kpis_by_category("permits")
        assert len(permits) == 1
        assert permits[0].kpi_id == "PRM-001"

    def test_get_kpis_by_dataset(self):
        """Test filtering KPIs by dataset."""
        registry = KPIRegistry()
        registry._loaded = True

        registry._kpis["TEST-001"] = KPIDefinition(
            kpi_id="TEST-001",
            name="Test 1",
            category="permits",
            source_dataset_key="inspection",
        )
        registry._kpis["TEST-002"] = KPIDefinition(
            kpi_id="TEST-002",
            name="Test 2",
            category="permits",
            source_dataset_key="violations",
        )

        inspection_kpis = registry.get_kpis_by_dataset("inspection")
        assert len(inspection_kpis) == 1
        assert inspection_kpis[0].kpi_id == "TEST-001"

    def test_chart_recommendations(self):
        """Test chart recommendations."""
        registry = KPIRegistry()
        registry._loaded = True

        registry._kpis["TEST-001"] = KPIDefinition(
            kpi_id="TEST-001",
            name="Test",
            category="permits",
            primary_chart_type="gauge",
            alternative_chart_types=["bar", "line"],
        )

        recommendations = registry.get_chart_recommendations("TEST-001")
        assert recommendations["primary"] == "gauge"
        assert "bar" in recommendations["alternatives"]

    def test_registry_validation_summary(self):
        """Test registry validation summary."""
        registry = KPIRegistry()
        registry._loaded = True

        # Add valid KPI
        registry._kpis["PRM-001"] = KPIDefinition(
            kpi_id="PRM-001",
            name="Test",
            category="permits",
        )

        validation = registry.validate_registry()
        assert validation["total_kpis"] == 1
        assert len(validation["duplicate_ids"]) == 0
        assert validation["by_category"]["permits"] == 1

    def test_to_dict_export(self):
        """Test exporting registry as dictionary."""
        registry = KPIRegistry()
        registry._loaded = True

        registry._kpis["PRM-001"] = KPIDefinition(
            kpi_id="PRM-001",
            name="Permit Revenue",
            category="permits",
            target=1000.0,
            unit="$",
            primary_chart_type="bar",
            source_dataset_key="permits",
        )

        export = registry.to_dict()
        assert "PRM-001" in export
        assert export["PRM-001"]["name"] == "Permit Revenue"
        assert export["PRM-001"]["category"] == "permits"


class TestCategoryMapping:
    """Tests for category mapping."""

    def test_map_category_by_dataset(self):
        """Test category mapping from dataset category."""
        registry = KPIRegistry()
        category = registry._map_category("core_daily", "UNKNOWN-001")
        assert category == "permits"

    def test_map_category_by_kpi_prefix(self):
        """Test category mapping from KPI prefix."""
        registry = KPIRegistry()
        assert registry._map_category("unknown", "PRM-001") == "permits"
        assert registry._map_category("unknown", "PED-001") == "pedestrian"
        assert registry._map_category("unknown", "SAF-001") == "safety"
        assert registry._map_category("unknown", "CAP-001") == "budget"
        assert registry._map_category("unknown", "CMP-001") == "compliance"


class TestChartTypeMapping:
    """Tests for chart type mapping."""

    def test_chart_type_gauge_indicators(self):
        """Test gauge chart types."""
        registry = KPIRegistry()
        assert registry._get_chart_type("PRM-002") == "indicator"
        assert registry._get_chart_type("APS-001") == "indicator"

    def test_chart_type_bar_indicators(self):
        """Test bar chart types."""
        registry = KPIRegistry()
        assert registry._get_chart_type("PRM-001") == "bar"
        assert registry._get_chart_type("COORD-002") == "bar"

    def test_chart_type_funnel(self):
        """Test funnel chart types."""
        registry = KPIRegistry()
        assert registry._get_chart_type("CAP-001") == "funnel"
        assert registry._get_chart_type("COORD-001") == "funnel"

    def test_alternative_charts(self):
        """Test alternative chart suggestions."""
        registry = KPIRegistry()
        alts = registry._get_alternative_charts("PRM-001")
        assert isinstance(alts, list)
        assert len(alts) > 0


class TestKPINameGeneration:
    """Tests for KPI name generation."""

    def test_get_kpi_name_permit(self):
        """Test name generation for permit KPI."""
        registry = KPIRegistry()
        name = registry._get_kpi_name("PRM-001")
        assert "Permit" in name
        assert "001" in name

    def test_get_kpi_name_pedestrian(self):
        """Test name generation for pedestrian KPI."""
        registry = KPIRegistry()
        name = registry._get_kpi_name("PED-002")
        assert "Pedestrian" in name

    def test_get_kpi_name_unknown_prefix(self):
        """Test name generation for unknown prefix."""
        registry = KPIRegistry()
        name = registry._get_kpi_name("XYZ-999")
        assert "XYZ" in name


# Performance and edge cases
class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_empty_dimensions_list(self):
        """Test KPI with no dimensions."""
        kpi = KPIDefinition(
            kpi_id="TEST-001",
            name="Test",
            category="permits",
            dimensions=[],
        )
        assert len(kpi.dimensions) == 0
        # Empty dimensions are valid
        errors = kpi.validate()
        assert len(errors) == 0

    def test_large_threshold_values(self):
        """Test with large threshold values."""
        config = ThresholdConfig(
            bronze_min=0.0,
            silver_min=5000.0,
            gold_min=10000.0,
            max_value=100000.0,
        )
        # 50000 is >= 10000 (gold_min), so it's GOLD level
        assert config.get_level(50000.0) == ThresholdLevel.GOLD
        # Test a value in silver range
        assert config.get_level(7500.0) == ThresholdLevel.SILVER

    def test_negative_values(self):
        """Test handling negative KPI values."""
        kpi = KPIDefinition(
            kpi_id="TEST-001",
            name="Test",
            category="permits",
            direction="down",  # Lower is better
        )
        result = KPIResult(
            kpi_id="TEST-001",
            kpi_definition=kpi,
            current_value=-10.0,
            target=0.0,
        )
        assert result.current_value == -10.0

    def test_zero_values(self):
        """Test handling zero KPI values."""
        result = KPIResult(
            kpi_id="TEST-001",
            kpi_definition=KPIDefinition(
                kpi_id="TEST-001",
                name="Test",
                category="permits",
            ),
            current_value=0.0,
            target=100.0,
        )
        assert result.current_value == 0.0
