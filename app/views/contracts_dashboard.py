"""Contract Analytics & Budget Tracker for NYC DOT SIM Program."""

from __future__ import annotations

import io
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from app.data_loader import (
    DATE_CANDIDATES,
    demo_mode_enabled,
    fetch_dataset,
    pick_column,
)

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False


# ---------------------------------------------------------------------------
# Socrata data loaders
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86_400, show_spinner="Loading built/inspection data from Socrata…")
def _load_productivity_from_socrata(limit: int = 25_000) -> pd.DataFrame:
    """Load inspector productivity proxy from SMD Built + Inspection datasets."""
    frames = []
    for key in ("built", "ramp_progress", "inspection"):
        try:
            df = fetch_dataset(key, limit=limit // 3)
            if not df.empty:
                df["_source"] = key
                frames.append(df)
        except Exception:
            pass
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    date_col = pick_column(combined, DATE_CANDIDATES)
    if date_col:
        combined["date"] = pd.to_datetime(combined[date_col], errors="coerce")
    return combined


def _upload_or_note(label: str, key: str, note: str = "") -> pd.DataFrame | None:
    """File uploader widget; returns None if no file selected."""
    if note:
        st.caption(note)
    up = st.file_uploader(label, type=["csv", "xlsx"], key=key)
    if up is None:
        return None
    try:
        if up.name.endswith(".xlsx"):
            return pd.read_excel(up)
        return pd.read_csv(up)
    except Exception as exc:
        st.error(f"Could not parse {up.name}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _cpi(awarded: float, spent: float, pct: float) -> float:
    if pct <= 0:
        return 0.0
    earned = awarded * (pct / 100.0)
    return round(earned / spent, 3) if spent > 0 else 0.0


def _excel_multisheet(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    buf.seek(0)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _render_contract_progress(df: pd.DataFrame) -> None:
    st.subheader("Contract Progress Dashboard")

    today = pd.Timestamp.today()
    total = len(df)
    total_awarded = df["awarded_value"].sum() if "awarded_value" in df.columns else 0
    total_spent = df["spent_to_date"].sum() if "spent_to_date" in df.columns else 0
    avg_pct = df["percent_complete"].mean() if "percent_complete" in df.columns else 0

    behind = 0
    if {"planned_end", "percent_complete"}.issubset(df.columns):
        df = df.copy()
        df["planned_end"] = pd.to_datetime(df["planned_end"], errors="coerce")
        behind = int(((df["planned_end"] < today) & (df["percent_complete"] < 100)).sum())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Contracts", total)
    c2.metric("Awarded Value", f"${total_awarded:,.0f}")
    c3.metric("Spent to Date", f"${total_spent:,.0f}")
    c4.metric("Avg Completion", f"{avg_pct:.1f}%")
    c5.metric("Behind Schedule", behind, delta=f"+{behind}" if behind else None, delta_color="inverse")

    if not HAS_PLOTLY:
        st.dataframe(df, use_container_width=True)
        return

    if {"contract_id", "percent_complete", "status"}.issubset(df.columns):
        df_sorted = df.sort_values("percent_complete", ascending=True)
        color_map = {"Active": "#1f77b4", "Closed": "#2ca02c", "Pending": "#aec7e8"}
        fig = px.bar(
            df_sorted,
            x="percent_complete",
            y="contract_id",
            color="status",
            color_discrete_map=color_map,
            orientation="h",
            title="Completion % by Contract",
            labels={"percent_complete": "% Complete", "contract_id": "Contract"},
            height=max(400, len(df) * 22),
        )
        fig.add_vline(x=100, line_dash="dash", line_color="gray")
        fig.update_layout(xaxis_range=[0, 110])
        st.plotly_chart(fig, use_container_width=True)

    if behind > 0:
        st.warning(f"⚠️ {behind} contract(s) are past planned end date with less than 100% completion.")
        behind_df = df[
            (df["planned_end"] < today) & (df["percent_complete"] < 100)
        ][["contract_id", "contractor", "borough", "planned_end", "percent_complete", "status"]
          if all(c in df.columns for c in ["contractor", "borough"])
          else [c for c in ["contract_id", "planned_end", "percent_complete", "status"] if c in df.columns]
        ].sort_values("percent_complete")
        st.dataframe(behind_df, use_container_width=True, hide_index=True)

    with st.expander("Full Contract Table"):
        display_cols = [c for c in ["contract_id", "contractor", "borough", "awarded_value",
                                     "spent_to_date", "percent_complete", "status", "planned_end"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


def _render_budget_analysis(df: pd.DataFrame) -> None:
    st.subheader("Budget Analysis")

    if df.empty or not {"awarded_value", "spent_to_date", "percent_complete"}.issubset(df.columns):
        st.warning("Budget analysis requires awarded_value, spent_to_date, and percent_complete columns.")
        return

    df = df.copy()
    df["cpi"] = df.apply(
        lambda r: _cpi(r["awarded_value"], r["spent_to_date"], r["percent_complete"]), axis=1
    )
    df["budget_status"] = df["cpi"].apply(
        lambda c: "🔴 Over Budget" if c < 0.9 else ("🟡 Watch" if c < 0.97 else "🟢 On Track")
    )

    over = (df["cpi"] < 0.9).sum()
    watch = ((df["cpi"] >= 0.9) & (df["cpi"] < 0.97)).sum()
    on_track = (df["cpi"] >= 0.97).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("🔴 Over Budget (CPI < 0.9)", over, delta=f"+{over}" if over else None, delta_color="inverse")
    c2.metric("🟡 Watch (0.9–0.97)", watch)
    c3.metric("🟢 On Track (≥ 0.97)", on_track)

    if HAS_PLOTLY and "contract_id" in df.columns:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Awarded", x=df["contract_id"], y=df["awarded_value"], marker_color="#4C78A8"))
        fig.add_trace(go.Bar(name="Spent", x=df["contract_id"], y=df["spent_to_date"], marker_color="#F58518"))
        fig.update_layout(
            barmode="group",
            title="Awarded vs Spent by Contract",
            xaxis_title="Contract",
            yaxis_title="Amount ($)",
            xaxis_tickangle=-45,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        if "borough" in df.columns:
            boro_budget = df.groupby("borough")["awarded_value"].sum().reset_index()
            fig2 = px.pie(boro_budget, names="borough", values="awarded_value",
                          title="Awarded Value by Borough")
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Cost Performance Index (CPI) — higher is better, <0.9 flags over-budget**")
    cpi_cols = [c for c in ["contract_id", "contractor", "awarded_value", "spent_to_date",
                             "percent_complete", "cpi", "budget_status"] if c in df.columns]
    st.dataframe(df[cpi_cols].sort_values("cpi"), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("**Budget Codes Validator**")
    col1, col2 = st.columns(2)
    with col1:
        allowed_input = st.text_area(
            "Allowed Budget Codes (one per line)",
            value="HW-001\nHW-002\nSW-003\nPR-004\nPR-005",
            height=120,
            key="budget_allowed",
        )
    with col2:
        if "budget_code" in df.columns:
            allowed = {c.strip() for c in allowed_input.splitlines() if c.strip()}
            invalid = df[~df["budget_code"].isin(allowed)][["contract_id", "budget_code"]]
            if invalid.empty:
                st.success(f"✅ All {len(df)} contracts use valid budget codes.")
            else:
                st.error(f"⚠️ {len(invalid)} contracts have invalid/unlisted budget codes:")
                st.dataframe(invalid, use_container_width=True, hide_index=True)
        else:
            st.info("Add a 'budget_code' column to your data to validate codes.")


def _render_productivity(df: pd.DataFrame) -> None:
    st.subheader("Productivity Tracker")

    if df.empty:
        st.info("No productivity data loaded.")
        return

    df = df.copy()
    date_col = pick_column(df, DATE_CANDIDATES) or (
        next((c for c in df.columns if "date" in c.lower()), None)
    )
    if date_col and date_col != "date":
        df = df.rename(columns={date_col: "date"})

    if "date" not in df.columns:
        st.warning("No date column found — cannot build time-series view.")
        st.dataframe(df.head(100), use_container_width=True)
        return

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    lot_col = next((c for c in df.columns if "lot" in c.lower()), None)
    sqft_col = next((c for c in df.columns if "sqft" in c.lower() or "area" in c.lower() or "length" in c.lower()), None)

    if lot_col and lot_col != "lots_inspected":
        df = df.rename(columns={lot_col: "lots_inspected"})
    if sqft_col and sqft_col != "sqft_completed":
        df = df.rename(columns={sqft_col: "sqft_completed"})

    if "lots_inspected" not in df.columns:
        df["lots_inspected"] = 1
    if "sqft_completed" not in df.columns:
        df["sqft_completed"] = np.nan

    avg_lots = df["lots_inspected"].mean()
    total_sqft = df["sqft_completed"].sum() if df["sqft_completed"].notna().any() else 0
    defect_col = next((c for c in df.columns if "defect" in c.lower() or "violation" in c.lower()), None)
    total_defects = int(df[defect_col].sum()) if defect_col else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Lots/Day", f"{avg_lots:.1f}")
    c2.metric("Total sqft Inspected", f"{total_sqft:,.0f}" if total_sqft else "N/A")
    c3.metric("Total Defects Found", f"{total_defects:,}")
    insp_col = next((c for c in df.columns if "inspector" in c.lower() or "officer" in c.lower()), None)
    if insp_col:
        c4.metric("Active Inspectors", df[insp_col].nunique())

    if not HAS_PLOTLY:
        st.dataframe(df.head(100), use_container_width=True)
        return

    daily = df.groupby("date")["lots_inspected"].sum().reset_index().sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=daily["lots_inspected"],
        mode="lines", name="Lots Inspected",
        line=dict(color="#1f77b4", width=2),
    ))
    rolling = daily["lots_inspected"].rolling(7, min_periods=1).mean()
    fig.add_trace(go.Scatter(
        x=daily["date"], y=rolling,
        mode="lines", name="7-Day Rolling Avg",
        line=dict(color="#ff7f0e", dash="dash", width=1.5),
    ))
    fig.update_layout(title="Daily Lots Inspected", height=350, xaxis_title="Date", yaxis_title="Lots")
    st.plotly_chart(fig, use_container_width=True)

    if "borough" in df.columns:
        boro_prod = df.groupby("borough")["lots_inspected"].sum().reset_index()
        fig_boro = px.bar(boro_prod, x="borough", y="lots_inspected",
                          color="borough", title="Lots Inspected by Borough")
        fig_boro.update_layout(showlegend=False, height=320)
        st.plotly_chart(fig_boro, use_container_width=True)


def _render_export(df_contracts: pd.DataFrame, df_productivity: pd.DataFrame) -> None:
    st.subheader("Export & Reporting")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Report Start Date", value=date(2024, 1, 1), key="exp_start")
    with col2:
        end_date = st.date_input("Report End Date", value=date.today(), key="exp_end")

    if st.button("📊 Generate Full Report"):
        sheets: dict[str, pd.DataFrame] = {}

        if not df_contracts.empty:
            if "planned_start" in df_contracts.columns:
                df_contracts = df_contracts.copy()
                df_contracts["planned_start"] = pd.to_datetime(df_contracts["planned_start"], errors="coerce")
                mask = df_contracts["planned_start"].between(str(start_date), str(end_date))
                sheets["Contract Progress"] = df_contracts[mask] if mask.any() else df_contracts

            if {"awarded_value", "spent_to_date", "percent_complete"}.issubset(df_contracts.columns):
                summary = df_contracts.agg(
                    total_contracts=("contract_id", "count"),
                    total_awarded=("awarded_value", "sum"),
                    total_spent=("spent_to_date", "sum"),
                    avg_completion=("percent_complete", "mean"),
                ).to_frame("Value").reset_index()
                summary.columns = ["Metric", "Value"]
                sheets["Budget Summary"] = summary

        if not df_productivity.empty:
            date_col = pick_column(df_productivity, DATE_CANDIDATES)
            if date_col:
                df_productivity = df_productivity.copy()
                df_productivity[date_col] = pd.to_datetime(df_productivity[date_col], errors="coerce")
                mask = df_productivity[date_col].between(str(start_date), str(end_date))
                sheets["Productivity"] = df_productivity[mask] if mask.any() else df_productivity

        if not sheets:
            st.warning("No data available to export.")
            return

        xlsx_bytes = _excel_multisheet(sheets)
        st.download_button(
            label="📥 Download Report (Excel)",
            data=xlsx_bytes,
            file_name=f"nyc_dot_report_{start_date}_{end_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.success(f"Report ready: {len(sheets)} sheets covering {sum(len(d) for d in sheets.values()):,} rows.")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_contracts_page() -> None:
    st.header("📋 Contract Analytics & Budget Tracker")
    st.caption("Contract progress, budget performance, productivity tracking, and reporting for SIM Program.")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Contract Progress",
        "💰 Budget Analysis",
        "🏃 Productivity",
        "📥 Export & Reports",
    ])

    # --- Contract data (upload only — no matching Socrata dataset) ---
    st.sidebar.markdown("**Contract Data**")
    st.sidebar.caption(
        "Upload a contracts CSV/Excel with columns: contract_id, contractor, borough, "
        "awarded_value, spent_to_date, percent_complete, planned_start, planned_end, status"
    )
    up_c = st.sidebar.file_uploader("Contracts CSV / Excel", type=["csv", "xlsx"], key="up_contracts")
    if up_c:
        df_contracts = pd.read_excel(up_c) if up_c.name.endswith(".xlsx") else pd.read_csv(up_c)
    else:
        df_contracts = pd.DataFrame()
        st.sidebar.info("No contract data loaded. Upload a file to begin.")

    # --- Productivity data (Socrata or upload) ---
    st.sidebar.markdown("**Productivity Data**")
    prod_src = st.sidebar.radio("Source", ["Socrata (live)", "Upload CSV/Excel"], key="prod_src")
    if prod_src == "Socrata (live)":
        prod_limit = st.sidebar.number_input("Row limit", 1_000, 50_000, 15_000, step=5_000, key="prod_lim")
        df_productivity = _load_productivity_from_socrata(int(prod_limit))
        if demo_mode_enabled():
            st.sidebar.caption("⚠️ Demo mode — configure SOCRATA_APP_TOKEN in Settings for live data.")
    else:
        up_p = st.sidebar.file_uploader("Productivity CSV / Excel", type=["csv", "xlsx"], key="up_prod")
        if up_p:
            df_productivity = pd.read_excel(up_p) if up_p.name.endswith(".xlsx") else pd.read_csv(up_p)
        else:
            df_productivity = pd.DataFrame()

    with tab1:
        if df_contracts.empty:
            st.info("Upload contract data in the sidebar to populate this view.")
        else:
            _render_contract_progress(df_contracts)
    with tab2:
        if df_contracts.empty:
            st.info("Upload contract data in the sidebar to populate this view.")
        else:
            _render_budget_analysis(df_contracts)
    with tab3:
        _render_productivity(df_productivity)
    with tab4:
        _render_export(df_contracts, df_productivity)
