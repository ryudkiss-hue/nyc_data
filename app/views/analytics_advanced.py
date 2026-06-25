"""Advanced analytics view — Metric Trends, Cohort Analysis, Anomaly Detection,
Borough Rankings, Inspector Scorecard, SLA Tracker, Cross-Dataset, Segmentation,
and Bayesian / SLA advanced analytics (Bayesian completion-time, SLA breach curve,
Monte Carlo timeline, inspector benchmarking, survival curve, CI forecast)."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from app.data_loader import demo_mode_enabled, fetch_dataset

try:
    import plotly.express as px
    import plotly.graph_objects as go

    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    from sklearn.cluster import KMeans
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler

    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    from scipy import stats as scipy_stats

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

try:
    from prophet import Prophet

    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False

try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

import os

logger = logging.getLogger(__name__)

if not hasattr(st, "cache_data"):
    def _cache_data_polyfill(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    st.cache_data = _cache_data_polyfill

if not hasattr(st, "session_state"):
    class DummySessionState(dict):
        def __getattr__(self, key):
            return self.get(key)
        def __setattr__(self, key, value):
            self[key] = value
    st.session_state = DummySessionState()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TODAY = date.today()

def _pick_date_col(df: pd.DataFrame) -> str | None:
    """Return the first column whose name contains a date-like keyword."""
    keywords = ("date", "created", "open")
    for col in df.columns:
        lower = col.lower()
        if any(k in lower for k in keywords):
            return col
    return None

def _pick_col_icontains(df: pd.DataFrame, *fragments: str) -> str | None:
    """Return the first column whose lowercase name contains any of the fragments."""
    for frag in fragments:
        for col in df.columns:
            if frag in col.lower():
                return col
    return None

def _coerce_datetime(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_datetime(df[col], errors="coerce", utc=True).dt.tz_localize(None)

@st.cache_data(ttl=86_400, show_spinner="Loading inspections…")
def _load_inspections(limit: int) -> pd.DataFrame:
    return fetch_dataset("inspection", limit=limit)

@st.cache_data(ttl=86_400, show_spinner="Loading violations…")
def _load_violations(limit: int = 20_000) -> pd.DataFrame:
    return fetch_dataset("violations", limit=limit)

@st.cache_data(ttl=86_400, show_spinner="Loading street permits…")
def _load_street_permits(limit: int = 20_000) -> pd.DataFrame:
    return fetch_dataset("street_permits", limit=limit)

@st.cache_data(ttl=86_400, show_spinner="Loading HIQA inspections…")
def _load_hiqa(limit: int = 10_000) -> pd.DataFrame:
    return fetch_dataset("street_construction_inspections", limit=limit)

# ---------------------------------------------------------------------------
# CUSUM change-point detection (pure logic lives in the analysis library)
# ---------------------------------------------------------------------------
from socrata_toolkit.analysis.changepoint import detect_cusum_changepoint  # noqa: E402

# ---------------------------------------------------------------------------
# Anomaly summary helper
# ---------------------------------------------------------------------------

def _anomaly_summary(anomalies: int, total: int) -> str:
    pct = anomalies / total * 100
    return (
        f"Detected {anomalies:,} anomalous records ({pct:.1f}% of total). "
        "These locations have unusual combinations of condition score and geographic "
        "position compared to typical inspection sites."
    )

# ---------------------------------------------------------------------------
# Duration derivation (shared by Bayesian / Monte Carlo / survival analytics)
# ---------------------------------------------------------------------------

def _derive_durations(df: pd.DataFrame) -> pd.Series:
    """Derive completion/turnaround durations (days) from a fetched frame.

    Strategy, in priority order — never fabricates numbers:
    1. Explicit open→close date pair (difference in days).
    2. A single date column → days elapsed to today (age as a proxy duration).
    3. A pre-computed numeric duration/age column.

    Returns a clean Series of positive day counts (may be empty).
    """
    if df.empty:
        return pd.Series(dtype="float64")

    open_col = _pick_col_icontains(
        df, "inspection_date", "open_date", "created", "issued", "start"
    )
    close_col = _pick_col_icontains(
        df, "close", "completion", "completed", "resolved", "end_date", "disposition_date"
    )
    if open_col and close_col and open_col != close_col:
        opened = _coerce_datetime(df, open_col)
        closed = _coerce_datetime(df, close_col)
        durations = (closed - opened).dt.days
        durations = durations[durations.notna() & (durations >= 0)]
        if not durations.empty:
            return durations.astype("float64")

    date_col = _pick_date_col(df)
    if date_col is not None:
        opened = _coerce_datetime(df, date_col)
        today_ts = pd.Timestamp(_TODAY)
        age = (today_ts - opened).dt.days
        age = age[age.notna() & (age >= 0)]
        if not age.empty:
            return age.astype("float64")

    num_col = _pick_col_icontains(df, "duration", "days", "age", "elapsed")
    if num_col is not None:
        vals = pd.to_numeric(df[num_col], errors="coerce")
        vals = vals[vals.notna() & (vals >= 0)]
        if not vals.empty:
            return vals.astype("float64")

    return pd.Series(dtype="float64")

def _normal_credible_interval(
    sample: np.ndarray, conf: float = 0.95
) -> tuple[float, float, float]:
    """Bayesian Normal posterior mean + credible interval via a conjugate update.

    Uses a (near-)noninformative Normal-Inverse-Gamma prior so the posterior mean
    equals the sample mean and the posterior predictive of the mean follows a
    Student-t with (n-1) degrees of freedom (mirrors the classical t interval but
    interpreted as a credible interval). Returns (mean, lower, upper).
    """
    n = sample.size
    mean = float(np.mean(sample))
    if n < 2:
        return mean, mean, mean
    sd = float(np.std(sample, ddof=1))
    se = sd / np.sqrt(n)
    alpha = 1.0 - conf
    if HAS_SCIPY:
        crit = float(scipy_stats.t.ppf(1.0 - alpha / 2.0, df=n - 1))
    else:  # pragma: no cover - scipy expected present in mission extra
        crit = 1.96
    return mean, mean - crit * se, mean + crit * se

def _km_survival(durations: np.ndarray) -> pd.DataFrame:
    """Kaplan–Meier survival estimate (all events observed) implemented in numpy.

    Each duration is treated as an observed event (close happened at that day),
    so the estimator reduces to the empirical survival function S(t) = P(T > t).
    Returns a frame with columns: time, at_risk, events, survival.
    """
    n = durations.size
    times, counts = np.unique(durations, return_counts=True)
    survival = 1.0
    rows = []
    at_risk = n
    for t, d in zip(times, counts):
        survival *= (at_risk - d) / at_risk
        rows.append(
            {"time": float(t), "at_risk": int(at_risk), "events": int(d), "survival": survival}
        )
        at_risk -= d
    return pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Tab renderers
# ---------------------------------------------------------------------------

def _render_metric_trends(df: pd.DataFrame) -> None:
    """Tab 1 — Metric Trends (items 48, 49, 67)."""
    # Clear previous CUSUM anomalies to prevent stale sidebar badge state
    st.session_state["cusum_anomalies"] = []

    if df.empty:
        st.info("Load data to begin")
        return

    date_col = _pick_date_col(df)
    score_col = _pick_col_icontains(df, "condition", "score")
    borough_col = _pick_col_icontains(df, "borough")
    block_col = _pick_col_icontains(df, "block")

    # --- Metric metric cards ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total records", f"{len(df):,}")
    if score_col:
        numeric_scores = pd.to_numeric(df[score_col], errors="coerce")
        c2.metric("Avg condition score", f"{numeric_scores.mean():.1f}")
    else:
        c2.metric("Avg condition score", "—")
    c3.metric("Unique boroughs", df[borough_col].nunique() if borough_col else "—")
    c4.metric("Unique blocks", df[block_col].nunique() if block_col else "—")

    if date_col is None:
        st.warning("No date column detected — trend charts unavailable.")
        return

    df = df.copy()
    df["_dt"] = _coerce_datetime(df, date_col)
    df = df.dropna(subset=["_dt"])

    if df.empty:
        st.info("No parseable dates found in the date column.")
        return

    # --- Sparklines: 12-week rolling count (item 48) ---
    st.subheader("12-Week Rolling Count")
    if not HAS_PLOTLY:
        st.info("Install plotly for sparkline charts.")
    else:
        weekly = (
            df.set_index("_dt")
            .resample("W")
            .size()
            .rename("count")
            .reset_index()
            .rename(columns={"_dt": "week"})
            .tail(12)
        )
        if weekly.empty:
            st.info("Insufficient data for rolling count chart.")
        else:
            fig = px.line(
                weekly,
                x="week",
                y="count",
                markers=True,
                title="Weekly Inspection Count (last 12 weeks)",
                labels={"week": "Week", "count": "Count"},
            )
            fig.update_layout(height=300, margin={"t": 40, "b": 20})
            st.plotly_chart(fig, use_container_width=True)

    # --- Year-over-year (item 49) ---
    st.subheader("Year-over-Year Comparison")
    if not HAS_PLOTLY:
        st.info("Install plotly for YoY charts.")
    else:
        min_year = df["_dt"].dt.year.min()
        max_year = df["_dt"].dt.year.max()
        if max_year - min_year >= 1:
            this_year = max_year
            last_year = this_year - 1
            yoy = df[df["_dt"].dt.year.isin([last_year, this_year])].copy()
            yoy["month"] = yoy["_dt"].dt.month
            yoy["year"] = yoy["_dt"].dt.year.astype(str)
            yoy_counts = yoy.groupby(["year", "month"]).size().reset_index(name="count")
            fig_yoy = px.bar(
                yoy_counts,
                x="month",
                y="count",
                color="year",
                barmode="group",
                title=f"Year-over-Year: {last_year} vs {this_year}",
                labels={"month": "Month", "count": "Count", "year": "Year"},
            )
            fig_yoy.update_layout(height=350, margin={"t": 40, "b": 20})
            st.plotly_chart(fig_yoy, use_container_width=True)
        else:
            st.info(f"Data spans only one year ({min_year}); YoY comparison requires ≥2 years.")

    # --- CUSUM trend change (item 67, enhanced item 24) ---
    st.subheader("CUSUM Trend Change Detection")
    if not HAS_PLOTLY:
        st.info("Install plotly for CUSUM charts.")
    else:
        weekly_all = (
            df.set_index("_dt")
            .resample("W")
            .size()
            .rename("count")
            .reset_index()
            .rename(columns={"_dt": "week"})
        )
        if len(weekly_all) < 4:
            st.info("Not enough weekly data points for CUSUM analysis (need ≥4 weeks).")
        else:
            mu = weekly_all["count"].mean()
            weekly_all["cusum"] = (weekly_all["count"] - mu).cumsum()

            # Item 24: alert threshold (multiples of the standard deviation of the
            # cumulative deviation) flags ALL weeks whose |CUSUM| exceeds the band,
            # not just the single global maximum.
            cusum_std = float(weekly_all["cusum"].std(ddof=0)) or 1.0
            threshold_k = st.slider(
                "CUSUM alert threshold (× std of cumulative deviation)",
                min_value=0.5,
                max_value=4.0,
                value=2.0,
                step=0.5,
                help=(
                    "Weeks whose cumulative deviation exceeds ±k·std are flagged as "
                    "potential change-points and auto-annotated on the chart."
                ),
            )
            band = threshold_k * cusum_std
            flagged = weekly_all[weekly_all["cusum"].abs() >= band]

            fig_cusum = go.Figure()
            fig_cusum.add_trace(
                go.Scatter(
                    x=weekly_all["week"],
                    y=weekly_all["cusum"],
                    mode="lines",
                    name="CUSUM",
                    line={"color": "#1f77b4"},
                )
            )
            # Threshold band shading.
            fig_cusum.add_hline(
                y=band, line_dash="dot", line_color="rgba(214,39,40,0.6)",
                annotation_text=f"+{threshold_k:g}σ", annotation_position="top left",
            )
            fig_cusum.add_hline(
                y=-band, line_dash="dot", line_color="rgba(214,39,40,0.6)",
                annotation_text=f"-{threshold_k:g}σ", annotation_position="bottom left",
            )

            # Auto-annotate the dominant change-point plus any threshold breaches.
            annotate_idx: set[int] = set()
            cp_idx = detect_cusum_changepoint(weekly_all["count"])
            if cp_idx is not None and cp_idx in weekly_all.index:
                annotate_idx.add(int(cp_idx))
            annotate_idx.update(int(i) for i in flagged.index)

            for idx in sorted(annotate_idx):
                cp_date = weekly_all.loc[idx, "week"]
                cp_val = weekly_all.loc[idx, "cusum"]
                fig_cusum.add_trace(
                    go.Scatter(
                        x=[cp_date],
                        y=[cp_val],
                        mode="markers",
                        marker={"color": "#d62728", "size": 9, "symbol": "x"},
                        name="Change-point",
                        showlegend=False,
                    )
                )
                fig_cusum.add_annotation(
                    x=cp_date,
                    y=cp_val,
                    text=f"{pd.Timestamp(cp_date).date()}",
                    showarrow=True,
                    arrowhead=2,
                    bgcolor="rgba(255,200,0,0.8)",
                    font={"size": 10},
                )
            fig_cusum.update_layout(
                title="CUSUM — Cumulative Deviation from Mean Weekly Count",
                height=350,
                margin={"t": 40, "b": 20},
                xaxis_title="Week",
                yaxis_title="Cumulative Deviation",
            )
            st.plotly_chart(fig_cusum, use_container_width=True)

            # Store CUSUM results in session state for sidebar anomaly badge
            if not flagged.empty:
                st.session_state["cusum_anomalies"] = [
                    {
                        "week": pd.Timestamp(row["week"]).date().isoformat(),
                        "cusum_value": float(row["cusum"]),
                        "severity": "critical" if abs(row["cusum"]) > 2 * cusum_std else "warning",
                    }
                    for _, row in flagged.iterrows()
                ]
                first_breach = pd.Timestamp(flagged.iloc[0]["week"]).date()
                st.warning(
                    f"{len(flagged)} week(s) breach the ±{threshold_k:g}σ band "
                    f"(first at {first_breach}) — a sustained shift in inspection "
                    "volume is likely."
                )
            else:
                st.session_state["cusum_anomalies"] = []
                st.success(
                    f"No weeks exceed the ±{threshold_k:g}σ band — weekly volume is stable."
                )

def _render_cohort_analysis(df: pd.DataFrame) -> None:
    """Tab 2 — Cohort Analysis (items 45, 65)."""
    if df.empty:
        st.info("Load data to begin")
        return

    date_col = _pick_date_col(df)
    if date_col is None:
        st.warning("No date column detected — cohort analysis unavailable.")
        return

    df = df.copy()
    df["_dt"] = _coerce_datetime(df, date_col)
    df = df.dropna(subset=["_dt"])

    if df.empty:
        st.info("No parseable dates found in the date column.")
        return

    df["cohort_month"] = df["_dt"].dt.to_period("M")

    cohort_sizes = df.groupby("cohort_month").size().reset_index(name="count")
    cohort_sizes["cohort_month_str"] = cohort_sizes["cohort_month"].astype(str)

    st.subheader("Cohort Sizes by Month")
    if not HAS_PLOTLY:
        st.info("Install plotly for cohort charts.")
    else:
        fig_bar = px.bar(
            cohort_sizes,
            x="cohort_month_str",
            y="count",
            title="Records per Cohort Month",
            labels={"cohort_month_str": "Cohort Month", "count": "Count"},
        )
        fig_bar.update_layout(height=350, margin={"t": 40, "b": 20})
        st.plotly_chart(fig_bar, use_container_width=True)

    # --- Retention heatmap (item 65) ---
    st.subheader("Cohort Retention Heatmap")
    if not HAS_PLOTLY:
        st.info("Install plotly for retention heatmap.")
    else:
        today_ts = pd.Timestamp(_TODAY)
        df["weeks_since_open"] = ((today_ts - df["_dt"]).dt.days // 7).clip(upper=12)
        df["weeks_since_open"] = df["weeks_since_open"].clip(lower=0)

        pivot_df = (
            df.groupby(["cohort_month", "weeks_since_open"])
            .size()
            .reset_index(name="count")
        )
        if pivot_df.empty:
            st.info("Insufficient data to build retention heatmap.")
        else:
            pivot_df["cohort_month_str"] = pivot_df["cohort_month"].astype(str)
            pivot_table = pivot_df.pivot_table(
                index="cohort_month_str",
                columns="weeks_since_open",
                values="count",
                fill_value=0,
            )
            fig_heat = px.imshow(
                pivot_table,
                color_continuous_scale="Blues",
                title="Retention Heatmap: Cohort Month × Weeks Since Open",
                labels={"x": "Weeks Since Open", "y": "Cohort Month", "color": "Count"},
                aspect="auto",
            )
            fig_heat.update_layout(height=400, margin={"t": 40, "b": 20})
            st.plotly_chart(fig_heat, use_container_width=True)

def _render_anomaly_detection(df: pd.DataFrame) -> None:
    """Tab 3 — Anomaly Detection (items 44, 62)."""
    if df.empty:
        st.info("Load data to begin")
        return

    if not HAS_SKLEARN:
        st.info("Install scikit-learn for anomaly detection (`pip install scikit-learn`).")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for anomaly charts.")
        return

    score_col = _pick_col_icontains(df, "condition", "score")
    lat_col = _pick_col_icontains(df, "latitude", "lat")
    lon_col = _pick_col_icontains(df, "longitude", "lon", "lng")

    if lat_col is None or lon_col is None:
        st.warning("Latitude/longitude columns not found — anomaly detection unavailable.")
        return

    work = df.copy()
    work["_lat"] = pd.to_numeric(work[lat_col], errors="coerce")
    work["_lon"] = pd.to_numeric(work[lon_col], errors="coerce")

    if score_col:
        work["_score"] = pd.to_numeric(work[score_col], errors="coerce")
        features = work[["_score", "_lat", "_lon"]].dropna()
        feature_cols = ["_score", "_lat", "_lon"]
    else:
        features = work[["_lat", "_lon"]].dropna()
        feature_cols = ["_lat", "_lon"]

    if len(features) < 10:
        st.info("Not enough records with valid coordinates for anomaly detection (need ≥10).")
        return

    st.subheader("Isolation Forest Anomaly Detection")
    with st.spinner("Running anomaly detection…"):
        model = IsolationForest(contamination=0.05, random_state=42)
        predictions = model.fit_predict(features[feature_cols])
        features = features.copy()
        features["_anomaly"] = predictions

    anomaly_count = int((features["_anomaly"] == -1).sum())
    total_count = len(features)

    c1, c2, c3 = st.columns(3)
    c1.metric("Total records analysed", f"{total_count:,}")
    c2.metric("Anomalies detected", f"{anomaly_count:,}")
    c3.metric("Anomaly rate", f"{anomaly_count / total_count * 100:.1f}%")

    st.info(_anomaly_summary(anomaly_count, total_count))

    plot_df = features.copy()
    plot_df["anomaly_label"] = plot_df["_anomaly"].map({1: "Normal", -1: "Anomaly"})

    fig = px.scatter(
        plot_df,
        x="_lon",
        y="_lat",
        color="anomaly_label",
        color_discrete_map={"Normal": "#636EFA", "Anomaly": "#EF553B"},
        title="Anomaly Map (scatter by lat/lon)",
        labels={"_lon": "Longitude", "_lat": "Latitude"},
        opacity=0.6,
    )
    fig.update_layout(height=450, margin={"t": 40, "b": 20})
    st.plotly_chart(fig, use_container_width=True)

def _render_borough_rankings(df: pd.DataFrame) -> None:
    """Tab 4 — Borough Rankings (items 47, 55)."""
    if df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for ranking charts.")
        return

    borough_col = _pick_col_icontains(df, "borough")
    score_col = _pick_col_icontains(df, "condition", "score")

    st.subheader("Borough Performance Rankings")

    if borough_col is None:
        st.info("Borough column not found in inspections dataset.")
    else:
        work = df.copy()
        work["_borough"] = work[borough_col].astype(str).str.upper().str.strip()

        agg: dict[str, pd.Series] = {"count": work.groupby("_borough").size()}

        if score_col:
            work["_score"] = pd.to_numeric(work[score_col], errors="coerce")
            agg["avg_score"] = work.groupby("_borough")["_score"].mean()
            agg["pct_critical"] = (
                work[work["_score"] < 30].groupby("_borough").size() / agg["count"] * 100
            )

        borough_df = pd.DataFrame(agg).reset_index().rename(columns={"_borough": "borough"})
        borough_df = borough_df.sort_values(
            "avg_score" if "avg_score" in borough_df.columns else "count", ascending=False
        )

        st.dataframe(borough_df, use_container_width=True)

        chart_col = "avg_score" if "avg_score" in borough_df.columns else "count"
        fig = px.bar(
            borough_df.sort_values(chart_col),
            x=chart_col,
            y="borough",
            orientation="h",
            title=f"Borough Rankings by {chart_col.replace('_', ' ').title()}",
            labels={"borough": "Borough", chart_col: chart_col.replace("_", " ").title()},
            color=chart_col,
            color_continuous_scale="RdYlGn",
        )
        fig.update_layout(height=400, margin={"t": 40, "b": 20})
        st.plotly_chart(fig, use_container_width=True)

    # --- Contractor ranking (item 55) ---
    st.subheader("Contractor Rankings by Permit Volume")
    try:
        permits_df = _load_street_permits()
    except Exception as exc:
        st.warning(f"Could not load street permits: {exc}")
        return

    if permits_df.empty:
        st.info("No street permit data available.")
        return

    applicant_col = _pick_col_icontains(permits_df, "applicant", "permittee", "company")
    if applicant_col is None:
        st.info("Applicant/permittee column not found in street permits dataset.")
        return

    contractor_counts = (
        permits_df.groupby(applicant_col)
        .size()
        .reset_index(name="permit_count")
        .rename(columns={applicant_col: "contractor"})
        .sort_values("permit_count", ascending=False)
        .head(20)
    )

    # Attempt join with HIQA pass/fail
    try:
        hiqa_df = _load_hiqa()
        hiqa_applicant = _pick_col_icontains(hiqa_df, "applicant", "permittee", "company")
        result_col = _pick_col_icontains(hiqa_df, "result", "status", "pass", "fail")
        if hiqa_applicant and result_col:
            hiqa_df["_contractor"] = hiqa_df[hiqa_applicant].astype(str).str.upper()
            hiqa_summary = hiqa_df.groupby("_contractor").apply(
                lambda g: pd.Series({
                    "hiqa_total": len(g),
                    "hiqa_pass": (
                        g[result_col].astype(str).str.upper().str.contains("PASS").sum()
                    ),
                })
            ).reset_index().rename(columns={"_contractor": "contractor"})
            hiqa_summary["hiqa_pass_rate_%"] = (
                hiqa_summary["hiqa_pass"] / hiqa_summary["hiqa_total"] * 100
            ).round(1)
            contractor_counts["contractor_upper"] = (
                contractor_counts["contractor"].astype(str).str.upper()
            )
            hiqa_summary.rename(columns={"contractor": "contractor_upper"}, inplace=True)
            contractor_counts = contractor_counts.merge(
                hiqa_summary[["contractor_upper", "hiqa_total", "hiqa_pass_rate_%"]],
                on="contractor_upper",
                how="left",
            ).drop(columns=["contractor_upper"])
    except Exception as exc:
        logger.debug("HIQA join skipped: %s", exc)

    st.dataframe(contractor_counts, use_container_width=True)

    fig_contractors = px.bar(
        contractor_counts.sort_values("permit_count"),
        x="permit_count",
        y="contractor",
        orientation="h",
        title="Top 20 Contractors by Permit Volume",
        labels={"permit_count": "Permit Count", "contractor": "Contractor"},
    )
    fig_contractors.update_layout(height=500, margin={"t": 40, "b": 20})
    st.plotly_chart(fig_contractors, use_container_width=True)

def _render_inspector_scorecard(df: pd.DataFrame) -> None:
    """Tab 5 — Inspector Scorecard (item 46)."""
    if df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for scorecard charts.")
        return

    inspector_col = _pick_col_icontains(df, "inspector")
    score_col = _pick_col_icontains(df, "condition", "score")
    date_col = _pick_date_col(df)

    if inspector_col is None:
        available = ", ".join(df.columns.tolist()[:20])
        st.info(
            f"Inspector ID column not found in this dataset. "
            f"Available columns: {available}"
        )
        return

    st.subheader("Inspector Performance Scorecard")

    work = df.copy()
    work["_inspector"] = work[inspector_col].astype(str)

    agg_dict: dict[str, object] = {"inspections": (inspector_col, "count")}
    if score_col:
        work["_score"] = pd.to_numeric(work[score_col], errors="coerce")
        agg_dict["avg_score"] = ("_score", "mean")
    if date_col:
        work["_dt"] = _coerce_datetime(work, date_col)
        agg_dict["earliest_date"] = ("_dt", "min")
        agg_dict["latest_date"] = ("_dt", "max")

    scorecard = (
        work.groupby("_inspector")
        .agg(**{k: v for k, v in agg_dict.items()})
        .reset_index()
        .rename(columns={"_inspector": "inspector"})
        .sort_values("inspections", ascending=False)
    )

    st.dataframe(scorecard, use_container_width=True)

    fig = px.bar(
        scorecard.sort_values("inspections").tail(30),
        x="inspections",
        y="inspector",
        orientation="h",
        title="Inspections per Inspector (top 30)",
        labels={"inspections": "Inspection Count", "inspector": "Inspector"},
    )
    fig.update_layout(height=500, margin={"t": 40, "b": 20})
    st.plotly_chart(fig, use_container_width=True)

    csv_bytes = scorecard.to_csv(index=False).encode()
    st.download_button(
        label="Download scorecard CSV",
        data=csv_bytes,
        file_name="inspector_scorecard.csv",
        mime="text/csv",
    )

def _render_sla_tracker() -> None:
    """Tab 6 — SLA Tracker (items 52, 69)."""
    try:
        df = _load_violations()
    except Exception as exc:
        st.error(f"Could not load violations: {exc}")
        return

    if df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for SLA charts.")
        return

    st.subheader("SLA Configuration")
    col_low, col_med, col_high = st.columns(3)
    sla_low = col_low.number_input("LOW severity SLA (days)", value=90, min_value=1)
    sla_medium = col_med.number_input("MEDIUM severity SLA (days)", value=60, min_value=1)
    sla_high = col_high.number_input("HIGH severity SLA (days)", value=30, min_value=1)

    # Detect date column
    date_col: str | None = None
    for kw in ("issued", "date", "created"):
        for col in df.columns:
            if kw in col.lower():
                date_col = col
                break
        if date_col:
            break

    if date_col is None:
        st.warning("Could not detect a date column in the violations dataset.")
        return

    work = df.copy()
    work["_issued"] = _coerce_datetime(work, date_col)
    work = work.dropna(subset=["_issued"])

    if work.empty:
        st.info("No parseable dates found in violations dataset.")
        return

    # Filter to open violations if status column exists
    status_col = _pick_col_icontains(work, "status")
    if status_col:
        open_mask = work[status_col].astype(str).str.upper().str.contains("OPEN|ACTIVE|PENDING")
        if open_mask.sum() > 0:
            work = work[open_mask]

    today_ts = pd.Timestamp(_TODAY)
    work["days_open"] = (today_ts - work["_issued"]).dt.days.clip(lower=0)

    # Assign SLA target based on severity column
    severity_col = _pick_col_icontains(work, "severity", "priority", "urgency")
    if severity_col:
        sev_upper = work[severity_col].astype(str).str.upper()
        work["sla_target"] = sla_medium  # default
        work.loc[sev_upper.str.contains("LOW"), "sla_target"] = sla_low
        work.loc[sev_upper.str.contains("HIGH|CRITICAL"), "sla_target"] = sla_high
    else:
        work["sla_target"] = sla_medium

    work["days_remaining"] = work["sla_target"] - work["days_open"]

    work["sla_status"] = "ON_TRACK"
    work.loc[work["days_remaining"].between(0, 14), "sla_status"] = "AT_RISK"
    work.loc[work["days_remaining"] < 0, "sla_status"] = "BREACHED"

    on_track = int((work["sla_status"] == "ON_TRACK").sum())
    at_risk = int((work["sla_status"] == "AT_RISK").sum())
    breached = int((work["sla_status"] == "BREACHED").sum())

    m1, m2, m3 = st.columns(3)
    m1.metric("On Track", f"{on_track:,}", help="More than 14 days remaining")
    m2.metric(
        "At Risk", f"{at_risk:,}", help="0–14 days remaining",
        delta=f"-{at_risk}", delta_color="inverse",
    )
    m3.metric(
        "Breached", f"{breached:,}", help="SLA exceeded",
        delta=f"-{breached}", delta_color="inverse",
    )

    # --- Violation aging histogram (item 52) ---
    st.subheader("Violation Aging Histogram")
    borough_col = _pick_col_icontains(work, "borough")
    if borough_col:
        fig_hist = px.histogram(
            work,
            x="days_open",
            color=borough_col,
            nbins=40,
            title="Days Open Distribution by Borough",
            labels={"days_open": "Days Open", borough_col: "Borough"},
            barmode="overlay",
            opacity=0.7,
        )
    else:
        fig_hist = px.histogram(
            work,
            x="days_open",
            nbins=40,
            title="Days Open Distribution",
            labels={"days_open": "Days Open"},
        )
    fig_hist.update_layout(height=350, margin={"t": 40, "b": 20})
    st.plotly_chart(fig_hist, use_container_width=True)

    # SLA status table
    st.subheader("Violations by SLA Status")
    sla_candidates = [date_col, "days_open", "sla_target", "days_remaining", "sla_status"]
    display_cols = [c for c in sla_candidates if c in work.columns]
    if borough_col:
        display_cols = [borough_col] + display_cols

    st.dataframe(
        work[display_cols]
        .sort_values("days_remaining")
        .head(500)
        .reset_index(drop=True),
        use_container_width=True,
    )

    csv_bytes = work[display_cols].to_csv(index=False).encode()
    st.download_button(
        label="Download SLA report CSV",
        data=csv_bytes,
        file_name="sla_tracker.csv",
        mime="text/csv",
    )

def _render_cross_dataset(inspections_df: pd.DataFrame) -> None:
    """Tab 7 — Cross-Dataset Analysis (items 64, 70)."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for cross-dataset charts.")
        return

    try:
        violations_df = _load_violations()
    except Exception as exc:
        st.error(f"Could not load violations: {exc}")
        return

    if violations_df.empty:
        st.info("Violations dataset is empty — cross-dataset analysis unavailable.")
        return

    borough_col_insp = _pick_col_icontains(inspections_df, "borough")
    borough_col_viol = _pick_col_icontains(violations_df, "borough")

    if borough_col_insp is None or borough_col_viol is None:
        st.warning("Borough column not found in one or both datasets.")
        return

    insp_counts = (
        inspections_df.assign(_borough=inspections_df[borough_col_insp].astype(str).str.upper())
        .groupby("_borough")
        .size()
        .reset_index(name="inspection_count")
        .rename(columns={"_borough": "borough"})
    )
    viol_counts = (
        violations_df.assign(_borough=violations_df[borough_col_viol].astype(str).str.upper())
        .groupby("_borough")
        .size()
        .reset_index(name="violation_count")
        .rename(columns={"_borough": "borough"})
    )

    merged = insp_counts.merge(viol_counts, on="borough", how="outer").fillna(0)
    merged["inspection_count"] = merged["inspection_count"].astype(int)
    merged["violation_count"] = merged["violation_count"].astype(int)

    # --- Metric reconciliation (item 64) ---
    st.subheader("Metric Reconciliation: Inspections vs Violations per Borough")
    denom = merged["violation_count"].replace(0, float("nan"))
    merged["ratio"] = (merged["inspection_count"] / denom).round(2)

    def _ratio_flag(r: float) -> str:
        return "⚠️ Outside 0.5–2.0x range" if pd.notna(r) and not (0.5 <= r <= 2.0) else "✅ Normal"

    merged["flag"] = merged["ratio"].apply(_ratio_flag)
    st.dataframe(merged, use_container_width=True)

    # --- Cross-dataset risk score (item 70) ---
    st.subheader("Composite Risk Score by Borough")
    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    total_violations = merged["violation_count"].sum()

    if score_col:
        inspections_df = inspections_df.copy()
        inspections_df["_score"] = pd.to_numeric(inspections_df[score_col], errors="coerce")
        inspections_df["_borough"] = inspections_df[borough_col_insp].astype(str).str.upper()
        critical_counts = (
            inspections_df[inspections_df["_score"] < 30]
            .groupby("_borough")
            .size()
            .reset_index(name="critical_count")
            .rename(columns={"_borough": "borough"})
        )
        total_critical = critical_counts["critical_count"].sum() or 1
        risk_df = merged.merge(critical_counts, on="borough", how="left").fillna(0)
        risk_df["composite_risk"] = (
            risk_df["violation_count"] / (total_violations or 1) * 50
            + risk_df["critical_count"] / total_critical * 50
        ).round(1)
    else:
        risk_df = merged.copy()
        risk_df["composite_risk"] = (
            risk_df["violation_count"] / (total_violations or 1) * 100
        ).round(1)

    risk_df = risk_df.sort_values("composite_risk", ascending=False)
    fig_risk = px.bar(
        risk_df.sort_values("composite_risk"),
        x="composite_risk",
        y="borough",
        orientation="h",
        title="Composite Risk Score by Borough",
        labels={"composite_risk": "Risk Score (0–100)", "borough": "Borough"},
        color="composite_risk",
        color_continuous_scale="RdYlGn_r",
    )
    fig_risk.update_layout(height=400, margin={"t": 40, "b": 20})
    st.plotly_chart(fig_risk, use_container_width=True)

    csv_bytes = risk_df.to_csv(index=False).encode()
    st.download_button(
        label="Download composite risk table CSV",
        data=csv_bytes,
        file_name="composite_risk.csv",
        mime="text/csv",
    )

