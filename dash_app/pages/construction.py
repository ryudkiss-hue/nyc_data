"""Construction list, week-over-week diff, and conflicts."""

import dash
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import html

from dash_app.data.analyst_pack import (
    latest_pack_dir,
    load_construction_diff,
    load_construction_list,
    load_manifest,
    load_pack_file,
)

dash.register_page(__name__, path="/construction", name="Construction", order=1)

pack = latest_pack_dir()
manifest = load_manifest(pack)
df = load_construction_list(pack)
diff_md = load_construction_diff(pack)

row_data = df.to_dict("records") if not df.empty else []
if "_wow_change" in df.columns:
    for row in row_data:
        if row.get("_wow_change") == "new":
            row["_badge"] = "NEW"

col_defs = [{"field": c} for c in df.columns] if not df.empty else []
if row_data and any(r.get("_wow_change") == "new" for r in row_data):
    col_defs.insert(0, {"field": "_wow_change", "headerName": "WoW", "width": 90})

layout = dbc.Container(
    [
        html.H1("Construction", className="nyc-page-title"),
        html.P(
            f"Pack: {manifest.get('run_date', 'none')} — {len(df)} items",
            className="nyc-page-sub",
        ),
        dag.AgGrid(
            id="construction-grid",
            rowData=row_data,
            columnDefs=col_defs,
            defaultColDef={"filter": True, "sortable": True, "resizable": True},
            style={"height": "420px"},
            className="ag-theme-alpine-dark",
            dashGridOptions={"domLayout": "normal"},
        ),
        html.H2("Week-over-week diff", style={"fontSize": "1.1rem", "marginTop": "1.5rem"}),
        html.Pre(
            diff_md or "No diff yet — run a second pack after the first to compare construction lists.",
            style={"whiteSpace": "pre-wrap", "maxHeight": "240px", "overflow": "auto"},
        ),
        html.H2("Conflicts summary", style={"fontSize": "1.1rem", "marginTop": "1.5rem"}),
        html.Pre(
            load_pack_file("conflicts_summary.md", pack) or "Run analyst pack with permits source.",
            style={"whiteSpace": "pre-wrap"},
        ),
    ],
    fluid=True,
)
