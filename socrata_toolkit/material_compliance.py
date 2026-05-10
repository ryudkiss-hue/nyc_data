"""
Material Compliance Checking and Validation Engine

Provides comprehensive compliance checking against ADA rules, design standards,
maintenance schedules, and lifecycle requirements. Enables batch compliance analysis
across geographies and material types.

Standards: Python 3.9+, type hints, comprehensive docstrings, logging
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional
from datetime import datetime, date, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Circular import handling - import at function level where needed
from socrata_toolkit.material_standards import (
    SurfaceAssessment,
    MaterialSpecification,
    SurfaceCondition,
    MaintenanceUrgency,
    ADAFailureSeverity,
)


class ComplianceStatus(str, Enum):
    """Overall compliance status."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL_COMPLIANCE = "partial_compliance"
    UNKNOWN = "unknown"


@dataclass
class ADAComplianceCheckResult:
    """Result of ADA compliance check for a single assessment.
    
    Attributes:
        assessment_id: Location or assessment identifier
        overall_compliant: Whether assessment meets all ADA requirements
        critical_violations: Count of CRITICAL severity violations
        high_violations: Count of HIGH severity violations
        medium_violations: Count of MEDIUM severity violations
        low_violations: Count of LOW severity violations
        violations_detail: List of violation dictionaries with rule_id, severity, description
        compliance_score: 0-100 score (100 = fully compliant)
        remediation_required: Whether remediation is needed
        urgency: MaintenanceUrgency based on violation severity
        estimated_remediation_cost: Cost to fix violations
        notes: Additional notes
    """
    
    assessment_id: str
    overall_compliant: bool
    critical_violations: int = 0
    high_violations: int = 0
    medium_violations: int = 0
    low_violations: int = 0
    violations_detail: list[dict[str, Any]] = field(default_factory=list)
    compliance_score: float = 100.0
    remediation_required: bool = False
    urgency: MaintenanceUrgency = MaintenanceUrgency.ROUTINE
    estimated_remediation_cost: float = 0.0
    notes: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['urgency'] = self.urgency.value
        return data


@dataclass
class MaintenanceScheduleCheckResult:
    """Result of maintenance schedule compliance check.
    
    Attributes:
        assessment_id: Location identifier
        material_id: Material specification ID
        last_maintenance: Date of last maintenance activity
        next_routine_due: When next routine maintenance is due
        preventive_overlay_due: When overlay/resurfacing should occur
        lifecycle_replacement_due: When full replacement is recommended
        maintenance_overdue: Whether any maintenance is overdue
        days_overdue: How many days overdue (if applicable)
        urgency: Maintenance urgency level
        recommended_activity: What maintenance activity should be performed
    """
    
    assessment_id: str
    material_id: str
    last_maintenance: date
    next_routine_due: date
    preventive_overlay_due: date
    lifecycle_replacement_due: date
    maintenance_overdue: bool = False
    days_overdue: int = 0
    urgency: MaintenanceUrgency = MaintenanceUrgency.ROUTINE
    recommended_activity: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['urgency'] = self.urgency.value
        return data


@dataclass
class LifecycleRecommendation:
    """Material lifecycle stage and replacement recommendation.
    
    Attributes:
        assessment_id: Location identifier
        material_id: Material specification ID
        installation_date: When material was installed
        current_age_years: Current age in years
        lifecycle_years: Expected lifecycle in years
        age_percent: Percentage through lifecycle (0-100)
        lifecycle_stage: Stage (early, mid, late, end_of_life)
        replacement_recommended: Whether replacement should be considered
        condition_vs_age: How condition compares to age expectation
        notes: Additional lifecycle notes
    """
    
    assessment_id: str
    material_id: str
    installation_date: date
    current_age_years: float
    lifecycle_years: int
    age_percent: float
    lifecycle_stage: str
    replacement_recommended: bool = False
    condition_vs_age: str = "normal"  # 'better_than_expected', 'normal', 'worse_than_expected'
    notes: str = ""


