from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class DashboardSummary:
    """Backward-compatible dashboard snapshot."""

    metrics: list
    overall_health: str
    green_count: int
    yellow_count: int
    red_count: int
    timestamp: str = ""
    budget_codes: list = field(default_factory=list)


@dataclass
class ReportSection:
    """A section within a report."""

    title: str
    content: str
    data: dict[str, Any] | None = None


@dataclass
class Report:
    """A complete generated report conforming to WCAG 2.1 AA accessibility standards."""

    title: str
    generated_at: str
    sections: list[ReportSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def add_section(self, title: str, content: str, data: dict[str, Any] | None = None) -> None:
        self.sections.append(ReportSection(title=title, content=content, data=data))

    def add_warning(self, warning: str) -> None:
        self.warnings.append(warning)

    def to_markdown(self) -> str:
        """Render the report as Markdown text."""
        lines = [
            f"# {self.title}",
            f"**Report Generated:** {self.generated_at} | **Department:** NYC DOT Operations",
            "---",
            "",
        ]

        if self.warnings:
            lines.append("### ⚠️ Data Limitations Notice")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")

        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append(f"{section.content}\n")
            if section.data:
                for key, value in section.data.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize the report as JSON."""
        return json.dumps(
            {
                "title": self.title,
                "generated_at": self.generated_at,
                "metadata": self.metadata,
                "warnings": self.warnings,
                "sections": [
                    {"title": s.title, "content": s.content, "data": s.data} for s in self.sections
                ],
            },
            indent=2,
            default=str,
        )

    def to_html(self) -> str:
        """Render the report as a highly accessible, styled HTML document for public administration."""
        sections_html = ""

        warnings_html = ""
        if self.warnings:
            warnings_list = "".join(f"<li>{w}</li>" for w in self.warnings)
            warnings_html = f"""
            <div class="alert-box" role="alert" aria-live="assertive">
                <h2>⚠️ Data Limitations Notice</h2>
                <ul>{warnings_list}</ul>
            </div>
            """

        for i, s in enumerate(self.sections):
            data_html = ""
            if s.data:
                data_html = (
                    '<dl class="data-grid">'
                    + "".join(
                        f'<div class="data-item"><dt>{k}</dt><dd>{v}</dd></div>'
                        for k, v in s.data.items()
                    )
                    + "</dl>"
                )
            sections_html += f"""
            <section id="sec-{i}">
                <h2>{s.title}</h2>
                <p>{s.content}</p>
                {data_html}
            </section>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.title}</title>
    <style>
        :root {{
            --primary: #0033A0; /* High contrast NYC Blue */
            --text-main: #1A1A1A;
            --bg-light: #F4F6F9;
            --border: #D1D5DB;
            --alert-bg: #FFF3CD;
            --alert-text: #856404;
            --alert-border: #FFEEBA;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: var(--text-main);
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            background-color: #FFFFFF;
        }}
        header {{
            border-bottom: 3px solid var(--primary);
            margin-bottom: 2rem;
            padding-bottom: 1rem;
        }}
        h1 {{
            color: var(--primary);
            font-size: 2.25rem;
            margin-bottom: 0.5rem;
        }}
        .meta-info {{
            color: #4B5563;
            font-size: 0.95rem;
            font-weight: 500;
        }}
        .alert-box {{
            background-color: var(--alert-bg);
            color: var(--alert-text);
            border: 1px solid var(--alert-border);
            border-radius: 6px;
            padding: 1rem 1.5rem;
            margin-bottom: 2rem;
        }}
        .alert-box h2 {{
            margin-top: 0;
            font-size: 1.1rem;
            color: var(--alert-text);
            border: none;
        }}
        section {{
            margin-bottom: 2.5rem;
        }}
        h2 {{
            color: var(--primary);
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.3rem;
            margin-top: 2rem;
        }}
        .data-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            margin: 1.5rem 0;
            padding: 0;
        }}
        .data-item {{
            background: var(--bg-light);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
        }}
        dt {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #4B5563;
            margin-bottom: 0.25rem;
            font-weight: 700;
        }}
        dd {{
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
            color: var(--text-main);
        }}
        @media (max-width: 600px) {{
            .data-grid {{ grid-template-columns: 1fr; }}
            body {{ padding: 1rem; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>{self.title}</h1>
        <div class="meta-info">
            <span aria-label="Generated Timestamp">Report Generated: {self.generated_at}</span><br>
            <span>Department: NYC DOT Operations</span>
        </div>
    </header>
    <main>
        {warnings_html}
        {sections_html}
    </main>
</body>
</html>"""

    def save(self, path: str) -> str:
        """Save the report to a file (format auto-detected from extension)."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        ext = p.suffix.lower()
        if ext == ".json":
            p.write_text(self.to_json(), encoding="utf-8")
        elif ext == ".html":
            p.write_text(self.to_html(), encoding="utf-8")
        else:
            p.write_text(self.to_markdown(), encoding="utf-8")
        return str(p)


def generate_contract_report(
    df: pd.DataFrame,
    contract_id_col: str = "contract_id",
    planned_sqft_col: str = "planned_sqft",
    actual_sqft_col: str = "actual_sqft",
    planned_spend_col: str = "planned_spend",
    actual_spend_col: str = "actual_spend",
    status_col: str = "status",
    borough_col: str = "borough",
) -> Report:
    """Generate a contract status report covering progress and budget."""
    report = Report(
        title="DOT Sidewalk Contract Status Report",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if df.empty:
        report.add_warning("The provided dataset is entirely empty. Report reflects 0 values.")
        return report

    # Check missing columns
    expected_cols = [
        contract_id_col,
        planned_sqft_col,
        actual_sqft_col,
        planned_spend_col,
        actual_spend_col,
        borough_col,
    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        report.add_warning(
            f"Missing expected columns in dataset: {', '.join(missing)}. Values derived from these columns will display as 'Data Unavailable' or 0."
        )

    def get_sum(col: str) -> float:
        return float(df[col].fillna(0).sum()) if col in df.columns else 0.0

    total_contracts = df[contract_id_col].nunique() if contract_id_col in df.columns else len(df)
    planned_sqft = get_sum(planned_sqft_col)
    actual_sqft = get_sum(actual_sqft_col)
    pct_complete = (
        round(actual_sqft / max(planned_sqft, 1) * 100, 1)
        if planned_sqft > 0
        else "Data Unavailable"
    )
    planned_budget = get_sum(planned_spend_col)
    actual_budget = get_sum(actual_spend_col)
    budget_variance = actual_budget - planned_budget

    report.add_section(
        "Portfolio Summary",
        f"Tracking {total_contracts} active records across the sidewalk repair program.",
        {
            "Total Records / Contracts": total_contracts,
            "Planned SqFt": f"{planned_sqft:,.0f}" if planned_sqft else "Data Unavailable",
            "Actual SqFt": f"{actual_sqft:,.0f}" if actual_sqft else "Data Unavailable",
            "% Complete": f"{pct_complete}%" if isinstance(pct_complete, float) else pct_complete,
            "Planned Budget": f"${planned_budget:,.2f}" if planned_budget else "Data Unavailable",
            "Actual Spend": f"${actual_budget:,.2f}" if actual_budget else "Data Unavailable",
        },
    )

    if borough_col in df.columns:
        boro_data = {}
        for borough, group in df.groupby(borough_col):
            b_planned = (
                float(group[planned_sqft_col].fillna(0).sum())
                if planned_sqft_col in group.columns
                else 0
            )
            b_actual = (
                float(group[actual_sqft_col].fillna(0).sum())
                if actual_sqft_col in group.columns
                else 0
            )
            if b_planned > 0:
                b_pct = round(b_actual / max(b_planned, 1) * 100, 1)
                boro_data[str(borough)] = (
                    f"{b_pct}% complete ({b_actual:,.0f} / {b_planned:,.0f} sqft)"
                )
            else:
                boro_data[str(borough)] = f"{len(group)} records (SqFt data unavailable)"
        report.add_section("Borough Breakdown", "Progress mapped by geographic region:", boro_data)

    if planned_budget > 0:
        variance_status = (
            "ON BUDGET"
            if abs(budget_variance) < planned_budget * 0.05
            else ("OVER BUDGET" if budget_variance > 0 else "UNDER BUDGET")
        )
        report.add_section(
            "Budget Analysis",
            f"Current budget trajectory assessment: **{variance_status}**",
            {
                "Variance Amount": f"${budget_variance:,.2f}",
                "Variance Percentage": f"{round(budget_variance / max(planned_budget, 1) * 100, 1)}%",
            },
        )

    return report


def generate_program_report(dashboard: Any) -> Report:
    """Generate a program KPI report from a ProgramDashboard."""
    report = Report(
        title="DOT Sidewalk Program KPI Executive Summary",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if not dashboard.metrics:
        report.add_warning("No active metrics recorded in the dashboard.")

    report.add_section(
        "Program Health",
        f"Overall programmatic health condition: **{dashboard.overall_health.upper()}**",
        {
            "Stable (Green) Metrics": dashboard.green_count,
            "At-Risk (Yellow) Metrics": dashboard.yellow_count,
            "Critical (Red) Metrics": dashboard.red_count,
        },
    )

    for metric in dashboard.metrics:
        icon = {"green": "✅", "yellow": "⚠️", "red": "❌"}.get(metric.status, "ℹ️")
        report.add_section(
            f"{icon} {metric.name.replace('_', ' ').title()}",
            f"Status: {metric.status.upper()}",
            {
                "Current Value": f"{metric.value}",
                "Target Goal": f"{metric.target}",
                "Delta": f"{metric.delta_from_target}",
            },
        )

    if dashboard.budget_codes:
        bc_data = {}
        for bc in dashboard.budget_codes:
            bc_data[f"{bc.code} - {bc.category.title()}"] = (
                f"${bc.spent:,.2f} spent of ${bc.allocated:,.2f} ({bc.pct_used}% utilization)"
            )
        report.add_section(
            "Budget Code Allocations", "Utilization rates across active funding lines:", bc_data
        )

    return report


def generate_inquiry_response(inquiry_type: str, df: pd.DataFrame, **kwargs) -> Report:
    """Generate an official response to an administrative data inquiry."""
    report = Report(
        title=f"Official Data Inquiry Response: {inquiry_type.replace('_', ' ').title()}",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    if df.empty:
        report.add_warning("The query returned an empty result set. No matching records found.")

    details = ", ".join(f"{k} = {v}" for k, v in kwargs.items()) if kwargs else "General Query"

    report.add_section(
        "Inquiry Synopsis",
        "This document serves as the automated data retrieval response for the requested parameters.",
        {
            "Inquiry Type": inquiry_type.replace("_", " ").title(),
            "Search Parameters": details,
            "Total Records Validated": len(df),
        },
    )

    return report
