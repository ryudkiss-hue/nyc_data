"""Automated Report Generation for DOT Sidewalk Inspection & Management.

Generate analytical reports for contract progress, budget analysis,
productivity metrics, and program KPIs. Reports can be exported as
JSON, HTML, or Markdown.

Key capabilities:
- Contract status reports with progress and budget sections
- Program-level KPI reports with red/yellow/green indicators
- Borough comparison reports
- Inquiry response templates for contract/infrastructure questions
- Scheduled report generation (for use with nightly jobs)

Example::

    from socrata_toolkit.reporting import (
        generate_contract_report,
        generate_program_report,
        generate_inquiry_response,
    )

    report = generate_contract_report(contracts_df)
    report.save("reports/contract_status.md")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ReportSection:
    """A section within a report."""
    title: str
    content: str
    data: dict[str, Any] | None = None


@dataclass
class Report:
    """A complete generated report."""
    title: str
    generated_at: str
    sections: list[ReportSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_section(self, title: str, content: str, data: dict[str, Any] | None = None) -> None:
        self.sections.append(ReportSection(title=title, content=content, data=data))

    def to_markdown(self) -> str:
        """Render the report as Markdown text."""
        lines = [
            f"# {self.title}",
            f"*Generated: {self.generated_at}*",
            "",
        ]
        for section in self.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            if section.data:
                for key, value in section.data.items():
                    lines.append(f"- **{key}**: {value}")
                lines.append("")
        return "\n".join(lines)

    def to_json(self) -> str:
        """Serialize the report as JSON."""
        return json.dumps({
            "title": self.title,
            "generated_at": self.generated_at,
            "metadata": self.metadata,
            "sections": [
                {"title": s.title, "content": s.content, "data": s.data}
                for s in self.sections
            ],
        }, indent=2, default=str)

    def to_html(self) -> str:
        """Render the report as a simple HTML document."""
        sections_html = ""
        for s in self.sections:
            data_html = ""
            if s.data:
                data_html = "<ul>" + "".join(
                    f"<li><strong>{k}</strong>: {v}</li>" for k, v in s.data.items()
                ) + "</ul>"
            sections_html += f"<h2>{s.title}</h2><p>{s.content}</p>{data_html}"
        return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{self.title}</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:auto;padding:2em}}
h1{{color:#003366}}h2{{color:#004488;border-bottom:1px solid #ccc}}
table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px;text-align:left}}
th{{background:#f5f5f5}}.green{{color:#228B22}}.yellow{{color:#B8860B}}.red{{color:#B22222}}</style>
</head><body><h1>{self.title}</h1><p><em>Generated: {self.generated_at}</em></p>
{sections_html}</body></html>"""

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


