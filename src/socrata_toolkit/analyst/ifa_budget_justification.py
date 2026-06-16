"""IFA Budget Justification Generator — ramp gap × cost/ramp → PDF memo."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

COST_PER_RAMP_USD: int = 45_000
SLA_TARGET_COMPLETION: float = 0.90
CONTINGENCY_FACTOR: float = 1.15


@dataclass
class BoroughBudgetAllocation:
    """Budget allocation for one borough."""

    borough: str
    total_ramps: int
    completed_ramps: int
    current_completion_rate: float
    target_completion_rate: float
    ramps_remaining: int
    base_cost_usd: float
    contingency_cost_usd: float
    total_cost_usd: float
    ci_lower_95: float | None = None
    ci_upper_95: float | None = None
    risk_level: str = "medium"


class IFABudgetJustification:
    """Generates IFA Budget Justification memos from ramp_progress completion gaps."""

    def __init__(
        self,
        cost_per_ramp: int = COST_PER_RAMP_USD,
        sla_target: float = SLA_TARGET_COMPLETION,
        contingency: float = CONTINGENCY_FACTOR,
    ) -> None:
        self.cost_per_ramp = cost_per_ramp
        self.sla_target = sla_target
        self.contingency = contingency

    def compute_allocations(self, borough_stats: list) -> list[BoroughBudgetAllocation]:
        """Compute per-borough budget needs from BoroughRampStats list.

        Args:
            borough_stats: List of BoroughRampStats from RampCompletionReportGenerator

        Returns:
            List of BoroughBudgetAllocation with cost and risk breakdown
        """
        allocations = []
        for stat in borough_stats:
            gap = max(0.0, self.sla_target - stat.completion_rate)
            ramps_remaining = int(round(stat.total_ramps * gap))
            base_cost = ramps_remaining * self.cost_per_ramp
            contingency_cost = base_cost * (self.contingency - 1.0)
            risk = "high" if gap > 0.20 else "medium" if gap > 0.10 else "low"
            allocations.append(
                BoroughBudgetAllocation(
                    borough=stat.borough,
                    total_ramps=stat.total_ramps,
                    completed_ramps=stat.completed_ramps,
                    current_completion_rate=stat.completion_rate,
                    target_completion_rate=self.sla_target,
                    ramps_remaining=ramps_remaining,
                    base_cost_usd=float(base_cost),
                    contingency_cost_usd=float(contingency_cost),
                    total_cost_usd=float(base_cost + contingency_cost),
                    ci_lower_95=stat.ci_lower,
                    ci_upper_95=stat.ci_upper,
                    risk_level=risk,
                )
            )
        return allocations

    def total_budget(self, allocations: list[BoroughBudgetAllocation]) -> float:
        """Sum total budget across all boroughs.

        Args:
            allocations: List of BoroughBudgetAllocation

        Returns:
            Total cost in USD
        """
        return sum(a.total_cost_usd for a in allocations)

    def export_to_pdf(self, allocations: list[BoroughBudgetAllocation], output_path: str) -> None:
        """Export PDF budget justification memo using ReportLab.

        Args:
            allocations: List of BoroughBudgetAllocation
            output_path: Path to write PDF file
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError:
            logger.warning("reportlab not installed — writing text fallback")
            self._write_text_fallback(allocations, output_path)
            return

        doc = SimpleDocTemplate(output_path, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("NYC DOT — IFA Budget Justification Memorandum", styles["Title"]))
        story.append(
            Paragraph("Pedestrian Ramp SLA Completion Program", styles["Heading1"])
        )
        story.append(Spacer(1, 12))

        total = self.total_budget(allocations)
        story.append(
            Paragraph(
                f"Total Budget Request: ${total:,.0f} (including {int((self.contingency-1)*100)}% contingency)",
                styles["Normal"],
            )
        )
        story.append(
            Paragraph(
                f"SLA Target: {self.sla_target*100:.0f}% ramp completion across all boroughs",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 20))

        table_data = [
            [
                "Borough",
                "Current %",
                "Target %",
                "Ramps\nNeeded",
                "Base Cost",
                "W/ Contingency",
                "Risk",
            ]
        ]
        for a in allocations:
            table_data.append(
                [
                    a.borough,
                    f"{a.current_completion_rate*100:.1f}%",
                    f"{a.target_completion_rate*100:.0f}%",
                    str(a.ramps_remaining),
                    f"${a.base_cost_usd:,.0f}",
                    f"${a.total_cost_usd:,.0f}",
                    a.risk_level.upper(),
                ]
            )
        table_data.append(["TOTAL", "", "", "", "", f"${total:,.0f}", ""])

        t = Table(table_data, colWidths=[60, 70, 70, 60, 80, 90, 50])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#EEF2F7")]),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ]
            )
        )
        story.append(t)
        doc.build(story)
        logger.info("IFA budget justification saved to %s", output_path)

    def _write_text_fallback(
        self, allocations: list[BoroughBudgetAllocation], path: str
    ) -> None:
        """Fallback text-only export when ReportLab unavailable."""
        lines = ["NYC DOT IFA Budget Justification", "=" * 50]
        for a in allocations:
            lines.append(
                f"{a.borough}: {a.ramps_remaining} ramps × ${self.cost_per_ramp:,} = ${a.total_cost_usd:,.0f}"
            )
        lines.append(f"TOTAL: ${self.total_budget(allocations):,.0f}")
        with open(path, "w") as f:
            f.write("\n".join(lines))