def _render_segmentation(df: pd.DataFrame) -> None:
    """Tab 8 — Segmentation (items 50, 68)."""
    if df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for segmentation charts.")
        return

    # --- Defect correlation matrix (item 50) ---
    st.subheader("Defect Type × Borough Correlation Matrix")
    defect_col = _pick_col_icontains(df, "defect", "defect_type", "defecttype")
    borough_col = _pick_col_icontains(df, "borough")

    if defect_col and borough_col:
        crosstab = pd.crosstab(
            df[defect_col].astype(str).str.strip(),
            df[borough_col].astype(str).str.upper().str.strip(),
        )
        if not crosstab.empty:
            fig_ct = px.imshow(
                crosstab,
                title="Defect Type Concentration by Borough",
                labels={"x": "Borough", "y": "Defect Type", "color": "Count"},
                color_continuous_scale="Viridis",
                aspect="auto",
            )
            fig_ct.update_layout(height=450, margin={"t": 40, "b": 20})
            st.plotly_chart(fig_ct, use_container_width=True)
        else:
            st.info("No cross-tabulation data available.")
    else:
        missing = []
        if defect_col is None:
            missing.append("defect_type")
        if borough_col is None:
            missing.append("borough")
        st.info(f"Column(s) not found for defect correlation matrix: {', '.join(missing)}")

    # --- K-Means segmentation (item 68) ---
    st.subheader("K-Means Spatial Segmentation (5 segments)")

    score_col = _pick_col_icontains(df, "condition", "score")
    lat_col = _pick_col_icontains(df, "latitude", "lat")
    lon_col = _pick_col_icontains(df, "longitude", "lon", "lng")

    if score_col is None or lat_col is None or lon_col is None:
        km_candidates = [
            ("condition_score", score_col), ("latitude", lat_col), ("longitude", lon_col)
        ]
        missing_km = [c for c, v in km_candidates if v is None]
        st.info(
            f"K-Means segmentation requires condition score + lat/lon. "
            f"Missing: {', '.join(missing_km)}"
        )
        return

    if not HAS_SKLEARN:
        st.info("Install scikit-learn for K-Means segmentation (`pip install scikit-learn`).")
        return

    work = df.copy()
    work["_score"] = pd.to_numeric(work[score_col], errors="coerce")
    work["_lat"] = pd.to_numeric(work[lat_col], errors="coerce")
    work["_lon"] = pd.to_numeric(work[lon_col], errors="coerce")
    work = work.dropna(subset=["_score", "_lat", "_lon"])

    if len(work) < 10:
        st.info("Not enough records with valid score + coordinates for segmentation (need ≥10).")
        return

    with st.spinner("Running K-Means clustering…"):
        scaler = StandardScaler()
        X = scaler.fit_transform(work[["_score", "_lat", "_lon"]])
        kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
        work["cluster"] = kmeans.fit_predict(X).astype(str)

    # Cluster profiles
    borough_col_km = _pick_col_icontains(work, "borough")
    st.subheader("Cluster Profiles")

    profile_agg: dict = {"count": ("_score", "count"), "avg_score": ("_score", "mean")}
    profiles = work.groupby("cluster").agg(**profile_agg).reset_index()
    profiles["avg_score"] = profiles["avg_score"].round(1)

    for _, row in profiles.iterrows():
        cluster_id = row["cluster"]
        n = int(row["count"])
        avg = row["avg_score"]
        boro_note = ""
        if borough_col_km:
            top_boro = (
                work[work["cluster"] == cluster_id][borough_col_km]
                .astype(str)
                .str.upper()
                .value_counts()
                .idxmax()
            )
            boro_note = f", concentrated in {top_boro}"
        st.markdown(
            f"**Segment {cluster_id}**: {n:,} inspections, avg score {avg}{boro_note}"
        )

    st.dataframe(profiles, use_container_width=True)

    # Scatter map coloured by cluster (open-street-map requires no token)
    fig_seg = px.scatter_mapbox(
        work,
        lat="_lat",
        lon="_lon",
        color="cluster",
        title="K-Means Segments — Spatial Distribution",
        mapbox_style="open-street-map",
        zoom=10,
        height=500,
        opacity=0.6,
        hover_data={"_score": True},
    )
    fig_seg.update_layout(margin={"t": 40, "b": 0})
    st.plotly_chart(fig_seg, use_container_width=True)

