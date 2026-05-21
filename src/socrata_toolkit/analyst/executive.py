"""Executive one-pager for analyst pack."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from ..engineering.contract_analytics import BudgetSummary, analyze_contract_progress, budget_analysis
from ..engineering.construction_list import ConflictCheckResult


def build_executive_summary(
    *,
    construction: pd.DataFrame,
    conflict_result: ConflictCheckResult | None,
    contracts: pd.DataFrame,
    kpi_payload: dict[str, Any] | None,
    run_date: str,
    profile_name: str,
) -> tuple[str, str]:
    """Return (markdown, html) executive one-pager."""
    borough_counts: dict[str, int] = {}
    if not construction.empty and "borough" in construction.columns:
        borough_counts = construction["borough"].value_counts().to_dict()

    top_conflicts: list[str] = []
    if conflict_result and conflict_result.conflict_count:
        for boro, cnt in list(conflict_result.summary_by_borough.items())[:5]:
            top_conflicts.append(f"{boro}: {cnt}")

    budget: BudgetSummary | None = None
    if not contracts.empty:
        try:
            budget = budget_analysis(contracts)
        except Exception:
            budget = None

    red_kpis = []
    if kpi_payload:
        for m in kpi_payload.get("metrics", []):
            if m.get("status") == "red":
                red_kpis.append(f"{m.get('name')}: {m.get('value')} (target {m.get('target')})")

    progress = []
    if not contracts.empty:
        try:
            progress = analyze_contract_progress(contracts)[:5]
        except Exception:
            pass

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md_lines = [
        f"# Executive Summary — {profile_name}",
        f"*Run date: {run_date} · Generated {generated}*",
        "",
        "## Borough activity",
    ]
    if borough_counts:
        for boro, cnt in sorted(borough_counts.items(), key=lambda x: -x[1]):
            md_lines.append(f"- **{boro}**: {cnt} locations")
    else:
        md_lines.append("- No construction list data")

    md_lines.extend(["", "## Conflicts"])
    if top_conflicts:
        for line in top_conflicts:
            md_lines.append(f"- {line}")
    elif conflict_result:
        md_lines.append(f"- Total conflicts: {conflict_result.conflict_count} ({conflict_result.conflict_rate}%)")
    else:
        md_lines.append("- No conflict scan performed")

    md_lines.extend(["", "## Budget (portfolio)"])
    if budget:
        md_lines.append(f"- Planned spend: ${budget.total_planned:,.0f}")
        md_lines.append(f"- Actual spend: ${budget.total_actual:,.0f}")
        md_lines.append(f"- **CPI:** {budget.cost_performance_index:.2f}")
        md_lines.append(f"- Variance: {budget.variance_pct:.1f}%")
    else:
        md_lines.append("- No contract budget data")

    md_lines.extend(["", "## Red KPIs"])
    if red_kpis:
        for k in red_kpis:
            md_lines.append(f"- {k}")
    else:
        md_lines.append("- None flagged red")

    if progress:
        md_lines.extend(["", "## Contract progress (top)"])
        for p in progress:
            md_lines.append(f"- {p.contract_id}: {p.pct_complete}% ({p.status})")

    md = "\n".join(md_lines)

    kpi_html = "".join(f"<li>{k}</li>" for k in red_kpis) or "<li>None flagged red</li>"
    boro_html = "".join(
        f"<li><strong>{b}</strong>: {c}</li>" for b, c in sorted(borough_counts.items(), key=lambda x: -x[1])
    ) or "<li>No data</li>"
    cpi = f"{budget.cost_performance_index:.2f}" if budget else "n/a"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Executive Summary — {profile_name}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; line-height: 1.5; color: #1e293b; }}
    h1 {{ font-size: 1.5rem; }} h2 {{ font-size: 1.1rem; margin-top: 1.5rem; }}
    .kpi-red {{ color: #b91c1c; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>Executive Summary — {profile_name}</h1>
  <p><em>Run date: {run_date}</em></p>
  <h2>Borough activity</h2>
  <ul>{boro_html}</ul>
  <h2>Budget CPI</h2>
  <p>Cost Performance Index: <strong>{cpi}</strong></p>
  <h2 class="kpi-red">Red KPIs</h2>
  <ul>{kpi_html}</ul>
</body>
</html>"""
    return md, html