# ---------------------------------------------------------------------------
# Contract Status Report
# ---------------------------------------------------------------------------

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
    """Generate a contract status report covering progress and budget.

    Produces sections for:
    - Overall contract portfolio summary
    - Per-borough breakdown
    - Budget variance analysis
    - At-risk contracts (behind schedule or over budget)
    """
    report = Report(
        title="DOT Sidewalk Contract Status Report",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    total_contracts = df[contract_id_col].nunique() if contract_id_col in df.columns else len(df)
    planned_sqft = float(df[planned_sqft_col].fillna(0).sum()) if planned_sqft_col in df.columns else 0
    actual_sqft = float(df[actual_sqft_col].fillna(0).sum()) if actual_sqft_col in df.columns else 0
    pct_complete = round(actual_sqft / max(planned_sqft, 1) * 100, 1)
    planned_budget = float(df[planned_spend_col].fillna(0).sum()) if planned_spend_col in df.columns else 0
    actual_budget = float(df[actual_spend_col].fillna(0).sum()) if actual_spend_col in df.columns else 0
    budget_variance = actual_budget - planned_budget

    report.add_section(
        "Portfolio Summary",
        f"Tracking {total_contracts} active contracts across the sidewalk repair program.",
        {
            "Total Contracts": total_contracts,
            "Planned SqFt": f"{planned_sqft:,.0f}",
            "Actual SqFt": f"{actual_sqft:,.0f}",
            "% Complete": f"{pct_complete}%",
            "Planned Budget": f"${planned_budget:,.2f}",
            "Actual Spend": f"${actual_budget:,.2f}",
            "Budget Variance": f"${budget_variance:,.2f}" + (" (over)" if budget_variance > 0 else " (under)"),
        },
    )

    # Borough breakdown
    if borough_col in df.columns:
        boro_data = {}
        for borough, group in df.groupby(borough_col):
            b_planned = float(group[planned_sqft_col].fillna(0).sum()) if planned_sqft_col in group.columns else 0
            b_actual = float(group[actual_sqft_col].fillna(0).sum()) if actual_sqft_col in group.columns else 0
            b_pct = round(b_actual / max(b_planned, 1) * 100, 1)
            boro_data[str(borough)] = f"{b_pct}% complete ({b_actual:,.0f} / {b_planned:,.0f} sqft)"
        report.add_section(
            "Borough Breakdown",
            "Progress by borough:",
            boro_data,
        )

    # Budget variance
    variance_status = "ON BUDGET" if abs(budget_variance) < planned_budget * 0.05 else (
        "OVER BUDGET" if budget_variance > 0 else "UNDER BUDGET"
    )
    report.add_section(
        "Budget Analysis",
        f"Current budget status: **{variance_status}**",
        {
            "Planned Budget": f"${planned_budget:,.2f}",
            "Actual Spend": f"${actual_budget:,.2f}",
            "Variance": f"${budget_variance:,.2f}",
            "Variance %": f"{round(budget_variance / max(planned_budget, 1) * 100, 1)}%",
        },
    )

    return report


# ---------------------------------------------------------------------------
# Program KPI Report
# ---------------------------------------------------------------------------

def generate_program_report(
    dashboard: Any,  # ProgramDashboard from program_metrics
) -> Report:
    """Generate a program KPI report from a ProgramDashboard.

    Args:
        dashboard: A ProgramDashboard instance from ``program_metrics``.

    Returns:
        Report with KPI status sections and budget code summary.
    """
    report = Report(
        title="DOT Sidewalk Program KPI Report",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    # Overall health
    report.add_section(
        "Program Health",
        f"Overall program health: **{dashboard.overall_health.upper()}**",
        {
            "Green Metrics": dashboard.green_count,
            "Yellow Metrics": dashboard.yellow_count,
            "Red Metrics": dashboard.red_count,
        },
    )

    # Individual metrics
    for metric in dashboard.metrics:
        icon = {"green": "[OK]", "yellow": "[WARN]", "red": "[CRITICAL]"}.get(metric.status, "")
        report.add_section(
            f"{icon} {metric.name}",
            f"Current: {metric.value} | Target: {metric.target} | Status: {metric.status.upper()}",
            {
                "Value": metric.value,
                "Target": metric.target,
                "Delta": metric.delta_from_target,
                "Status": metric.status.upper(),
            },
        )

    # Budget codes
    if dashboard.budget_codes:
        bc_data = {}
        for bc in dashboard.budget_codes:
            bc_data[f"{bc.code} ({bc.category})"] = f"${bc.spent:,.2f} / ${bc.allocated:,.2f} ({bc.pct_used}% used)"
        report.add_section("Budget Codes", "Personnel and program budget code utilization:", bc_data)

    return report


# ---------------------------------------------------------------------------
# Inquiry Response
# ---------------------------------------------------------------------------

def generate_inquiry_response(
    inquiry_type: str,
    df: pd.DataFrame,
    contract_id: str | None = None,
    location: str | None = None,
    borough: str | None = None,
    contract_id_col: str = "contract_id",
    borough_col: str = "borough",
    status_col: str = "status",
    address_col: str = "address",
) -> Report:
    """Generate a response to a contract or infrastructure planning inquiry.

    Supports common inquiry types:
    - "contract_status": Status of a specific contract
    - "location_status": Status of repairs at a specific location
    - "borough_overview": Overview of a borough's sidewalk program

    Args:
        inquiry_type: One of "contract_status", "location_status", "borough_overview".
        df: Relevant data.
        contract_id: For contract_status inquiries.
        location: Address/location for location_status inquiries.
        borough: Borough name for borough_overview inquiries.
    """
    report = Report(
        title=f"Inquiry Response: {inquiry_type.replace('_', ' ').title()}",
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        metadata={"inquiry_type": inquiry_type},
    )

    if inquiry_type == "contract_status" and contract_id:
        subset = df[df[contract_id_col] == contract_id] if contract_id_col in df.columns else df
        if subset.empty:
            report.add_section("Not Found", f"No data found for contract '{contract_id}'.")
        else:
            statuses = subset[status_col].value_counts().to_dict() if status_col in subset.columns else {}
            report.add_section(
                f"Contract {contract_id}",
                f"Found {len(subset)} records for this contract.",
                {"Records": len(subset), **{f"Status: {k}": v for k, v in statuses.items()}},
            )

    elif inquiry_type == "location_status" and location:
        subset = df[df[address_col].str.contains(location, case=False, na=False)] if address_col in df.columns else df
        report.add_section(
            f"Location: {location}",
            f"Found {len(subset)} records matching this location.",
            {"Matching Records": len(subset)},
        )

    elif inquiry_type == "borough_overview" and borough:
        subset = df[df[borough_col].str.upper() == borough.upper()] if borough_col in df.columns else df
        statuses = subset[status_col].value_counts().to_dict() if status_col in subset.columns else {}
        report.add_section(
            f"Borough Overview: {borough}",
            f"Total records: {len(subset)}",
            {"Total Records": len(subset), **{f"Status: {k}": v for k, v in statuses.items()}},
        )

    else:
        report.add_section("Unknown Inquiry", f"Inquiry type '{inquiry_type}' not recognized or missing parameters.")

    return report
