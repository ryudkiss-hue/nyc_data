"""
Test Suite for NYC Street Design Manual Material Standards

Tests material definitions, surface assessment classification, ADA compliance rules,
maintenance schedules, and lifecycle cost computations.

Standards: pytest, comprehensive coverage (25+ test cases)
"""

from __future__ import annotations

import pytest
from datetime import datetime, date, timedelta
from socrata_toolkit.material.standards import (
    MaterialCategory,
    SurfaceCondition,
    DefectType,
    ADAFailureSeverity,
    MaintenanceUrgency,
    ADAComplianceRule,
    MaterialSpecification,
    MaintenanceSchedule,
    SurfaceAssessment,
    DefectSeverityAssessment,
)
from socrata_toolkit.material.definitions import (
    MATERIAL_DEFINITIONS,
    ASPH_STANDARD,
    CONC_STANDARD,
    PAVER_UNIT,
    get_material_by_id,
    get_material_by_category,
    get_materials_by_lifecycle_cost_range,
)
from socrata_toolkit.standards.design import (
    ADA_COMPLIANCE_RULES,
    get_rule,
    get_rules_for_material,
    get_critical_rules,
    get_rules_by_severity,
    MATERIAL_APPLICABLE_RULES,
)
from socrata_toolkit.material.compliance import (
    MaterialCompliance,
    ComplianceStatus,
    ADAComplianceCheckResult,
    MaintenanceScheduleCheckResult,
)


# ============================================================================
# MATERIAL DEFINITIONS TESTS (5 tests)
# ============================================================================

class TestMaterialDefinitions:
    """Tests for material specification definitions."""
    
    def test_material_definitions_loaded(self):
        """Verify all expected materials are loaded."""
        assert len(MATERIAL_DEFINITIONS) >= 8, "Should have at least 8 standard materials"
        assert "ASPH_STANDARD" in MATERIAL_DEFINITIONS
        assert "CONC_STANDARD" in MATERIAL_DEFINITIONS
        assert "STONE_NATURAL" in MATERIAL_DEFINITIONS
    
    def test_asphalt_standard_specification(self):
        """Test asphalt standard material properties."""
        spec = ASPH_STANDARD
        assert spec.material_id == "ASPH-NYC-001"
        assert spec.category == MaterialCategory.ASPHALT
        assert spec.lifecycle_years == 20
        assert spec.cost_per_sqft > 0
        assert spec.lifecycle_cost_per_sqft > spec.cost_per_sqft
    
    def test_concrete_standard_specification(self):
        """Test concrete standard material properties."""
        spec = CONC_STANDARD
        assert spec.category == MaterialCategory.CONCRETE
        assert spec.lifecycle_years == 30
        assert spec.maintenance_schedule.routine_interval_years == 5
        assert spec.design_standards["compressive_strength_psi"] == 3500
    
    def test_material_by_id_lookup(self):
        """Test material lookup by ID."""
        spec = get_material_by_id("ASPH-NYC-001")
        assert spec is not None
        assert spec.material_id == "ASPH-NYC-001"
        
        missing = get_material_by_id("NONEXISTENT")
        assert missing is None
    
    def test_material_by_category_lookup(self):
        """Test material lookup by category."""
        asphalt_materials = get_material_by_category(MaterialCategory.ASPHALT)
        assert len(asphalt_materials) >= 2  # ASPH_STANDARD and ASPH_POROUS
        
        concrete_materials = get_material_by_category(MaterialCategory.CONCRETE)
        assert len(concrete_materials) >= 2
        
        for mat in asphalt_materials:
            assert mat.category == MaterialCategory.ASPHALT


# ============================================================================
# MAINTENANCE SCHEDULE TESTS (5 tests)
# ============================================================================

