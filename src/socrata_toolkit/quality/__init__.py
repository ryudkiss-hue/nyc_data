"""Quality module for NYC DOT SIM Analyst Toolkit.

Exports data quality rules, expectations, SLA tracking, and scoring utilities.
"""

from __future__ import annotations

from socrata_toolkit.quality.rules import (
    DATASET_EXPECTATIONS,
    BusinessRulesEngine,
    QualityRule,
    RuleMode,
    RuleSeverity,
    RuleViolation,
    RuleViolations,
    build_data_dictionary,
    create_311_complaints_rules,
    create_sidewalk_rules,
    quality_scorecard,
    validate_expectations,
    validate_schema,
)
from socrata_toolkit.quality.domain_rules import (
    DomainRuleResult,
    summarize_domain_rule_results,
    validate_all_domain_rules,
    validate_borough_coverage_distribution,
    validate_material_lifespan_rule,
    validate_permit_inspection_relationship,
)
from socrata_toolkit.quality.sla_tracking import (
    SLAMetrics,
    SLATarget,
    compute_cycle_times,
    compute_sla_metrics,
    flag_sla_violations,
    forecast_sla_breaches,
    load_quality_trend,
    record_quality_score,
)

__all__ = [
    # Rules
    "DATASET_EXPECTATIONS",
    "BusinessRulesEngine",
    "QualityRule",
    "RuleMode",
    "RuleSeverity",
    "RuleViolation",
    "RuleViolations",
    "build_data_dictionary",
    "create_311_complaints_rules",
    "create_sidewalk_rules",
    "quality_scorecard",
    "validate_expectations",
    "validate_schema",
    # Domain Rules
    "DomainRuleResult",
    "summarize_domain_rule_results",
    "validate_all_domain_rules",
    "validate_borough_coverage_distribution",
    "validate_material_lifespan_rule",
    "validate_permit_inspection_relationship",
    # SLA tracking
    "SLAMetrics",
    "SLATarget",
    "compute_cycle_times",
    "compute_sla_metrics",
    "flag_sla_violations",
    "forecast_sla_breaches",
    "load_quality_trend",
    "record_quality_score",
]