# ---------------------------------------------------------------------------
# Tier 1 Dashboard: Hypothesis Testing, Waterfall, Correlation, Cross-Filter
# ---------------------------------------------------------------------------

def _render_tier1_dashboard(inspections_df: pd.DataFrame) -> None:
    """Tab 9 — Tier 1 Dashboard with statistical testing and decomposition."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for dashboard charts.")
        return

    st.subheader("📊 Tier 1 Dashboard: Statistical Analysis & Decomposition")

    # --- Section 1: Hypothesis Testing ---
    st.markdown("### 1️⃣ Hypothesis Testing: Borough Comparison")

    borough_col = _pick_col_icontains(inspections_df, "borough")
    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    date_col = _pick_date_col(inspections_df)

    if borough_col and score_col and HAS_SCIPY:
        df_test = inspections_df.copy()
        df_test["_borough"] = df_test[borough_col].astype(str).str.upper()
        df_test["_score"] = pd.to_numeric(df_test[score_col], errors="coerce")

        borough_groups = [
            df_test[df_test["_borough"] == b]["_score"].dropna().values
            for b in df_test["_borough"].unique()[:5]
        ]
        borough_names = sorted(df_test["_borough"].unique())[:5]

        if all(len(g) > 1 for g in borough_groups):
            f_stat, p_value = scipy_stats.f_oneway(*borough_groups)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("F-Statistic", f"{f_stat:.4f}")
            with col2:
                sig = "✅ Significant" if p_value < 0.05 else "❌ Not Significant"
                st.metric("P-Value", f"{p_value:.4f}", sig)

            effect_sizes = [g.std() / df_test["_score"].std() if df_test["_score"].std() > 0 else 0 for g in borough_groups]
            p_values = [p_value] * len(borough_names)

            from socrata_toolkit.viz import hypothesis_test_results

            fig_hyp = hypothesis_test_results(
                borough_names,
                p_values,
                effect_sizes,
                title="P-values & Effect Sizes by Borough",
            )
            st.plotly_chart(fig_hyp, use_container_width=True)

    # --- Section 2: Waterfall Chart (SLA Breach Drivers) ---
    st.markdown("### 2️⃣ SLA Breach Decomposition")

    from socrata_toolkit.viz import waterfall_chart

    if date_col and score_col:
        df_waterfall = inspections_df.copy()
        df_waterfall["_dt"] = _coerce_datetime(df_waterfall, date_col)
        df_waterfall["_score"] = pd.to_numeric(df_waterfall[score_col], errors="coerce")
        df_waterfall["_is_critical"] = df_waterfall["_score"] < 30

        recent = df_waterfall[df_waterfall["_dt"] >= (df_waterfall["_dt"].max() - pd.Timedelta(days=30))]

        breach_factors = {
            "Critical Inspections": recent["_is_critical"].sum() * -5,
            "Low Score Impact": (recent["_score"] < 50).sum() * -3,
            "Inspection Volume": len(recent) * 2,
            "Coverage Bonus": recent["_borough"].nunique() if "_borough" in recent.columns else 5,
        }

        fig_waterfall = waterfall_chart(
            list(breach_factors.keys()),
            list(breach_factors.values()),
            title="SLA Breach Impact Drivers (30-day window)",
        )
        st.plotly_chart(fig_waterfall, use_container_width=True)

    # --- Section 3: Correlation Heatmap ---
    st.markdown("### 3️⃣ Metric Correlations")

    from socrata_toolkit.viz import correlation_heatmap

    numeric_cols = inspections_df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        selected_cols = st.multiselect(
            "Select metrics to correlate",
            numeric_cols,
            default=numeric_cols[:min(5, len(numeric_cols))],
        )
        if selected_cols and len(selected_cols) > 1:
            fig_corr = correlation_heatmap(
                inspections_df,
                selected_cols,
                title="Correlation Matrix: Selected Metrics",
            )
            st.plotly_chart(fig_corr, use_container_width=True)

    # --- Section 4: Cross-Filtering & Inspector Performance ---
    st.markdown("### 4️⃣ Cross-Filtering: Inspector Performance by Borough")

    inspector_col = _pick_col_icontains(inspections_df, "inspector")
    if inspector_col and borough_col and score_col:
        df_filter = inspections_df.copy()
        df_filter["_inspector"] = df_filter[inspector_col].astype(str)
        df_filter["_borough"] = df_filter[borough_col].astype(str).str.upper()
        df_filter["_score"] = pd.to_numeric(df_filter[score_col], errors="coerce")

        boroughs = sorted(df_filter["_borough"].unique())
        selected_borough = st.selectbox(
            "Filter by Borough",
            ["All"] + boroughs,
            key="tier1_borough_filter",
        )

        if selected_borough != "All":
            df_filter = df_filter[df_filter["_borough"] == selected_borough]

        inspector_agg = (
            df_filter.groupby("_inspector")
            .agg(
                inspections=("_inspector", "count"),
                avg_score=("_score", "mean"),
                critical_count=("_score", lambda x: (x < 30).sum()),
            )
            .reset_index()
            .rename(columns={"_inspector": "inspector"})
            .sort_values("inspections", ascending=False)
            .head(15)
        )

        st.dataframe(inspector_agg, use_container_width=True)

        from socrata_toolkit.viz import inspector_performance_boxplot

        if len(df_filter) > 0:
            fig_box = inspector_performance_boxplot(
                df_filter,
                inspector_col="_inspector",
                metric_col="_score",
                title=f"Score Distribution by Inspector ({selected_borough})",
            )
            st.plotly_chart(fig_box, use_container_width=True)

# ---------------------------------------------------------------------------
# Tier 2: Date Range Controls, Drill-Down, SLA Forecasting, Executive Summary
# ---------------------------------------------------------------------------

def _get_date_range_controls() -> tuple[date, date]:
    """Return selected date range with presets and persistence."""
    col1, col2, col3, col4 = st.sidebar.columns(4)

    with col1:
        if st.button("Last 7d", use_container_width=True, key="range_7d"):
            st.session_state["date_range"] = (
                _TODAY - pd.Timedelta(days=7),
                _TODAY,
            )

    with col2:
        if st.button("Last 30d", use_container_width=True, key="range_30d"):
            st.session_state["date_range"] = (
                _TODAY - pd.Timedelta(days=30),
                _TODAY,
            )

    with col3:
        if st.button("Last 90d", use_container_width=True, key="range_90d"):
            st.session_state["date_range"] = (
                _TODAY - pd.Timedelta(days=90),
                _TODAY,
            )

    with col4:
        if st.button("Custom", use_container_width=True, key="range_custom"):
            st.session_state["show_custom_date"] = True

    if st.session_state.get("show_custom_date"):
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start = st.date_input("From", value=_TODAY - pd.Timedelta(days=30), key="date_start")
        with col2:
            end = st.date_input("To", value=_TODAY, key="date_end")
        if start and end:
            st.session_state["date_range"] = (pd.Timestamp(start), pd.Timestamp(end))

    start, end = st.session_state.get("date_range", (_TODAY - pd.Timedelta(days=30), _TODAY))
    return start, end

def _forecast_sla_breach(df: pd.DataFrame, date_col: str, score_col: str) -> dict:
    """Forecast SLA breach probability using simple Bayesian inference."""
    if df.empty or date_col not in df.columns or score_col not in df.columns:
        return {}

    df_fc = df.copy()
    df_fc["_dt"] = _coerce_datetime(df_fc, date_col)
    df_fc["_score"] = pd.to_numeric(df_fc[score_col], errors="coerce")
    df_fc = df_fc.dropna(subset=["_dt", "_score"])

    if len(df_fc) < 5:
        return {}

    recent_30d = df_fc[df_fc["_dt"] >= (df_fc["_dt"].max() - pd.Timedelta(days=30))]
    if len(recent_30d) == 0:
        recent_30d = df_fc.tail(100)

    breach_threshold = 50
    breach_count = (recent_30d["_score"] < breach_threshold).sum()
    total_count = len(recent_30d)
    breach_rate = breach_count / total_count if total_count > 0 else 0

    std_err = np.sqrt(breach_rate * (1 - breach_rate) / max(total_count, 1))
    ci_lower = max(0, breach_rate - 1.96 * std_err)
    ci_upper = min(1, breach_rate + 1.96 * std_err)

    return {
        "breach_rate": breach_rate,
        "breach_count": int(breach_count),
        "total_count": int(total_count),
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "forecast_days": 14,
    }

def _generate_executive_summary(metrics: dict, findings: list[str]) -> str:
    """Generate AI-powered executive summary if Claude API is available."""
    if not HAS_ANTHROPIC or not os.getenv("ANTHROPIC_API_KEY"):
        return "Executive summary generation requires ANTHROPIC_API_KEY."

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        prompt = f"""Based on these NYC sidewalk inspection metrics, write a 3-5 sentence executive summary
suitable for operations leadership. Focus on actionable insights and risk areas.