class TestMaintenanceSchedules:
    """Tests for material maintenance schedules."""
    
    def test_asphalt_maintenance_cycle(self):
        """Test asphalt maintenance schedule."""
        schedule = ASPH_STANDARD.maintenance_schedule
        assert schedule.routine_interval_years == 3
        assert schedule.preventive_overlay_years == 7
        assert schedule.lifecycle_years == 20
    
    def test_concrete_maintenance_cycle(self):
        """Test concrete maintenance schedule has longer intervals."""
        asph_schedule = ASPH_STANDARD.maintenance_schedule
        conc_schedule = CONC_STANDARD.maintenance_schedule
        
        # Concrete should have longer intervals than asphalt
        assert conc_schedule.routine_interval_years > asph_schedule.routine_interval_years
        assert conc_schedule.lifecycle_years > asph_schedule.lifecycle_years
    
    def test_maintenance_due_date_calculation(self):
        """Test calculation of next maintenance due date."""
        last_maint = date(2023, 1, 1)
        next_due = ASPH_STANDARD.get_maintenance_due_date(last_maint)
        
        expected = date(2026, 1, 1)  # 3 years later
        assert next_due == expected
    
    def test_lifecycle_replacement_date(self):
        """Test calculation of replacement date."""
        install_date = date(2000, 1, 1)
        replace_date = ASPH_STANDARD.get_lifecycle_replacement_date(install_date)
        
        expected = date(2020, 1, 1)  # 20 years later
        assert replace_date == expected
    
    def test_permeable_maintenance_requires_frequent_attention(self):
        """Test that permeable materials need more frequent maintenance."""
        spec = MATERIAL_DEFINITIONS["PAVER_UNIT"]
        schedule = spec.maintenance_schedule
        
        # Permeable surfaces should need more frequent maintenance
        assert schedule.routine_interval_years <= 3


# ============================================================================
# ADA COMPLIANCE RULES TESTS (6 tests)
# ============================================================================

class TestADAComplianceRules:
    """Tests for ADA compliance rule definitions."""
    
    def test_ada_rules_loaded(self):
        """Verify ADA compliance rules are loaded."""
        assert len(ADA_COMPLIANCE_RULES) >= 9
        assert "ADA-1.2.1" in ADA_COMPLIANCE_RULES
        assert "ADA-1.5.1" in ADA_COMPLIANCE_RULES
    
    def test_rule_width_requirement(self):
        """Test accessible route width rule."""
        rule = get_rule("ADA-1.2.1")
        assert rule is not None
        assert rule.rule_id == "ADA-1.2.1"
        assert rule.failure_severity in [ADAFailureSeverity.HIGH, ADAFailureSeverity.CRITICAL]
        assert rule.parameters["min_clear_width_feet"] == 4.0
    
    def test_rule_slip_resistance(self):
        """Test slip resistance rule."""
        rule = get_rule("ADA-1.3.1")
        assert rule is not None
        assert rule.parameters["min_bpn_dry"] == 60
        assert rule.validation_method == "equipment_test"
    
    def test_critical_rules_identification(self):
        """Test identification of critical severity rules."""
        critical = get_critical_rules()
        assert len(critical) > 0
        
        for rule in critical:
            assert rule.failure_severity == ADAFailureSeverity.CRITICAL
    
    def test_rules_by_severity(self):
        """Test filtering rules by severity."""
        high_rules = get_rules_by_severity(ADAFailureSeverity.HIGH)
        assert len(high_rules) > 0
        
        for rule in high_rules:
            assert rule.failure_severity == ADAFailureSeverity.HIGH
    
    def test_material_applicable_rules(self):
        """Test material-to-rules mapping."""
        asphalt_rules = get_rules_for_material(MaterialCategory.ASPHALT)
        assert len(asphalt_rules) > 0
        
        # Asphalt should have standard sidewalk rules
        rule_ids = [r.rule_id for r in asphalt_rules]
        assert "ADA-1.2.1" in rule_ids or any("1.2" in rid for rid in rule_ids)


# ============================================================================
# SURFACE ASSESSMENT TESTS (5 tests)
# ============================================================================

