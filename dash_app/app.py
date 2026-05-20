"""
dash_app/app.py
───────────────
NYC DOT Sidewalk Toolkit — primary analyst GUI (Dash)

  python dash_app/app.py
  gunicorn "dash_app.app:server"
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
import dash_bootstrap_components as dbc
import plotly.io as pio
from dash import Dash, Input, Output, State, callback, dcc, html, no_update

from dash_app.components.onboarding import onboarding_modal
from dash_app.data.pack_loader import manifest_summary, resolve_pack_dir
from dash_app.data.ui_prefs import get_ui_pref, load_ui_prefs, save_ui_prefs
from socrata_toolkit.core.profiles import active_profile_name, list_profiles

_DEBUG = os.getenv("NYC_DOT_DEBUG", "").lower() in ("1", "true", "yes")
_ROOT = Path(__file__).resolve().parents[1]

_ui = load_ui_prefs()
_theme = get_ui_pref("theme", "dark")
_font_scale = get_ui_pref("font_scale", "normal")
_sidebar_collapsed = bool(get_ui_pref("sidebar_collapsed", False))

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True,
    title="NYC DOT Sidewalk Toolkit",
    update_title=None,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {
            "name": "description",
            "content": "NYC DOT Sidewalk Inspection & Management — Analyst Pack dashboard",
        },
    ],
)
server = app.server

pio.templates.default = "plotly_dark" if _theme == "dark" else "plotly_white"

NAV_SECTIONS = [
    {
        "title": "Work",
        "items": [
            {"label": "Home", "icon": "bi bi-house", "path": "/", "key": "home"},
            {"label": "Construction", "icon": "bi bi-cone-striped", "path": "/construction", "key": "construction"},
            {"label": "Contracts", "icon": "bi bi-file-earmark-text", "path": "/contracts", "key": "contracts"},
            {"label": "Metrics", "icon": "bi bi-speedometer2", "path": "/metrics", "key": "metrics"},
        ],
    },
    {
        "title": "Decide",
        "items": [
            {"label": "Review", "icon": "bi bi-check2-square", "path": "/review", "key": "review"},
            {"label": "Inquiries", "icon": "bi bi-chat-left-text", "path": "/inquiries", "key": "inquiries"},
        ],
    },
    {
        "title": "Share",
        "items": [
            {"label": "Publish", "icon": "bi bi-send", "path": "/publish", "key": "publish"},
        ],
    },
    {
        "title": "Advanced",
        "items": [
            {"label": "Explore", "icon": "bi bi-sliders", "path": "/explore", "key": "explore"},
            {"label": "Data Trust", "icon": "bi bi-shield-check", "path": "/data-trust", "key": "data-trust"},
            {"label": "Settings", "icon": "bi bi-gear", "path": "/settings", "key": "settings"},
        ],
    },
]

NAV = [item for section in NAV_SECTIONS for item in section["items"]]

_PAGE_PATHS = {
    "home": "/",
    "explore": "/explore",
    "construction": "/construction",
    "contracts": "/contracts",
    "metrics": "/metrics",
    "inquiries": "/inquiries",
    "review": "/review",
    "data-trust": "/data-trust",
    "publish": "/publish",
    "settings": "/settings",
}

if _DEBUG:
    NAV.extend(
        [
            {"label": "Map View", "icon": "bi bi-map", "path": "/geospatial", "key": "geospatial"},
            {"label": "Dev tools", "icon": "bi bi-grid", "path": "/devtools", "key": "devtools"},
        ]
    )


def build_sidebar(collapsed: bool = False) -> html.Div:
    nav_sections = []
    for section in NAV_SECTIONS:
        nav_items = []
        for item in section["items"]:
            content = [
                html.I(className=f"{item['icon']} nyc-nav-icon", **{"aria-hidden": "true"}),
                html.Span(item["label"], className="nyc-nav-label") if not collapsed else None,
            ]
            nav_items.append(
                dcc.Link(
                    content,
                    href=item["path"],
                    className="nyc-nav-link",
                    id={"type": "nav-link", "href": item["path"]},
                    title=item["label"],
                )
            )
        nav_sections.append(
            html.Div(
                [
                    (
                        html.Div(section["title"], className="nyc-nav-section-title")
                        if not collapsed
                        else None
                    ),
                    *nav_items,
                ],
                className="nyc-nav-section",
            )
        )

    return html.Div(
        id="nyc-sidebar",
        className="sidebar-collapsed" if collapsed else "",
        children=[
            html.Div(
                [
                    html.Div(
                        [html.I(className="bi bi-buildings-fill", **{"aria-hidden": "true"})],
                        className="nyc-logo-icon",
                    ),
                    (
                        html.Div(
                            [
                                html.Div("NYC DOT", className="nyc-logo-title"),
                                html.Div("Sidewalk Toolkit", className="nyc-logo-sub"),
                            ],
                            className="nyc-logo-text",
                        )
                        if not collapsed
                        else None
                    ),
                ],
                className="nyc-logo-section",
            ),
            html.Nav(nav_sections, className="nyc-nav-container", **{"aria-label": "Main navigation"}),
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className=(
                                    "bi bi-chevron-left" if not collapsed else "bi bi-chevron-right"
                                ),
                                **{"aria-hidden": "true"},
                            ),
                            html.Span("Collapse", className="nyc-nav-label") if not collapsed else None,
                        ],
                        id="sidebar-toggle",
                        className="nyc-collapse-btn",
                        title="Toggle sidebar",
                    )
                ],
                className="nyc-sidebar-footer",
            ),
        ],
    )


def build_header() -> html.Header:
    profiles = list_profiles(root=_ROOT) or ["default"]
    current = active_profile_name()
    if current not in profiles:
        profiles = sorted(set(profiles + [current]))

    return html.Header(
        id="nyc-header",
        children=[
            html.Div(
                [
                    html.Div(
                        "NYC DOT — Sidewalk Inspection & Management",
                        className="nyc-header-title",
                    ),
                    html.Div(id="nyc-header-pack-badge", className="nyc-header-badge-wrap"),
                ],
                className="nyc-header-left",
            ),
            html.Div(
                className="nyc-header-right",
                children=[
                    dcc.Dropdown(
                        id="header-profile",
                        options=[{"label": p, "value": p} for p in profiles],
                        value=current,
                        clearable=False,
                        className="nyc-profile-dropdown",
                    ),
                ],
            ),
        ],
    )


app.layout = html.Div(
    id="app-root",
    **{
        "data-theme": _theme,
        "data-font-scale": _font_scale,
    },
    children=[
        html.A("Skip to main content", href="#nyc-content", className="skip-link"),
        dcc.Store(id="sidebar-store", data=_sidebar_collapsed, storage_type="local"),
        dcc.Store(id="ui-prefs-store", data=_ui),
        dcc.Store(id="pack-route-store", data=""),
        dcc.Store(id="offline-banner-store", data=False),
        dcc.Store(id="onboarding-store", data=not bool(get_ui_pref("onboarding_complete", False))),
        onboarding_modal(),
        dcc.Location(id="url"),
        html.Div(id="offline-banner", className="nyc-offline-banner-wrap", role="status"),
        html.Div(
            id="global-toast",
            className="nyc-feedback-toast",
            role="status",
            **{"aria-live": "polite", "aria-atomic": "true"},
        ),
        html.Div(
            id="layout-container",
            style={"display": "flex"},
            children=[
                html.Div(id="sidebar-container", children=build_sidebar(_sidebar_collapsed)),
                html.Div(
                    id="main-container",
                    children=[
                        build_header(),
                        html.Main(dash.page_container, id="nyc-content", tabIndex=-1),
                    ],
                ),
            ],
        ),
    ],
)


@callback(
    Output("sidebar-container", "children"),
    Output("sidebar-store", "data"),
    Input("sidebar-toggle", "n_clicks"),
    State("sidebar-store", "data"),
    prevent_initial_call=True,
)
def toggle_sidebar(n, is_collapsed):
    collapsed = not bool(is_collapsed)
    prefs = load_ui_prefs()
    prefs["sidebar_collapsed"] = collapsed
    save_ui_prefs(prefs)
    return build_sidebar(collapsed), collapsed


@callback(
    Output("sidebar-container", "children", allow_duplicate=True),
    Input("sidebar-store", "data"),
    prevent_initial_call=True,
)
def init_sidebar(is_collapsed):
    return build_sidebar(bool(is_collapsed))


@callback(
    Output("app-root", "data-theme"),
    Output("app-root", "data-font-scale"),
    Input("ui-prefs-store", "data"),
)
def apply_theme_from_store(prefs):
    if not prefs:
        return no_update, no_update
    theme = prefs.get("theme", "dark")
    pio.templates.default = "plotly_dark" if theme == "dark" else "plotly_white"
    return theme, prefs.get("font_scale", "normal")


@callback(
    Output("nyc-header-pack-badge", "children"),
    Input("pack-route-store", "data"),
    Input("url", "pathname"),
)
def update_header_badge(pack_override, _pathname):
    pack = resolve_pack_dir(pack_override) if pack_override else resolve_pack_dir()
    if not pack:
        return html.Span(
            [html.I(className="bi bi-circle me-1", **{"aria-hidden": "true"}), "No pack"],
            className="nyc-status-pill nyc-status-muted",
            **{"aria-label": "No analyst pack loaded"},
        )
    summary = manifest_summary(pack)
    health = summary.get("health", "ok")
    icon = "bi-check-circle-fill" if health == "ok" else "bi-exclamation-triangle-fill"
    label = f"Pack {summary.get('run_date', '')}"
    if health != "ok":
        label += f" ({summary.get('warning_count', 0)} warnings)"
    return html.Span(
        [html.I(className=f"bi {icon} me-1", **{"aria-hidden": "true"}), label],
        className=f"nyc-status-pill nyc-status-{health}",
        **{"aria-label": label},
    )


@callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("pack-route-store", "data"),
    Input("url", "search"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def deep_link_routing(search, pathname):
    if not search:
        return no_update, no_update
    params = parse_qs(search.lstrip("?"))
    page = (params.get("page") or [""])[0].lower().replace("_", "-")
    pack = (params.get("pack") or [""])[0]
    pack_path = ""
    if pack:
        candidate = _ROOT / "outputs" / "analyst_pack" / pack
        if candidate.is_dir():
            pack_path = str(candidate)
    target = _PAGE_PATHS.get(page)
    if target and target != pathname:
        return target, pack_path or no_update
    if pack_path:
        return no_update, pack_path
    return no_update, no_update


@callback(
    Output("offline-banner", "children"),
    Input("offline-banner-store", "data"),
    Input("ui-prefs-store", "data"),
)
def show_offline_banner(force_offline, prefs):
    offline = bool(force_offline) or bool((prefs or {}).get("offline_mode"))
    pack = resolve_pack_dir()
    if pack:
        summary = manifest_summary(pack)
        if summary.get("health") == "warn" and not offline:
            return dbc.Alert(
                [
                    html.I(className="bi bi-wifi-off me-2", **{"aria-hidden": "true"}),
                    "Latest pack has source warnings — you can still view cached artifacts. ",
                    dcc.Link("Data Trust", href="/data-trust"),
                ],
                color="warning",
                className="mb-0 nyc-offline-alert",
                dismissable=True,
            )
    if offline:
        return dbc.Alert(
            [
                html.I(className="bi bi-wifi-off me-2", **{"aria-hidden": "true"}),
                "Offline mode — Socrata sources skipped; pack-only viewing and Explore on cached data.",
            ],
            color="info",
            className="mb-0 nyc-offline-alert",
        )
    return html.Div()


@callback(
    Output("ui-prefs-store", "data", allow_duplicate=True),
    Input("header-profile", "value"),
    prevent_initial_call=True,
)
@callback(
    Output("onboarding-modal", "is_open"),
    Input("onboarding-store", "data"),
    prevent_initial_call=False,
)
def toggle_onboarding(show: bool):
    return bool(show)


@callback(
    Output("onboarding-store", "data", allow_duplicate=True),
    Input("onboarding-dismiss", "n_clicks"),
    prevent_initial_call=True,
)
def dismiss_onboarding(_n):
    prefs = load_ui_prefs()
    prefs["onboarding_complete"] = True
    save_ui_prefs(prefs)
    return False


@callback(
    Output("onboarding-store", "data"),
    Output("pack-route-store", "data", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call="initial_duplicate",
)
def first_visit_bootstrap(_pathname):
    prefs = load_ui_prefs()
    if prefs.get("onboarding_complete"):
        return False, no_update
    pack = resolve_pack_dir()
    if not pack:
        try:
            from dash_app.data.demo_pack import ensure_demo_pack
            from dash_app.data.pack_loader import invalidate_pack_cache

            demo = ensure_demo_pack()
            if demo:
                invalidate_pack_cache()
                prefs["first_run_demo"] = True
                save_ui_prefs(prefs)
                return True, str(demo)
        except Exception:
            pass
    return not prefs.get("onboarding_complete", False), no_update


def switch_profile(profile_name):
    if profile_name:
        os.environ["TOOLKIT_PROFILE"] = str(profile_name)
    try:
        from dash_app.data.pack_loader import invalidate_pack_cache

        invalidate_pack_cache()
    except Exception:
        pass
    return load_ui_prefs()


if __name__ == "__main__":
    port = int(os.getenv("NYC_DOT_DASH_PORT", "8050"))
    host = os.getenv("NYC_DOT_DASH_HOST", "127.0.0.1")
    app.run(
        debug=_DEBUG,
        host=host,
        port=port,
        use_reloader=False,
    )
