"""dash_app/pages/tasks.py — DuckDB-backed Kanban task board"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from datetime import date

import dash
import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, callback, dcc, html

from dash_app.data import db

dash.register_page(__name__, path="/tasks", name="Task Board", order=8)

# ── Ensure DuckDB table exists ────────────────────────────────────────────────
db.execute("""
CREATE TABLE IF NOT EXISTS _task_board (
    id          VARCHAR PRIMARY KEY,
    title       VARCHAR,
    description VARCHAR,
    status      VARCHAR DEFAULT 'Backlog',
    priority    VARCHAR DEFAULT 'Medium',
    category    VARCHAR DEFAULT 'General',
    created_at  DATE,
    due_date    DATE
)
""")

STATUSES = ["Backlog", "In Progress", "Review", "Done"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
CATEGORIES = [
    "General",
    "Infrastructure",
    "Data Quality",
    "Compliance",
    "Engineering",
    "Governance",
]

STATUS_COLORS = {
    "Backlog": "secondary",
    "In Progress": "primary",
    "Review": "warning",
    "Done": "success",
}

layout = dbc.Container(
    [
        html.Div(
            [
                html.H1("✅ Task Board", className="nyc-page-title"),
                html.P(
                    "Kanban board for NYC DOT infrastructure work items — persisted in DuckDB.",
                    className="nyc-page-sub",
                ),
            ],
            className="nyc-page-header",
        ),
        # Add task form
        dbc.Collapse(
            [
                dbc.Card(
                    dbc.CardBody(
                        [
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Title"),
                                            dbc.Input(
                                                id="task-title",
                                                placeholder="Task title…",
                                                size="sm",
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Priority"),
                                            dcc.Dropdown(
                                                id="task-priority",
                                                options=[
                                                    {"label": p, "value": p} for p in PRIORITIES
                                                ],
                                                value="Medium",
                                                clearable=False,
                                                style={"background": "var(--bg-secondary)"},
                                            ),
                                        ],
                                        md=2,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Category"),
                                            dcc.Dropdown(
                                                id="task-category",
                                                options=[
                                                    {"label": c, "value": c} for c in CATEGORIES
                                                ],
                                                value="General",
                                                clearable=False,
                                                style={"background": "var(--bg-secondary)"},
                                            ),
                                        ],
                                        md=2,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Due date"),
                                            dbc.Input(id="task-due", type="date", size="sm"),
                                        ],
                                        md=2,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Div(style={"height": "24px"}),
                                            dbc.Button(
                                                "Add Task",
                                                id="task-add-btn",
                                                color="success",
                                                size="sm",
                                            ),
                                        ],
                                        md=2,
                                    ),
                                ],
                                className="mb-2",
                            ),
                            dbc.Textarea(
                                id="task-desc",
                                placeholder="Description (optional)…",
                                rows=2,
                                size="sm",
                                style={
                                    "background": "var(--bg-secondary)",
                                    "color": "var(--text-primary)",
                                    "border": "1px solid var(--border-color)",
                                    "borderRadius": "6px",
                                },
                            ),
                        ]
                    ),
                    style={
                        "background": "var(--bg-secondary)",
                        "border": "1px solid var(--border-color)",
                    },
                ),
            ],
            id="task-form-collapse",
            is_open=False,
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "➕ New Task",
                        id="task-form-toggle",
                        color="primary",
                        outline=True,
                        size="sm",
                    ),
                    md=2,
                ),
                dbc.Col(
                    dbc.Button(
                        "🔄 Refresh",
                        id="task-refresh-btn",
                        color="secondary",
                        outline=True,
                        size="sm",
                    ),
                    md=2,
                ),
            ],
            className="mb-3 mt-2",
        ),
        dcc.Loading(html.Div(id="task-add-status"), type="dot"),
        html.Div(id="task-board-content"),
    ],
    fluid=True,
)


@callback(
    Output("task-form-collapse", "is_open"),
    Input("task-form-toggle", "n_clicks"),
    State("task-form-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_form(_, is_open):
    return not is_open


@callback(
    Output("task-add-status", "children"),
    Output("task-board-content", "children"),
    Input("task-add-btn", "n_clicks"),
    Input("task-refresh-btn", "n_clicks"),
    Input({"type": "task-move", "id": ALL}, "n_clicks"),
    State("task-title", "value"),
    State("task-desc", "value"),
    State("task-priority", "value"),
    State("task-category", "value"),
    State("task-due", "value"),
    prevent_initial_call=True,
)
def manage_tasks(add_clicks, refresh_clicks, move_clicks, title, desc, priority, category, due):
    ctx = dash.callback_context
    tid = ctx.triggered_id
    alert = html.Div()

    # Add task
    if tid == "task-add-btn" and title:
        db.execute(
            "INSERT OR REPLACE INTO _task_board VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                str(uuid.uuid4()),
                title,
                desc or "",
                "Backlog",
                priority or "Medium",
                category or "General",
                str(date.today()),
                due or None,
            ],
        )
        alert = dbc.Alert(
            f"✅ Task '{title}' added", color="success", dismissable=True, duration=4000
        )

    # Move task
    if isinstance(tid, dict) and tid.get("type") == "task-move":
        task_id, new_status = tid["id"].split("|")
        db.execute("UPDATE _task_board SET status = ? WHERE id = ?", [new_status, task_id])

    return alert, _render_board()


def _render_board() -> html.Div:
    df = db.query_df("SELECT * FROM _task_board ORDER BY created_at DESC")
    if df.empty:
        return dbc.Alert("No tasks yet — click '➕ New Task' to get started.", color="info")

    cols = []
    for status in STATUSES:
        tasks_in_col = df[df["status"] == status]
        cards = [_task_card(row) for _, row in tasks_in_col.iterrows()]
        badge = html.Span(
            str(len(tasks_in_col)), className=f"badge bg-{STATUS_COLORS[status]} ms-1"
        )
        col_children = [
            html.Div(
                [html.Span(status, style={"fontWeight": 700}), badge], className="nyc-kanban-header"
            )
        ]
        col_children += (
            cards
            if cards
            else [
                html.Div(
                    "Empty",
                    style={"color": "var(--text-muted)", "fontSize": "0.78rem", "padding": "8px"},
                )
            ]
        )
        cols.append(dbc.Col(html.Div(col_children, className="nyc-kanban-col"), md=3))

    return dbc.Row(cols)


def _task_card(row: pd.Series) -> html.Div:
    pri_color = {"Low": "blue", "Medium": "yellow", "High": "red", "Critical": "red"}.get(
        row.priority, "blue"
    )
    next_status = STATUSES[(STATUSES.index(row.status) + 1) % len(STATUSES)]
    prev_status = STATUSES[(STATUSES.index(row.status) - 1) % len(STATUSES)]
    return html.Div(
        [
            html.Div(
                [
                    html.Span(row.title, style={"fontWeight": 600, "fontSize": "0.83rem"}),
                    html.Span(row.priority, className=f"nyc-pill nyc-pill-{pri_color} ms-1"),
                ]
            ),
            html.Div(
                str(row.description or "")[:80],
                style={"fontSize": "0.74rem", "color": "var(--text-muted)", "margin": "4px 0"},
            ),
            html.Div(
                [
                    html.Span(
                        str(row.category),
                        style={"fontSize": "0.72rem", "color": "var(--text-muted)"},
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                "←",
                                id={"type": "task-move", "id": f"{row.id}|{prev_status}"},
                                size="sm",
                                color="link",
                                style={"padding": "0 4px", "fontSize": "0.75rem"},
                            ),
                            dbc.Button(
                                "→",
                                id={"type": "task-move", "id": f"{row.id}|{next_status}"},
                                size="sm",
                                color="link",
                                style={"padding": "0 4px", "fontSize": "0.75rem"},
                            ),
                        ],
                        style={"float": "right"},
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "center",
                },
            ),
        ],
        className="nyc-task-card",
    )