class TestSurfaceAssessment:
    """Tests for surface assessment model."""
    
    def test_surface_assessment_creation(self):
        """Test creating a surface assessment."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.FAIR,
        )
        
        assert assessment.location_id == "block-001"
        assert assessment.material == ASPH_STANDARD
        assert assessment.condition == SurfaceCondition.FAIR
        assert assessment.ada_compliance_score == 100.0
    
    def test_surface_assessment_with_defects(self):
        """Test assessment with defects."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.POOR,
            defects=[
                {
                    "defect_code": "SP001",
                    "defect_type": DefectType.SPALLING,
                    "severity": "moderate",
                    "square_feet_affected": 50,
                },
            ],
        )
        
        assert len(assessment.defects) == 1
        assert assessment.defects[0]["defect_code"] == "SP001"
    
    def test_surface_assessment_ada_violations(self):
        """Test assessment with ADA violations."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.CRITICAL,
            ada_compliance_score=50.0,
            ada_violations=[
                {
                    "rule_id": "ADA-1.5.1",
                    "violation_description": "Surface has 1.2 inch vertical displacement",
                    "severity": ADAFailureSeverity.HIGH,
                    "remediation_required": True,
                }
            ],
        )
        
        assert not assessment.is_ada_compliant()
        assert assessment.ada_compliance_score < 100
    
    def test_surface_assessment_to_dict(self):
        """Test serialization to dictionary."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime(2024, 1, 1),
            condition=SurfaceCondition.GOOD,
        )
        
        data = assessment.to_dict()
        assert data["location_id"] == "block-001"
        assert data["condition"] == "good"
        assert "last_inspected" in data
    
    def test_deterioration_rate_calculation(self):
        """Test calculation of deterioration rate over time."""
        now = datetime.now()
        earlier = now - timedelta(days=365)
        
        earlier_assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=earlier,
            condition=SurfaceCondition.EXCELLENT,
        )
        
        current_assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=now,
            condition=SurfaceCondition.GOOD,
        )
        
        rate = current_assessment.get_deterioration_rate([earlier_assessment, current_assessment])
        assert rate > 0  # Should be deteriorating


# ============================================================================
# COMPLIANCE CHECKING TESTS (5 tests)
# ============================================================================