@dataclass
class ComplianceReport:
    """Comprehensive compliance report for a surface assessment.
    
    Combines ADA compliance, maintenance schedule, and lifecycle analysis
    into a single actionable report.
    """
    
    assessment_id: str
    location_description: str
    assessment_timestamp: datetime
    material_category: str
    material_name: str
    
    # ADA Compliance
    ada_compliance: ADAComplianceCheckResult
    
    # Maintenance Schedule
    maintenance_schedule: MaintenanceScheduleCheckResult
    
    # Lifecycle
    lifecycle: LifecycleRecommendation
    
    # Overall Status
    overall_status: ComplianceStatus
    overall_score: float  # 0-100 weighted score
    
    # Actions Required
    critical_actions: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    
    # Cost Summary
    estimated_total_cost: float = 0.0
    estimated_ada_remediation: float = 0.0
    estimated_maintenance_cost: float = 0.0
    estimated_replacement_cost: float = 0.0
    
    # Timeline
    days_until_urgent_action: int = 999
    
    # Generated Report
    report_generated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'assessment_id': self.assessment_id,
            'location_description': self.location_description,
            'assessment_timestamp': self.assessment_timestamp.isoformat(),
            'material_category': self.material_category,
            'material_name': self.material_name,
            'ada_compliance': self.ada_compliance.to_dict(),
            'maintenance_schedule': self.maintenance_schedule.to_dict(),
            'lifecycle': asdict(self.lifecycle),
            'overall_status': self.overall_status.value,
            'overall_score': self.overall_score,
            'critical_actions': self.critical_actions,
            'recommended_actions': self.recommended_actions,
            'estimated_total_cost': self.estimated_total_cost,
            'estimated_ada_remediation': self.estimated_ada_remediation,
            'estimated_maintenance_cost': self.estimated_maintenance_cost,
            'estimated_replacement_cost': self.estimated_replacement_cost,
            'days_until_urgent_action': self.days_until_urgent_action,
            'report_generated_at': self.report_generated_at.isoformat(),
        }