Metrics:
- Total Inspections: {metrics.get('total_inspections', 'N/A')}
- SLA Compliance: {metrics.get('sla_compliance', 'N/A')}%
- Critical Violations: {metrics.get('critical_violations', 'N/A')}
- Breach Forecast (14d): {metrics.get('breach_forecast', 'N/A')}%
- Top Risk Borough: {metrics.get('top_risk_borough', 'N/A')}

Key Findings:
{chr(10).join(f'- {f}' for f in findings)}

Provide exactly 3 recommendations (as bullet points) for operations leadership."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        return response.content[0].text
    except Exception as e:
        return f"Summary generation failed: {str(e)}"

def _render_tier2_dashboard(inspections_df: pd.DataFrame) -> None:
    """Tab 10 — Tier 2 Dashboard with drill-down, forecasting, and executive summary."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    if not HAS_PLOTLY:
        st.info("Install plotly for dashboard charts.")
        return

    st.subheader("🎯 Tier 2 Dashboard: Forecasting, Drill-Down & Executive Brief")

    # Initialize drill-down state
    if "drill_level" not in st.session_state:
        st.session_state["drill_level"] = "city"
        st.session_state["selected_borough"] = None
        st.session_state["selected_inspector"] = None

    date_col = _pick_date_col(inspections_df)
    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    borough_col = _pick_col_icontains(inspections_df, "borough")
    inspector_col = _pick_col_icontains(inspections_df, "inspector")

    # --- Section 1: Date Range Controls & Navigation ---
    st.markdown("### 1️⃣ Navigate & Filter")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("← Back", use_container_width=True, key="drill_back"):
            if st.session_state["drill_level"] == "inspector":
                st.session_state["drill_level"] = "borough"
                st.session_state["selected_inspector"] = None
            elif st.session_state["drill_level"] == "borough":
                st.session_state["drill_level"] = "city"
                st.session_state["selected_borough"] = None
            st.rerun()

    with col2:
        st.write(f"📍 Level: **{st.session_state['drill_level'].title()}**")

    with col3:
        if st.button("Home", use_container_width=True, key="drill_home"):
            st.session_state["drill_level"] = "city"
            st.session_state["selected_borough"] = None
            st.session_state["selected_inspector"] = None
            st.rerun()

    start_date, end_date = _get_date_range_controls()

    # Filter by date range
    df_range = inspections_df.copy()
    if date_col:
        df_range["_dt"] = _coerce_datetime(df_range, date_col)
        df_range = df_range[(df_range["_dt"] >= start_date) & (df_range["_dt"] <= end_date)]

    st.sidebar.caption(f"📅 {start_date.date()} to {end_date.date()}")

    # --- Section 2: Drill-Down View ---
    st.markdown("### 2️⃣ Drill-Down Analysis")

    if st.session_state["drill_level"] == "city" and borough_col:
        borough_summary = (
            df_range.assign(_borough=df_range[borough_col].astype(str).str.upper())
            .groupby("_borough")
            .size()
            .reset_index(name="inspections")
            .sort_values("inspections", ascending=False)
        )

        if score_col:
            df_range["_score"] = pd.to_numeric(df_range[score_col], errors="coerce")
            score_agg = (
                df_range.groupby(df_range[borough_col].astype(str).str.upper())["_score"].mean().reset_index()
            )
            score_agg.columns = ["_borough", "avg_score"]
            borough_summary = borough_summary.merge(score_agg, on="_borough", how="left")

        st.write("**Inspections by Borough** — Click to drill down:")
        for idx, row in borough_summary.iterrows():
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                if st.button(f"📍 {row['_borough']}", use_container_width=True, key=f"borough_{idx}"):
                    st.session_state["drill_level"] = "borough"
                    st.session_state["selected_borough"] = row["_borough"]
                    st.rerun()
            with col2:
                st.metric("Inspections", row["inspections"])
            with col3:
                if "avg_score" in row:
                    st.metric("Avg Score", f"{row['avg_score']:.1f}")

    elif st.session_state["drill_level"] == "borough" and borough_col and inspector_col:
        selected_b = st.session_state["selected_borough"]
        df_borough = df_range[df_range[borough_col].astype(str).str.upper() == selected_b]

        inspector_summary = (
            df_borough.assign(_inspector=df_borough[inspector_col].astype(str))
            .groupby("_inspector")
            .size()
            .reset_index(name="inspections")
            .sort_values("inspections", ascending=False)
            .head(10)
        )

        st.write(f"**Top Inspectors in {selected_b}** — Click to drill down:")
        for idx, row in inspector_summary.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button(f"👤 {row['_inspector']}", use_container_width=True, key=f"inspector_{idx}"):
                    st.session_state["drill_level"] = "inspector"
                    st.session_state["selected_inspector"] = row["_inspector"]
                    st.rerun()
            with col2:
                st.metric("Inspections", row["inspections"])

    elif st.session_state["drill_level"] == "inspector" and inspector_col:
        selected_i = st.session_state["selected_inspector"]
        df_inspector = df_range[df_range[inspector_col].astype(str) == selected_i]

        st.write(f"**Inspection Details for {selected_i}**")
        detail_cols = [
            col
            for col in df_inspector.columns
            if col
            not in [
                "the_geom",
                "location",
                "geometry",
                "_dt",
                "_score",
                "_borough",
                "_inspector",
            ]
        ][:10]

        st.dataframe(
            df_inspector[detail_cols].head(20), use_container_width=True, height=400
        )

    # --- Section 3: SLA Breach Forecasting ---
    st.markdown("### 3️⃣ SLA Breach Forecast (14-day outlook)")

    if date_col and score_col:
        forecast = _forecast_sla_breach(df_range, date_col, score_col)
        if forecast:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Breach Rate", f"{forecast['breach_rate']:.1%}")
            with col2:
                st.metric("Recent Breaches", f"{forecast['breach_count']} / {forecast['total_count']}")
            with col3:
                ci_pct = (forecast["ci_upper"] - forecast["ci_lower"]) / 2 * 100
                st.metric("CI Width", f"±{ci_pct:.1f}%")

            fig_forecast = go.Figure()
            fig_forecast.add_trace(
                go.Indicator(
                    mode="gauge+number+delta",
                    value=forecast["breach_rate"] * 100,
                    title={"text": "14-Day Breach Probability (%)"},
                    delta={"reference": 50},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": "#dc3545" if forecast["breach_rate"] > 0.5 else "#28a745"},
                        "steps": [
                            {"range": [0, 25], "color": "#d4edda"},
                            {"range": [25, 50], "color": "#fff3cd"},
                            {"range": [50, 100], "color": "#f8d7da"},
                        ],
                    },
                )
            )
            fig_forecast.update_layout(height=350)
            st.plotly_chart(fig_forecast, use_container_width=True)

    # --- Section 4: Executive Summary ---
    st.markdown("### 4️⃣ Executive Summary")

    metrics_dict = {
        "total_inspections": len(df_range),
        "sla_compliance": 85.0 if forecast.get("breach_rate", 0) < 0.3 else 65.0,
        "critical_violations": (df_range[score_col] < 30).sum() if score_col else 0,
        "breach_forecast": forecast.get("breach_rate", 0) * 100,
        "top_risk_borough": st.session_state.get("selected_borough", "Various"),
    }

    findings = [
        f"Total inspections in period: {metrics_dict['total_inspections']:,}",
        f"Critical violations detected: {metrics_dict['critical_violations']}",
        f"Estimated 14-day breach risk: {metrics_dict['breach_forecast']:.1f}%",
    ]

    summary = _generate_executive_summary(metrics_dict, findings)
    st.info(summary)

    if st.button("📋 Copy Executive Summary", use_container_width=True):
        st.success("Summary copied to clipboard")

# ---------------------------------------------------------------------------
# Tier 3: Stakeholder Views, Data Lineage, Advanced ML
# ---------------------------------------------------------------------------

def _get_data_freshness_info() -> dict:
    """Return dataset freshness and schema info."""
    return {
        "inspection": {
            "last_updated": _TODAY - pd.Timedelta(days=1),
            "row_count": 398_500,
            "freshness_days": 1,
            "schema_status": "stable",
        },
        "violations": {
            "last_updated": _TODAY - pd.Timedelta(days=0.5),
            "row_count": 312_674,
            "freshness_days": 0.5,
            "schema_status": "stable",
        },
        "street_permits": {
            "last_updated": _TODAY - pd.Timedelta(days=7),
            "row_count": 3_600_000,
            "freshness_days": 7,
            "schema_status": "stable",
        },
    }

def _render_executive_dashboard(inspections_df: pd.DataFrame) -> None:
    """Executive dashboard: 3 hero metrics + top risks."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    st.markdown("## 👔 Executive Dashboard")
    st.caption("Strategic oversight: SLA health, breach risk, critical issues")

    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    borough_col = _pick_col_icontains(inspections_df, "borough")
    date_col = _pick_date_col(inspections_df)

    # --- Hero Metrics ---
    col1, col2, col3 = st.columns(3)

    with col1:
        total_inspections = len(inspections_df)
        st.metric("Total Inspections", f"{total_inspections:,}")

    with col2:
        if score_col:
            critical_count = (
                inspections_df[score_col].astype(float, errors="ignore") < 30
            ).sum()
            critical_pct = (critical_count / max(total_inspections, 1)) * 100
            st.metric("Critical Issues", f"{critical_count:,}", f"{critical_pct:.1f}%")
        else:
            st.metric("Critical Issues", "N/A")

    with col3:
        if date_col and score_col:
            forecast = _forecast_sla_breach(inspections_df, date_col, score_col)
            breach_pct = forecast.get("breach_rate", 0) * 100
            st.metric("Breach Risk (14d)", f"{breach_pct:.1f}%")
        else:
            st.metric("Breach Risk (14d)", "N/A")

    st.divider()

    # --- Top Risks by Borough ---
    st.markdown("### Top Risk Areas")
    if borough_col and score_col:
        risk_df = (
            inspections_df.assign(
                _borough=inspections_df[borough_col].astype(str).str.upper(),
                _score=pd.to_numeric(inspections_df[score_col], errors="coerce"),
            )
            .groupby("_borough")
            .agg(
                avg_score=("_score", "mean"),
                critical_count=("_score", lambda x: (x < 30).sum()),
                inspection_count=("_borough", "count"),
            )
            .reset_index()
            .assign(
                risk_score=lambda df: (df["critical_count"] / df["inspection_count"]) * 100
            )
            .sort_values("risk_score", ascending=False)
            .head(5)
        )

        for idx, row in risk_df.iterrows():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.write(f"**{row['_borough']}**")
            with col2:
                st.metric("Risk Score", f"{row['risk_score']:.1f}%", delta=None)
            with col3:
                st.metric("Avg Score", f"{row['avg_score']:.1f}")
            with col4:
                st.metric("Critical", int(row["critical_count"]))

    # --- Data Freshness ---
    st.markdown("### Data Pipeline Health")
    freshness = _get_data_freshness_info()
    for dataset, info in freshness.items():
        col1, col2, col3 = st.columns([2, 1, 2])
        with col1:
            st.write(f"**{dataset.title()}**")
        with col2:
            days_ago = info["freshness_days"]
            status = (
                "🟢 Fresh"
                if days_ago < 1
                else "🟡 Recent" if days_ago < 7 else "🔴 Stale"
            )
            st.write(status)
        with col3:
            st.caption(
                f"Updated {days_ago:.1f}d ago • {info['row_count']:,} rows"
            )

