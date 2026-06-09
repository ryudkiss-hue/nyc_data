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
from socrata_toolkit.core.utils import coerce_series_datetime

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


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


@st.cache_data(ttl=86_400, show_spinner="Loading violations from Socrata…")
def _load_violations_from_socrata(limit: int = 20_000) -> pd.DataFrame:
    """Load SMD Violations (6kbp-uz6m) for quality / defect-recurrence analysis."""
    try:
        return fetch_dataset("violations", limit=limit)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86_400, show_spinner="Loading dismissal inspections from Socrata…")
def _load_dismissals_from_socrata(limit: int = 15_000) -> pd.DataFrame:
    """Load Sidewalk Dismissal Inspection Tracking (p4u2-3jgx)."""
    try:
        return fetch_dataset("dismissals", limit=limit)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86_400, show_spinner="Loading correspondences from Socrata…")
def _load_correspondences_from_socrata(limit: int = 10_000) -> pd.DataFrame:
    """Load Sidewalk Program Correspondences and parse date columns."""
    try:
        df = fetch_dataset("correspondences", limit=limit)
        for date_col in ("date_received", "date_closed"):
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        return df
    except Exception:
        return pd.DataFrame()


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


def _find_col(df: pd.DataFrame, *keywords: str) -> str | None:
    """Return the first column whose lowercased name contains any keyword."""
    for col in df.columns:
        low = col.lower()
        if any(kw in low for kw in keywords):
            return col
    return None


def _coerce_dates(df: pd.DataFrame, col: str) -> pd.Series:
    """Parse a column to datetime, tolerating bad values."""
    return coerce_series_datetime(df[col])


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


def _render_dismissals_correspondences() -> None:
    st.subheader("Dismissal Inspections & Program Correspondences")
    st.caption(
        "Dismissals track property owners who repaired their sidewalk privately. "
        "Correspondences track all written communications to the Sidewalk Program (SIM, CCU, BC, OSM)."
    )

    d_col, c_col = st.columns(2)
    d_limit = d_col.number_input("Dismissal row limit", 1_000, 50_000, 10_000, step=1_000, key="dis_lim")
    c_limit = c_col.number_input("Correspondence row limit", 1_000, 30_000, 5_000, step=1_000, key="cor_lim")

    tab_dis, tab_cor = st.tabs(["📋 Dismissal Inspections", "📨 Correspondences"])

    with tab_dis:
        df_dis = _load_dismissals_from_socrata(int(d_limit))
        if df_dis.empty:
            st.info("No dismissal data loaded. Ensure SOCRATA_APP_TOKEN is configured in Settings.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total records", f"{len(df_dis):,}")
            pass_mask = df_dis.get("pass_fail", pd.Series(dtype=str)).str.upper().eq("PASS")
            c2.metric("Pass", int(pass_mask.sum()))
            c3.metric("Fail", int((~pass_mask & df_dis.get("pass_fail", pd.Series(dtype=str)).notna()).sum()))
            exp_mask = df_dis.get("expedited", pd.Series(dtype=str)).str.upper().eq("Y")
            c4.metric("Expedited", int(exp_mask.sum()))

            boroughs = ["All"] + sorted(df_dis["borough"].dropna().unique().tolist()) if "borough" in df_dis.columns else ["All"]
            boro_filter = st.selectbox("Borough filter", boroughs, key="dis_boro")
            view = df_dis if boro_filter == "All" else df_dis[df_dis["borough"].str.upper() == boro_filter.upper()]

            show_cols = [c for c in ("borough", "block", "lot", "request_date", "inspection_date",
                                     "pass_fail", "reason_for_failure", "homeowner_contractor",
                                     "permit", "expedited", "violation") if c in view.columns]
            st.dataframe(view[show_cols] if show_cols else view, use_container_width=True, hide_index=True)
            st.download_button("⬇ Export (CSV)", view.to_csv(index=False).encode(), "dismissals.csv", mime="text/csv")

            if HAS_PLOTLY and "pass_fail" in df_dis.columns:
                pf_counts = df_dis["pass_fail"].value_counts().reset_index()
                pf_counts.columns = ["result", "count"]
                fig = px.pie(pf_counts, names="result", values="count",
                             title="Pass / Fail distribution", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)

    with tab_cor:
        df_cor = _load_correspondences_from_socrata(int(c_limit))
        if df_cor.empty:
            st.info("No correspondence data loaded. Ensure SOCRATA_APP_TOKEN is configured in Settings.")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total correspondences", f"{len(df_cor):,}")
            open_mask = df_cor.get("date_closed", pd.Series(dtype="datetime64[ns]")).isna()
            c2.metric("Open (no close date)", int(open_mask.sum()))
            if "date_received" in df_cor.columns:
                recent = df_cor["date_received"].dropna().max()
                c3.metric("Most recent", str(recent)[:10] if pd.notna(recent) else "—")

            issue_filter = "All"
            if "issue" in df_cor.columns:
                issues = ["All"] + sorted(df_cor["issue"].dropna().unique().tolist())[:30]
                issue_filter = st.selectbox("Issue type filter", issues, key="cor_issue")

            view = df_cor if issue_filter == "All" else df_cor[df_cor["issue"] == issue_filter]
            show_cols = [c for c in ("date_received", "borough", "block", "lot", "issue", "class",
                                     "referred_routed_to", "resoultion", "date_closed",
                                     "results_of_inspection", "sim") if c in view.columns]
            st.dataframe(view[show_cols] if show_cols else view, use_container_width=True, hide_index=True)
            st.download_button("⬇ Export (CSV)", view.to_csv(index=False).encode(), "correspondences.csv", mime="text/csv")

            if HAS_PLOTLY and "issue" in df_cor.columns:
                top_issues = df_cor["issue"].value_counts().head(10).reset_index()
                top_issues.columns = ["issue", "count"]
                fig = px.bar(top_issues, x="count", y="issue", orientation="h",
                             title="Top 10 correspondence issue types")
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)


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
# Item 28 — Contractor weighted KPI scorecard
# ---------------------------------------------------------------------------