class MaterialCompliance:
    """Compliance checking engine for surface assessments.
    
    Validates assessments against ADA rules, design standards, and maintenance schedules.
    Provides scoring and actionable recommendations.
    
    Example:
        >>> from socrata_toolkit.material_compliance import MaterialCompliance
        >>> from socrata_toolkit.material_definitions import MATERIAL_DEFINITIONS
        >>> compliance_checker = MaterialCompliance()
        >>> assessment = SurfaceAssessment(...)
        >>> report = compliance_checker.generate_compliance_report(
        ...     assessment, location_description="Block 123, 5th Ave"
        ... )
        >>> print(f"Compliance Score: {report.overall_score:.1f}%")
    """
    
    def __init__(self):
        """Initialize compliance checker."""
        # Lazy-load design rules to avoid circular imports
        self._rules = None
        self._material_rules_map = None
    
    @property
    def rules(self):
        """Lazy-load ADA compliance rules."""
        if self._rules is None:
            from socrata_toolkit.design_rules import ADA_COMPLIANCE_RULES
            self._rules = ADA_COMPLIANCE_RULES
        return self._rules
    
    @property
    def material_rules_map(self):
        """Lazy-load material-to-rules mapping."""
        if self._material_rules_map is None:
            from socrata_toolkit.design_rules import MATERIAL_APPLICABLE_RULES
            self._material_rules_map = MATERIAL_APPLICABLE_RULES
        return self._material_rules_map
    
    def ada_compliance_check(
        self,
        assessment: SurfaceAssessment,
        as_of_date: Optional[date] = None,
    ) -> ADAComplianceCheckResult:
        """Check ADA compliance for a surface assessment.
        
        Evaluates assessment against all applicable ADA rules for the material type.
        Counts violations by severity and calculates compliance score.
        
        Args:
            assessment: SurfaceAssessment to check
            as_of_date: Date for evaluation (default: today)
            
        Returns:
            ADAComplianceCheckResult with violation details
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        result = ADAComplianceCheckResult(
            assessment_id=assessment.location_id,
            overall_compliant=True,
        )
        
        # Apply material-specific rules
        applicable_rule_ids = self.material_rules_map.get(assessment.material.category, [])
        
        for rule_id in applicable_rule_ids:
            rule = self.rules.get(rule_id)
            if not rule:
                continue
            
            # Check if assessment has violations matching this rule
            has_violation = self._check_rule_violation(assessment, rule)
            
            if has_violation:
                result.overall_compliant = False
                
                # Count by severity
                if rule.failure_severity == ADAFailureSeverity.CRITICAL:
                    result.critical_violations += 1
                    result.urgency = MaintenanceUrgency.EMERGENCY
                elif rule.failure_severity == ADAFailureSeverity.HIGH:
                    result.high_violations += 1
                    if result.urgency == MaintenanceUrgency.ROUTINE:
                        result.urgency = MaintenanceUrgency.URGENT
                elif rule.failure_severity == ADAFailureSeverity.MEDIUM:
                    result.medium_violations += 1
                    if result.urgency == MaintenanceUrgency.ROUTINE:
                        result.urgency = MaintenanceUrgency.PLANNED
                else:  # LOW
                    result.low_violations += 1
                
                # Add violation detail
                result.violations_detail.append({
                    'rule_id': rule_id,
                    'title': rule.title,
                    'severity': rule.failure_severity.value,
                    'description': rule.description,
                    'remediation_required': rule.failure_severity in [
                        ADAFailureSeverity.CRITICAL,
                        ADAFailureSeverity.HIGH,
                    ],
                })
        
        # Calculate compliance score (100 - violations weighted by severity)
        total_violations = (
            result.critical_violations * 10 +
            result.high_violations * 5 +
            result.medium_violations * 2 +
            result.low_violations * 1
        )
        result.compliance_score = max(0.0, 100.0 - total_violations)
        
        result.remediation_required = result.critical_violations > 0 or result.high_violations > 0
        
        logger.info(
            f"ADA compliance check for {assessment.location_id}: "
            f"score={result.compliance_score:.1f}, violations={len(result.violations_detail)}"
        )
        
        return result
    
    def maintenance_schedule_check(
        self,
        assessment: SurfaceAssessment,
        last_maintenance: date,
        as_of_date: Optional[date] = None,
    ) -> MaintenanceScheduleCheckResult:
        """Check if maintenance is due per material schedule.
        
        Args:
            assessment: SurfaceAssessment to check
            last_maintenance: Date of last maintenance activity
            as_of_date: Evaluation date (default: today)
            
        Returns:
            MaintenanceScheduleCheckResult with due dates
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        spec = assessment.material
        schedule = spec.maintenance_schedule
        
        # Calculate due dates
        next_routine = spec.get_maintenance_due_date(last_maintenance)
        overlay_date = date(
            last_maintenance.year + schedule.preventive_overlay_years,
            last_maintenance.month,
            last_maintenance.day,
        )
        replacement_date = spec.get_lifecycle_replacement_date(last_maintenance)
        
        # Check if overdue
        overdue = as_of_date > next_routine
        days_overdue = max(0, (as_of_date - next_routine).days) if overdue else 0
        
        # Determine urgency and recommended activity
        urgency = MaintenanceUrgency.ROUTINE
        recommended_activity = "No immediate maintenance required"
        
        if replacement_date <= as_of_date:
            urgency = MaintenanceUrgency.EMERGENCY
            recommended_activity = f"Full replacement (material is {(as_of_date - last_maintenance).days // 365} years old)"
        elif overlay_date <= as_of_date:
            urgency = MaintenanceUrgency.URGENT
            recommended_activity = "Preventive overlay or resurfacing"
        elif overdue:
            urgency = MaintenanceUrgency.PLANNED
            recommended_activity = f"Routine maintenance ({schedule.routine_interval_years}-year cycle)"
        
        result = MaintenanceScheduleCheckResult(
            assessment_id=assessment.location_id,
            material_id=spec.material_id,
            last_maintenance=last_maintenance,
            next_routine_due=next_routine,
            preventive_overlay_due=overlay_date,
            lifecycle_replacement_due=replacement_date,
            maintenance_overdue=overdue,
            days_overdue=days_overdue,
            urgency=urgency,
            recommended_activity=recommended_activity,
        )
        
        logger.info(
            f"Maintenance schedule check for {assessment.location_id}: "
            f"next due {result.next_routine_due}, overdue={overdue}"
        )
        
        return result
    
    def lifecycle_check(
        self,
        assessment: SurfaceAssessment,
        installation_date: date,
        as_of_date: Optional[date] = None,
    ) -> LifecycleRecommendation:
        """Assess material lifecycle stage and replacement recommendation.
        
        Args:
            assessment: SurfaceAssessment to check
            installation_date: When material was installed
            as_of_date: Evaluation date (default: today)
            
        Returns:
            LifecycleRecommendation with stage and replacement guidance
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        spec = assessment.material
        days_old = (as_of_date - installation_date).days
        current_age_years = days_old / 365.25
        age_percent = (current_age_years / spec.lifecycle_years) * 100
        
        # Determine lifecycle stage
        if age_percent < 30:
            stage = "early"
        elif age_percent < 70:
            stage = "mid"
        elif age_percent < 90:
            stage = "late"
        else:
            stage = "end_of_life"
        
        # Compare condition to age
        condition_vs_age = "normal"
        replacement_recommended = False
        
        if assessment.condition == SurfaceCondition.CRITICAL:
            replacement_recommended = True
            condition_vs_age = "worse_than_expected"
        elif assessment.condition == SurfaceCondition.POOR and age_percent < 70:
            condition_vs_age = "worse_than_expected"
        elif assessment.condition == SurfaceCondition.EXCELLENT and age_percent > 80:
            condition_vs_age = "better_than_expected"
        
        if age_percent >= 90:
            replacement_recommended = True
        
        result = LifecycleRecommendation(
            assessment_id=assessment.location_id,
            material_id=spec.material_id,
            installation_date=installation_date,
            current_age_years=current_age_years,
            lifecycle_years=spec.lifecycle_years,
            age_percent=age_percent,
            lifecycle_stage=stage,
            replacement_recommended=replacement_recommended,
            condition_vs_age=condition_vs_age,
            notes=f"Material is {current_age_years:.1f} years into {spec.lifecycle_years}-year lifecycle",
        )
        
        return result
    
    def generate_compliance_report(
        self,
        assessment: SurfaceAssessment,
        location_description: str = "",
        last_maintenance: Optional[date] = None,
        installation_date: Optional[date] = None,
        as_of_date: Optional[date] = None,
    ) -> ComplianceReport:
        """Generate comprehensive compliance report for an assessment.
        
        Combines ADA compliance, maintenance schedule, and lifecycle checks
        into a single actionable report.
        
        Args:
            assessment: SurfaceAssessment to evaluate
            location_description: Human-readable location description
            last_maintenance: Date of last maintenance (default: 1 year ago)
            installation_date: Material installation date (default: 10 years ago)
            as_of_date: Evaluation date (default: today)
            
        Returns:
            ComplianceReport with all analysis
        """
        if as_of_date is None:
            as_of_date = date.today()
        if last_maintenance is None:
            last_maintenance = as_of_date - timedelta(days=365)
        if installation_date is None:
            installation_date = as_of_date - timedelta(days=365*10)
        
        # Perform all checks
        ada_result = self.ada_compliance_check(assessment, as_of_date)
        maint_result = self.maintenance_schedule_check(assessment, last_maintenance, as_of_date)
        lifecycle_result = self.lifecycle_check(assessment, installation_date, as_of_date)
        
        # Determine overall status
        if ada_result.overall_compliant and not maint_result.maintenance_overdue:
            overall_status = ComplianceStatus.COMPLIANT
        elif ada_result.critical_violations > 0 or maint_result.urgency == MaintenanceUrgency.EMERGENCY:
            overall_status = ComplianceStatus.NON_COMPLIANT
        else:
            overall_status = ComplianceStatus.PARTIAL_COMPLIANCE
        
        # Calculate overall score (weighted average)
        overall_score = (
            ada_result.compliance_score * 0.5 +
            (100 - maint_result.days_overdue) * 0.25 +
            (100 - lifecycle_result.age_percent) * 0.25
        )
        overall_score = max(0.0, min(100.0, overall_score))
        
        # Build action list
        critical_actions = []
        recommended_actions = []
        
        if ada_result.critical_violations > 0:
            critical_actions.append(
                f"Fix {ada_result.critical_violations} CRITICAL ADA violations immediately"
            )
        
        if maint_result.urgency == MaintenanceUrgency.EMERGENCY:
            critical_actions.append(f"Perform emergency maintenance: {maint_result.recommended_activity}")
        
        if lifecycle_result.replacement_recommended:
            critical_actions.append(f"Material replacement recommended (age: {lifecycle_result.current_age_years:.1f} years)")
        
        if ada_result.high_violations > 0:
            recommended_actions.append(
                f"Address {ada_result.high_violations} HIGH severity ADA violations within 7 days"
            )
        
        if maint_result.urgency == MaintenanceUrgency.URGENT:
            recommended_actions.append(f"Schedule planned maintenance: {maint_result.recommended_activity}")
        
        if assessment.maintenance_due:
            recommended_actions.append(f"Material-specific maintenance cycle due: {maint_result.recommended_activity}")
        
        # Estimate costs
        estimated_ada_cost = assessment.estimated_repair_cost
        estimated_maint_cost = 100.0 if maint_result.maintenance_overdue else 0.0  # Simplified
        estimated_replacement_cost = assessment.material.cost_per_sqft * 1000  # Assume 1000 sqft
        
        days_until_urgent = 999
        if critical_actions:
            days_until_urgent = 0
        elif recommended_actions:
            days_until_urgent = 7 if any("7 days" in a for a in recommended_actions) else 30
        
        report = ComplianceReport(
            assessment_id=assessment.location_id,
            location_description=location_description or assessment.location_id,
            assessment_timestamp=assessment.last_inspected,
            material_category=assessment.material.category.value,
            material_name=assessment.material.name,
            ada_compliance=ada_result,
            maintenance_schedule=maint_result,
            lifecycle=lifecycle_result,
            overall_status=overall_status,
            overall_score=overall_score,
            critical_actions=critical_actions,
            recommended_actions=recommended_actions,
            estimated_ada_remediation=estimated_ada_cost,
            estimated_maintenance_cost=estimated_maint_cost,
            estimated_replacement_cost=estimated_replacement_cost,
            estimated_total_cost=estimated_ada_cost + estimated_maint_cost,
            days_until_urgent_action=days_until_urgent,
        )
        
        logger.info(
            f"Compliance report generated for {assessment.location_id}: "
            f"status={overall_status.value}, score={overall_score:.1f}"
        )
        
        return report
    
    def _check_rule_violation(self, assessment: SurfaceAssessment, rule: Any) -> bool:
        """Check if assessment violates a specific rule.
        
        Simple heuristic-based check. In production, would integrate with
        actual measurement data and inspection protocols.
        
        Args:
            assessment: SurfaceAssessment to check
            rule: ADAComplianceRule to check against
            
        Returns:
            True if violation detected
        """
        rule_id = rule.rule_id
        
        # Existing ADA violations in assessment
        if assessment.ada_violations:
            for violation in assessment.ada_violations:
                if violation.get('rule_id') == rule_id:
                    return True
        
        # Heuristic-based checks based on condition
        if rule_id == "ADA-1.5.1" and assessment.condition in [
            SurfaceCondition.POOR,
            SurfaceCondition.CRITICAL,
        ]:
            return True
        
        if rule_id == "ADA-1.3.1" and assessment.condition == SurfaceCondition.CRITICAL:
            return True
        
        if rule_id == "ADA-NYC-LOC-LAW-60" and assessment.condition == SurfaceCondition.CRITICAL:
            return True
        
        return False


logger.info("Material Compliance checking engine initialized")
