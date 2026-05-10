"""
Tests for Material-Aware KPI Computation (socrata_toolkit.dot_sidewalk)

Tests material-specific KPI calculation, ADA compliance rates, contractor quality scoring,
and KPI lineage tracking.
"""

import pandas as pd
import pytest
from datetime import datetime

from socrata_toolkit.dot_sidewalk import (
    SidewalkKPI,
    MaterialAwareSidewalkKPI,
    compute_sidewalk_kpis,
    compute_material_aware_kpis,
)


class TestLegacySidewalkKPI:
    """Tests for backward-compatible SidewalkKPI class."""

    def test_sidewalk_kpi_creation(self):
        """Test creating a SidewalkKPI object."""
        kpi = SidewalkKPI(
            defect_density=5.2,
            throughput_velocity=150.0,
            burn_variance=1000.0,
            first_pass_yield=0.95,
            rework_factor=0.05,
        )
        assert kpi.defect_density == 5.2
        assert kpi.throughput_velocity == 150.0
        assert kpi.burn_variance == 1000.0
        assert kpi.first_pass_yield == 0.95
        assert kpi.rework_factor == 0.05

    def test_compute_sidewalk_kpis_basic(self):
        """Test computing legacy sidewalk KPIs."""
        df = pd.DataFrame({
            "violations": [10, 15],
            "curb_miles": [2, 3],
            "built_linear_feet": [1000, 500],
            "days": [10, 5],
            "actual_spend": [100, 200],
            "planned_spend": [90, 210],
            "first_pass": [8, 10],
            "total_inspections": [10, 15],
            "rework_spend": [5, 10],
        })
        kpi = compute_sidewalk_kpis(df)

        # Verify structure
        assert isinstance(kpi, SidewalkKPI)
        assert kpi.defect_density > 0
        assert 0 <= kpi.first_pass_yield <= 1
        assert kpi.rework_factor >= 0

    def test_compute_sidewalk_kpis_zero_handling(self):
        """Test KPI computation with zero values (avoiding division errors)."""
        df = pd.DataFrame({
            "violations": [0, 0],
            "curb_miles": [0, 0],
            "built_linear_feet": [0, 0],
            "days": [0, 0],
            "actual_spend": [0, 0],
            "planned_spend": [0, 0],
            "first_pass": [0, 0],
            "total_inspections": [0, 0],
            "rework_spend": [0, 0],
        })
        # Should not raise ZeroDivisionError
        kpi = compute_sidewalk_kpis(df)
        assert kpi is not None

    def test_compute_sidewalk_kpis_missing_columns(self):
        """Test KPI computation handles missing columns gracefully."""
        df = pd.DataFrame({"violations": [10, 15]})
        # Should not raise KeyError
        kpi = compute_sidewalk_kpis(df)
        assert kpi is not None


