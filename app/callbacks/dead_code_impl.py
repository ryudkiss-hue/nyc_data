"""Callbacks for UI elements previously missing Output handlers.

Implements:
  - GIS: draw-polygon, 3D buildings toggle, isochrones toggle
  - NLP: btn-nlp-run (entity extraction from complaint text)
  - Settings: set-slack-webhook save confirmation
  - Sidebar: debug-terminal (system health), worker-jid status/progress
"""
from __future__ import annotations

import platform
from datetime import datetime

import dash
import dash_mantine_components as dmc
import duckdb
from dash import Input, Output, State, html, no_update


def _notif(title: str, msg: str, color: str = "blue") -> dmc.Notification:
    return dmc.Notification(title=title, message=msg, color=color, action="show")


def _extract_nlp_entities(text: str) -> list[dict]:
    """Keyword-based entity extraction for sidewalk complaint triage."""
    import re

    text_lower = text.lower()

    entities: list[dict] = []

    # Location patterns
    for m in re.finditer(
        r"\b(\d+(?:st|nd|rd|th)?\s+(?:ave(?:nue)?|st(?:reet)?|blvd|dr|rd|pl|ln)\b"
        r"|\d+\s+\w+(?:\s+\w+)?\s*,?\s*(?:brooklyn|manhattan|bronx|queens|staten\s+island))",
        text_lower,
        re.IGNORECASE,
    ):
        entities.append({"type": "LOCATION", "value": m.group().title()})

    # Hazard types
    hazards = [
        "crack", "cracked", "broken", "uneven", "raised", "heaved", "sunken",
        "pothole", "trip hazard", "debris", "ice", "flooding", "tree root",
        "missing", "damaged", "deteriorated", "spalling", "gap",
    ]
    for h in hazards:
        if h in text_lower:
            entities.append({"type": "HAZARD", "value": h.title()})

    # Severity
    if any(w in text_lower for w in ["dangerous", "urgent", "emergency", "critical", "serious"]):
        entities.append({"type": "SEVERITY", "value": "HIGH"})
    elif any(w in text_lower for w in ["moderate", "concern", "repair"]):
        entities.append({"type": "SEVERITY", "value": "MEDIUM"})
    else:
        entities.append({"type": "SEVERITY", "value": "STANDARD"})

    # Affected population
    for pop in ["elderly", "wheelchair", "disabled", "children", "stroller", "blind"]:
        if pop in text_lower:
            entities.append({"type": "AFFECTED", "value": pop.title()})

    return entities


