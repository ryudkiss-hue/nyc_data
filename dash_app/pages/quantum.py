"""dash_app/pages/quantum.py — Quantum-inspired optimization (classical simulation)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd
import numpy as np
import math
from dash_app.data import db

dash.register_page(__name__, path="/quantum", name="Quantum", order=3)

layout = dbc.Container([
    html.Div([html.H1("⚡ Quantum Optimizer", className="nyc-page-title"),
              html.P("Classical simulation of quantum-inspired algorithms: Grover search, TSP route, crew assignment.", className="nyc-page-sub")], className="nyc-page-header"),
    dbc.Tabs([dbc.Tab(label="🔍 Grover Search", tab_id="grover"), dbc.Tab(label="🗺️ Route", tab_id="route"), dbc.Tab(label="👥 Crew", tab_id="crew")],
             id="q-tabs", active_tab="grover", className="nyc-tabs mb-3"),
    html.Div(id="q-content"),
], fluid=True)

@callback(Output("q-content", "children"), Input("q-tabs", "active_tab"), Input("session-store", "data"))
def render(tab, _):
    tables = [{"label": t, "value": t} for t in db.list_tables()]
    if tab == "grover":
        return html.Div([
            dbc.Row([
                dbc.Col([html.Label("Table"), dcc.Dropdown(id="qg-table", options=tables, style={"background":"var(--bg-secondary)"})], md=4),
                dbc.Col([html.Label("Column"), dcc.Dropdown(id="qg-col", style={"background":"var(--bg-secondary)"})], md=3),
                dbc.Col([html.Label("Value"), dbc.Input(id="qg-val", size="sm")], md=3),
                dbc.Col([html.Div(style={"height":"22px"}), dbc.Button("Search", id="qg-btn", color="primary", size="sm")], md=2),
            ], className="mb-3"),
            dcc.Loading(html.Div(id="qg-result"), type="dot"),
        ])
    if tab == "route":
        return html.Div([
            dbc.Row([
                dbc.Col([html.Label("Table"), dcc.Dropdown(id="qr-table", options=tables, style={"background":"var(--bg-secondary)"})], md=3),
                dbc.Col([html.Label("Lat"), dcc.Dropdown(id="qr-lat", style={"background":"var(--bg-secondary)"})], md=3),
                dbc.Col([html.Label("Lon"), dcc.Dropdown(id="qr-lon", style={"background":"var(--bg-secondary)"})], md=3),
                dbc.Col([html.Label("Stops"), dbc.Input(id="qr-stops", type="number", value=20, size="sm")], md=1),
                dbc.Col([html.Div(style={"height":"22px"}), dbc.Button("Optimize", id="qr-btn", color="success", size="sm")], md=2),
            ], className="mb-3"),
            dcc.Loading(html.Div(id="qr-result"), type="dot"),
        ])
    return html.Div([
        dbc.Row([
            dbc.Col([html.Label("Crew"), dbc.Input(id="qc-crew", type="number", value=5, size="sm")], md=3),
            dbc.Col([html.Label("Tasks"), dbc.Input(id="qc-tasks", type="number", value=10, size="sm")], md=3),
            dbc.Col([html.Label("Seed"), dbc.Input(id="qc-seed", type="number", value=42, size="sm")], md=2),
            dbc.Col([html.Div(style={"height":"22px"}), dbc.Button("Assign", id="qc-btn", color="warning", size="sm")], md=2),
        ], className="mb-3"),
        dcc.Loading(html.Div(id="qc-result"), type="dot"),
    ])

@callback(Output("qg-col","options"), Input("qg-table","value"), prevent_initial_call=True)
def grover_cols(t):
    if not t: return []
    return [{"label": c, "value": c} for c in db.query_df(f'SELECT * FROM "{t}" LIMIT 1').columns]

@callback(Output("qg-result","children"), Input("qg-btn","n_clicks"),
          State("qg-table","value"), State("qg-col","value"), State("qg-val","value"), State("theme-store","data"), prevent_initial_call=True)
def grover(_, table, col, val, theme):
    if not all([table, col, val]): return dbc.Alert("Fill all fields.", color="warning")
    tmpl = {"dark":"plotly_dark","light":"simple_white","sepia":"ggplot2"}.get(theme or "dark","plotly_dark")
    df   = db.query_df(f'SELECT * FROM "{table}"')
    n    = len(df); hits = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]; k = max(len(hits),1)
    iters = max(1, int(math.pi/4 * math.sqrt(n/k)))
    theta = math.asin(math.sqrt(k/n)) if n > 0 else 0
    steps = list(range(1, iters+1)); probs = [math.sin((2*i-1)*theta)**2 for i in steps]
    fig = px.line(x=steps, y=probs, template=tmpl, title="Grover Amplitude Amplification",
                  labels={"x":"Iteration","y":"P(marked)"}, height=280, markers=True)
    fig.update_layout(margin=dict(l=0,r=0,t=36,b=0), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return html.Div([
        dbc.Row([
            dbc.Col(html.Div([html.Div(str(n),      className="nyc-metric-value"), html.Div("Search Space", className="nyc-metric-label")], className="nyc-metric"), md=3),
            dbc.Col(html.Div([html.Div(str(len(hits)),className="nyc-metric-value"), html.Div("Matches",    className="nyc-metric-label")], className="nyc-metric"), md=3),
            dbc.Col(html.Div([html.Div(str(iters),  className="nyc-metric-value"), html.Div("Iterations",  className="nyc-metric-label")], className="nyc-metric"), md=3),
        ], className="mb-3"),
        dcc.Graph(figure=fig, config={"displayModeBar": False}),
        dbc.Alert(f"No matches for '{val}'", color="info") if hits.empty else
        dcc.Markdown(hits.head(5).to_markdown(index=False), style={"fontSize":"0.78rem"}),
    ])

@callback(Output("qr-lat","options"), Output("qr-lon","options"), Input("qr-table","value"), prevent_initial_call=True)
def route_cols(t):
    if not t: return [], []
    opts = [{"label": c, "value": c} for c in db.query_df(f'SELECT * FROM "{t}" LIMIT 1').columns]
    return opts, opts

@callback(Output("qr-result","children"), Input("qr-btn","n_clicks"),
          State("qr-table","value"), State("qr-lat","value"), State("qr-lon","value"), State("qr-stops","value"), State("theme-store","data"), prevent_initial_call=True)
def route(_, table, lat, lon, stops, theme):
    if not all([table, lat, lon]): return dbc.Alert("Fill all fields.", color="warning")
    mstyle = {"dark":"carto-darkmatter","light":"carto-positron","sepia":"stamen-terrain"}.get(theme or "dark","carto-darkmatter")
    df = db.query_df(f'SELECT * FROM "{table}" LIMIT {int(stops or 20)}')
    df[lat] = pd.to_numeric(df[lat], errors="coerce"); df[lon] = pd.to_numeric(df[lon], errors="coerce")
    df = df.dropna(subset=[lat, lon]).head(int(stops or 20))
    if len(df) < 2: return dbc.Alert("Need ≥2 locations.", color="warning")
    coords = df[[lat,lon]].values; visited = [0]; unvisited = list(range(1, len(coords)))
    while unvisited:
        last = visited[-1]; dists = [math.dist(coords[last], coords[u]) for u in unvisited]
        nxt  = unvisited[dists.index(min(dists))]; visited.append(nxt); unvisited.remove(nxt)
    route = df.iloc[visited].copy(); route["stop"] = range(len(route))
    total = sum(math.dist(coords[visited[i]], coords[visited[i+1]])*111 for i in range(len(visited)-1))
    fig = px.line_mapbox(route, lat=lat, lon=lon, mapbox_style=mstyle, zoom=10,
                         title=f"Optimized Route — {len(route)} stops, ~{total:.1f} km", text="stop", height=460)
    fig.update_traces(mode="lines+markers+text", marker=dict(size=10))
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0))
    return dcc.Graph(figure=fig)

@callback(Output("qc-result","children"), Input("qc-btn","n_clicks"),
          State("qc-crew","value"), State("qc-tasks","value"), State("qc-seed","value"), State("theme-store","data"), prevent_initial_call=True)
def crew(_, n_c, n_t, seed, theme):
    tmpl = {"dark":"plotly_dark","light":"simple_white","sepia":"ggplot2"}.get(theme or "dark","plotly_dark")
    rng  = np.random.default_rng(int(seed or 42)); n_c = int(n_c or 5); n_t = int(n_t or 10)
    cost = rng.integers(1, 100, (n_c, n_t))
    pairs = sorted([(cost[c,t],c,t) for c in range(n_c) for t in range(n_t)])
    asgn  = {}; uc = set(); ut = set()
    for v,c,t in pairs:
        if c not in uc and t not in ut: asgn[c]=t; uc.add(c); ut.add(t)
    rows = [{"Crew":f"Crew {c+1}","Task":f"Task {t+1}","Cost":int(cost[c,t])} for c,t in asgn.items()]
    fig  = px.imshow(cost, template=tmpl, title="Cost Matrix", height=300, color_continuous_scale="RdYlGn_r")
    fig.update_layout(margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="rgba(0,0,0,0)")
    return html.Div([
        dcc.Graph(figure=fig, config={"displayModeBar":False}),
        dcc.Markdown(pd.DataFrame(rows).to_markdown(index=False), style={"fontSize":"0.8rem","marginTop":"12px"}),
    ])
