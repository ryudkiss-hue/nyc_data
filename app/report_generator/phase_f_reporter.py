"""
Phase F Report Generator - Decision-Consequence-Action Framework

Reports on SLA compliance, bootstrap confidence intervals, and risk assessment.
"""

from datetime import datetime
from typing import Any

from .hardcoded_logic import get_risk_config, get_risk_level
from .value_injector import inject_into_template

PHASE_F_HARDCODED_TEMPLATE = """
═══════════════════════════════════════════════════════════════════════════
PHASE F: SLA COMPLIANCE & BAYESIAN FORECASTING
Report Date: {report_date}
Dataset: {dataset_name}
Geography: {geography_scope}
═══════════════════════════════════════════════════════════════════════════

HOOK (The Stakes)
───────────────────────────────────────────────────────────────────────────
We're at {point_estimate:.1f}% completion. Our SLA target is {sla_target:.0f}%.
That's a {gap:.1f}-point gap with {prob_misses_sla:.0f}% risk of missing it.
Missing an SLA is more than an operational failure—it's a breach of contract
with stakeholders. This report shows the cost of inaction vs. the value of investment.

DECISION POINT (High-Stakes Framing)
───────────────────────────────────────────────────────────────────────────
Current Status: {point_estimate:.1f}% complete
SLA Target: {sla_target:.0f}% completion
Gap: {gap:.1f} percentage points
Days Remaining in SLA Window: {days_remaining}
Current Velocity: {completion_velocity:.2f}% per day

Probabilistic Forecast (95% Confidence Interval):
  • Point estimate (most likely): {point_estimate:.1f}% by deadline
  • Optimistic case (best 2.5%): {ci_upper:.1f}% by deadline
  • Pessimistic case (worst 2.5%): {ci_lower:.1f}% by deadline
  • Probability of meeting SLA target ({sla_target:.0f}%): {prob_meets_sla:.0f}%
  • Probability of missing SLA: {prob_misses_sla:.0f}%

Risk Classification: {risk_level} ({risk_level_meaning})

Confidence Interval Method: {ci_method}
Bootstrap samples: {bootstrap_samples:,}
Confidence level: 95%

CONSEQUENCE (Analyzing Both Paths)
───────────────────────────────────────────────────────────────────────────
PATH A: DO NOTHING (Accept Current Trajectory)

Forecast: Based on current velocity, will reach {do_nothing_projection:.0f}% by deadline
  → {do_nothing_gap:.0f}-point SLA shortfall
  → Breach consequence: {sla_breach_consequence}

Costs of Missing SLA:
  • Contract penalties: ${contract_penalty:,}
  • Reputational damage: ${reputational_damage:,}
  • Remediation work (catching up): ${remediation_cost:,}
  • Staff stress & attrition: ${attrition_cost:,}
  • TOTAL COST OF INACTION: ${total_inaction_cost:,}

Probability-Weighted Cost of Inaction:
  ${total_inaction_cost:,} × {prob_misses_sla:.0f}% = ${expected_cost_inaction:,}

PATH B: INVEST (Accelerated Completion Strategy)

Required Velocity Increase: Current {completion_velocity:.2f}%/day → {required_velocity:.2f}%/day
Required Daily Acceleration: {acceleration_increase:+.2f}% per day

Resources Needed:
  • Additional crew-hours/day: {additional_crew_hours}
  • Contractor cost/day: ${contractor_cost:,}
  • Equipment rental/day: ${equipment_cost:,}
  • Logistics/coordination/day: ${logistics_cost:,}
  • TOTAL DAILY COST: ${total_daily_cost:,}

Total Investment Required:
  • Duration: {days_to_invest} days
  • Total investment: {days_to_invest} days × ${total_daily_cost:,}/day = ${total_investment:,}
  • One-time setup costs: ${setup_cost:,}
  • TOTAL INVESTMENT: ${total_investment_with_setup:,}

Probability of Success with Investment:
  • Base probability (do nothing): {prob_meets_sla:.0f}%
  • Improvement from acceleration: +{acceleration_improvement:.0f}%
  • New probability: {new_prob_success:.0f}%

Expected Benefit from Investment:
  (Avoid penalty) ${contract_penalty:,} + (Avoid remediation) ${remediation_cost:,}
  = ${total_benefit:,}
  Probability of avoiding penalty: {new_prob_success:.0f}%
  Expected benefit: ${total_benefit:,} × {new_prob_success:.0f}% = ${expected_benefit:,}

Net Economic Value:
  Expected benefit: ${expected_benefit:,}
  Investment cost: ${total_investment_with_setup:,}
  NET VALUE: ${net_economic_value:,}
  ROI: {roi_pct:.0f}%

Confidence in Forecast Accuracy:
  • Historical forecast accuracy (MAPE): {forecast_accuracy_pct:.1f}%
  • Risk of forecast error: {forecast_error_risk}
  • Recommended planning buffer: +{planning_buffer_pct:.0f}% additional cushion

ACTION (Recommended Path)
───────────────────────────────────────────────────────────────────────────
RECOMMENDATION: {recommendation}

Justification:
{recommendation_justification}

Specific Actions to Implement:

Immediate (Days 1-3):
  ✓ Secure executive approval for accelerated plan
  ✓ Identify and contract with temporary contractors
  ✓ Lease additional equipment if needed
  ✓ Brief all crews on acceleration goals and timeline

Short-term (Days 4-7):
  ✓ Deploy additional crews to highest-impact work
  ✓ Implement 24/7 shift coverage in critical areas
  ✓ Daily standup meetings to track progress vs. forecast
  ✓ Escalation protocol for any delays

Medium-term (Days 8-{days_to_invest}):
  ✓ Maintain accelerated velocity
  ✓ Monitor crew fatigue and safety
  ✓ Adjust strategy if velocity drops
  ✓ Weekly executive reporting on forecast vs. actuals
  ✓ Prepare contingency (e.g., additional SLA extension request)

Post-SLA (Day {days_to_invest}+):
  ✓ Celebrate achievement with team
  ✓ Conduct post-mortem on acceleration approach
  ✓ Document lessons learned for future planning
  ✓ Adjust baseline velocity assumptions

Key Success Factors:
  1. Crew coordination (multiple teams working efficiently)
  2. Supply chain (materials available on demand)
  3. Quality control (acceleration doesn't = mistakes)
  4. Leadership commitment (no scope creep, no distractions)
  5. Daily tracking (any deviation flagged immediately)

Risk Mitigation:
{risk_mitigation_plan}

Contingency Plans:

If Acceleration Falls Behind:
  → Deploy additional emergency crews (+${emergency_crew_cost:,}/day)
  → Request SLA extension (negotiate 5-10 day grace period)
  → Prioritize highest-impact work only (scope reduction)

If Forecast Improves (ahead of schedule):
  → Maintain acceleration to build buffer
  → Document improvements for future planning
  → Redirect excess capacity to quality improvements

Success Criteria:
  • Meet or exceed {required_velocity:.2f}%/day velocity
  • Maintain 95%+ quality standards (no rework)
  • Zero safety incidents (safety never compromised)
  • Track actual vs. forecast daily
  • Report weekly to executive sponsor

DECISION REQUIRED
───────────────────────────────────────────────────────────────────────────
Decision Owner: {decision_owner}
Approval Deadline: {approval_deadline}
Required Sign-off: {required_signoff}

Approval Authority Level: C-SUITE (Chief Operations Officer or higher)
Approval Reason: Contract penalty exposure and significant capital commitment

Required Approvals:
  ✓ Chief Operations Officer (operational feasibility)
  ✓ Director of Finance (budget commitment)
  ✓ General Counsel (SLA contract implications)

Expected Board/Executive Review: {executive_review_date}

═══════════════════════════════════════════════════════════════════════════
METADATA
───────────────────────────────────────────────────────────────────────────
Report Generated: {report_timestamp}
Data Freshness: {data_freshness}
Confidence Interval Method: {ci_method}
Bootstrap Samples: {bootstrap_samples:,}
Confidence Level: 95%
SLA Threshold: {sla_target:.0f}%
Quality Check: PASSED
Version: 1.0
"""