class TestMaterialAwareSidewalkKPI:
    """Tests for MaterialAwareSidewalkKPI dataclass."""

    def test_material_aware_kpi_creation(self):
        """Test creating a MaterialAwareSidewalkKPI object."""
        kpi = MaterialAwareSidewalkKPI(
            timestamp=datetime.utcnow(),
            period_label="2024-Q1",
            defect_density=5.2,
            defect_rate_asphalt=6.1,
            defect_rate_concrete=4.3,
            defect_rate_permeable=2.1,
            defect_rate_specialty=1.5,
            ada_compliance_rate=87.5,
            hazardous_defect_count=12,
        )
        assert kpi.period_label == "2024-Q1"
        assert kpi.defect_density == 5.2
        assert kpi.defect_rate_asphalt == 6.1
        assert kpi.ada_compliance_rate == 87.5

    def test_material_aware_kpi_to_dict(self):
        """Test serializing MaterialAwareSidewalkKPI to dictionary."""
        kpi = MaterialAwareSidewalkKPI(
            timestamp=datetime.utcnow(),
            period_label="2024-Q1",
            defect_density=5.2,
        )
        kpi_dict = kpi.to_dict()
        assert isinstance(kpi_dict, dict)
        assert kpi_dict["period_label"] == "2024-Q1"
        assert kpi_dict["defect_density"] == 5.2
        assert isinstance(kpi_dict["timestamp"], str)  # Should be ISO string

    def test_material_aware_kpi_hazardous_defect_coverage(self):
        """Test KPI includes hazardous defect coverage by material."""
        kpi = MaterialAwareSidewalkKPI(
            timestamp=datetime.utcnow(),
            period_label="2024-Q1",
            defect_density=5.2,
            hazardous_defect_coverage={
                "asphalt": 1250.0,
                "concrete": 830.0,
                "pavers": 120.0,
            },
            hazardous_defect_count=45,
        )
        assert kpi.hazardous_defect_count == 45
        assert kpi.hazardous_defect_coverage["asphalt"] == 1250.0

    def test_material_aware_kpi_contractor_quality(self):
        """Test KPI includes contractor quality scores by material."""
        kpi = MaterialAwareSidewalkKPI(
            timestamp=datetime.utcnow(),
            period_label="2024-Q1",
            defect_density=5.2,
            contractor_quality_by_material={
                "asphalt": {
                    "contractor_001": 0.92,
                    "contractor_002": 0.88,
                },
                "concrete": {
                    "contractor_003": 0.95,
                },
            },
        )
        assert kpi.contractor_quality_by_material["asphalt"]["contractor_001"] == 0.92

    def test_material_aware_kpi_material_longevity(self):
        """Test KPI includes material lifecycle data."""
        kpi = MaterialAwareSidewalkKPI(
            timestamp=datetime.utcnow(),
            period_label="2024-Q1",
            defect_density=5.2,
            material_longevity={
                "asphalt": {
                    "segment_count": 1250,
                    "total_linear_feet": 85000.0,
                },
                "concrete": {
                    "segment_count": 880,
                    "total_linear_feet": 62000.0,
                },
            },
        )
        assert kpi.material_longevity["asphalt"]["segment_count"] == 1250


