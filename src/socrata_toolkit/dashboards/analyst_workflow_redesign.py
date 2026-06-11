"""
Analyst Workflow — Brutalist Terminal Chic
High-density, no-nonsense utilitarian interface with neon accents.
Command palette aesthetic for power users, expandable query panels.
"""

import dash
from dash import dcc, html, callback, Input, Output, State
import plotly.graph_objects as go

# ============================================================================
# THEME & STYLING
# ============================================================================

DARK_BG = "#0a0e27"
PANEL_BG = "#0f1219"
ACCENT_CYAN = "#00d9ff"
ACCENT_LIME = "#39ff14"
ACCENT_MAGENTA = "#ff00ff"
TEXT_PRIMARY = "#e0e0e0"
TEXT_SECONDARY = "#808080"
BORDER = "#1a1f35"

ANALYST_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap');

* {{
    box-sizing: border-box;
}}

body {{
    background-color: {DARK_BG};
    color: {TEXT_PRIMARY};
    font-family: 'IBM Plex Sans', monospace;
    margin: 0;
    padding: 0;
    overflow-x: hidden;
}}

.analyst-container {{
    display: grid;
    grid-template-columns: 280px 1fr;
    min-height: 100vh;
    gap: 0;
}}

.sidebar {{
    background-color: {PANEL_BG};
    border-right: 2px solid {BORDER};
    padding: 1.5rem 0;
    overflow-y: auto;
}}

.sidebar-header {{
    padding: 0 1.5rem;
    margin-bottom: 2rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9rem;
    color: {ACCENT_CYAN};
    text-transform: uppercase;
    letter-spacing: 2px;
}}

.sidebar-section {{
    margin-bottom: 1.5rem;
    padding: 0 0.75rem;
}}

.sidebar-section-title {{
    font-size: 0.75rem;
    color: {TEXT_SECONDARY};
    text-transform: uppercase;
    padding: 0 0.75rem;
    margin-bottom: 0.75rem;
    letter-spacing: 1px;
    font-weight: 600;
}}

.sidebar-item {{
    padding: 0.75rem 1rem;
    margin: 0.25rem 0;
    border-left: 3px solid transparent;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    color: {TEXT_PRIMARY};
}}

.sidebar-item:hover {{
    background-color: rgba(0, 217, 255, 0.05);
    border-left-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}

.sidebar-item.active {{
    border-left-color: {ACCENT_LIME};
    color: {ACCENT_LIME};
    background-color: rgba(57, 255, 20, 0.05);
}}

.main-content {{
    display: flex;
    flex-direction: column;
}}

.analyst-header {{
    background-color: {PANEL_BG};
    border-bottom: 2px solid {BORDER};
    padding: 1rem 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}

.analyst-header h1 {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.2rem;
    margin: 0;
    color: {ACCENT_CYAN};
    letter-spacing: 1px;
}}

.command-palette {{
    background-color: rgba(0, 217, 255, 0.05);
    border: 1px solid {ACCENT_CYAN};
    border-radius: 4px;
    padding: 0.5rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    color: {TEXT_PRIMARY};
    font-size: 0.85rem;
    width: 300px;
}}

.command-palette::placeholder {{
    color: {TEXT_SECONDARY};
}}

.workspace {{
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
    gap: 1.5rem;
}}

.panel {{
    background-color: {PANEL_BG};
    border: 2px solid {BORDER};
    border-radius: 0;
    display: flex;
    flex-direction: column;
    transition: all 0.2s ease;
}}

.panel:hover {{
    border-color: {ACCENT_CYAN};
    box-shadow: 0 0 20px rgba(0, 217, 255, 0.1);
}}

.panel-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid {BORDER};
    cursor: pointer;
    user-select: none;
}}

.panel-header-title {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    color: {ACCENT_LIME};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0;
}}

.panel-status {{
    font-size: 0.75rem;
    color: {ACCENT_CYAN};
    font-weight: 600;
}}

.panel-content {{
    padding: 1rem;
    flex: 1;
    overflow-y: auto;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    line-height: 1.6;
}}

