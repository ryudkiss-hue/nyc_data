"""Contract Analytics & Budget Tracker for NYC DOT SIM Program."""

from __future__ import annotations

import io
from datetime import date

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

import numpy as np

# ---------------------------------------------------------------------------
# Demo data generators
# ---------------------------------------------------------------------------

def _demo_contracts(n: int = 20) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    statuses = ["Active", "Active", "Active", "Pending", "Closed"]
    contractors = ["ACME Paving LLC", "BoroPave Inc.", "SidewalkPro NY", "MetroConstruct", "Urban Surfaces Ltd"]
    starts = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")
    durations = rng.integers(180, 730, n)
    pct = rng.uniform(10, 100, n).round(1)
    awarded = rng.integers(500_000, 8_000_000, n)
    return pd.DataFrame({
        "contract_id": [f"C-2025-{i:03d}" for i in range(1, n + 1)],
        "contractor": rng.choice(contractors, n),
        "borough": rng.choice(boroughs, n),
        "awarded_value": awarded,
        "spent_to_date": (awarded * pct / 100 * rng.uniform(0.85, 1.05, n)).astype(int),
        "planned_start": starts,
        "planned_end": starts + pd.to_timedelta(durations, unit="D"),
        "actual_start": starts + pd.to_timedelta(rng.integers(-14, 30, n), unit="D"),
        "percent_complete": pct,
        "status": rng.choice(statuses, n),
        "budget_code": rng.choice(["HW-001", "HW-002", "SW-003", "PR-004", "PR-005"], n),
    })


def _demo_productivity(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(7)
    boroughs = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    inspectors = [f"INSP-{i:03d}" for i in range(1, 11)]
    base_date = pd.Timestamp("2024-01-01")
    dates = [base_date + pd.Timedelta(days=int(i)) for i in rng.integers(0, 365, n)]
    return pd.DataFrame({
        "inspector_id": rng.choice(inspectors, n),
        "date": dates,
        "lots_inspected": rng.integers(5, 40, n),
        "sqft_completed": rng.integers(500, 8000, n),
        "borough": rng.choice(boroughs, n),
        "defects_found": rng.integers(0, 15, n),
        "contract_id": rng.choice([f"C-2025-{i:03d}" for i in range(1, 6)], n),
    })


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

    # KPI cards
    total = len(df)
    total_awarded = df["awarded_value"].sum() if "awarded_value" in df.columns else 0
    total_spent = df["spent_to_date"].sum() if "spent_to_date" in df.columns else 0
    avg_pct = df["percent_complete"].mean() if "percent_complete" in df.columns else 0

    behind = 0
    if {"planned_end", "percent_complete"}.issubset(df.columns):
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

    # Progress bar chart
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

    # Behind-schedule table
    if behind > 0:
        st.warning(f"⚠️ {behind} contract(s) are past planned end date with less than 100% completion.")
        behind_df = df[(df["planned_end"] < today) & (df["percent_complete"] < 100)][
            ["contract_id", "contractor", "borough", "planned_end", "percent_complete", "status"]
        ].sort_values("percent_complete")
        st.dataframe(behind_df, use_container_width=True, hide_index=True)

    # Full table
    with st.expander("Full Contract Table"):
        display_cols = [c for c in ["contract_id", "contractor", "borough", "awarded_value",
                                     "spent_to_date", "percent_complete", "status", "planned_end"] if c in df.columns]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)