class TestComplianceChecking:
    """Tests for material compliance checking."""
    
    def test_compliance_checker_initialization(self):
        """Test compliance checker initialization."""
        checker = MaterialCompliance()
        assert checker is not None
        assert checker.rules is not None
        assert len(checker.rules) > 0
    
    def test_ada_compliance_check_compliant(self):
        """Test ADA compliance check for compliant assessment."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.EXCELLENT,
            ada_compliance_score=100.0,
        )
        
        checker = MaterialCompliance()
        result = checker.ada_compliance_check(assessment)
        
        assert isinstance(result, ADAComplianceCheckResult)
        assert result.compliance_score >= 95
    
    def test_ada_compliance_check_violations(self):
        """Test ADA compliance check detects violations."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.CRITICAL,
            ada_compliance_score=30.0,
            ada_violations=[
                {
                    "rule_id": "ADA-1.5.1",
                    "violation_description": "Severe surface defects",
                    "severity": ADAFailureSeverity.HIGH,
                }
            ],
        )
        
        checker = MaterialCompliance()
        result = checker.ada_compliance_check(assessment)
        
        assert not result.overall_compliant
        assert result.compliance_score < 100
    
    def test_maintenance_schedule_check(self):
        """Test maintenance schedule compliance check."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.GOOD,
        )
        
        last_maint = date.today() - timedelta(days=365*2)  # 2 years ago
        
        checker = MaterialCompliance()
        result = checker.maintenance_schedule_check(assessment, last_maint)
        
        assert isinstance(result, MaintenanceScheduleCheckResult)
        # At 2 years, routine 3-year maintenance not yet due
        assert not result.maintenance_overdue
    
    def test_lifecycle_check(self):
        """Test material lifecycle stage assessment."""
        assessment = SurfaceAssessment(
            location_id="block-001",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.GOOD,
        )
        
        # Material installed 15 years ago
        installation_date = date.today() - timedelta(days=365*15)
        
        checker = MaterialCompliance()
        result = checker.lifecycle_check(assessment, installation_date)
        
        # 15 years into 20-year lifecycle = 75% through
        assert result.age_percent >= 70
        assert result.lifecycle_stage in ["late", "end_of_life"]


# ============================================================================
# DEFECT SEVERITY ASSESSMENT TESTS (3 tests)
# ============================================================================

class TestDefectSeverityAssessment:
    """Tests for defect severity analysis."""
    
    def test_defect_severity_assessment_creation(self):
        """Test creating a defect severity assessment."""
        assessment = DefectSeverityAssessment(
            defect_type=DefectType.POTHOLES,
            severity_level="severe",
            area_sqft=50,
            depth_inches=2.5,
            safety_hazard=True,
            trip_hazard=True,
        )
        
        assert assessment.defect_type == DefectType.POTHOLES
        assert assessment.safety_hazard
    
    def test_defect_trip_hazard_detection(self):
        """Test identification of trip hazards."""
        assessment = DefectSeverityAssessment(
            defect_type=DefectType.SETTLEMENT,
            severity_level="moderate",
            area_sqft=100,
            trip_hazard=True,
        )
        
        assert assessment.trip_hazard
        assert assessment.trip_hazard  # > 0.5 inch displacement
    
    def test_defect_ada_violation_flag(self):
        """Test ADA violation flagging for defects."""
        assessment = DefectSeverityAssessment(
            defect_type=DefectType.HEAVE,
            severity_level="severe",
            area_sqft=200,
            ada_violation=True,
        )
        
        assert assessment.ada_violation


# ============================================================================
# COST ANALYSIS TESTS (2 tests)
# ============================================================================

class TestCostAnalysis:
    """Tests for lifecycle cost analysis."""
    
    def test_lifecycle_cost_per_material(self):
        """Test lifecycle cost comparison across materials."""
        asph_cost = ASPH_STANDARD.lifecycle_cost_per_sqft
        conc_cost = CONC_STANDARD.lifecycle_cost_per_sqft
        
        # Both should have reasonable costs
        assert asph_cost > 0
        assert conc_cost > 0
        
        # Concrete likely costs more due to longer life
        # (less frequent maintenance)
    
    def test_material_cost_range_lookup(self):
        """Test finding materials within cost range."""
        # Get materials under $20/sqft total lifecycle cost
        affordable = get_materials_by_lifecycle_cost_range(0, 20)
        assert len(affordable) > 0
        
        for mat in affordable:
            assert mat.lifecycle_cost_per_sqft <= 20
        
        # Get premium materials
        premium = get_materials_by_lifecycle_cost_range(20, 100)
        assert len(premium) > 0


# ============================================================================
# SUSTAINABILITY TESTS (2 tests)
# ============================================================================

class TestSustainability:
    """Tests for material sustainability metrics."""
    
    def test_sustainability_score_range(self):
        """Test that sustainability scores are in valid range."""
        for spec in MATERIAL_DEFINITIONS.values():
            assert 0 <= spec.sustainability_score <= 100
    
    def test_carbon_footprint_tracking(self):
        """Test carbon footprint metrics."""
        for spec in MATERIAL_DEFINITIONS.values():
            assert spec.carbon_footprint_kg_per_sqft >= 0
        
        # Recycled rubber should have very low or negative footprint
        rubber = MATERIAL_DEFINITIONS.get("RUBBER_MATS")
        if rubber:
            assert rubber.sustainability_score >= 75


# ============================================================================
# INTEGRATION TESTS (3 tests)
# ============================================================================

class TestIntegration:
    """Integration tests across multiple modules."""
    
    def test_end_to_end_compliance_report(self):
        """Test generating complete compliance report."""
        assessment = SurfaceAssessment(
            location_id="block-001-seg-01",
            material=ASPH_STANDARD,
            last_inspected=datetime.now(),
            condition=SurfaceCondition.FAIR,
            ada_compliance_score=75,
        )
        
        checker = MaterialCompliance()
        report = checker.generate_compliance_report(
            assessment,
            location_description="123 Main St, Manhattan",
            last_maintenance=date.today() - timedelta(days=2*365),
            installation_date=date.today() - timedelta(days=12*365),
        )
        
        assert report.assessment_id == "block-001-seg-01"
        assert report.overall_status in [
            ComplianceStatus.COMPLIANT,
            ComplianceStatus.PARTIAL_COMPLIANCE,
            ComplianceStatus.NON_COMPLIANT,
        ]
        assert 0 <= report.overall_score <= 100
    
    def test_material_definition_has_required_ada_rules(self):
        """Test that all materials reference applicable ADA rules."""
        for mat_spec in MATERIAL_DEFINITIONS.values():
            # Should have some applicable ADA rules
            assert len(mat_spec.applicable_ada_rules) > 0
            
            # All referenced rules should exist
            for rule_id in mat_spec.applicable_ada_rules:
                assert rule_id in ADA_COMPLIANCE_RULES
    
    def test_assessment_serialization_roundtrip(self):
        """Test that assessment can be serialized and contains all data."""
        original = SurfaceAssessment(
            location_id="test-001",
            material=ASPH_STANDARD,
            last_inspected=datetime(2024, 1, 15, 10, 30),
            condition=SurfaceCondition.POOR,
            defect_area_sqft=150.5,
            estimated_repair_cost=5000.0,
            notes="Test assessment for validation",
        )
        
        data = original.to_dict()
        
        # Verify all critical fields are in dictionary
        assert data["location_id"] == "test-001"
        assert data["condition"] == "poor"
        assert data["defect_area_sqft"] == 150.5
        assert data["estimated_repair_cost"] == 5000.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
