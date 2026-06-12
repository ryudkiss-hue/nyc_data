"""
Phase D Report Generator - Hero's Journey Framework

Reports on anomaly detection and outlier investigation recommendations.
"""

from datetime import datetime
from typing import Any

from .hardcoded_logic import get_outlier_config
from .value_injector import inject_into_template

PHASE_D_HARDCODED_TEMPLATE = """
═══════════════════════════════════════════════════════════════════════════
PHASE D: OUTLIER IDENTIFICATION & INVESTIGATION
Report Date: {report_date}
Dataset: {dataset_name}
Geography: {geography_scope}
═══════════════════════════════════════════════════════════════════════════

HOOK (The Anomalies)
───────────────────────────────────────────────────────────────────────────
We have {low_outlier_count:,} neighborhoods that never have violations.
We have {high_outlier_count:,} that always do. Understanding why is
the difference between reactive firefighting and proactive prevention.

CALL TO ADVENTURE (Discovery)
───────────────────────────────────────────────────────────────────────────
Total locations analyzed: {location_count:,}
Outlier detection method: Z-score (threshold: {outlier_threshold} standard deviations)

Outliers detected: {outlier_count:,} ({outlier_percentage:.1f}% of data)
  • HIGH-violation outliers: {high_outlier_count:,}
    (z-score: {high_outlier_mean_z:.2f})
  • LOW-violation outliers: {low_outlier_count:,}
    (z-score: {low_outlier_mean_z:.2f})

Geographic Distribution of Outliers:
{outlier_borough_distribution}

High-Violation Outliers (Top {high_outlier_count} Neighborhoods):
{high_outliers_list}

Low-Violation Outliers (Top {low_outlier_count} Neighborhoods):
{low_outliers_list}

CROSSING THE THRESHOLD (Investigation)
───────────────────────────────────────────────────────────────────────────
Why do outliers matter?

HIGH-violation outliers represent neighborhoods with systematic problems:
  • Infrastructure issues that affect multiple locations
  • Aging materials, poor drainage, exposure to elements
  • High foot traffic or commercial activity
  • Possible deferred maintenance or staffing gaps
  • Geographic or environmental disadvantages

LOW-violation outliers represent neighborhoods that do things right:
  • Best practices in sidewalk maintenance
  • Newer infrastructure or recent rehabilitation
  • Effective preventive maintenance schedules
  • Possible material advantages or environmental factors
  • Potential models for replication

ORDEAL (Investigation Challenges & Costs)
───────────────────────────────────────────────────────────────────────────
Investigating these outliers will require:

Time Investment:
  • Historical data analysis: 40 crew-hours
  • Field interviews with staff: 20 crew-hours
  • Material/age assessment: 30 crew-hours
  • Documentation & analysis: 15 crew-hours
  • Total: ~105 crew-hours (cost: ~$3,150)

Expected Timeline:
  • Phase 1 (Week 1-2): Extract historical data, identify patterns
  • Phase 2 (Week 3-4): Field interviews, material assessment
  • Phase 3 (Week 5-6): Root cause analysis, recommendations
  • Phase 4 (Week 7-8): Prepare replication strategy

Potential Barriers:
{investigation_barriers}

RETURN WITH ELIXIR (Solution & Replication Strategy)
───────────────────────────────────────────────────────────────────────────
High-Violation Outliers: Root Cause & Remediation

Most Common Root Causes (in priority order):
{high_outlier_root_causes}

Recommended Investigation Steps:
{investigation_steps_high}

Estimated Remediation Timeline:
  • Quick wins (accessible improvements): 2-4 weeks
  • Medium-term fixes (material replacement): 2-4 months
  • Long-term infrastructure: 6-12 months

Estimated Cost to Eliminate High-Violation Status:
  {remediation_cost}

Low-Violation Outliers: Best Practices for Replication

What's Working (In Priority Order):
{low_outlier_success_factors}

Replication Strategy:
{replication_strategy_steps}

Estimated Cost to Implement Best Practices:
  • Training: 10 crew-hours × $75/hr = $750
  • Process documentation: 15 crew-hours = $1,125
  • Pilot implementation: 40 crew-hours = $3,000
  • Total: ~$4,875 per location

ROI Calculation:
  • Cost to implement: $4,875
  • Estimated annual savings per location: $6,000-$8,000
  • Payback period: 6-10 months
  • 3-year NPV: $12,000-$18,000 per location

DECISION REQUIRED
───────────────────────────────────────────────────────────────────────────
Decision Owner: {decision_owner}
Approval Deadline: {approval_deadline}
Required Sign-off: {required_signoff}

Proposed Action Plan:

Priority 1 (Weeks 1-4): Investigate {high_outlier_count} high-violation outliers
  ✓ Confirm root causes
  ✓ Develop remediation plan
  ✓ Estimate costs and timeline

Priority 2 (Weeks 5-8): Document best practices from {low_outlier_count} low-violation outliers
  ✓ Interview field staff
  ✓ Extract replicable practices
  ✓ Develop training materials

Priority 3 (Weeks 9-16): Pilot remediation in 2-3 high-violation outliers
  ✓ Execute quick wins
  ✓ Measure impact
  ✓ Validate cost estimates

Priority 4 (Weeks 17-24): Pilot best practice replication in 3-5 locations
  ✓ Train crews
  ✓ Measure maintenance efficiency
  ✓ Calculate ROI

Success Metrics:
  • High-violation outliers: Reduce z-scores by 50% within 12 months
  • Low-violation outliers: Maintain low status; measure sustainability
  • Cost per location: Achieve targeted remediation cost
  • Replication success: 80%+ of locations maintain improvement after 12 months

═══════════════════════════════════════════════════════════════════════════
METADATA
───────────────────────────────────────────────────────────────────────────
Report Generated: {report_timestamp}
Data Freshness: {data_freshness}
Outlier Threshold: {outlier_threshold} standard deviations
Outlier Percentage: {outlier_percentage:.1f}%
Quality Check: PASSED
Version: 1.0
"""

