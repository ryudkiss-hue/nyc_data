"""Governance, lineage, and audit tab for Manhattan Mission Control."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

# Optional lineage imports
try:
    from socrata_toolkit.lineage.core import (  # type: ignore[import]
        DAG,
        NodeType,
        TransformationNode,
    )

    _HAS_LINEAGE = True
except ImportError:
    _HAS_LINEAGE = False
    DAG = None  # type: ignore[assignment,misc]
    NodeType = None  # type: ignore[assignment]
    TransformationNode = None  # type: ignore[assignment]

_CONFIG_PATH = Path(__file__).parents[2] / "config" / "datasets.yaml"
_INGEST_LOG_PATH = Path(__file__).parents[2] / "outputs" / "logs" / "ingest.jsonl"
_OPEN_DATA_BASE = "https://data.cityofnewyork.us/resource/"


# ── helpers ──────────────────────────────────────────────────────────────────


def _load_datasets_config() -> dict[str, Any]:
    """Load config/datasets.yaml; return empty dict on failure."""
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def _find_date_col(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        lc = col.lower()
        if "created_date" in lc or lc == "date":
            return col
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            return col
    return None


def _days_ago(df: pd.DataFrame, date_col: str) -> int | None:
    try:
        series = pd.to_datetime(df[date_col], errors="coerce")
        max_dt = series.max()
        if pd.isna(max_dt):
            return None
        delta = datetime.datetime.now() - max_dt.to_pydatetime().replace(tzinfo=None)
        return int(delta.days)
    except Exception:  # noqa: BLE001
        return None


def _record_audit(action: str, dataset: str = "", details: str = "") -> None:
    """Append an entry to st.session_state['audit_trail']."""
    if "audit_trail" not in st.session_state:
        st.session_state["audit_trail"] = []
    st.session_state["audit_trail"].append(
        {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": action,
            "dataset": dataset,
            "details": details,
        }
    )


# ── lineage graph ─────────────────────────────────────────────────────────────


def _build_lineage_figure(dataset_keys: list[str]) -> go.Figure:
    """Build a Plotly layered lineage graph."""
    # Node definitions: (label, layer, color)
    source_nodes = dataset_keys or ["inspection", "street_permits", "violations"]
    transform_nodes = ["QA Join", "Spatial Join", "Apex Hiring Model"]
    output_nodes = ["Analyst Pack", "Forecast", "Map Output"]

    node_colors = {
        "source": "#3B82F6",    # blue
        "transform": "#F59E0B",  # amber
        "output": "#10B981",    # emerald
    }

    nodes: list[dict[str, Any]] = []
    edges: list[tuple[int, int]] = []

    # Sources at x=0
    for i, label in enumerate(source_nodes):
        y = i - (len(source_nodes) - 1) / 2
        nodes.append({"label": label, "x": 0, "y": y, "color": node_colors["source"]})

    src_count = len(source_nodes)

    # Transforms at x=1
    for i, label in enumerate(transform_nodes):
        y = i - (len(transform_nodes) - 1) / 2
        nodes.append({"label": label, "x": 1, "y": y, "color": node_colors["transform"]})

    # Outputs at x=2
    for i, label in enumerate(output_nodes):
        y = i - (len(output_nodes) - 1) / 2
        nodes.append({"label": label, "x": 2, "y": y, "color": node_colors["output"]})

    # Edges: every source → every transform
    for s in range(src_count):
        for t in range(len(transform_nodes)):
            edges.append((s, src_count + t))

    # Edges: every transform → every output
    for t in range(len(transform_nodes)):
        for o in range(len(output_nodes)):
            edges.append((src_count + t, src_count + len(transform_nodes) + o))

    # Build edge traces
    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for src_idx, dst_idx in edges:
        edge_x += [nodes[src_idx]["x"], nodes[dst_idx]["x"], None]
        edge_y += [nodes[src_idx]["y"], nodes[dst_idx]["y"], None]

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line={"width": 1, "color": "#6B7280"},
        hoverinfo="none",
    )

    # Build node traces grouped by color
    node_traces = []
    for color_key, color_val in node_colors.items():
        xs = [n["x"] for n in nodes if n["color"] == color_val]
        ys = [n["y"] for n in nodes if n["color"] == color_val]
        labels = [n["label"] for n in nodes if n["color"] == color_val]
        node_traces.append(
            go.Scatter(
                x=xs,
                y=ys,
                mode="markers+text",
                marker={"size": 18, "color": color_val, "line": {"width": 1, "color": "#1F2937"}},
                text=labels,
                textposition="middle right",
                textfont={"size": 11, "color": "#F9FAFB"},
                name=color_key.title(),
                hoverinfo="text",
            )
        )

    fig = go.Figure(
        data=[edge_trace, *node_traces],
        layout=go.Layout(
            template="plotly_dark",
            showlegend=True,
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            margin={"l": 20, "r": 120, "t": 20, "b": 20},
            height=400,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


# ── main render ───────────────────────────────────────────────────────────────


def render_governance_tab(loaded_frames: dict[str, pd.DataFrame]) -> None:
    """Render the governance, lineage, and audit tab."""
    st.header("🏛️ Governance & Lineage")

    # Initialise audit trail if needed
    if "audit_trail" not in st.session_state:
        st.session_state["audit_trail"] = []

    config_data = _load_datasets_config()
    datasets_cfg: dict[str, Any] = config_data.get("datasets", {})

    # ── 1. Lineage DAG ────────────────────────────────────────────────────────
    st.subheader("Dataset Lineage DAG")
    with st.container(border=True):
        if _HAS_LINEAGE:
            st.caption("Lineage powered by socrata_toolkit.lineage")
        else:
            st.caption("Manual lineage graph (socrata_toolkit.lineage not available)")

        fig = _build_lineage_figure(list(loaded_frames.keys()))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── 2. Dataset registry table ─────────────────────────────────────────────
    st.subheader("Dataset Registry")
    if datasets_cfg:
        reg_rows: list[dict[str, Any]] = []
        for key, meta in datasets_cfg.items():
            fourfour = meta.get("fourfour", "")
            link = f"{_OPEN_DATA_BASE}{fourfour}" if fourfour else ""
            reg_rows.append(
                {
                    "Key": key,
                    "Label": meta.get("label", ""),
                    "Group": meta.get("group", ""),
                    "FourFour ID": fourfour,
                    "NYC Open Data": f'<a href="{link}" target="_blank">{fourfour}</a>' if link else "",
                }
            )
        reg_df = pd.DataFrame(reg_rows)
        # Show table without HTML column as st.dataframe, then hyperlinks via markdown
        st.dataframe(
            reg_df[["Key", "Label", "Group", "FourFour ID"]],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown("**Direct links to NYC Open Data:**")
        for row in reg_rows:
            if row["NYC Open Data"]:
                st.markdown(f"- **{row['Key']}**: {row['NYC Open Data']}", unsafe_allow_html=True)
    else:
        st.warning("Could not load config/datasets.yaml.")

    st.divider()

    # ── 3. Ingest audit log ───────────────────────────────────────────────────
    st.subheader("Ingest Audit Log")
    if _INGEST_LOG_PATH.exists():
        log_rows: list[dict[str, Any]] = []
        with _INGEST_LOG_PATH.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    log_rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if log_rows:
            log_df = pd.DataFrame(log_rows)
            # Normalise expected columns
            expected_cols = ["timestamp", "dataset_key", "rows_fetched", "duration_sec", "status"]
            for col in expected_cols:
                if col not in log_df.columns:
                    log_df[col] = None
            st.dataframe(
                log_df[expected_cols],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Ingest log file is empty.")
    else:
        st.info("No ingest events recorded yet. (outputs/logs/ingest.jsonl not found)")

    st.divider()

    # ── 4. Data freshness compliance ──────────────────────────────────────────
    st.subheader("Data Freshness Compliance (SLA: 7-day)")
    freshness_rows: list[dict[str, Any]] = []
    for key, df in loaded_frames.items():
        date_col = _find_date_col(df)
        if not date_col:
            continue
        days = _days_ago(df, date_col)
        if days is None:
            status = "⚪ Unknown"
        elif days <= 7:
            status = "🟢 Compliant"
        elif days <= 30:
            status = "🟡 Stale"
        else:
            status = "🔴 Overdue"
        freshness_rows.append(
            {
                "Dataset": key,
                "Last Updated": date_col,
                "Days Stale": days if days is not None else "—",
                "Status": status,
            }
        )

    if freshness_rows:
        st.dataframe(pd.DataFrame(freshness_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No datasets with detectable date columns are loaded.")

    st.divider()

    # ── 5. Session audit trail ────────────────────────────────────────────────
    st.subheader("Session Audit Trail")

    with st.container(border=True):
        trail: list[dict[str, Any]] = st.session_state.get("audit_trail", [])
        if not trail:
            st.caption("No audit events recorded this session.")
        else:
            trail_df = pd.DataFrame(trail[::-1])  # most recent first
            st.dataframe(trail_df, use_container_width=True, hide_index=True, height=250)

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🧪 Record test event", key="gov_test_event"):
                _record_audit(
                    action="manual_test",
                    dataset="—",
                    details="Audit trail test entry from Governance tab",
                )
                st.rerun()
        with col_b:
            if st.button("🗑️ Clear audit trail", key="gov_clear_trail"):
                st.session_state["audit_trail"] = []
                st.rerun()

    # Record that governance tab was viewed
    _record_audit(
        action="view_governance",
        dataset="",
        details=f"{len(loaded_frames)} dataset(s) loaded",
    )
