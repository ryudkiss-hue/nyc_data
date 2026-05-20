"""Program KPI traffic lights — accessible status indicators with filters."""

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dash_app.components.explainers import default_kpi_description, kpi_metric_explainer
from dash_app.components.shell import empty_state, page_shell
from dash_app.data.analyst_pack import (
    latest_pack_dir,
    list_configured_roles,
    load_manifest,
    load_program_kpi,
    load_role_kpi_dashboard,
)
from socrata_toolkit.analyst.explore import filter_kpi_metrics

dash.register_page(__name__, path="/metrics", name="Metrics", order=4)

pack = latest_pack_dir()
manifest = load_manifest(pack)
_kpi = load_program_kpi(pack)
_role_kpi = load_role_kpi_dashboard(pack)
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
    mid = name.lower().replace(" ", "-")[:40]
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
                kpi_metric_explainer(name, default_kpi_description(name), mid),
            ],
        ),
        md=4,
        className="mb-3",
    )


role_compare_rows = []
for r in configured_roles:
    jid = f" jid-{r['jid']}" if r.get("jid") else ""
    role_compare_rows.append(
        html.Li(
            f"{r['display_name']} ({r['role_id']}){jid}",
            style={"fontSize": "0.82rem"},
        )
    )

_kpi_body = (
    [
        html.H2("Filter KPI categories", style={"fontSize": "1rem"}),
        dbc.Checklist(
            id="metrics-categories",
            options=[
                {"label": "All", "value": "all"},
                {"label": "Backlog", "value": "backlog"},
                {"label": "Completion", "value": "completion"},
                {"label": "Conflicts", "value": "conflict"},
                {"label": "ADA", "value": "ada"},
                {"label": "Budget", "value": "budget"},
                {"label": "Productivity", "value": "productivity"},
            ],
            value=["all"],
            inline=True,
            className="mb-3",
            inputClassName="me-1",
        ),
        dcc.Store(id="metrics-program-store", data=_kpi.get("metrics", [])),
        dcc.Store(id="metrics-role-store", data=_role_kpi.get("metrics", [])),
        html.H2("Standard program KPIs", style={"fontSize": "1.1rem"}),
        html.Div(id="metrics-program-row"),
        html.Hr(),
        html.H2("Role KPIs", style={"fontSize": "1.1rem"}),
        html.P(
            [
                "Active role from latest pack: ",
                html.Strong(_role_kpi.get("display_name") or "—"),
                f" — health {_role_kpi.get('overall_health', '').upper()}" if _role_kpi else "",
            ],
            className="nyc-page-sub",
        ),
        html.Div(id="metrics-role-row"),
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
    ]
    if _kpi.get("metrics") or _role_kpi.get("metrics")
    else [empty_state("No program KPIs in pack — run Analyst Pack with program_kpi enabled.", show_demo=False)]
)

layout = dbc.Container(
    [
        *page_shell(
            "Program Metrics",
            f"Program health: {_kpi.get('overall_health', 'unknown').upper()} — traffic-light KPIs with filters.",
            page_key="metrics",
            pack_dir=pack,
            children=_kpi_body,
        ),
    ],
    fluid=True,
)


@callback(
    Output("metrics-program-row", "children"),
    Input("metrics-program-store", "data"),
    Input("metrics-categories", "value"),
)
def filter_program_kpis(metrics, categories):
    metrics = metrics or []
    filtered = filter_kpi_metrics(metrics, categories=categories or ["all"])
    if not filtered:
        return dbc.Row([dbc.Col(html.P("No program KPI data matching filters."))])
    return dbc.Row([kpi_card(m) for m in filtered])


@callback(
    Output("metrics-role-row", "children"),
    Input("metrics-role-store", "data"),
    Input("metrics-categories", "value"),
)
def filter_role_kpis(metrics, categories):
    metrics = metrics or []
    filtered = filter_kpi_metrics(metrics, categories=categories or ["all"])
    if not filtered:
        return dbc.Row(
            [dbc.Col(html.P("Set role in analyst_profile.yaml and re-run the pack."))]
        )
    return dbc.Row([kpi_card(m, prefix="Role") for m in filtered])
