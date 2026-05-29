"""Consistent page shell, context line, empty states, and error banners."""



from __future__ import annotations



from pathlib import Path

from typing import Any



import dash_bootstrap_components as dbc

from dash import dcc, html



from dash_app.data.analyst_pack import latest_pack_dir, load_manifest

from dash_app.data.pack_loader import manifest_summary, resolve_pack_dir



CLI_HINTS: dict[str, str] = {

    "home": "socrata analyst run --profile config/analyst_profile.yaml",

    "explore": "socrata analyst run (pack unchanged; copy weights from Explore snippet)",

    "construction": "socrata analyst run — refreshes construction_list.xlsx",

    "contracts": "socrata analyst run — contract_status.md + contract_analytics.json",

    "metrics": "socrata analyst run — program_kpi.json",

    "inquiries": "socrata analyst run — inquiry_drafts/*.md",

    "review": "socrata review list --pack-date YYYY-MM-DD",

    "data-trust": "socrata analyst run — data_dictionary.json",

    "publish": "socrata analyst publish --profile config/publish_profile.yaml --pack <dir>",

    "settings": "socrata doctor",

}





def active_pack_context(pack_dir: Path | str | None = None) -> tuple[str, str]:

    pack = resolve_pack_dir(pack_dir) if pack_dir else resolve_pack_dir()

    if not pack:

        return "", ""

    manifest = load_manifest(pack)

    run_date = manifest.get("run_date", pack.name)

    return str(pack), run_date





def page_context_line(page_label: str, pack_dir: Path | str | None = None) -> html.Div:

    _, run_date = active_pack_context(pack_dir)

    pack_part = f"Pack {run_date}" if run_date else "No pack loaded"

    return html.Div(

        className="nyc-page-context",

        children=[

            html.Span("You are viewing: ", className="nyc-context-prefix"),

            html.Strong(page_label),

            html.Span(" · ", **{"aria-hidden": "true"}),

            html.Span(pack_part, id="nyc-context-pack"),

        ],

        role="navigation",

        **{"aria-label": "Page context"},

    )





def cli_parity_hint(page_key: str) -> html.Div:

    cmd = CLI_HINTS.get(page_key, "")

    if not cmd:

        return html.Div()

    return html.Div(

        className="nyc-cli-hint",

        children=[

            html.Span("Same as: ", className="nyc-cli-label"),

            html.Code(cmd, className="nyc-cli-code"),

        ],

    )





def primary_action_bar(*children: Any) -> html.Div:

    return html.Div(className="nyc-action-bar", children=list(children))





def page_shell(

    title: str,

    subtitle: str,

    *,

    page_key: str = "",

    pack_dir: Path | str | None = None,

    actions: list | None = None,

    children: list | None = None,

) -> list:

    """Return layout children: header block + content grid wrapper."""

    label = title.replace("Analyst ", "").strip()

    header = html.Div(

        className="nyc-page-header-block",

        children=[

            page_context_line(label, pack_dir),

            html.H1(title, className="nyc-page-title"),

            html.P(subtitle, className="nyc-page-sub"),

            cli_parity_hint(page_key),

            primary_action_bar(*(actions or [])),

        ],

    )

    body = html.Div(className="nyc-content-grid", children=list(children or []))

    return [
        html.Div(className="nyc-page-shell", children=[header, body]),
    ]





def empty_state(

    message: str,

    *,

    show_run_pack: bool = True,

    show_demo: bool = True,

    run_pack_id: str = "empty-run-pack",

    demo_id: str = "empty-load-demo",

) -> html.Div:

    buttons = []

    if show_run_pack:

        buttons.append(

            html.Button(

                "Run Analyst Pack",

                id=run_pack_id,

                className="nyc-btn-primary me-2",

                **{"aria-label": "Run analyst pack"},

            )

        )

    if show_demo:

        buttons.append(

            html.Button(

                "Load demo data",

                id=demo_id,

                className="nyc-btn-secondary",

                **{"aria-label": "Load demo pack from fixtures"},

            )

        )

    return html.Div(

        className="nyc-empty-state",

        role="status",

        children=[

            html.I(className="bi bi-inbox", **{"aria-hidden": "true"}),

            html.P(message),

            html.Div(buttons, className="nyc-empty-actions") if buttons else None,

        ],

    )





def error_banner(message: str, *, fix_links: list[tuple[str, str]] | None = None) -> html.Div:

    links = []

    for label, href in fix_links or []:

        links.append(dcc.Link(label, href=href, className="nyc-error-fix-link"))

    return html.Div(

        className="nyc-error-banner",

        role="alert",

        children=[

            html.Strong("Something needs attention"),

            html.P(message),

            html.Div(links, className="nyc-error-fixes") if links else None,

        ],

    )





def pack_status_badge() -> html.Span:

    pack = latest_pack_dir()

    if not pack:

        return html.Span(

            [html.I(className="bi bi-circle me-1", **{"aria-hidden": "true"}), "No pack"],

            className="nyc-status-pill nyc-status-muted",

        )

    summary = manifest_summary(pack)

    health = summary.get("health", "ok")

    icon = "bi-check-circle-fill" if health == "ok" else "bi-exclamation-triangle-fill"

    label = "Pack OK" if health == "ok" else "Pack warnings"

    return html.Span(

        [html.I(className=f"bi {icon} me-1", **{"aria-hidden": "true"}), label],

        className=f"nyc-status-pill nyc-status-{health}",

        **{"aria-label": label},

    )


