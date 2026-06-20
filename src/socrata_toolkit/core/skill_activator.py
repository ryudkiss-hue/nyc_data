"""
Skill Activation Framework

Routes analyst questions to appropriate data analytics skills with pre-populated context.
Chains skills based on findings (e.g., outliers detected → root-cause-investigation).

Architecture: Deep module with small, well-defined interface.
- Input: QuestionResolution from question_resolver
- Output: SkillActivationContext with everything the skill needs
- Locality: Skill routing logic centralized; changes to chains only affect this module
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from .question_resolver import AnalysisSkill, QuestionResolution, DatasetReference


@dataclass
class SkillContext:
    """Pre-populated context for skill activation"""
    skill: AnalysisSkill
    question_id: str
    question_text: str
    datasets: List[DatasetReference]
    kpi_ids: List[str]
    critical_datasets: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)  # Skill-specific params
    notes: Optional[str] = None


@dataclass
class SkillChain:
    """Sequence of skills to run for complex analysis"""
    primary_skill: AnalysisSkill
    trigger_conditions: Dict[str, str] = field(default_factory=dict)  # "outliers_found" → AnalysisSkill.ROOT_CAUSE
    confidence_boost: float = 1.0


class SkillActivator:
    """
    Routes questions to skills and chains skills based on findings.

    Design pattern: Deep module
    - Small interface: activate(question_resolution) → SkillContext
    - Large implementation: 10 skills, routing logic, chaining rules
    - Locality: All activation logic centralized; chains don't scatter

    Test surface: Skill selection matches question, context populated correctly
    """

    # Skill routing rules: Question category → Primary skill
    CATEGORY_TO_SKILL = {
        "A": AnalysisSkill.EDA,  # Condition → exploratory
        "B": AnalysisSkill.SEGMENTATION,  # Equity → segmentation
        "C": AnalysisSkill.DATA_QUALITY,  # Data quality → audit
        "D": AnalysisSkill.BUSINESS_METRICS,  # Budget → metrics
        "E": AnalysisSkill.COHORT,  # Ramp program → cohort tracking
        "F": AnalysisSkill.ROOT_CAUSE,  # Efficiency → root cause
        "G": AnalysisSkill.PLANNING,  # Integration → planning
        "H": AnalysisSkill.PLANNING,  # Innovation → planning
    }

    # Skill chains: When skill A finds X, run skill B next
    SKILL_CHAINS = {
        AnalysisSkill.EDA: {
            "outliers_detected": AnalysisSkill.ROOT_CAUSE,
            "temporal_pattern": AnalysisSkill.TIME_SERIES,
            "geographic_disparity": AnalysisSkill.SEGMENTATION,
        },
        AnalysisSkill.TIME_SERIES: {
            "seasonal_component_strong": AnalysisSkill.SEGMENTATION,
            "deterioration_accelerating": AnalysisSkill.ROOT_CAUSE,
        },
        AnalysisSkill.COHORT: {
            "cohort_performance_diverges": AnalysisSkill.ROOT_CAUSE,
            "different_segments_affected": AnalysisSkill.SEGMENTATION,
        },
        AnalysisSkill.DATA_QUALITY: {
            "bias_detected": AnalysisSkill.SEGMENTATION,
            "gaps_concentrated": AnalysisSkill.ROOT_CAUSE,
        },
    }

    # Skill-specific context parameters
    SKILL_PARAMETERS = {
        AnalysisSkill.EDA: {
            "outlier_threshold_std": 3,
            "group_by_geographic": True,
            "distribution_bins": 30,
        },
        AnalysisSkill.TIME_SERIES: {
            "decomposition_type": "additive",
            "forecast_confidence_interval": 0.95,
            "forecast_horizon_months": 12,
        },
        AnalysisSkill.COHORT: {
            "cohort_defining_column": "assessment_date",
            "min_cohort_size": 100,
            "retention_timeframes": ["1_year", "2_year", "3_year"],
        },
        AnalysisSkill.SEGMENTATION: {
            "clustering_method": "kmeans",
            "n_segments": 5,
            "minimize_metrics": ["condition_score"],
            "include_demographic_context": True,
        },
        AnalysisSkill.ROOT_CAUSE: {
            "test_type": "t-test",
            "significance_level": 0.05,
            "control_variables": [],
        },
        AnalysisSkill.DATA_QUALITY: {
            "completeness_threshold": 0.95,
            "timeliness_sla_days": 730,  # 2 years
            "consistency_kappa_target": 0.85,
        },
        AnalysisSkill.BUSINESS_METRICS: {
            "monetization_enabled": True,
            "scenario_analysis": True,
            "sensitivity_analysis": True,
        },
        AnalysisSkill.IMPACT: {
            "monetization_model": "health_impact",
            "discount_rate": 0.03,
        },
    }

    def activate(self, question_resolution: QuestionResolution) -> SkillContext:
        """
        Activate skill for a question with pre-populated context.

        Returns SkillContext ready to pass to the skill.
        """
        skill = question_resolution.primary_skill
        params = self.SKILL_PARAMETERS.get(skill, {})

        return SkillContext(
            skill=skill,
            question_id=question_resolution.question_id,
            question_text=question_resolution.question_text,
            datasets=question_resolution.datasets,
            kpi_ids=[k.kpi_id for k in question_resolution.kpis],
            critical_datasets=[d.name for d in question_resolution.critical_datasets],
            parameters=params,
            notes=question_resolution.notes,
        )

    def get_chained_skills(self, skill: AnalysisSkill, finding_key: str) -> Optional[AnalysisSkill]:
        """
        Get the next skill to run based on a finding from the current skill.

        Example: skill=EDA, finding_key="outliers_detected" → AnalysisSkill.ROOT_CAUSE
        """
        chains = self.SKILL_CHAINS.get(skill, {})
        return chains.get(finding_key)

    def activate_chain(self, question_resolution: QuestionResolution, finding_key: str) -> Optional[SkillContext]:
        """
        Activate the next skill in a chain based on a finding.

        Returns new SkillContext for chained skill, or None if no chain defined.
        """
        current_skill = question_resolution.primary_skill
        next_skill = self.get_chained_skills(current_skill, finding_key)

        if not next_skill:
            return None

        # Update question resolution with chained skill
        question_resolution.primary_skill = next_skill
        return self.activate(question_resolution)

    def describe_activation(self, context: SkillContext) -> str:
        """Human-readable description of skill activation"""
        dataset_names = ", ".join([d.name for d in context.datasets])
        return f"""
Skill Activation
================
Question: {context.question_id} - {context.question_text}
Skill: {context.skill.value}
Datasets: {dataset_names}
KPIs: {", ".join(context.kpi_ids)}
Critical: {", ".join(context.critical_datasets)}

Parameters: {context.parameters}

Notes: {context.notes}
        """.strip()


__all__ = [
    "SkillActivator",
    "SkillContext",
    "SkillChain",
]