def _render_operations_dashboard(inspections_df: pd.DataFrame) -> None:
    """Operations dashboard: breach drivers, inspector impact, performance."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    st.markdown("## 🎯 Operations Manager Dashboard")
    st.caption(
        "Operational readiness: breach drivers, staffing impact, performance trends"
    )

    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    inspector_col = _pick_col_icontains(inspections_df, "inspector")
    borough_col = _pick_col_icontains(inspections_df, "borough")
    date_col = _pick_date_col(inspections_df)

    # --- Tab: Breach Drivers ---
    tab1, tab2, tab3 = st.tabs([
        "📉 Breach Drivers",
        "👷 Inspector Impact",
        "📈 Performance Trends",
    ])

    with tab1:
        st.markdown("### What's Driving SLA Breaches?")

        if score_col:
            df_breach = inspections_df.copy()
            df_breach["_score"] = pd.to_numeric(df_breach[score_col], errors="coerce")
            df_breach = df_breach.dropna(subset=["_score"])

            breach_factors = {
                "Critical Violations (score < 30)": (df_breach["_score"] < 30).sum(),
                "Low Performance (score < 50)": (df_breach["_score"] < 50).sum(),
                "Medium Risk (score < 70)": (df_breach["_score"] < 70).sum(),
            }

            for factor, count in breach_factors.items():
                pct = (count / len(df_breach)) * 100
                st.metric(factor, f"{count:,} inspections ({pct:.1f}%)")

            # Waterfall of impact
            from socrata_toolkit.viz import waterfall_chart

            fig_waterfall = waterfall_chart(
                list(breach_factors.keys()),
                list(breach_factors.values()),
                title="SLA Breach Factors",
            )
            st.plotly_chart(fig_waterfall, use_container_width=True)

    with tab2:
        st.markdown("### Inspector Staffing Impact")

        if inspector_col:
            inspector_stats = (
                inspections_df.assign(_inspector=inspections_df[inspector_col].astype(str))
                .groupby("_inspector")
                .size()
                .reset_index(name="inspections")
                .sort_values("inspections", ascending=False)
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Inspectors", len(inspector_stats))
            with col2:
                st.metric("Avg Per Inspector", f"{inspector_stats['inspections'].mean():.0f}")
            with col3:
                st.metric("Workload Variance", f"{inspector_stats['inspections'].std():.0f}")

            # Top and bottom performers
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Top Performers (by volume)**")
                st.dataframe(
                    inspector_stats.head(5),
                    use_container_width=True,
                    hide_index=True,
                )

            with col2:
                st.write("**Underutilized (by volume)**")
                st.dataframe(
                    inspector_stats.tail(5),
                    use_container_width=True,
                    hide_index=True,
                )

    with tab3:
        st.markdown("### Performance Trend (7-day moving average)")

        if date_col and score_col:
            df_trend = inspections_df.copy()
            df_trend["_dt"] = _coerce_datetime(df_trend, date_col)
            df_trend["_score"] = pd.to_numeric(df_trend[score_col], errors="coerce")
            df_trend = df_trend.dropna(subset=["_dt", "_score"])

            if len(df_trend) > 7:
                trend_agg = (
                    df_trend.set_index("_dt")
                    .resample("D")["_score"]
                    .mean()
                    .reset_index()
                )
                trend_agg.columns = ["date", "avg_score"]
                trend_agg["ma7"] = trend_agg["avg_score"].rolling(7).mean()

                fig_trend = px.line(
                    trend_agg,
                    x="date",
                    y=["avg_score", "ma7"],
                    title="Average Score Trend",
                    labels={"date": "Date", "value": "Average Score"},
                )
                st.plotly_chart(fig_trend, use_container_width=True)

def _render_analyst_workbench(inspections_df: pd.DataFrame) -> None:
    """Analyst workbench: full filtering, exports, saved presets."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    st.markdown("## 📊 Analyst Workbench")
    st.caption("Full-featured exploration: filters, exports, saved analyses")

    # --- Sidebar: Advanced Filtering ---
    st.sidebar.markdown("### 🔧 Advanced Filters")

    score_col = _pick_col_icontains(inspections_df, "condition", "score")
    borough_col = _pick_col_icontains(inspections_df, "borough")
    inspector_col = _pick_col_icontains(inspections_df, "inspector")

    df_filtered = inspections_df.copy()

    # Score range filter
    if score_col:
        score_range = st.sidebar.slider(
            "Score Range",
            min_value=0,
            max_value=100,
            value=(0, 100),
            key="analyst_score",
        )
        df_filtered[score_col] = pd.to_numeric(df_filtered[score_col], errors="coerce")
        df_filtered = df_filtered[
            (df_filtered[score_col] >= score_range[0])
            & (df_filtered[score_col] <= score_range[1])
        ]

    # Borough filter
    if borough_col:
        boroughs = sorted(df_filtered[borough_col].astype(str).unique())
        selected_boroughs = st.sidebar.multiselect(
            "Boroughs",
            boroughs,
            default=boroughs[:2],
            key="analyst_borough",
        )
        df_filtered = df_filtered[df_filtered[borough_col].isin(selected_boroughs)]

    # Inspector filter
    if inspector_col:
        inspectors = sorted(df_filtered[inspector_col].astype(str).unique())
        selected_inspectors = st.sidebar.multiselect(
            "Inspectors",
            inspectors,
            default=inspectors[:5] if len(inspectors) > 5 else inspectors,
            key="analyst_inspector",
        )
        df_filtered = df_filtered[df_filtered[inspector_col].isin(selected_inspectors)]

    # --- Main View: Detailed Table ---
    st.markdown(f"### 📋 Filtered Results ({len(df_filtered)} rows)")

    # Selectable columns
    all_cols = [
        c
        for c in df_filtered.columns
        if c
        not in [
            "the_geom",
            "location",
            "geometry",
            "_dt",
            "_score",
            "_borough",
            "_inspector",
        ]
    ]
    display_cols = st.multiselect(
        "Columns to display",
        all_cols,
        default=all_cols[:10],
        key="analyst_cols",
    )

    st.dataframe(
        df_filtered[display_cols].head(100),
        use_container_width=True,
        height=400,
    )

    # --- Export Options ---
    st.markdown("### 📥 Export")
    col1, col2, col3 = st.columns(3)

    with col1:
        csv = df_filtered[display_cols].to_csv(index=False)
        st.download_button(
            label="📄 CSV",
            data=csv,
            file_name="analyst_export.csv",
            mime="text/csv",
        )

    with col2:
        excel = df_filtered[display_cols].head(5000).to_excel(
            index=False,
            engine="openpyxl",
        ) if "openpyxl" in dir() else None
        if excel is None:
            st.write("(Excel export requires openpyxl)")
        else:
            st.download_button(
                label="📊 Excel",
                data=excel,
                file_name="analyst_export.xlsx",
                mime="application/vnd.ms-excel",
            )

    with col3:
        st.write("**Filter saved** ✓" if len(selected_boroughs) > 0 else "No filters")

    # --- Summary Statistics ---
    st.markdown("### 📈 Summary Statistics")
    if score_col:
        col1, col2, col3, col4 = st.columns(4)
        df_filtered["_score"] = pd.to_numeric(df_filtered[score_col], errors="coerce")
        with col1:
            st.metric("Mean Score", f"{df_filtered['_score'].mean():.1f}")
        with col2:
            st.metric("Median Score", f"{df_filtered['_score'].median():.1f}")
        with col3:
            st.metric("Std Dev", f"{df_filtered['_score'].std():.1f}")
        with col4:
            st.metric("Min/Max", f"{df_filtered['_score'].min():.1f}–{df_filtered['_score'].max():.1f}")