.query-editor {{
    background-color: {DARK_BG};
    border: 1px solid {BORDER};
    padding: 1rem;
    border-radius: 0;
    color: {ACCENT_LIME};
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    min-height: 120px;
    resize: vertical;
}}

.query-editor:focus {{
    outline: none;
    border-color: {ACCENT_CYAN};
    box-shadow: 0 0 10px rgba(0, 217, 255, 0.2);
}}

.button-group {{
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
}}

.btn {{
    padding: 0.5rem 1rem;
    background-color: transparent;
    border: 1px solid;
    border-radius: 0;
    cursor: pointer;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.2s ease;
    flex: 1;
}}

.btn-primary {{
    border-color: {ACCENT_LIME};
    color: {ACCENT_LIME};
}}

.btn-primary:hover {{
    background-color: rgba(57, 255, 20, 0.1);
    box-shadow: 0 0 10px rgba(57, 255, 20, 0.3);
}}

.btn-secondary {{
    border-color: {ACCENT_CYAN};
    color: {ACCENT_CYAN};
}}

.btn-secondary:hover {{
    background-color: rgba(0, 217, 255, 0.1);
    box-shadow: 0 0 10px rgba(0, 217, 255, 0.3);
}}

.output-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
}}

.output-table th {{
    background-color: rgba(0, 217, 255, 0.1);
    color: {ACCENT_CYAN};
    padding: 0.5rem;
    text-align: left;
    border-bottom: 1px solid {BORDER};
}}

.output-table td {{
    padding: 0.5rem;
    border-bottom: 1px solid {BORDER};
    color: {TEXT_PRIMARY};
}}

.output-table tr:hover {{
    background-color: rgba(57, 255, 20, 0.05);
}}

.status-badge {{
    display: inline-block;
    padding: 0.25rem 0.5rem;
    border-radius: 2px;
    font-size: 0.75rem;
    text-transform: uppercase;
}}

.status-badge.success {{
    background-color: rgba(57, 255, 20, 0.2);
    color: {ACCENT_LIME};
}}

.status-badge.loading {{
    background-color: rgba(0, 217, 255, 0.2);
    color: {ACCENT_CYAN};
    animation: pulse-status 1s infinite;
}}

@keyframes pulse-status {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.6; }}
}}

::-webkit-scrollbar {{
    width: 8px;
}}

::-webkit-scrollbar-track {{
    background-color: {DARK_BG};
}}

::-webkit-scrollbar-thumb {{
    background-color: {BORDER};
    border-radius: 4px;
}}

