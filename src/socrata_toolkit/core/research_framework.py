"""
Programmatic Research Question/Methodology Framework for NYC DOT SIM Division

Generates research questions, methodologies, and analysis workflows based on:
1. Operational scope (SIM Division mandate, asset types, geographic coverage)
2. Data governance (dataset availability, freshness SLAs, quality thresholds)
3. Analyst responsibilities (official job duties, stakeholder reporting)
4. Academic/government standards (FHWA, ASTM, ADA, NIST)

Architecture: Deep module
- Input: Scope definition (agency, division, time_period)
- Output: Structured research question taxonomy with methodology mapping
- Locality: All question/methodology generation logic centralized
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Tuple
from enum import Enum


class ResearchDomain(Enum):
    """Major research domains for infrastructure analysis"""
    CONDITION_ASSESSMENT = "condition_assessment"  # PCI/SCI, distress types
    ACCESSIBILITY_EQUITY = "accessibility_equity"  # ADA, equity analysis
    DATA_QUALITY = "data_quality"  # Governance, validation
    ASSET_MANAGEMENT = "asset_management"  # Budgeting, lifecycle
    OPERATIONAL_EFFICIENCY = "operational_efficiency"  # Turnaround times, performance
    SAFETY_INTEGRATION = "safety_integration"  # Vision Zero, injury prevention
    CLIMATE_RESILIENCE = "climate_resilience"  # Environmental adaptation
    INNOVATION = "innovation"  # Emerging technologies


class AnalysisMethodology(Enum):
    """Standard methodologies for infrastructure analysis"""
    DESCRIPTIVE_STATISTICS = "descriptive_stats"  # Mean, median, distribution
    TIME_SERIES_DECOMPOSITION = "time_series"  # Trend, seasonality, anomalies
    COHORT_TRACKING = "cohort"  # Lifecycle, retention, performance by group
    SPATIAL_ANALYSIS = "spatial"  # Geographic patterns, clustering
    EQUITY_ANALYSIS = "equity"  # Disparity measurement, fairness metrics
    COST_BENEFIT = "cost_benefit"  # ROI, payback periods, efficiency
    QUALITY_ASSESSMENT = "quality"  # Completeness, validity, consistency
    PREDICTIVE_MODELING = "predictive"  # Forecasting, risk scoring
    COMPARATIVE_ANALYSIS = "comparative"  # Peer benchmarking, before/after


@dataclass
class ResearchQuestion:
    """Structured research question with methodology mapping"""
    question_id: str  # e.g., "A1", "B3.2"
    text: str  # Natural language question
    domain: ResearchDomain
    primary_methodology: AnalysisMethodology
    secondary_methodologies: List[AnalysisMethodology] = field(default_factory=list)
    required_datasets: List[str] = field(default_factory=list)
    kpi_outputs: List[str] = field(default_factory=list)
    analyst_duty: Optional[str] = None  # Official job responsibility it serves
    stakeholder: Optional[str] = None  # Who needs this answer (DOT leadership, program manager, etc.)
    frequency: Optional[str] = None  # How often should this be analyzed (daily, weekly, quarterly, annually)
    success_criteria: Optional[str] = None  # How to know the analysis worked
    academic_standard: Optional[str] = None  # Reference standard (ASTM, FHWA, ADA, etc.)


@dataclass
class MethodologyGuide:
    """Guidance for executing a specific methodology"""
    methodology: AnalysisMethodology
    description: str
    typical_questions: List[str]
    required_skills: List[str]  # Data analysis skills needed
    output_format: str  # Expected output type (metric, table, visualization, report)
    validation_criteria: List[str]  # How to verify the analysis is correct


class ResearchFramework:
    """
    Generates and manages research question taxonomy for NYC DOT SIM Division.

    Design: Deep module
    - Small interface: generate_questions(scope) → List[ResearchQuestion]
    - Large implementation: Question generation rules, methodology mapping, validation
    - Locality: All framework logic centralized; scales to new domains/methodologies
    """

    # Academic/government standards referenced
    STANDARDS = {
        "ASTM D6433": "Pavement Condition Index calculation",
        "FHWA": "Federal Highway Administration pavement management",
        "ADA": "Americans with Disabilities Act accessibility standards",
        "NIST": "National Institute of Standards and Technology data quality",
        "ISO 19157": "Geographic data quality measurement",
    }

    # NYC DOT analyst official duties (from job descriptions JID-35715, JID-42159)
    ANALYST_DUTIES = {
        "duty_001": "Monitor SCI trends and alert leadership to changes",
        "duty_002": "Track ADA transition plan progress and compliance",
        "duty_003": "Analyze equity in infrastructure investment",
        "duty_004": "Forecast budgets and prioritize repairs",
        "duty_005": "Report SLA compliance (inspection/repair turnaround)",
        "duty_006": "Detect spatial conflicts between programs",
        "duty_007": "Generate borough-level performance reports",
        "duty_008": "Track ramp program completion and quality",
        "duty_009": "Investigate data quality issues and recommend remediation",
        "duty_010": "Identify cost optimization opportunities",
        "duty_011": "Support strategic planning and policy decisions",
    }

    # Stakeholder groups and their information needs
    STAKEHOLDERS = {
        "dot_leadership": {
            "role": "Executive leadership",
            "frequency": "monthly",
            "focus": ["overall_condition", "equity_progress", "budget_efficiency"]
        },
        "sim_program_manager": {
            "role": "SIM Division management",
            "frequency": "weekly",
            "focus": ["inspection_progress", "ramp_completion", "quality_metrics"]
        },
        "transportation_planner": {
            "role": "Capital planning and budgeting",
            "frequency": "quarterly",
            "focus": ["budget_forecast", "lifecycle_analysis", "roi_analysis"]
        },
        "equity_officer": {
            "role": "Equity and accessibility",
            "frequency": "monthly",
            "focus": ["equity_disparity", "accessibility_compliance", "underserved_areas"]
        },
        "operations_manager": {
            "role": "Day-to-day operations",
            "frequency": "daily",
            "focus": ["inspection_backlog", "sla_compliance", "bottlenecks"]
        },
    }

    def __init__(self):
        """Initialize framework with standard methodologies and question templates"""
        self.methodology_guides = self._build_methodology_guides()
        self.question_templates = self._build_question_templates()

    def generate_questions(self,
                          domains: Optional[List[ResearchDomain]] = None,
                          stakeholder: Optional[str] = None) -> List[ResearchQuestion]:
        """
        Generate research questions for specified scope.

        Args:
            domains: Filter to specific domains (None = all)
            stakeholder: Filter to specific stakeholder needs (None = all)

        Returns:
            List of structured research questions with methodology mapping
        """
        questions = []

        # Generate base questions from templates
        for template in self.question_templates:
            # Filter by domain if specified
            if domains and template["domain"] not in domains:
                continue

            # Filter by stakeholder if specified
            if stakeholder and stakeholder not in template.get("stakeholders", []):
                continue

            # Instantiate question from template
            question = ResearchQuestion(
                question_id=template["id"],
                text=template["text"],
                domain=template["domain"],
                primary_methodology=template["primary_methodology"],
                secondary_methodologies=template.get("secondary_methodologies", []),
                required_datasets=template.get("required_datasets", []),
                kpi_outputs=template.get("kpi_outputs", []),
                analyst_duty=template.get("analyst_duty"),
                stakeholder=template.get("primary_stakeholder"),
                frequency=template.get("frequency"),
                success_criteria=template.get("success_criteria"),
                academic_standard=template.get("academic_standard"),
            )
            questions.append(question)

        return questions

    def get_methodology_guide(self, methodology: AnalysisMethodology) -> MethodologyGuide:
        """Get detailed guidance for executing a specific methodology"""
        return self.methodology_guides.get(methodology)

    def validate_question(self, question: ResearchQuestion) -> Tuple[bool, List[str]]:
        """
        Validate that a research question is well-formed and implementable.

        Returns: (is_valid, list_of_issues)
        """
        issues = []

        if not question.question_id:
            issues.append("Missing question_id")
        if not question.text:
            issues.append("Missing question text")
        if not question.required_datasets:
            issues.append("No datasets specified")
        if not question.kpi_outputs:
            issues.append("No KPI outputs specified")
        if question.primary_methodology not in AnalysisMethodology.__members__.values():
            issues.append(f"Invalid methodology: {question.primary_methodology}")

        return (len(issues) == 0, issues)

    def _build_methodology_guides(self) -> Dict[AnalysisMethodology, MethodologyGuide]:
        """Build guidance for each analysis methodology"""
        return {
            AnalysisMethodology.DESCRIPTIVE_STATISTICS: MethodologyGuide(
                methodology=AnalysisMethodology.DESCRIPTIVE_STATISTICS,
                description="Calculate summary statistics (mean, median, percentiles, distribution)",
                typical_questions=[
                    "What is the current condition across boroughs?",
                    "How many segments need repair?",
                ],
                required_skills=["programmatic-eda"],
                output_format="Table with statistics and visualizations",
                validation_criteria=[
                    "Sample size documented",
                    "Missing data handling explained",
                    "Outliers identified and justified",
                ]
            ),
            AnalysisMethodology.TIME_SERIES_DECOMPOSITION: MethodologyGuide(
                methodology=AnalysisMethodology.TIME_SERIES_DECOMPOSITION,
                description="Decompose time series into trend, seasonality, residual",
                typical_questions=[
                    "Is condition improving or deteriorating?",
                    "What is the seasonal pattern?",
                ],
                required_skills=["time-series-analysis"],
                output_format="Time series charts with decomposition",
                validation_criteria=[
                    "Stationarity tested",
                    "Decomposition method justified",
                    "Forecast confidence intervals provided",
                ]
            ),
            AnalysisMethodology.COHORT_TRACKING: MethodologyGuide(
                methodology=AnalysisMethodology.COHORT_TRACKING,
                description="Track groups over time (e.g., ramp completion cohorts by year)",
                typical_questions=[
                    "Do ramps completed in 2023 differ from 2022 in quality?",
                    "What is contractor performance over time?",
                ],
                required_skills=["cohort-analysis"],
                output_format="Cohort lifecycle curves and retention tables",
                validation_criteria=[
                    "Cohort sizes documented",
                    "Survival curves verified",
                    "Sample size adequate for statistical claims",
                ]
            ),
            AnalysisMethodology.SPATIAL_ANALYSIS: MethodologyGuide(
                methodology=AnalysisMethodology.SPATIAL_ANALYSIS,
                description="Analyze geographic patterns, clustering, spatial relationships",
                typical_questions=[
                    "Which neighborhoods have poorest condition?",
                    "Are poor conditions concentrated or dispersed?",
                ],
                required_skills=["segmentation-analysis"],
                output_format="Maps, spatial statistics, cluster definitions",
                validation_criteria=[
                    "Geographic units clearly defined",
                    "Spatial autocorrelation tested",
                    "Results justified by observed patterns",
                ]
            ),
            AnalysisMethodology.EQUITY_ANALYSIS: MethodologyGuide(
                methodology=AnalysisMethodology.EQUITY_ANALYSIS,
                description="Measure fairness in distribution of condition, investment, or benefits",
                typical_questions=[
                    "Do low-income neighborhoods have worse conditions?",
                    "Is repair investment proportional to need?",
                ],
                required_skills=["segmentation-analysis"],
                output_format="Equity metrics, disparity indices, allocation tables",
                validation_criteria=[
                    "Equity metric formula documented",
                    "Demographic data reliable and current",
                    "Confounders identified and controlled",
                ]
            ),
            AnalysisMethodology.COST_BENEFIT: MethodologyGuide(
                methodology=AnalysisMethodology.COST_BENEFIT,
                description="Calculate ROI, payback periods, cost-effectiveness",
                typical_questions=[
                    "What is the ROI for preventative vs. corrective repair?",
                    "Which budget allocation maximizes benefit?",
                ],
                required_skills=["business-metrics-calculator"],
                output_format="Cost tables, ROI charts, scenario analysis",
                validation_criteria=[
                    "All costs captured (materials, labor, overhead)",
                    "Discount rate justified",
                    "Sensitivity analysis performed",
                ]
            ),
            AnalysisMethodology.QUALITY_ASSESSMENT: MethodologyGuide(
                methodology=AnalysisMethodology.QUALITY_ASSESSMENT,
                description="Evaluate data completeness, validity, consistency, timeliness",
                typical_questions=[
                    "Can we trust the inspection data?",
                    "Are assessments consistent across inspectors?",
                ],
                required_skills=["data-quality-audit"],
                output_format="Quality scorecard, dimension assessments, issue log",
                validation_criteria=[
                    "Quality dimensions clearly defined",
                    "Thresholds justified",
                    "Remediation options identified",
                ]
            ),
            AnalysisMethodology.PREDICTIVE_MODELING: MethodologyGuide(
                methodology=AnalysisMethodology.PREDICTIVE_MODELING,
                description="Build models to forecast future conditions, risks, outcomes",
                typical_questions=[
                    "When will sidewalk failure occur?",
                    "Which ramps have highest defect risk?",
                ],
                required_skills=["time-series-analysis"],
                output_format="Model coefficients, forecast tables, risk scores",
                validation_criteria=[
                    "Model accuracy validated on test set",
                    "Assumptions documented",
                    "Confidence intervals provided",
                ]
            ),
            AnalysisMethodology.COMPARATIVE_ANALYSIS: MethodologyGuide(
                methodology=AnalysisMethodology.COMPARATIVE_ANALYSIS,
                description="Compare across time, space, or peer agencies",
                typical_questions=[
                    "How does NYC compare to peer cities?",
                    "Before vs. after: did the intervention work?",
                ],
                required_skills=["root-cause-investigation"],
                output_format="Comparison tables, rankings, statistical tests",
                validation_criteria=[
                    "Peer agencies/periods comparable",
                    "Statistical significance tested",
                    "Confounders controlled",
                ]
            ),
        }

    def _build_question_templates(self) -> List[Dict]:
        """Build templates for research questions by domain"""
        return [
            # CONDITION_ASSESSMENT domain
            {
                "id": "A1",
                "text": "What is the current Sidewalk Condition Index (SCI) across all boroughs?",
                "domain": ResearchDomain.CONDITION_ASSESSMENT,
                "primary_methodology": AnalysisMethodology.DESCRIPTIVE_STATISTICS,
                "secondary_methodologies": [AnalysisMethodology.SPATIAL_ANALYSIS],
                "required_datasets": ["violations", "street_centerline", "census_blocks_2020"],
                "kpi_outputs": ["KPI-001", "KPI-002", "KPI-003"],
                "analyst_duty": "duty_001",
                "primary_stakeholder": "dot_leadership",
                "frequency": "monthly",
                "success_criteria": "SCI calculated for each borough with 95% confidence interval",
                "academic_standard": "ASTM D6433",
                "stakeholders": ["dot_leadership", "sim_program_manager"],
            },
            {
                "id": "A2",
                "text": "What is the deterioration rate of sidewalk conditions year-over-year?",
                "domain": ResearchDomain.CONDITION_ASSESSMENT,
                "primary_methodology": AnalysisMethodology.TIME_SERIES_DECOMPOSITION,
                "required_datasets": ["violations"],
                "kpi_outputs": ["KPI-006", "KPI-007", "KPI-008"],
                "analyst_duty": "duty_001",
                "primary_stakeholder": "dot_leadership",
                "frequency": "quarterly",
                "success_criteria": "Year-over-year rate calculated with trend direction clear",
                "academic_standard": "FHWA",
            },
            # ACCESSIBILITY_EQUITY domain
            {
                "id": "B1",
                "text": "What percentage of intersections have ADA-compliant curb ramps?",
                "domain": ResearchDomain.ACCESSIBILITY_EQUITY,
                "primary_methodology": AnalysisMethodology.DESCRIPTIVE_STATISTICS,
                "required_datasets": ["ramp_progress", "street_centerline"],
                "kpi_outputs": ["KPI-036", "KPI-037", "KPI-038"],
                "analyst_duty": "duty_002",
                "primary_stakeholder": "equity_officer",
                "frequency": "monthly",
                "success_criteria": "Compliance % calculated by borough with gap identification",
                "academic_standard": "ADA",
                "stakeholders": ["equity_officer", "dot_leadership"],
            },
            {
                "id": "B3",
                "text": "Are low-income neighborhoods systematically underfunded in sidewalk repairs?",
                "domain": ResearchDomain.ACCESSIBILITY_EQUITY,
                "primary_methodology": AnalysisMethodology.EQUITY_ANALYSIS,
                "secondary_methodologies": [AnalysisMethodology.SPATIAL_ANALYSIS],
                "required_datasets": ["violations", "in_house_resurfacing", "census_blocks_2020"],
                "kpi_outputs": ["KPI-047", "KPI-048"],
                "analyst_duty": "duty_003",
                "primary_stakeholder": "equity_officer",
                "frequency": "quarterly",
                "success_criteria": "Equity index calculated; disparities quantified with statistical tests",
                "academic_standard": "ISO 19157",
            },
            # DATA_QUALITY domain
            {
                "id": "C1",
                "text": "What percentage of sidewalk segments have current (≤2 year old) condition assessments?",
                "domain": ResearchDomain.DATA_QUALITY,
                "primary_methodology": AnalysisMethodology.QUALITY_ASSESSMENT,
                "required_datasets": ["violations", "street_centerline"],
                "kpi_outputs": ["KPI-089", "KPI-090"],
                "analyst_duty": "duty_009",
                "primary_stakeholder": "sim_program_manager",
                "frequency": "weekly",
                "success_criteria": "Coverage % calculated; stale data identified by location",
            },
            # ASSET_MANAGEMENT domain
            {
                "id": "D1",
                "text": "What year-by-year budget is needed to maintain current condition levels?",
                "domain": ResearchDomain.ASSET_MANAGEMENT,
                "primary_methodology": AnalysisMethodology.COST_BENEFIT,
                "secondary_methodologies": [AnalysisMethodology.PREDICTIVE_MODELING],
                "required_datasets": ["violations", "in_house_resurfacing", "street_centerline"],
                "kpi_outputs": ["KPI-141", "KPI-142"],
                "analyst_duty": "duty_004",
                "primary_stakeholder": "transportation_planner",
                "frequency": "annually",
                "success_criteria": "5-year budget forecast with confidence intervals; scenarios modeled",
            },
            # OPERATIONAL_EFFICIENCY domain
            {
                "id": "F1",
                "text": "What is the average time from 311 complaint to repair completion?",
                "domain": ResearchDomain.OPERATIONAL_EFFICIENCY,
                "primary_methodology": AnalysisMethodology.DESCRIPTIVE_STATISTICS,
                "secondary_methodologies": [AnalysisMethodology.COMPARATIVE_ANALYSIS],
                "required_datasets": ["complaints_311", "violations", "dismissals"],
                "kpi_outputs": ["KPI-236", "KPI-237", "KPI-239"],
                "analyst_duty": "duty_005",
                "primary_stakeholder": "operations_manager",
                "frequency": "daily",
                "success_criteria": "Turnaround time calculated; SLA compliance tracked; bottlenecks identified",
            },
        ]


__all__ = [
    "ResearchFramework",
    "ResearchQuestion",
    "ResearchDomain",
    "AnalysisMethodology",
    "MethodologyGuide",
]
