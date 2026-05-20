"""Program KPI traffic lights — accessible status indicators."""

import json

import dash
import dash_bootstrap_components as dbc
from dash import html

from dash_app.data.analyst_pack import (
    latest_pack_dir,
    list_configured_roles,
    load_manifest,
    load_program_kpi,
    load_role_kpi_dashboard,
)

dash.register_page(__name__, path="/metrics", name="Metrics", order=3)

pack = latest_pack_dir()
manifest = load_manifest(pack)
kpi = load_program_kpi(pack)
role_kpi = load_role_kpi_dashboard(pack)
configured_roles = list_configured_roles()

STATUS_ICON = {
    "green": ("bi-check-circle-fill", "On track", "success"),
    "yellow": ("bi-exclamation-triangle-fill", "At risk", "warning"),
    "red": ("bi-x-octagon-fill", "Critical", "danger"),
}


def kpi_card(metric: dict, *, prefix: str = "") -> dbc.Col:
    status = metric.get("status", "unknown")
    icon_cls, label, color = STATUS_ICON.get(status, ("bi-dash-circle", status, "secondary"))
    name = metric.get("name", "")
    if prefix:
        name = f"{prefix}: {name}"
    return dbc.Col(
        html.Div(
            className="nyc-kpi-card",
            children=[
                html.H3(name, style={"fontSize": "1rem"}),
                html.P(
                    f"{metric.get('value')} / target {metric.get('target')}",
                    className="mb-0",
                ),
                html.Div(
                    className="nyc-kpi-status",
                    children=[
                        html.I(className=f"bi {icon_cls}", **{"aria-hidden": "true"}),
                        html.Span(label),
                        dbc.Badge(label, color=color, className="ms-2"),
                    ],
                    **{"aria-label": f"{name}: {label}"},
                ),
            ],
        ),
        md=4,
        className="mb-3",
    )


program_cards = [kpi_card(m) for m in kpi.get("metrics", [])]
role_cards = [kpi_card(m) for m in role_kpi.get("metrics", [])]
overall = kpi.get("overall_health", "unknown")
role_overall = role_kpi.get("overall_health", "unknown")
active_role = role_kpi.get("display_name") or "—"

role_compare_rows = []
for r in configured_roles:
    jid = f" jid-{r['jid']}" if r.get("jid") else ""
    role_compare_rows.append(
        html.Li(
            f"{r['display_name']} ({r['role_id']}){jid}",
            style={"fontSize": "0.82rem"},
        )
    )

layout = dbc.Container(
    [
        html.H1("Program Metrics", className="nyc-page-title"),
        html.P(
            f"Program health: {overall.upper()} — pack {manifest.get('run_date', '')}",
            className="nyc-page-sub",
        ),
        html.H2("Standard program KPIs", style={"fontSize": "1.1rem"}),
        dbc.Row(program_cards if program_cards else [dbc.Col(html.P("No program KPI data."))]),
        html.Hr(),
        html.H2("Role KPIs", style={"fontSize": "1.1rem"}),
        html.P(
            [
                "Active role from latest pack: ",
                html.Strong(active_role),
                f" — health {role_overall.upper()}" if role_kpi else "",
            ],
            className="nyc-page-sub",
        ),
        dbc.Row(role_cards if role_cards else [dbc.Col(html.P(
            "Set role: sw_project_analyst or project_analyst_sw in analyst_profile.yaml, then re-run the pack."
        ))]),
        html.Hr(),
        html.H2("Team roles (profiles)", style={"fontSize": "1.1rem"}),
        html.Ul(role_compare_rows)
        if role_compare_rows
        else html.P("No role profiles in config/role_profiles/."),
        html.P(
            "Compare Project Analyst - SW (jid-35715) vs SW Project Analyst (jid-42159) in Settings.",
            style={"fontSize": "0.8rem", "color": "var(--text-muted)"},
        ),
        html.Hr(),
        html.H2("Executive summary", style={"fontSize": "1.1rem"}),
        html.A(
            "Open executive_summary.html",
            href=f"file:///{pack / 'executive_summary.html'}"
            if pack and (pack / "executive_summary.html").exists()
            else "#",
            target="_blank",
        )
        if pack and (pack / "executive_summary.html").exists()
        else html.P("Run pack with executive_summary step enabled."),
        html.Br(),
        html.A(
            "Open role_task_status.md",
            href=f"file:///{pack / 'role_task_status.md'}"
            if pack and (pack / "role_task_status.md").exists()
            else "#",
            target="_blank",
        )
        if pack and (pack / "role_task_status.md").exists()
        else None,
    ],
    fluid=True,
)