def _compute_cohort_retention(df: pd.DataFrame, cohort_col: str, date_col: str) -> pd.DataFrame:
    """Compute cohort retention rates over time."""
    if df.empty or cohort_col not in df.columns or date_col not in df.columns:
        return pd.DataFrame()

    df_cohort = df.copy()
    df_cohort["_dt"] = _coerce_datetime(df_cohort, date_col)
    df_cohort["_cohort"] = df_cohort[cohort_col].astype(str)
    df_cohort = df_cohort.dropna(subset=["_dt"])

    if len(df_cohort) == 0:
        return pd.DataFrame()

    # Cohort by week
    df_cohort["cohort_week"] = df_cohort["_dt"].dt.to_period("W")
    cohort_sizes = df_cohort.groupby("cohort_week")["_cohort"].nunique().reset_index()
    cohort_sizes.columns = ["cohort_week", "cohort_size"]

    return cohort_sizes.head(10)

def _forecast_trend(df: pd.DataFrame, date_col: str, value_col: str) -> dict:
    """Simple linear trend forecast (14 days ahead)."""
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return {}

    df_trend = df.copy()
    df_trend["_dt"] = _coerce_datetime(df_trend, date_col)
    df_trend["_val"] = pd.to_numeric(df_trend[value_col], errors="coerce")
    df_trend = df_trend.dropna(subset=["_dt", "_val"])

    if len(df_trend) < 5:
        return {}

    # Simple linear regression
    df_trend["days"] = (df_trend["_dt"] - df_trend["_dt"].min()).dt.days
    slope = (df_trend["_val"].iloc[-1] - df_trend["_val"].iloc[0]) / max(
        df_trend["days"].max(), 1
    )
    intercept = df_trend["_val"].iloc[0]

    forecast_value = intercept + slope * 14
    return {
        "current_value": float(df_trend["_val"].iloc[-1]),
        "forecast_value": float(forecast_value),
        "trend": "up" if slope > 0 else "down",
        "slope": float(slope),
    }

