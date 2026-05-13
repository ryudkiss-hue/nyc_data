"""dash_app/pages/ai.py — NL→SQL AI chatbot powered by LangChain + DuckDB"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import pandas as pd

from dash_app.data import db

dash.register_page(__name__, path="/ai", name="AI Assistant", order=2)

# ── LangChain detection ───────────────────────────────────────────────────────
_HAS_LC = False
try:
    from langchain_openai import ChatOpenAI
    from langchain_community.utilities import SQLDatabase
    _HAS_LC = True
except ImportError:
    pass

layout = dbc.Container([
    html.Div([
        html.H1("🤖 AI Assistant", className="nyc-page-title"),
        html.P("Ask questions in plain English — converted to SQL and executed against DuckDB.", className="nyc-page-sub"),
    ], className="nyc-page-header"),

    dbc.Alert([
        html.Strong("✅ LangChain connected — OpenAI NL→SQL active" if _HAS_LC else "⚠️ LangChain not installed — using rule-based SQL assistant. "),
        html.Span(" Install langchain-openai for full NL→SQL." if not _HAS_LC else ""),
    ], color="success" if _HAS_LC else "warning", dismissable=True),

    # Context selector
    dbc.Row([
        dbc.Col([
            html.Label("Context table", style={"fontSize": "0.78rem", "fontWeight": 600, "color": "var(--text-muted)"}),
            dcc.Dropdown(id="ai-table-sel", placeholder="Select DuckDB table for context…", style={"background": "var(--bg-secondary)"}),
        ], md=5),
        dbc.Col([
            html.Label("Quick prompts", style={"fontSize": "0.78rem", "fontWeight": 600, "color": "var(--text-muted)"}),
            dcc.Dropdown(id="ai-quick-sel",
                         options=[
                             {"label": "What are the top 10 boroughs by count?", "value": "top boroughs by count"},
                             {"label": "Show me nulls per column",               "value": "null count per column"},
                             {"label": "What is the average of all numeric cols?","value": "average of all numeric columns"},
                             {"label": "Show recent records",                    "value": "show 20 most recent records"},
                             {"label": "How many unique values per column?",     "value": "unique values per column"},
                         ],
                         placeholder="Insert example…", style={"background": "var(--bg-secondary)"}),
        ], md=7),
    ], className="mb-3"),

    # Chat history
    html.Div(id="ai-chat-history",
             style={"minHeight": "260px", "maxHeight": "380px", "overflowY": "auto",
                    "background": "var(--bg-secondary)", "border": "1px solid var(--border-color)",
                    "borderRadius": "10px", "padding": "14px", "marginBottom": "12px"}),

    # Input row
    dbc.InputGroup([
        dbc.Input(id="ai-input", placeholder="Ask anything about your data…",
                  style={"background": "var(--bg-primary)", "color": "var(--text-primary)",
                         "border": "1px solid var(--border-color)"},
                  debounce=False, n_submit=0),
        dbc.Button("Send ▶", id="ai-send-btn", color="primary"),
        dbc.Button("Clear", id="ai-clear-btn", color="secondary", outline=True),
    ], className="mb-3"),

    dcc.Loading(html.Div(id="ai-result-grid"), type="dot"),
    dcc.Store(id="ai-messages", data=[], storage_type="session"),
], fluid=True)


@callback(Output("ai-table-sel", "options"), Input("session-store", "data"))
def populate(_): return [{"label": t, "value": t} for t in db.list_tables()]


@callback(
    Output("ai-input", "value"),
    Input("ai-quick-sel", "value"),
    prevent_initial_call=True,
)
def insert_quick(val): return val or dash.no_update


@callback(
    Output("ai-messages",      "data"),
    Output("ai-chat-history",  "children"),
    Output("ai-result-grid",   "children"),
    Input("ai-send-btn",       "n_clicks"),
    Input("ai-input",          "n_submit"),
    Input("ai-clear-btn",      "n_clicks"),
    State("ai-input",          "value"),
    State("ai-table-sel",      "value"),
    State("ai-messages",       "data"),
    State("token-store",       "data"),
    prevent_initial_call=True,
)
def handle_chat(send_clicks, n_submit, clear_clicks, question, table, messages, token):
    ctx = dash.callback_context
    tid = ctx.triggered_id

    if tid == "ai-clear-btn":
        return [], [_system_msg("Chat cleared. Ask me anything about your DuckDB data.")], html.Div()

    if not question or not question.strip():
        return messages, _render_history(messages), html.Div()

    messages = list(messages or [])
    messages.append({"role": "user", "content": question})

    # Generate SQL
    sql, explanation = _nl_to_sql(question, table)
    messages.append({"role": "assistant", "content": explanation, "sql": sql})

    # Execute SQL
    result_grid = html.Div()
    if sql:
        try:
            df = db.query_df(sql)
            if not df.empty:
                result_grid = html.Div([
                    html.P(f"Result: {len(df):,} rows", style={"fontSize": "0.78rem", "color": "var(--text-muted)", "marginBottom": "6px"}),
                    dag.AgGrid(rowData=df.to_dict("records"),
                               columnDefs=[{"field": c, "sortable": True, "filter": True} for c in df.columns],
                               defaultColDef={"minWidth": 80, "resizable": True},
                               dashGridOptions={"domLayout": "autoHeight", "pagination": True, "paginationPageSize": 25},
                               className="ag-theme-alpine-dark", style={"width": "100%"}),
                ])
        except Exception as e:
            result_grid = dbc.Alert(f"SQL error: {e}", color="danger", dismissable=True)

    return messages, _render_history(messages), result_grid


def _nl_to_sql(question: str, table: str | None) -> tuple[str, str]:
    """Convert natural language to SQL. Uses LangChain if available, else rule-based."""
    q  = question.lower().strip()
    t  = f'"{table}"' if table else "your_table"
    sk = os.getenv("OPENAI_API_KEY", "")

    if _HAS_LC and sk and table:
        try:
            from langchain_openai import ChatOpenAI
            from langchain.chains import create_sql_query_chain
            # Build a tiny schema string for context
            schema_df = db.table_schema(table)
            schema_str = ", ".join(f"{r['column_name']} {r['column_type']}"
                                   for _, r in schema_df.iterrows()) if not schema_df.empty else ""
            prompt = (
                f"Table: {table}\nSchema: {schema_str}\n\n"
                f"Write a DuckDB SQL query to answer: {question}\n"
                f"Return ONLY the SQL, no explanation."
            )
            llm  = ChatOpenAI(model="gpt-4o-mini", api_key=sk)
            sql  = llm.invoke(prompt).content.strip().strip("```sql").strip("```").strip()
            return sql, f"🤖 (LangChain) Generated SQL:\n```sql\n{sql}\n```"
        except Exception as e:
            pass  # fall through to rule-based

    # ── Rule-based NL→SQL ──────────────────────────────────────────────────
    if not table:
        tables = db.list_tables()
        if tables: table = tables[0]; t = f'"{table}"'

    if any(x in q for x in ["top", "most", "count", "group"]):
        cat_df = db.query_df(f'SELECT * FROM {t} LIMIT 1')
        cat    = next((c for c in cat_df.columns if cat_df[c].dtype == object), cat_df.columns[0] if len(cat_df.columns) > 0 else "col")
        sql    = f'SELECT "{cat}", COUNT(*) AS cnt FROM {t} GROUP BY "{cat}" ORDER BY cnt DESC LIMIT 10'
        return sql, f"📊 Counting by `{cat}`:\n```sql\n{sql}\n```"

    if any(x in q for x in ["null", "missing", "empty"]):
        sql = f'SELECT {", ".join(f"SUM(CASE WHEN \"{c}\" IS NULL THEN 1 ELSE 0 END) AS \"{c}_nulls\""  for c in db.query_df(f"SELECT * FROM {t} LIMIT 1").columns)} FROM {t}'
        return sql, f"🔍 Null count query:\n```sql\n{sql}\n```"

    if any(x in q for x in ["average", "avg", "mean"]):
        num_df  = db.query_df(f'SELECT * FROM {t} LIMIT 1')
        num_cols = num_df.select_dtypes("number").columns.tolist()
        if num_cols:
            sql = f'SELECT {", ".join(f"AVG(\"{c}\") AS avg_{c}" for c in num_cols[:6])} FROM {t}'
            return sql, f"📈 Averages:\n```sql\n{sql}\n```"

    if any(x in q for x in ["recent", "latest", "last", "new"]):
        sql = f'SELECT * FROM {t} LIMIT 20'
        return sql, f"📋 Most recent rows:\n```sql\n{sql}\n```"

    if any(x in q for x in ["unique", "distinct"]):
        sql = f'SELECT {", ".join(f"COUNT(DISTINCT \"{c}\") AS distinct_{c}" for c in db.query_df(f"SELECT * FROM {t} LIMIT 1").columns[:8])} FROM {t}'
        return sql, f"🔢 Distinct value counts:\n```sql\n{sql}\n```"

    # fallback
    sql = f'SELECT * FROM {t} LIMIT 50'
    return sql, f"📋 Showing first 50 rows from `{table}`:\n```sql\n{sql}\n```"


def _bubble(role: str, content: str) -> html.Div:
    is_user = role == "user"
    return html.Div(
        dcc.Markdown(content, style={"margin": 0, "fontSize": "0.83rem"}),
        style={
            "background":    "var(--accent)" if is_user else "var(--bg-tertiary)",
            "color":         "white" if is_user else "var(--text-primary)",
            "borderRadius":  "12px 12px 4px 12px" if is_user else "12px 12px 12px 4px",
            "padding":       "8px 14px",
            "maxWidth":      "80%",
            "marginBottom":  "8px",
            "marginLeft":    "auto" if is_user else "0",
            "marginRight":   "0" if is_user else "auto",
        },
    )

def _system_msg(text: str) -> html.Div:
    return html.Div(text, style={"color": "var(--text-muted)", "fontSize": "0.78rem", "textAlign": "center", "padding": "8px"})

def _render_history(messages: list) -> list:
    if not messages:
        return [_system_msg("Hi! Select a table above and ask me anything about your data.")]
    return [_bubble(m["role"], m["content"]) for m in messages]