def _render_contractor_scorecard(df: pd.DataFrame) -> None:
    """Composite KPI = velocity x quality x timeliness, ranked per contractor."""
    st.markdown("### 🏆 Contractor Weighted KPI Scorecard")
    st.caption(
        "Composite score (0–100) = velocity × quality × timeliness, equally weighted. "
        "Velocity = avg completion; timeliness = share of contracts on schedule; "
        "quality = cost efficiency (CPI capped at 1.0)."
    )

    if "contractor" not in df.columns:
        st.info("Add a 'contractor' column to your contract data to build the scorecard.")
        return
    if "percent_complete" not in df.columns:
        st.info("Add a 'percent_complete' column to compute the velocity component.")
        return

    work = df.copy()
    work["percent_complete"] = pd.to_numeric(work["percent_complete"], errors="coerce")

    # Velocity: average completion (0..1)
    velocity = work.groupby("contractor")["percent_complete"].mean() / 100.0

    # Timeliness: share NOT behind schedule (planned_end in past with <100% done)
    if {"planned_end"}.issubset(work.columns):
        pe = pd.to_datetime(work["planned_end"], errors="coerce")
        today = pd.Timestamp.today()
        behind = (pe < today) & (work["percent_complete"] < 100)
        work["_on_track"] = (~behind).astype(float)
        timeliness = work.groupby("contractor")["_on_track"].mean()
    else:
        timeliness = pd.Series(1.0, index=velocity.index)

    # Quality: cost efficiency via CPI (capped at 1.0); fallback to neutral 0.85
    if {"awarded_value", "spent_to_date"}.issubset(work.columns):
        work["_cpi"] = work.apply(
            lambda r: _cpi(r.get("awarded_value", 0), r.get("spent_to_date", 0),
                           r.get("percent_complete", 0)),
            axis=1,
        )
        quality = work.groupby("contractor")["_cpi"].mean().clip(upper=1.0)
    else:
        quality = pd.Series(0.85, index=velocity.index)

    score = pd.DataFrame({
        "contractor": velocity.index,
        "velocity": velocity.values,
        "quality": quality.reindex(velocity.index).fillna(0.0).values,
        "timeliness": timeliness.reindex(velocity.index).fillna(0.0).values,
    })
    score["composite"] = (
        score["velocity"].clip(0, 1)
        * score["quality"].clip(0, 1)
        * score["timeliness"].clip(0, 1)
    ) * 100.0
    score = score.sort_values("composite", ascending=False).reset_index(drop=True)
    score["rank"] = score.index + 1

    if HAS_PLOTLY:
        fig = px.bar(
            score,
            x="composite",
            y="contractor",
            orientation="h",
            color="composite",
            color_continuous_scale="RdYlGn",
            title="Composite KPI Score by Contractor",
            labels={"composite": "Composite KPI (0–100)", "contractor": "Contractor"},
            height=max(320, len(score) * 36),
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    display = score[["rank", "contractor", "velocity", "quality", "timeliness", "composite"]].copy()
    for col in ("velocity", "quality", "timeliness"):
        display[col] = (display[col] * 100).round(1)
    display["composite"] = display["composite"].round(1)
    st.dataframe(display, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Item 33 — Contract milestone Gantt chart
# ---------------------------------------------------------------------------

def _render_contract_gantt(df: pd.DataFrame) -> None:
    """Gantt timeline of contract milestones (planned_start → planned_end)."""
    st.markdown("### 📅 Contract Milestone Gantt")

    if not HAS_PLOTLY:
        st.info("Install plotly to view the Gantt chart.")
        return
    if not {"planned_start", "planned_end"}.issubset(df.columns):
        st.info("Add 'planned_start' and 'planned_end' columns to view the milestone Gantt.")
        return

    work = df.copy()
    work["_start"] = pd.to_datetime(work["planned_start"], errors="coerce")
    work["_end"] = pd.to_datetime(work["planned_end"], errors="coerce")
    work = work.dropna(subset=["_start", "_end"])
    if work.empty:
        st.info("No contracts with valid planned_start / planned_end dates to chart.")
        return

    label_col = "contractor" if "contractor" in work.columns else (
        "contract_id" if "contract_id" in work.columns else None
    )
    if label_col is None:
        work = work.reset_index().rename(columns={"index": "_row"})
        work["_row"] = work["_row"].astype(str)
        label_col = "_row"

    color_col = "status" if "status" in work.columns else None
    fig = px.timeline(
        work,
        x_start="_start",
        x_end="_end",
        y=label_col,
        color=color_col,
        title="Contract Timeline (planned start → planned end)",
        labels={label_col: label_col.replace("_", " ").title()},
        height=max(320, work[label_col].nunique() * 30 + 120),
    )
    fig.update_yaxes(autorange="reversed")
    fig.add_vline(x=pd.Timestamp.today(), line_dash="dash", line_color="red")
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Item 29 — Budget utilization burn-down
# ---------------------------------------------------------------------------

def _render_budget_burndown(df: pd.DataFrame) -> None:
    """Cumulative spend over time vs a linear budget target line."""
    st.markdown("### 🔥 Budget Utilization Burn-down")

    if not HAS_PLOTLY:
        st.info("Install plotly to view the burn-down chart.")
        return
    if "spent_to_date" not in df.columns:
        st.info("Add a 'spent_to_date' column to chart cumulative spend.")
        return

    work = df.copy()
    work["spent_to_date"] = pd.to_numeric(work["spent_to_date"], errors="coerce").fillna(0.0)

    # Order spend by a time axis when available, else by contract.
    time_col = next((c for c in ("planned_start", "planned_end") if c in work.columns), None)
    if time_col:
        work["_axis"] = pd.to_datetime(work[time_col], errors="coerce")
        work = work.dropna(subset=["_axis"]).sort_values("_axis")
        x_title = time_col.replace("_", " ").title()
    else:
        order_col = "contract_id" if "contract_id" in work.columns else None
        work = work.sort_values(order_col) if order_col else work
        work = work.reset_index(drop=True)
        work["_axis"] = (work[order_col] if order_col else work.index.astype(str))
        x_title = "Contract" if order_col else "Sequence"

    if work.empty:
        st.info("No spend records with a valid ordering axis to chart.")
        return

    work["_cum_spent"] = work["spent_to_date"].cumsum()

    # Total budget = awarded budget if present, else cumulative spend itself.
    if "awarded_value" in work.columns:
        total_budget = pd.to_numeric(work["awarded_value"], errors="coerce").fillna(0.0).sum()
    else:
        total_budget = float(work["_cum_spent"].iloc[-1])
    n = len(work)
    target = np.linspace(total_budget / n, total_budget, n) if n else np.array([])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=work["_axis"], y=work["_cum_spent"],
        mode="lines+markers", name="Cumulative Spend",
        line=dict(color="#F58518", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=work["_axis"], y=target,
        mode="lines", name="Linear Budget Target",
        line=dict(color="#4C78A8", dash="dash", width=2),
    ))
    fig.update_layout(
        title="Cumulative Spend vs Linear Budget Target",
        xaxis_title=x_title, yaxis_title="Cumulative $ ",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    util = (work["_cum_spent"].iloc[-1] / total_budget * 100) if total_budget else 0.0
    st.metric("Budget Utilization", f"{util:.1f}%",
              help="Cumulative spend as a share of total awarded budget.")


# ---------------------------------------------------------------------------
# Item 32 — Year-over-year comparison with Mann–Whitney U test
# ---------------------------------------------------------------------------

def _render_yoy_comparison(df: pd.DataFrame) -> None:
    """Compare a metric across two years; flag significance via Mann–Whitney U."""
    st.markdown("### 📊 Year-over-Year Contract Comparison")

    date_col = next((c for c in ("planned_start", "planned_end") if c in df.columns), None)
    metric_candidates = [c for c in ("percent_complete", "awarded_value", "spent_to_date")
                         if c in df.columns]
    if date_col is None or not metric_candidates:
        st.info(
            "Year-over-year comparison needs a date column (planned_start/planned_end) "
            "and a numeric metric (percent_complete, awarded_value, or spent_to_date)."
        )
        return

    work = df.copy()
    work["_year"] = pd.to_datetime(work[date_col], errors="coerce").dt.year
    work = work.dropna(subset=["_year"])
    years = sorted(work["_year"].dropna().unique().tolist())
    if len(years) < 2:
        st.info("Need contracts spanning at least two distinct years to compare.")
        return

    c1, c2, c3 = st.columns(3)
    metric = c1.selectbox("Metric", metric_candidates, key="yoy_metric")
    year_a = c2.selectbox("Year A", years, index=len(years) - 2, key="yoy_a")
    year_b = c3.selectbox("Year B", years, index=len(years) - 1, key="yoy_b")
    if year_a == year_b:
        st.info("Select two different years to compare.")
        return

    sample_a = pd.to_numeric(work.loc[work["_year"] == year_a, metric], errors="coerce").dropna()
    sample_b = pd.to_numeric(work.loc[work["_year"] == year_b, metric], errors="coerce").dropna()
    if sample_a.empty or sample_b.empty:
        st.info("Not enough non-null values in one of the selected years.")
        return

    m1, m2, m3 = st.columns(3)
    m1.metric(f"{year_a} median", f"{sample_a.median():,.1f}")
    m2.metric(f"{year_b} median", f"{sample_b.median():,.1f}")
    delta = sample_b.median() - sample_a.median()
    m3.metric("Δ median", f"{delta:,.1f}")

    if HAS_PLOTLY:
        box_df = pd.concat([
            pd.DataFrame({"year": str(year_a), metric: sample_a}),
            pd.DataFrame({"year": str(year_b), metric: sample_b}),
        ])
        fig = px.box(box_df, x="year", y=metric, color="year",
                     title=f"{metric} distribution: {year_a} vs {year_b}", points="outliers")
        fig.update_layout(showlegend=False, height=360)
        st.plotly_chart(fig, use_container_width=True)

    if not HAS_SCIPY:
        st.caption("Install scipy for the Mann–Whitney U significance test.")
        return
    if len(sample_a) < 2 or len(sample_b) < 2:
        st.caption("Need at least 2 values per year for a significance test.")
        return

    try:
        u_stat, p_value = scipy_stats.mannwhitneyu(
            sample_a, sample_b, alternative="two-sided"
        )
    except ValueError as exc:
        st.caption(f"Mann–Whitney U could not be computed: {exc}")
        return

    if p_value < 0.05:
        st.success(
            f"✅ Statistically significant difference (Mann–Whitney U = {u_stat:,.0f}, "
            f"p = {p_value:.4f} < 0.05). The {metric} distributions differ between "
            f"{year_a} and {year_b}."
        )
    else:
        st.warning(
            f"⚠️ No statistically significant difference (Mann–Whitney U = {u_stat:,.0f}, "
            f"p = {p_value:.4f} ≥ 0.05). Cannot conclude {metric} changed between "
            f"{year_a} and {year_b}."
        )


# ---------------------------------------------------------------------------
# Item 30 — Change-order / re-work frequency heatmap (violations)
# ---------------------------------------------------------------------------

def _render_rework_heatmap(df_viol: pd.DataFrame) -> None:
    """Density heatmap of re-work / violation frequency by block × contractor."""
    st.markdown("### 🔁 Change-Order / Re-work Frequency Heatmap")
    st.caption(
        "Derived from SMD Violations (6kbp-uz6m): density of violations / re-inspections "
        "by block and responsible party — hotspots indicate recurring re-work."
    )

    if df_viol.empty:
        st.info("No violations data loaded — configure SOCRATA_APP_TOKEN in Settings for live data.")
        return
    if not HAS_PLOTLY:
        st.info("Install plotly to view the heatmap.")
        return

    block_col = _find_col(df_viol, "block")
    party_col = _find_col(df_viol, "contractor", "responsible", "owner", "homeowner")
    if block_col is None or party_col is None:
        st.info(
            "Heatmap needs a block column and a contractor/responsible-party column. "
            f"Available columns: {', '.join(list(df_viol.columns)[:20])}"
        )
        return

    work = df_viol[[block_col, party_col]].copy()
    work[block_col] = work[block_col].astype(str)
    work[party_col] = work[party_col].astype(str)
    work = work[(work[block_col].str.strip() != "") & (work[party_col].str.strip() != "")]
    work = work[~work[block_col].str.lower().isin(("nan", "none"))]
    work = work[~work[party_col].str.lower().isin(("nan", "none"))]
    if work.empty:
        st.info("No usable block / party pairs found in the violations data.")
        return

    # Limit to the busiest blocks/parties for a readable heatmap.
    top_blocks = work[block_col].value_counts().head(25).index
    top_parties = work[party_col].value_counts().head(15).index
    work = work[work[block_col].isin(top_blocks) & work[party_col].isin(top_parties)]
    if work.empty:
        st.info("Not enough overlapping records to build a heatmap.")
        return

    fig = px.density_heatmap(
        work,
        x=party_col,
        y=block_col,
        title="Re-work Frequency: Block × Responsible Party (top 25 blocks)",
        labels={block_col: "Block", party_col: "Responsible Party"},
        color_continuous_scale="Reds",
        height=max(400, len(top_blocks) * 22),
    )
    fig.update_xaxes(tickangle=-45)
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Item 31 — Defect recurrence rate (same BBL re-inspected within 12 months)
# ---------------------------------------------------------------------------

def _render_defect_recurrence(df_viol: pd.DataFrame) -> None:
    """Share of BBLs with a repeat violation within 12 months of the first."""
    st.markdown("### 🔂 Defect Recurrence Rate (12-month window)")
    st.caption(
        "A BBL is a 'recurrence' when it has a second violation within 12 months of an "
        "earlier one — derived from SMD Violations (6kbp-uz6m)."
    )

    if df_viol.empty:
        st.info("No violations data loaded — configure SOCRATA_APP_TOKEN in Settings for live data.")
        return

    bbl_col = next(
        (c for c in df_viol.columns if c == "_bbl"),
        _find_col(df_viol, "bblid", "bbl"),
    )
    date_col = _find_col(df_viol, "issued", "inspection_date", "created", "date")
    if bbl_col is None or date_col is None:
        st.info(
            "Defect recurrence needs a BBL identifier and a date column. "
            f"Available columns: {', '.join(list(df_viol.columns)[:20])}"
        )
        return

    work = df_viol[[bbl_col, date_col]].copy()
    work["_bbl_key"] = work[bbl_col].astype(str).str.strip()
    work["_date"] = pd.to_datetime(work[date_col], errors="coerce")
    work = work.dropna(subset=["_date"])
    work = work[~work["_bbl_key"].str.lower().isin(("", "nan", "none"))]
    if work.empty:
        st.info("No violations with parseable dates and BBLs to analyze.")
        return

    work = work.sort_values(["_bbl_key", "_date"])
    work["_prev_date"] = work.groupby("_bbl_key")["_date"].shift(1)
    work["_gap_days"] = (work["_date"] - work["_prev_date"]).dt.days
    work["_recur"] = work["_prev_date"].notna() & (work["_gap_days"] <= 365)

    total_bbls = work["_bbl_key"].nunique()
    recurring_bbls = work.loc[work["_recur"], "_bbl_key"].nunique()
    recur_rate = (recurring_bbls / total_bbls * 100) if total_bbls else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Unique BBLs", f"{total_bbls:,}")
    c2.metric("BBLs with 12-mo recurrence", f"{recurring_bbls:,}")
    c3.metric("Recurrence Rate", f"{recur_rate:.1f}%")

    repeat_offenders = (
        work[work["_recur"]]
        .groupby("_bbl_key")
        .size()
        .reset_index(name="recurrences")
        .sort_values("recurrences", ascending=False)
        .head(20)
        .rename(columns={"_bbl_key": "bbl"})
    )
    if not repeat_offenders.empty:
        st.markdown("**Top repeat-offender BBLs**")
        st.dataframe(repeat_offenders, use_container_width=True, hide_index=True)

        if HAS_PLOTLY:
            fig = px.bar(
                repeat_offenders.head(15),
                x="recurrences", y="bbl", orientation="h",
                title="Top 15 BBLs by repeat violations (≤12 months apart)",
                labels={"recurrences": "Repeat violations", "bbl": "BBL"},
                color="recurrences", color_continuous_scale="Oranges",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"},
                              coloraxis_showscale=False, height=420)
            st.plotly_chart(fig, use_container_width=True)


def _render_quality_recurrence_tab() -> None:
    """Quality & Re-work tab — items 30 & 31 (real Socrata violations data)."""
    st.subheader("Quality, Re-work & Defect Recurrence")
    st.caption("Live analysis of SMD Violations to surface recurring defects and re-work hotspots.")

    limit = st.number_input(
        "Violations row limit", 2_000, 50_000, 20_000, step=2_000, key="qual_viol_lim"
    )
    if demo_mode_enabled():
        st.caption("⚠️ Demo mode — configure SOCRATA_APP_TOKEN in Settings for live data.")

    df_viol = _load_violations_from_socrata(int(limit))
    _render_rework_heatmap(df_viol)
    st.markdown("---")
    _render_defect_recurrence(df_viol)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_contracts_page() -> None:
    st.header("📋 Contract Analytics & Budget Tracker")
    st.caption("Contract progress, budget performance, productivity tracking, and reporting for SIM Program.")

    # --- New Layout: Executive Summary ---
    st.markdown("### 🏛️ Executive Summary")
    st.text(
        "This dashboard provides a comprehensive view of the SIM Program's contract budget and schedule health, "
        "highlighting high-risk contracts and operational hotspots for strategic intervention."
    )
    st.markdown("---")

    # --- New Layout: Level 1 - Core Metrics (KPI Hierarchy) ---
    st.markdown("### 📊 Level 1: Core KPI Metrics")
    kpi_cont = st.container(border=True)
    with kpi_cont:
        c1, c2, c3, c4 = st.columns(4)
        if not df_contracts.empty:
            today = pd.Timestamp.today()
            total = len(df_contracts)
            total_awarded = df_contracts["awarded_value"].sum() if "awarded_value" in df_contracts.columns else 0
            avg_pct = df_contracts["percent_complete"].mean() if "percent_complete" in df_contracts.columns else 0
            behind = 0
            if {"planned_end", "percent_complete"}.issubset(df_contracts.columns):
                mask = (pd.to_datetime(df_contracts["planned_end"], errors="coerce") < today) & (df_contracts["percent_complete"] < 100)
                behind = int(mask.sum())
            c1.metric("Active Contracts", total)
            c2.metric("Total Awarded", f"${total_awarded:,.0f}")
            c3.metric("Avg Completion", f"{avg_pct:.1f}%")
            c4.metric("Behind Schedule", behind)
        else:
            c1.metric("Active Contracts", "—")
            c2.metric("Total Awarded", "—")
            c3.metric("Avg Completion", "—")
            c4.metric("Behind Schedule", "—")

    # --- New Layout: Level 2 - Diagnostics ---
    st.markdown("### 🔍 Level 2: Diagnostic Insights")
    diag_cont = st.container()
    with diag_cont:
        st.info("Select a tab below for deeper diagnostic drill-downs.")
    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Contract Progress",
        "💰 Budget Analysis",
        "🏃 Productivity",
        "📋 Dismissals & Correspondences",
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
        _render_dismissals_correspondences()
    with tab5:
        _render_export(df_contracts, df_productivity)