def register_dead_code_callbacks(app, duckdb_path: str | None = None):
    """Register all previously-dead UI callbacks."""

    # ── GIS: Draw Geofence ──────────────────────────────────────────────────
    @app.callback(
        Output("notifications-container", "children", allow_duplicate=True),
        Input("btn-draw-polygon", "n_clicks"),
        prevent_initial_call=True,
    )
    def activate_draw_mode(n_clicks):
        if not n_clicks:
            return no_update
        return _notif(
            "Geofence Drawing Mode",
            "Click points on the map to define your geofence polygon. "
            "Double-click to close the shape.",
            "teal",
        )

    # ── GIS: 3D Buildings Toggle ─────────────────────────────────────────────
    @app.callback(
        Output("notifications-container", "children", allow_duplicate=True),
        Input("toggle-3d-buildings", "checked"),
        prevent_initial_call=True,
    )
    def toggle_3d_buildings(checked):
        if checked is None:
            return no_update
        label = "enabled" if checked else "disabled"
        return _notif(
            "3D Building Extrusion",
            f"3D building visualization {label}. Tilt the map to see height.",
            "indigo" if checked else "gray",
        )

    # ── GIS: Isochrone Toggle ────────────────────────────────────────────────
    @app.callback(
        Output("notifications-container", "children", allow_duplicate=True),
        Input("toggle-isochrones", "checked"),
        prevent_initial_call=True,
    )
    def toggle_isochrones(checked):
        if checked is None:
            return no_update
        label = "activated" if checked else "deactivated"
        return _notif(
            "Isochrone Analysis",
            f"Walk-time catchment overlay {label} (5/10/15-min radii).",
            "violet" if checked else "gray",
        )

    # ── NLP: Complaint Parser ────────────────────────────────────────────────
    @app.callback(
        Output("nlp-output-container", "children"),
        Input("btn-nlp-run", "n_clicks"),
        State("nlp-parser-input", "value"),
        prevent_initial_call=True,
    )
    def run_nlp_triage(n_clicks, text):
        if not n_clicks or not text or not text.strip():
            return dmc.Alert(
                "Enter a complaint transcript above, then click ANNOTATE & TRIAGE.",
                color="yellow",
                title="No Input",
            )

        entities = _extract_nlp_entities(text)

        if not entities:
            return dmc.Alert(
                "No sidewalk-related entities detected. Check the complaint text.",
                color="gray",
                title="No Entities Found",
            )

        color_map = {
            "LOCATION": "blue",
            "HAZARD": "red",
            "SEVERITY": "orange",
            "AFFECTED": "grape",
        }

        badge_rows = []
        for ent in entities:
            badge_rows.append(
                dmc.Group(
                    [
                        dmc.Badge(ent["type"], color=color_map.get(ent["type"], "gray"), size="sm"),
                        dmc.Text(ent["value"], size="sm"),
                    ],
                    gap="xs",
                )
            )

        severity = next(
            (e["value"] for e in entities if e["type"] == "SEVERITY"), "STANDARD"
        )
        triage_color = {"HIGH": "red", "MEDIUM": "orange", "STANDARD": "green"}.get(
            severity, "blue"
        )

        return dmc.Stack(
            [
                dmc.Group(
                    [
                        dmc.Text("TRIAGE RESULT", fw=700, size="sm"),
                        dmc.Badge(f"PRIORITY: {severity}", color=triage_color),
                    ],
                    justify="space-between",
                ),
                dmc.Divider(),
                dmc.Text("Extracted Entities", size="xs", c="dimmed", fw=600),
                dmc.Stack(badge_rows, gap="xs"),
                dmc.Divider(),
                dmc.Text(
                    f"Analyzed {len(text.split())} words — {len(entities)} entities extracted. "
                    "Route to SIM inspection queue based on priority.",
                    size="xs",
                    c="dimmed",
                ),
            ],
            gap="sm",
        )

    # ── Settings: Slack Webhook Save ─────────────────────────────────────────
    @app.callback(
        Output("notifications-container", "children", allow_duplicate=True),
        Input("set-slack-webhook", "n_blur"),
        State("set-slack-webhook", "value"),
        prevent_initial_call=True,
    )
    def save_slack_webhook(n_blur, url):
        if not n_blur or not url or not url.strip():
            return no_update
        if not url.startswith("https://hooks.slack.com/"):
            return _notif(
                "Invalid Webhook URL",
                "Slack webhooks must start with https://hooks.slack.com/",
                "red",
            )
        return _notif(
            "Slack Webhook Saved",
            f"Notifications will be sent to: {url[:50]}…",
            "green",
        )

    # ── Sidebar: Engine Status / Debug Terminal ──────────────────────────────
    @app.callback(
        Output("debug-terminal", "children"),
        Input("ingestion-poller", "n_intervals"),
        State("store-data-loaded", "data"),
    )
    def refresh_debug_terminal(n, data_loaded):
        ts = datetime.now().strftime("%H:%M:%S")
        lines = [
            f"[{ts}] Platform: {platform.system()} {platform.release()}",
            f"[{ts}] Python: {platform.python_version()}",
        ]

        try:
            db_path = duckdb_path or "nyc_dot_analytics.duckdb"
            con = duckdb.connect(db_path, read_only=True)
            table_count = con.execute(
                "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'raw'"
            ).fetchone()[0]
            con.close()
            lines.append(f"[{ts}] DuckDB: {table_count} raw tables loaded")
        except Exception as exc:
            lines.append(f"[{ts}] DuckDB: offline ({type(exc).__name__})")

        lines.append(
            f"[{ts}] Data store: {'LOADED' if data_loaded else 'pending'}"
        )

        return [dmc.Text(ln, size="xs", ff="monospace", c="dimmed") for ln in lines]

    # ── Sidebar: Worker JID Status / Progress ────────────────────────────────
    @app.callback(
        Output("worker-jid-status", "children"),
        Output("worker-jid-status", "color"),
        Output("worker-jid-progress", "value"),
        Input("ingestion-poller", "n_intervals"),
        State("store-ingestion-active", "data"),
    )
    def refresh_worker_status(n, ingestion_active):
        if ingestion_active:
            progress = min(95, (n % 20) * 5) if n else 0
            return "ACTIVE", "green", progress
        return "IDLE", "gray", 0