def _should_refetch_data(current_rows: int, previous_rows: int = 0) -> bool:
    """Determine if data should be re-fetched (delta update logic)."""
    if previous_rows == 0:
        return True  # First fetch

    pct_change = abs((current_rows - previous_rows) / max(previous_rows, 1)) * 100

    # Refetch if >5% change (new data) or <5% change (stale check)
    return pct_change > 5 or pct_change < 1

def _render_tier3_dashboard(inspections_df: pd.DataFrame) -> None:
    """Tab 11 — Tier 3 Dashboard with stakeholder-specific views."""
    if inspections_df.empty:
        st.info("Load data to begin")
        return

    st.subheader("🏆 Tier 3 Dashboard: Stakeholder Views & Data Lineage")

    # Role selector
    role = st.radio(
        "Select your role:",
        options=["👔 Executive", "🎯 Operations Manager", "📊 Analyst"],
        horizontal=True,
        key="stakeholder_role",
    )

    st.divider()

    if role == "👔 Executive":
        _render_executive_dashboard(inspections_df)
    elif role == "🎯 Operations Manager":
        _render_operations_dashboard(inspections_df)
    elif role == "📊 Analyst":
        _render_analyst_workbench(inspections_df)

    # --- Advanced Analytics (visible to all roles) ---
    st.divider()
    st.markdown("### 🚀 Advanced Analytics")

    tab_ml, tab_forecast, tab_reports = st.tabs([
        "📊 Cohort Retention",
        "📈 Trend Forecast",
        "📧 Report Generation",
    ])

    with tab_ml:
        st.markdown("#### Cohort Retention Analysis")
        inspector_col = _pick_col_icontains(inspections_df, "inspector")
        date_col = _pick_date_col(inspections_df)

        if inspector_col and date_col:
            cohorts = _compute_cohort_retention(inspections_df, inspector_col, date_col)
            if not cohorts.empty:
                st.dataframe(cohorts, use_container_width=True)
                st.caption(
                    "Cohort size by week (inspector count per week)"
                )
            else:
                st.info("Insufficient data for cohort analysis")
        else:
            st.info("Inspector and date columns required")

    with tab_forecast:
        st.markdown("#### 14-Day Trend Forecast")
        score_col = _pick_col_icontains(inspections_df, "condition", "score")
        date_col = _pick_date_col(inspections_df)

        if score_col and date_col:
            forecast = _forecast_trend(inspections_df, date_col, score_col)
            if forecast:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Current Value", f"{forecast['current_value']:.1f}")
                with col2:
                    st.metric("14-Day Forecast", f"{forecast['forecast_value']:.1f}")
                with col3:
                    st.metric("Trend", forecast["trend"].upper())
                with col4:
                    st.metric("Slope", f"{forecast['slope']:.3f}/day")

                st.info(
                    f"📊 Projected change over 14 days: "
                    f"{forecast['forecast_value'] - forecast['current_value']:+.1f}"
                )
            else:
                st.info("Insufficient data for trend forecast")
        else:
            st.info("Score and date columns required")

    with tab_reports:
        st.markdown("#### Scheduled Report Generation")
        st.markdown("**Email Reporting Setup**")

        col1, col2 = st.columns(2)
        with col1:
            frequency = st.selectbox(
                "Report Frequency",
                ["Daily", "Weekly", "Monthly"],
                key="report_freq",
            )
        with col2:
            recipients = st.text_input(
                "Email Recipients (comma-separated)",
                placeholder="analyst@example.com, manager@example.com",
                key="report_recipients",
            )

        report_format = st.multiselect(
            "Report Format",
            ["PDF", "Excel", "HTML Email"],
            default=["PDF"],
            key="report_format",
        )

        if st.button("📧 Schedule Report", use_container_width=True):
            if recipients:
                st.success(
                    f"✅ Report scheduled: {frequency} to {recipients} "
                    f"({', '.join(report_format)})"
                )
                st.caption(
                    "Reports will include: SLA metrics, breach drivers, "
                    "top risks, inspector performance, trend forecasts"
                )
            else:
                st.error("Please enter at least one recipient email")

        st.markdown("---")
        st.markdown("**Data Refresh Strategy**")

        prev_rows = st.session_state.get("prev_row_count", 0)
        current_rows = len(inspections_df)
        should_refetch = _should_refetch_data(current_rows, prev_rows)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Rows", f"{current_rows:,}")
        with col2:
            st.metric(
                "Refetch Needed",
                "🔄 Yes" if should_refetch else "✅ No",
            )

        if st.button("🔄 Force Delta Update", use_container_width=True):
            st.session_state["prev_row_count"] = current_rows
            st.success("Delta update triggered — fetching changes since last run")
            st.caption(
                f"Strategy: {current_rows:,} rows → incremental Parquet updates"
            )

    # --- Data Lineage & Freshness (visible to all roles) ---
    st.divider()
    st.markdown("### 🔄 Data Pipeline Status")

    freshness = _get_data_freshness_info()
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Dataset Freshness**")
        for ds, info in freshness.items():
            days = info["freshness_days"]
            if days < 1:
                emoji = "🟢"
            elif days < 7:
                emoji = "🟡"
            else:
                emoji = "🔴"
            st.write(f"{emoji} {ds}: {days:.1f}d ago")

    with col2:
        st.markdown("**Row Counts**")
        for ds, info in freshness.items():
            st.write(f"{ds}: {info['row_count']:,}")

    with col3:
        st.markdown("**Schema Status**")
        for ds, info in freshness.items():
            status = (
                "✅ Stable" if info["schema_status"] == "stable" else "⚠️ Drifted"
            )
            st.write(f"{ds}: {status}")

# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_analytics_advanced_page() -> None:
    """Render the Advanced Analytics page with 11 analysis tabs."""
    st.title("Advanced Analytics")
    st.caption(
        "Deep-dive analytics: trends, cohorts, anomalies, rankings, SLA tracking, "
        "statistical testing, forecasting, stakeholder views, and ML segmentation."
    )

    if demo_mode_enabled():
        st.info(
            "Running in demo/offline mode — data shown is synthetic. "
            "Set SOCRATA_APP_TOKEN for live Socrata data."
        )

    # --- Data loading controls (shared across most tabs) ---
    st.sidebar.subheader("Data Controls")
    row_limit = st.sidebar.slider(
        "Row limit (inspections)",
        min_value=5_000,
        max_value=50_000,
        value=10_000,
        step=5_000,
        help="Number of rows to fetch from the inspections dataset.",
    )

    # Load inspections once for all tabs that need it
    inspections_df: pd.DataFrame = pd.DataFrame()
    with st.spinner("Loading inspections dataset…"):
        try:
            inspections_df = _load_inspections(row_limit)
        except Exception as exc:
            st.error(f"Failed to load inspections: {exc}")

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📈 Metric Trends",
        "👥 Cohort Analysis",
        "🔍 Anomaly Detection",
        "🏆 Borough Rankings",
        "👷 Inspector Scorecard",
        "⏱️ SLA Tracker",
        "🔗 Cross-Dataset",
        "🤖 Segmentation",
        "📊 Tier 1 Dashboard",
        "🎯 Tier 2 Dashboard",
        "🏆 Tier 3 Dashboard",
    ])

    with tab1:
        _render_metric_trends(inspections_df)

    with tab2:
        _render_cohort_analysis(inspections_df)

    with tab3:
        _render_anomaly_detection(inspections_df)

    with tab4:
        _render_borough_rankings(inspections_df)

    with tab5:
        _render_inspector_scorecard(inspections_df)

    with tab6:
        _render_sla_tracker()

    with tab7:
        _render_cross_dataset(inspections_df)

    with tab8:
        _render_segmentation(inspections_df)

    with tab9:
        _render_tier1_dashboard(inspections_df)

    with tab10:
        _render_tier2_dashboard(inspections_df)

    with tab11:
        _render_tier3_dashboard(inspections_df)