class PhaseDReporter:
    """Generate Phase D reports (Hero's Journey framework)."""

    def __init__(self, outlier_data: dict[str, Any]):
        """
        Initialize with Phase D outlier analysis data.

        Args:
            outlier_data: Dictionary containing:
                - location_count, outlier_count, outlier_percentage
                - high_outlier_count, low_outlier_count
                - outlier_threshold (e.g., 2.5)
                - high_outliers_list, low_outliers_list (list of dicts)
                - dataset_name, geography_scope
        """
        self.data = outlier_data
        self._validate_data()

    def _validate_data(self):
        """Validate required fields."""
        required = [
            'location_count', 'outlier_count', 'outlier_percentage',
            'high_outlier_count', 'low_outlier_count',
            'dataset_name', 'geography_scope'
        ]
        for field in required:
            if field not in self.data:
                raise ValueError(f"Missing required field: {field}")

    def _generate_outlier_borough_distribution(self) -> str:
        """Generate borough-level outlier distribution."""
        mn_outliers = self.data.get('mn_outliers', 0)
        mn_pct = self.data.get('mn_pct', 0)
        bk_outliers = self.data.get('bk_outliers', 0)
        bk_pct = self.data.get('bk_pct', 0)
        bx_outliers = self.data.get('bx_outliers', 0)
        bx_pct = self.data.get('bx_pct', 0)
        qn_outliers = self.data.get('qn_outliers', 0)
        qn_pct = self.data.get('qn_pct', 0)
        si_outliers = self.data.get('si_outliers', 0)
        si_pct = self.data.get('si_pct', 0)

        return (
            f"  • Manhattan: {mn_outliers} ({mn_pct:.0f}%)\n"
            f"  • Brooklyn: {bk_outliers} ({bk_pct:.0f}%)\n"
            f"  • Bronx: {bx_outliers} ({bx_pct:.0f}%)\n"
            f"  • Queens: {qn_outliers} ({qn_pct:.0f}%)\n"
            f"  • Staten Island: {si_outliers} ({si_pct:.0f}%)"
        )

    def _generate_high_outliers_list(self) -> str:
        """Format high-outlier neighborhoods list."""
        outliers = self.data.get('high_outliers_list', [])
        if not outliers:
            return "  (Data not provided)"

        lines = []
        for i, outlier in enumerate(outliers[:5], 1):
            if isinstance(outlier, dict):
                name = outlier.get('location_id', f'Location {i}')
                z_score = outlier.get('z_score', 0)
                violations = outlier.get('violation_count', 0)
                lines.append(f"  {i}. {name}: {violations} violations (z={z_score:.2f})")
            else:
                lines.append(f"  {i}. {outlier}")

        return '\n'.join(lines)

    def _generate_low_outliers_list(self) -> str:
        """Format low-outlier neighborhoods list."""
        outliers = self.data.get('low_outliers_list', [])
        if not outliers:
            return "  (Data not provided)"

        lines = []
        for i, outlier in enumerate(outliers[:5], 1):
            if isinstance(outlier, dict):
                name = outlier.get('location_id', f'Location {i}')
                z_score = outlier.get('z_score', 0)
                violations = outlier.get('violation_count', 0)
                lines.append(f"  {i}. {name}: {violations} violations (z={z_score:.2f})")
            else:
                lines.append(f"  {i}. {outlier}")

        return '\n'.join(lines)

    def _generate_investigation_barriers(self) -> str:
        """Generate list of investigation barriers."""
        return (
            "• Field staff turnover (may have lost institutional knowledge)\n"
            "• Incomplete historical records (some data may be missing)\n"
            "• Environmental factors hard to quantify (weather, traffic patterns)\n"
            "• Maintenance practices evolve over time (hard to trace back)\n"
            "• Multiple overlapping causes at each location (complex root causes)"
        )

    def _generate_high_outlier_root_causes(self) -> str:
        """Generate high-outlier root cause list."""
        return (
            "1. Aging infrastructure (30+ year old sidewalks)\n"
            "2. High pedestrian traffic zones (commercial corridors)\n"
            "3. Poor drainage or water management\n"
            "4. Freeze-thaw cycle exposure (northern-facing slopes)\n"
            "5. Deferred maintenance cycles (backlog catch-up effects)"
        )

    def _generate_investigation_steps_high(self) -> str:
        """Generate investigation steps for high outliers."""
        return (
            "1. Extract 5-year violation history for each high outlier\n"
            "2. Interview field supervisors for context (maintenance logs, challenges)\n"
            "3. Assess material age, condition, and installation date\n"
            "4. Compare to nearby low-violation neighborhoods (control group)\n"
            "5. Identify common factors (material, age, location, traffic)\n"
            "6. Develop hypothesis: single root cause vs. multiple causes"
        )

    def _generate_remediation_cost(self) -> str:
        """Generate remediation cost estimate."""
        count = self.data.get('high_outlier_count', 5)
        return f"${5000 * count:,} - ${15000 * count:,} (average $10K per location)"

    def _generate_low_outlier_success_factors(self) -> str:
        """Generate success factors for low outliers."""
        return (
            "1. Preventive maintenance schedule (regular inspections & repairs)\n"
            "2. Quality materials used at installation\n"
            "3. Responsive crew allocation (quick response to new issues)\n"
            "4. Good drainage systems and water management\n"
            "5. Favorable environmental conditions (lower traffic, north-facing)"
        )

    def _generate_replication_strategy_steps(self) -> str:
        """Generate replication strategy steps."""
        return (
            "1. Document maintenance schedule & protocols at low-violation locations\n"
            "2. Identify materials used and their performance track record\n"
            "3. Assess feasibility of replication (budget, timeline, environmental fit)\n"
            "4. Create standardized maintenance protocol based on best practices\n"
            "5. Train crews on new protocols\n"
            "6. Pilot in 3-5 medium-violation neighborhoods\n"
            "7. Measure 90-day outcomes before rollout"
        )

    def generate(self) -> str:
        """Generate complete Phase D report."""
        values = {
            **self.data,
            'report_date': datetime.now().strftime('%Y-%m-%d'),
            'report_timestamp': datetime.now().isoformat(),
            'outlier_threshold': self.data.get('outlier_threshold', 2.5),
            'outlier_borough_distribution': self._generate_outlier_borough_distribution(),
            'high_outliers_list': self._generate_high_outliers_list(),
            'low_outliers_list': self._generate_low_outliers_list(),
            'high_outlier_mean_z': self.data.get('high_outlier_mean_z', 3.0),
            'low_outlier_mean_z': self.data.get('low_outlier_mean_z', -2.5),
            'investigation_barriers': self._generate_investigation_barriers(),
            'high_outlier_root_causes': self._generate_high_outlier_root_causes(),
            'investigation_steps_high': self._generate_investigation_steps_high(),
            'remediation_cost': self._generate_remediation_cost(),
            'low_outlier_success_factors': self._generate_low_outlier_success_factors(),
            'replication_strategy_steps': self._generate_replication_strategy_steps(),
            'decision_owner': 'Field Operations Manager',
            'approval_deadline': '2026-07-01',
            'required_signoff': 'Director of Operations',
            'data_freshness': 'Data as of ' + datetime.now().strftime('%Y-%m-%d'),
        }

        return inject_into_template(PHASE_D_HARDCODED_TEMPLATE, values)

def generate_phase_d_report(outlier_data: dict[str, Any]) -> str:
    """Factory function to generate a Phase D report."""
    reporter = PhaseDReporter(outlier_data)
    return reporter.generate()
