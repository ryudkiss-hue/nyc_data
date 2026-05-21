"""First-run onboarding tour (keyboard-accessible)."""

from __future__ import annotations

import dash_bootstrap_components as dbc
from dash import html

ONBOARDING_STEPS = [
    ("Welcome", "This dashboard runs your weekly Analyst Pack: prioritize repairs, review conflicts, and publish results."),
    ("Setup", "Run the install wizard once, then edit config/analyst_profile.yaml for your Excel or SQL paths."),
    ("Run", "Click Run Analyst Pack on Home — or use Load demo data to explore without production files."),
    ("Review", "Use Review to mark conflicts resolved and construction items approved before publishing."),
    ("Publish", "Publish sends the pack to folders, email, Teams, or BI staging per config/publish_profile.yaml."),
]


def onboarding_modal(modal_id: str = "onboarding-modal") -> dbc.Modal:
    steps = [
        html.Li([html.Strong(title), html.Span(f" — {body}")], className="mb-2")
        for title, body in ONBOARDING_STEPS
    ]
    return dbc.Modal(
        [
            dbc.ModalHeader(dbc.ModalTitle("Quick tour")),
            dbc.ModalBody(
                [
                    html.P("Five steps to your weekly workflow:", className="mb-3"),
                    html.Ol(steps, **{"aria-label": "Onboarding steps"}),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Got it",
                        id="onboarding-dismiss",
                        className="nyc-btn-primary",
                        title="Dismiss onboarding tour",
                    ),
                ]
            ),
        ],
        id=modal_id,
        is_open=False,
        centered=True,
        backdrop="static",
        keyboard=True,
    )