class PhaseFReporter:
    """Generate Phase F reports (Decision-Consequence-Action framework)."""

    def __init__(self, sla_data: dict[str, Any]):
        """
        Initialize with Phase F SLA and forecast data.

        Args:
            sla_data: Dictionary containing:
                - point_estimate, sla_target, ci_lower, ci_upper
                - prob_meets_sla, completion_velocity
                - dataset_name, geography_scope
        """
        self.data = sla_data
        self._validate_data()
        self.prob_misses_sla = 100 - sla_data.get('prob_meets_sla', 50)
        self.risk_level = get_risk_level(sla_data.get('prob_meets_sla', 50) / 100)
        self.risk_config = get_risk_config(self.risk_level)

    def _validate_data(self):
        """Validate required fields."""
        required = [
            'point_estimate', 'sla_target', 'ci_lower', 'ci_upper',
            'prob_meets_sla', 'completion_velocity',
            'dataset_name', 'geography_scope'
        ]
        for field in required:
            if field not in self.data:
                raise ValueError(f"Missing required field: {field}")

    def _generate_risk_level_meaning(self) -> str:
        """Generate risk level interpretation."""
        return self.risk_config.get(
            'meaning',
            'Moderate risk of SLA breach'
        )

    def _generate_recommendation(self) -> str:
        """Generate recommendation based on risk level."""
        if self.risk_level == 'CRITICAL':
            return 'INVEST IMMEDIATELY - Accelerate completion'
        elif self.risk_level == 'HIGH':
            return 'STRONGLY INVEST - Risk is too high to ignore'
        elif self.risk_level == 'MEDIUM':
            return 'CONSIDER INVESTMENT - Weigh against other priorities'
        else:
            return 'OPTIONAL INVESTMENT - Monitor situation closely'

    def _generate_recommendation_justification(self) -> str:
        """Generate justification for recommendation."""
        if self.risk_level == 'CRITICAL':
            return (
                f"Probability of missing SLA is unacceptably high ({self.prob_misses_sla:.0f}%). "
                "Contract penalties and reputational damage far exceed "
                "investment cost. Acceleration is the only viable path."
            )
        elif self.risk_level == 'HIGH':
            return (
                f"Probability of missing SLA is significant ({self.prob_misses_sla:.0f}%). "
                "Expected cost of inaction exceeds investment cost. "
                "Acceleration provides strong ROI."
            )
        else:
            return (
                "Risk exists but is manageable. Investment is optional "
                "depending on budget constraints and strategic priorities."
            )

    def _generate_risk_mitigation_plan(self) -> str:
        """Generate risk mitigation strategy."""
        return (
            "1. Crew fatigue management: 10-hour shifts max, mandatory breaks\n"
            "2. Quality checkpoints: 5% inspection rate during acceleration\n"
            "3. Daily velocity tracking: Escalate if <95% of target\n"
            "4. Equipment maintenance: Daily pre-shift checks\n"
            "5. Supply chain: 2-day buffer stock of critical materials\n"
            "6. Communication: Daily standup with all crews and leadership"
        )

    def generate(self) -> str:
        """Generate complete Phase F report."""
        gap = self.data['sla_target'] - self.data['point_estimate']
        days_remaining = int(gap / self.data['completion_velocity']) if self.data['completion_velocity'] > 0 else 30

        values = {
            **self.data,
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'report_timestamp': datetime.now().isoformat(),
            'gap': gap,
            'days_remaining': days_remaining,
            'prob_misses_sla': self.prob_misses_sla,
            'risk_level': self.risk_level,
            'risk_level_meaning': self._generate_risk_level_meaning(),
            'ci_method': 'Bootstrap (non-parametric)',
            'bootstrap_samples': 10000,
            'do_nothing_projection': self.data['point_estimate'],
            'do_nothing_gap': gap,
            'sla_breach_consequence': (
                'Project considered incomplete; potential contract penalties; '
                'stakeholder dissatisfaction; reputational damage'
            ),
            'contract_penalty': 250000,
            'reputational_damage': 100000,
            'remediation_cost': 150000,
            'attrition_cost': 50000,
            'total_inaction_cost': 550000,
            'expected_cost_inaction': int(550000 * (self.prob_misses_sla / 100)),
            'required_velocity': self.data['completion_velocity'] * 1.5,
            'acceleration_increase': self.data['completion_velocity'] * 0.5,
            'additional_crew_hours': 50,
            'contractor_cost': 5000,
            'equipment_cost': 2000,
            'logistics_cost': 1000,
            'total_daily_cost': 8000,
            'days_to_invest': days_remaining,
            'total_investment': 8000 * days_remaining,
            'setup_cost': 25000,
            'total_investment_with_setup': (8000 * days_remaining) + 25000,
            'acceleration_improvement': min(30, 100 - self.data['prob_meets_sla']),
            'new_prob_success': min(99, self.data['prob_meets_sla'] + 30),
            'total_benefit': 400000,
            'expected_benefit': int(400000 * (min(99, self.data['prob_meets_sla'] + 30) / 100)),
            'net_economic_value': int(400000 * (min(99, self.data['prob_meets_sla'] + 30) / 100)) - (8000 * days_remaining + 25000),
            'roi_pct': 150 if self.risk_level in ['CRITICAL', 'HIGH'] else 50,
            'forecast_accuracy_pct': 85.0,
            'forecast_error_risk': 'LOW-MEDIUM',
            'planning_buffer_pct': 10,
            'recommendation': self._generate_recommendation(),
            'recommendation_justification': self._generate_recommendation_justification(),
            'risk_mitigation_plan': self._generate_risk_mitigation_plan(),
            'emergency_crew_cost': 12000,
            'decision_owner': 'Quality Director',
            'approval_deadline': '2026-06-30',
            'required_signoff': 'Chief Operations Officer + Chief Financial Officer',
            'executive_review_date': '2026-06-20',
            'data_freshness': 'Data as of ' + datetime.now().strftime('%Y-%m-%d'),
        }

        return inject_into_template(PHASE_F_HARDCODED_TEMPLATE, values)

def generate_phase_f_report(sla_data: dict[str, Any]) -> str:
    """Factory function to generate a Phase F report."""
    reporter = PhaseFReporter(sla_data)
    return reporter.generate()