class TestMaterialAwareKPIComputation:
    """Tests for compute_material_aware_kpis function."""

    @pytest.fixture
    def sample_sidewalk_data(self):
        """Create sample sidewalk segment data for testing."""
        return pd.DataFrame({
            "segment_id": [1, 2, 3, 4, 5, 6],
            "material_type": [
                "HMA",
                "HMA",
                "PCC",
                "PCC",
                "Permeable Pavers",
                "Granite Block",
            ],
            "defect_count": [2, 3, 1, 2, 0, 1],
            "linear_feet": [200, 150, 300, 250, 100, 50],
            "ada_compliant": [True, False, True, True, False, True],
            "severity": ["minor", "moderate", "minor", "severe", "minor", "hazardous"],
            "repair_cost": [500, 800, 400, 2000, 300, 1500],
        })

    def test_compute_material_aware_kpis_basic(self, sample_sidewalk_data):
        """Test basic material-aware KPI computation."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )

        # Verify structure
        assert isinstance(kpi, MaterialAwareSidewalkKPI)
        assert kpi.period_label == "2024-Q1"
        assert kpi.defect_density > 0
        assert kpi.timestamp is not None

    def test_compute_material_aware_kpis_defect_rates(self, sample_sidewalk_data):
        """Test material-specific defect rates are computed."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )

        # Asphalt: 5 defects / 350 linear feet = ~1.43 (per 1000 ft / 10 = ~14.3%)
        assert kpi.defect_rate_asphalt > 0
        # Concrete: 3 defects / 550 linear feet = ~0.55 (per 1000 ft / 10 = ~5.5%)
        assert kpi.defect_rate_concrete > 0
        # Permeable: 0 defects / 100 linear feet = 0%
        assert kpi.defect_rate_permeable == 0

    def test_compute_material_aware_kpis_ada_compliance(self, sample_sidewalk_data):
        """Test ADA compliance rate calculation."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
            ada_compliant_col="ada_compliant",
        )

        # 4 out of 6 segments are ADA compliant = 66.67%
        assert 65 < kpi.ada_compliance_rate < 68

    def test_compute_material_aware_kpis_hazardous_defects(self, sample_sidewalk_data):
        """Test hazardous defect identification and coverage."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
            severity_col="severity",
        )

        # Should identify hazardous defect in granite block (50 linear feet)
        assert kpi.hazardous_defect_count >= 1
        assert "Granite Block" in kpi.hazardous_defect_coverage

    def test_compute_material_aware_kpis_lineage(self, sample_sidewalk_data):
        """Test KPI includes complete lineage metadata."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )

        # Verify lineage metadata
        assert kpi.lineage_metadata is not None
        assert kpi.lineage_metadata["source_row_count"] == 6
        assert kpi.lineage_metadata["period_label"] == "2024-Q1"
        assert "material_col" in kpi.lineage_metadata
        assert "computed_at" in kpi.lineage_metadata

    def test_compute_material_aware_kpis_cost_analysis(self, sample_sidewalk_data):
        """Test cost-per-linear-foot calculation."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
            repair_cost_col="repair_cost",
        )

        # Total cost = 500+800+400+2000+300+1500 = 5500
        # Total linear feet = 200+150+300+250+100+50 = 1050
        # Cost per linear foot = 5500 / 1050 ≈ 5.24
        assert "overall" in kpi.cost_per_linear_foot
        assert 5 < kpi.cost_per_linear_foot["overall"] < 6

    def test_compute_material_aware_kpis_material_longevity(self, sample_sidewalk_data):
        """Test material longevity/age distribution calculation."""
        kpi = compute_material_aware_kpis(
            sample_sidewalk_data,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )

        # Verify material longevity structure
        assert "HMA" in kpi.material_longevity
        assert "PCC" in kpi.material_longevity
        assert kpi.material_longevity["HMA"]["segment_count"] == 2
        assert kpi.material_longevity["HMA"]["total_linear_feet"] == 350.0

    def test_compute_material_aware_kpis_custom_column_names(self):
        """Test KPI computation with custom column names."""
        df = pd.DataFrame({
            "seg_id": [1, 2, 3],
            "mat": ["HMA", "PCC", "HMA"],
            "defs": [2, 1, 3],
            "length": [200, 300, 150],
        })

        kpi = compute_material_aware_kpis(
            df,
            period_label="2024-Q1",
            material_col="mat",
            defect_col="defs",
            linear_feet_col="length",
        )

        assert kpi is not None
        assert kpi.defect_density > 0

    def test_compute_material_aware_kpis_empty_dataframe(self):
        """Test KPI computation with empty DataFrame."""
        df = pd.DataFrame({
            "material_type": [],
            "defect_count": [],
            "linear_feet": [],
        })

        # Should not raise error
        kpi = compute_material_aware_kpis(
            df,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )
        assert kpi is not None
        assert kpi.defect_density == 0

    def test_compute_material_aware_kpis_null_handling(self):
        """Test KPI computation gracefully handles null values."""
        df = pd.DataFrame({
            "material_type": ["HMA", None, "PCC"],
            "defect_count": [2, 3, None],
            "linear_feet": [200, 150, 300],
        })

        # Should not raise error
        kpi = compute_material_aware_kpis(
            df,
            period_label="2024-Q1",
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )
        assert kpi is not None


class TestKPIIntegration:
    """Integration tests for legacy and material-aware KPIs together."""

    def test_legacy_and_material_aware_consistency(self):
        """Test that legacy and material-aware KPIs are consistent."""
        df = pd.DataFrame({
            "violations": [10, 15],
            "curb_miles": [2, 3],
            "built_linear_feet": [1000, 500],
            "days": [10, 5],
            "actual_spend": [100, 200],
            "planned_spend": [90, 210],
            "first_pass": [8, 10],
            "total_inspections": [10, 15],
            "rework_spend": [5, 10],
            # Material-aware columns
            "material_type": ["HMA", "PCC"],
            "defect_count": [25, 15],
            "linear_feet": [5280 * 5, 5280 * 5],  # 5 miles each
        })

        # Compute both
        legacy_kpi = compute_sidewalk_kpis(df)
        material_aware_kpi = compute_material_aware_kpis(
            df,
            material_col="material_type",
            defect_col="defect_count",
            linear_feet_col="linear_feet",
        )

        # Legacy defect_density should be ~1.4 (40 defects / 10 miles)
        # Material-aware defect_density should be similar
        assert abs(legacy_kpi.defect_density - material_aware_kpi.defect_density) < 2