::-webkit-scrollbar-thumb:hover {{
    background-color: {ACCENT_CYAN};
}}
"""

def create_analyst_workflow():
    """Create analyst workflow layout."""

    return html.Div([
        dcc.Style(children=ANALYST_CSS),

        html.Div([
            # Sidebar
            html.Div([
                html.Div("◆ Analyst", className="sidebar-header"),

                html.Div([
                    html.Div("Queries", className="sidebar-section-title"),
                    html.Div("New Query", className="sidebar-item active"),
                    html.Div("Saved Queries", className="sidebar-item"),
                    html.Div("Query History", className="sidebar-item"),
                ], className="sidebar-section"),

                html.Div([
                    html.Div("Datasets", className="sidebar-section-title"),
                    html.Div("Inspections", className="sidebar-item"),
                    html.Div("Violations", className="sidebar-item"),
                    html.Div("Ramp Progress", className="sidebar-item"),
                    html.Div("Permits", className="sidebar-item"),
                ], className="sidebar-section"),

                html.Div([
                    html.Div("Reports", className="sidebar-section-title"),
                    html.Div("Generate Report", className="sidebar-item"),
                    html.Div("Export Data", className="sidebar-item"),
                    html.Div("Scheduled Jobs", className="sidebar-item"),
                ], className="sidebar-section"),

                html.Div([
                    html.Div("Analysis", className="sidebar-section-title"),
                    html.Div("Advanced Analytics", className="sidebar-item"),
                    html.Div("Forecasting", className="sidebar-item"),
                    html.Div("Quality Audit", className="sidebar-item"),
                ], className="sidebar-section"),

            ], className="sidebar"),

            # Main Content
            html.Div([
                # Header
                html.Div([
                    html.H1("analyst / new-query"),
                    html.Input(
                        type="text",
                        placeholder="⌘ search datasets, commands...",
                        className="command-palette"
                    )
                ], className="analyst-header"),

                # Workspace
                html.Div([
                    # Query Panel
                    html.Div([
                        html.Div([
                            html.H3("QUERY EDITOR", className="panel-header-title"),
                            html.Span("READY", className="panel-status")
                        ], className="panel-header"),
                        html.Div([
                            html.Textarea(
                                placeholder="SELECT * FROM inspections WHERE created_date > '2026-06-01'",
                                className="query-editor",
                                id="query-input"
                            ),
                            html.Div([
                                html.Button("▶ Execute", className="btn btn-primary", id="execute-btn"),
                                html.Button("○ Save", className="btn btn-secondary"),
                            ], className="button-group")
                        ], className="panel-content")
                    ], className="panel"),

                    # Results Panel
                    html.Div([
                        html.Div([
                            html.H3("RESULTS", className="panel-header-title"),
                            html.Span("1,247 rows", className="panel-status")
                        ], className="panel-header"),
                        html.Div([
                            html.Table([
                                html.Thead(html.Tr([
                                    html.Th("id"),
                                    html.Th("borough"),
                                    html.Th("created_date"),
                                    html.Th("status"),
                                ])),
                                html.Tbody([
                                    html.Tr([html.Td(f"SIM-{1000+i}"), html.Td("Manhattan"),
                                           html.Td("2026-06-10"), html.Td(
                                               html.Span("COMPLETE", className="status-badge success")
                                           )])
                                    for i in range(5)
                                ])
                            ], className="output-table")
                        ], className="panel-content")
                    ], className="panel"),

                    # Statistics Panel
                    html.Div([
                        html.Div([
                            html.H3("STATISTICS", className="panel-header-title"),
                            html.Span("ANALYZED", className="panel-status")
                        ], className="panel-header"),
                        html.Div([
                            html.Div([
                                html.Div("Rows Returned", style={"color": TEXT_SECONDARY, "fontSize": "0.8rem"}),
                                html.Div("1,247", style={"fontSize": "1.5rem", "color": ACCENT_LIME, "fontWeight": "600"})
                            ], style={"marginBottom": "1rem"}),
                            html.Div([
                                html.Div("Query Time", style={"color": TEXT_SECONDARY, "fontSize": "0.8rem"}),
                                html.Div("234 ms", style={"fontSize": "1.5rem", "color": ACCENT_CYAN, "fontWeight": "600"})
                            ], style={"marginBottom": "1rem"}),
                            html.Div([
                                html.Div("Data Size", style={"color": TEXT_SECONDARY, "fontSize": "0.8rem"}),
                                html.Div("2.4 MB", style={"fontSize": "1.5rem", "color": ACCENT_MAGENTA, "fontWeight": "600"})
                            ]),
                        ], className="panel-content")
                    ], className="panel"),

                    # Export Panel
                    html.Div([
                        html.Div([
                            html.H3("EXPORT", className="panel-header-title"),
                            html.Span("READY", className="panel-status")
                        ], className="panel-header"),
                        html.Div([
                            html.Div("Export Format:", style={"marginBottom": "0.75rem", "fontSize": "0.85rem"}),
                            html.Div([
                                html.Button("CSV", className="btn btn-secondary", style={"marginBottom": "0.5rem"}),
                                html.Button("XLSX", className="btn btn-secondary", style={"marginBottom": "0.5rem"}),
                                html.Button("PPTX", className="btn btn-secondary", style={"marginBottom": "0.5rem"}),
                                html.Button("JSON", className="btn btn-secondary"),
                            ], className="button-group", style={"flexDirection": "column"}),
                        ], className="panel-content")
                    ], className="panel"),

                ], className="workspace"),
            ], className="main-content"),
        ], className="analyst-container"),
    ], style={"margin": 0, "padding": 0})

if __name__ == "__main__":
    app = dash.Dash(__name__)
    app.layout = create_analyst_workflow()
    app.run_server(debug=True, port=8052)