def _render_budget_analysis(df: pd.DataFrame) -> None:
    st.subheader("Budget Analysis")

    if df.empty or not {"awarded_value", "spent_to_date", "percent_complete"}.issubset(df.columns):
        st.warning("Budget analysis requires awarded_value, spent_to_date, and percent_complete columns.")
        return

    # CPI calculation
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
        # Awarded vs Spent grouped bar
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

        # Borough breakdown pie
        if "borough" in df.columns:
            boro_budget = df.groupby("borough")["awarded_value"].sum().reset_index()
            fig2 = px.pie(boro_budget, names="borough", values="awarded_value",
                          title="Awarded Value by Borough")
            st.plotly_chart(fig2, use_container_width=True)

    # CPI table
    st.markdown("**Cost Performance Index (CPI) — higher is better, <0.9 flags over-budget**")
    cpi_cols = [c for c in ["contract_id", "contractor", "awarded_value", "spent_to_date",
                             "percent_complete", "cpi", "budget_status"] if c in df.columns]
    st.dataframe(df[cpi_cols].sort_values("cpi"), use_container_width=True, hide_index=True)

    # Budget codes validator
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

    required = {"lots_inspected", "sqft_completed", "date"}
    if not required.issubset(df.columns):
        st.warning(f"Missing columns for productivity analysis: {required - set(df.columns)}")
        return

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])

    # Summary KPIs
    avg_lots = df["lots_inspected"].mean()
    total_sqft = df["sqft_completed"].sum()
    total_defects = df["defects_found"].sum() if "defects_found" in df.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Lots/Day", f"{avg_lots:.1f}")
    c2.metric("Total sqft Inspected", f"{total_sqft:,.0f}")
    c3.metric("Total Defects Found", f"{total_defects:,}")
    if "inspector_id" in df.columns:
        c4.metric("Active Inspectors", df["inspector_id"].nunique())

    if not HAS_PLOTLY:
        st.dataframe(df.head(100), use_container_width=True)
        return

    # Daily trend
    daily = df.groupby("date")[["lots_inspected", "sqft_completed"]].sum().reset_index()
    daily = daily.sort_values("date")

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
    fig.update_layout(title="Daily Lots Inspected", height=350,
                      xaxis_title="Date", yaxis_title="Lots")
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        # Inspector leaderboard
        if "inspector_id" in df.columns:
            leaderboard = df.groupby("inspector_id").agg(
                total_lots=("lots_inspected", "sum"),
                total_sqft=("sqft_completed", "sum"),
                days_active=("date", "nunique"),
            ).reset_index().sort_values("total_sqft", ascending=False)
            leaderboard["avg_sqft_day"] = (leaderboard["total_sqft"] / leaderboard["days_active"]).round(0)
            st.markdown("**Inspector Leaderboard**")
            st.dataframe(leaderboard, use_container_width=True, hide_index=True)

    with col2:
        # Borough breakdown
        if "borough" in df.columns:
            boro_prod = df.groupby("borough")[["lots_inspected", "sqft_completed"]].sum().reset_index()
            fig_boro = px.bar(boro_prod, x="borough", y="sqft_completed",
                              color="borough", title="sqft Completed by Borough")
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
            if "date" in df_productivity.columns:
                df_productivity["date"] = pd.to_datetime(df_productivity["date"], errors="coerce")
                mask = df_productivity["date"].between(str(start_date), str(end_date))
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

    use_demo = st.sidebar.checkbox("Use demo data (all tabs)", value=True, key="contracts_demo")

    if use_demo:
        df_contracts = _demo_contracts()
        df_productivity = _demo_productivity()
        st.sidebar.caption("Showing synthetic demo data. Uncheck to upload your own.")
    else:
        st.sidebar.markdown("**Upload Contract Data**")
        up_c = st.sidebar.file_uploader("Contracts CSV", type="csv", key="up_contracts")
        df_contracts = pd.read_csv(up_c) if up_c else pd.DataFrame()

        st.sidebar.markdown("**Upload Productivity Data**")
        up_p = st.sidebar.file_uploader("Productivity CSV", type="csv", key="up_prod")
        df_productivity = pd.read_csv(up_p) if up_p else pd.DataFrame()

    with tab1:
        _render_contract_progress(df_contracts)
    with tab2:
        _render_budget_analysis(df_contracts)
    with tab3:
        _render_productivity(df_productivity)
    with tab4:
        _render_export(df_contracts, df_productivity)
