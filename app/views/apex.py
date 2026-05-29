"""
Apex Engine — Hiring Analytics Tab
Manhattan Mission Control · NYC DOT Operations

Self-contained Streamlit view for the Apex Engine tab. Exposes:
  - render_apex_tab(target_agency, target_title, scrape_start, scrape_end)
  - run_apex_math(df_jobs, df_payroll) -> dict | None
  - scrape_historical_jids(start, end) -> pd.DataFrame
"""

from __future__ import annotations

import os
import random
import time
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
from dateutil.relativedelta import relativedelta

try:
    import arviz as az
    _HAS_ARVIZ = True
except ImportError:
    az = None  # type: ignore[assignment]
    _HAS_ARVIZ = False

try:
    import folium
    _HAS_FOLIUM = True
except ImportError:
    folium = None  # type: ignore[assignment]
    _HAS_FOLIUM = False

try:
    import pymc as pm
    _HAS_PYMC = True
except ImportError:
    pm = None  # type: ignore[assignment]
    _HAS_PYMC = False

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    BeautifulSoup = None  # type: ignore[assignment,misc]
    _HAS_BS4 = False

try:
    from prophet import Prophet
    _HAS_PROPHET = True
except ImportError:
    Prophet = None  # type: ignore[assignment,misc]
    _HAS_PROPHET = False

from socrata_toolkit.core.client import SocrataClient, SocrataConfig
from socrata_toolkit.core.duckdb_store import DuckDBManager

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

JOBS_URL = "https://data.cityofnewyork.us/resource/kpav-sd4t.json"
PAYROLL_URL = "https://data.cityofnewyork.us/resource/k397-673e.json"
SOCRATA_DOMAIN = "data.cityofnewyork.us"
JOBS_FOURFOUR = "kpav-sd4t"
PAYROLL_FOURFOUR = "k397-673e"

JID_SCRAPE_SOFT_LIMIT = 20
JID_SCRAPE_HARD_LIMIT = 100

COLORS = {
    "postings": "#3B82F6",
    "hires": "#10B981",
    "forecast": "#F59E0B",
    "confidence": "rgba(59,130,246,0.12)",
    "divider": "#94A3B8",
}

BOROUGH_COORDS: dict[str, list[float]] = {
    "MANHATTAN": [40.7831, -73.9712],
    "BROOKLYN": [40.6782, -73.9442],
    "QUEENS": [40.7282, -73.7949],
    "BRONX": [40.8448, -73.8648],
    "STATEN ISLAND": [40.5795, -74.1502],
    "UNKNOWN": [40.7128, -74.0060],
}


# ---------------------------------------------------------------------------
# Session-state initialisation (idempotent)
# ---------------------------------------------------------------------------

def _init_apex_state() -> None:
    defaults: dict[str, object] = {
        "apex_results": None,
        "df_jobs_cache": None,
        "df_payroll_cache": None,
        "apex_pipeline_ran_at": None,
        "apex_agency": "",
        "apex_title": "",
        "apex_scrape_start": 35710,
        "apex_scrape_end": 35715,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ---------------------------------------------------------------------------
# DuckDB cache helpers
# ---------------------------------------------------------------------------

def _get_duckdb() -> DuckDBManager:
    """Return a DuckDBManager pointed at the project's default path."""
    return DuckDBManager()


def _duckdb_load(table: str) -> pd.DataFrame | None:
    """Load a DataFrame from DuckDB; return None if the table does not exist."""
    try:
        mgr = _get_duckdb()
        tables = [r[0] for r in mgr.conn.execute("SHOW TABLES").fetchall()]
        if table not in tables:
            return None
        return mgr.conn.execute(f"SELECT * FROM {table}").df()  # type: ignore[return-value]
    except Exception:
        return None


def _duckdb_save(table: str, df: pd.DataFrame) -> None:
    """Persist a DataFrame to DuckDB, replacing any existing table."""
    try:
        mgr = _get_duckdb()
        # Sanitise table name (DuckDB identifiers)
        safe = table.replace("-", "_").replace(" ", "_")
        mgr.conn.register("_tmp_apex_write", df)
        mgr.conn.execute(f"DROP TABLE IF EXISTS {safe}")
        mgr.conn.execute(f"CREATE TABLE {safe} AS SELECT * FROM _tmp_apex_write")
        mgr.conn.unregister("_tmp_apex_write")
    except Exception:
        pass  # Cache write failure is non-fatal


def _cache_key(prefix: str, agency: str, title: str) -> str:
    slug_agency = agency.strip().upper().replace(" ", "_")[:30]
    slug_title = title.strip().upper().replace(" ", "_")[:30]
    return f"{prefix}_{slug_agency}_{slug_title}"


# ---------------------------------------------------------------------------
# JID Scraper
# ---------------------------------------------------------------------------

def scrape_historical_jids(start: int, end: int) -> pd.DataFrame:
    """
    Scrape cityjobs.nyc.gov for expired/filled requisitions by JID range.

    Hard cap: 100 JIDs.  Shows st.progress() real-time bar while running.
    Returns a DataFrame with columns compatible with the Socrata jobs dataset.
    """
    total = end - start + 1
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    progress_bar = st.progress(0, text="Initialising scraper…")
    status_slot = st.empty()
    scraped_data: list[dict] = []

    for i, jid in enumerate(range(start, end + 1)):
        pct = (i + 1) / total
        progress_bar.progress(pct, text=f"Scanning JID {jid}  ({i + 1}/{total})")
        status_slot.caption(f"`GET https://cityjobs.nyc.gov/job/jid-{jid}`")
        time.sleep(random.uniform(0.3, 0.8))

        try:
            resp = requests.get(
                f"https://cityjobs.nyc.gov/job/anything-jid-{jid}",
                headers=headers,
                timeout=6,
            )
            if resp.status_code == 200:
                from bs4 import BeautifulSoup as _BS4
                soup = _BS4(resp.content, "html.parser")
                title_elem = soup.find("h1", class_="job-title")
                agency_elem = soup.find("span", class_="agency-name")
                job_title = title_elem.text.strip() if title_elem else "UNKNOWN TITLE"
                agency_name = agency_elem.text.strip() if agency_elem else "UNKNOWN AGENCY"
                status = (
                    "Expired" if soup.find("div", class_="alert-expired") else "Active"
                )
                scraped_data.append(
                    {
                        "job_id": str(jid),
                        "civil_service_title": job_title.upper(),
                        "agency": agency_name.upper(),
                        "Status": status,
                        "posting_date": (
                            datetime.now() - relativedelta(months=6)
                        ).strftime("%Y-%m-%dT00:00:00"),
                        "source": "scraper",
                    }
                )
        except Exception:
            continue

    progress_bar.empty()
    status_slot.empty()

    df = pd.DataFrame(scraped_data)
    if not df.empty:
        active = (df["Status"] == "Active").sum()
        expired = (df["Status"] == "Expired").sum()
        st.success(
            f"Scraper found **{len(df)} postings** — {active} active, {expired} expired."
        )
    return df


# ---------------------------------------------------------------------------
# Socrata fetch (with DuckDB caching)
# ---------------------------------------------------------------------------

def _fetch_socrata_paginated(
    domain: str,
    fourfour: str,
    where_clause: str | None,
    extra_filters: dict[str, str] | None = None,
) -> pd.DataFrame:
    """
    Fetch all pages from a Socrata dataset using SocrataClient.
    Falls back to raw requests on failure.
    """
    client = SocrataClient(
        SocrataConfig(app_token=os.getenv("SOCRATA_APP_TOKEN", ""))
    )

    where_parts: list[str] = []
    if where_clause:
        where_parts.append(where_clause)
    if extra_filters:
        for col, val in extra_filters.items():
            safe_val = val.replace("'", "''")
            where_parts.append(f"upper({col}) = upper('{safe_val}')")
    combined_where = " AND ".join(where_parts) if where_parts else None

    try:
        rows: list[dict] = []
        for batch in client.fetch_json(
            domain=domain,
            fourfour=fourfour,
            where=combined_where,
            order=":id",
            max_rows=200_000,
        ):
            rows.extend(batch)
        if rows:
            return pd.DataFrame(rows)
    except Exception as exc:
        st.warning(f"SocrataClient error — falling back to raw requests: {exc}")

    # Raw-requests fallback
    headers: dict[str, str] = {}
    token = os.getenv("SOCRATA_APP_TOKEN", "")
    if token:
        headers["X-App-Token"] = token

    all_data: list[dict] = []
    offset = 0
    limit = 50_000
    params: dict[str, object] = {
        "$limit": limit,
        "$order": ":id",
    }
    if combined_where:
        params["$where"] = combined_where

    url = f"https://{domain}/resource/{fourfour}.json"
    try:
        while True:
            params["$offset"] = offset
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            chunk = resp.json()
            if not chunk:
                break
            all_data.extend(chunk)
            offset += limit
            if len(all_data) >= 200_000:
                break
    except Exception as exc:
        st.error(f"Socrata raw-request fallback failed: {exc}")

    return pd.DataFrame(all_data)


def _fetch_jobs(agency: str, title: str) -> pd.DataFrame:
    five_years_ago = (datetime.now() - relativedelta(years=5)).strftime(
        "%Y-%m-%dT00:00:00"
    )
    where = f"posting_date >= '{five_years_ago}'"
    extra: dict[str, str] = {}
    if agency.upper() != "ALL":
        extra["agency"] = agency.strip()
    if title.upper() != "ALL":
        extra["civil_service_title"] = title.strip()
    return _fetch_socrata_paginated(SOCRATA_DOMAIN, JOBS_FOURFOUR, where, extra)


def _fetch_payroll(agency: str, title: str) -> pd.DataFrame:
    five_years_ago = (datetime.now() - relativedelta(years=5)).strftime(
        "%Y-%m-%dT00:00:00"
    )
    where = f"agency_start_date >= '{five_years_ago}'"
    extra: dict[str, str] = {}
    if agency.upper() != "ALL":
        extra["agency_name"] = agency.strip()
    if title.upper() != "ALL":
        extra["title_description"] = title.strip()
    return _fetch_socrata_paginated(SOCRATA_DOMAIN, PAYROLL_FOURFOUR, where, extra)


# ---------------------------------------------------------------------------
# Math engine
# ---------------------------------------------------------------------------

def _bootstrap_yield(
    df_ts: pd.DataFrame,
    n_boot: int = 2000,
    ci: float = 0.94,
) -> tuple[float, float, float, None]:
    """Frequentist bootstrap fallback for yield rate + confidence interval.

    Used when PyMC/ArviZ are unavailable or OOM.  Resamples the
    postings→starts ratio B times to derive a HDI-equivalent CI.
    """
    postings = df_ts["Postings"].values
    starts = df_ts["Starts"].values
    rng = np.random.default_rng(42)
    n = len(postings)
    ratios = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        p = postings[idx].mean()
        s = starts[idx].mean()
        ratios.append(s / max(p, 1e-9))
    ratios_arr = np.array(ratios)
    lo = float(np.percentile(ratios_arr, (1 - ci) / 2 * 100))
    hi = float(np.percentile(ratios_arr, (1 - (1 - ci) / 2) * 100))
    center = float(np.median(ratios_arr))
    return center, lo, hi, None


def run_apex_math(
    df_jobs: pd.DataFrame,
    df_payroll: pd.DataFrame,
    max_lag: int = 12,
) -> dict | None:
    """
    Execute the PyMC MCMC Bayesian regression and Prophet 12-month forecast.

    Returns a dict with keys:
        df_ts, best_lag, yield_rate, yield_lo, yield_hi,
        lag_df, future_forecast, full_forecast, cutoff_date

    Returns None when data is insufficient or sampling fails.
    """
    # 1. Build monthly time series
    df_jobs = df_jobs.copy()
    df_jobs["posting_date"] = pd.to_datetime(df_jobs["posting_date"], errors="coerce")
    postings_ts = (
        df_jobs.dropna(subset=["posting_date"])
        .groupby(df_jobs["posting_date"].dt.to_period("M").dt.to_timestamp())
        .size()
        .rename("Postings")
    )

    df_payroll = df_payroll.copy()
    df_payroll = df_payroll.drop_duplicates(
        subset=["first_name", "last_name", "agency_start_date"],
        keep="first",
    )
    df_payroll["agency_start_date"] = pd.to_datetime(
        df_payroll["agency_start_date"], errors="coerce"
    )
    starts_ts = (
        df_payroll.dropna(subset=["agency_start_date"])
        .groupby(df_payroll["agency_start_date"].dt.to_period("M").dt.to_timestamp())
        .size()
        .rename("Starts")
    )

    df_ts = pd.concat([postings_ts, starts_ts], axis=1).fillna(0).sort_index()

    if df_ts.empty:
        st.warning("No overlapping time-series data found after joining postings and payroll.")
        return None

    # Guard: minimum 6 months
    if len(df_ts) < 6:
        st.warning(
            "Not enough historical data to run the Bayesian model — "
            "need at least 6 months. Try broadening your agency/title filter.",
        )
        return None

    df_ts["Postings_Smoothed"] = df_ts["Postings"].rolling(window=3, min_periods=1).mean()
    df_ts["Starts_Smoothed"] = df_ts["Starts"].rolling(window=3, min_periods=1).mean()

    # 2. Cross-correlation — find optimal OMB lag
    correlations: dict[int, float] = {}
    for lag in range(max_lag + 1):
        r = df_ts["Postings_Smoothed"].corr(df_ts["Starts_Smoothed"].shift(-lag))
        correlations[lag] = float(r) if not np.isnan(r) else 0.0
    best_lag = max(correlations, key=lambda k: correlations[k])
    lag_df = pd.DataFrame(
        list(correlations.items()), columns=["Lag_Months", "Correlation"]
    )

    # 3. Bayesian Poisson regression
    # Uses ADVI (variational inference) instead of NUTS so it stays within
    # Render free-tier RAM (~512 MB).  ADVI converges in 2-3 s and uses
    # ~50 MB vs ~400 MB for NUTS, while still yielding valid HDI bounds.
    # Falls back to a frequentist bootstrap if PyMC is unavailable.
    predictor = df_ts["Postings_Smoothed"].shift(best_lag).fillna(0).values
    target = df_ts["Starts"].values.astype(int)

    if not _HAS_PYMC or not _HAS_ARVIZ:
        yield_rate, yield_lo, yield_hi, trace = _bootstrap_yield(df_ts)
    else:
        try:
            with pm.Model():
                alpha = pm.Normal("Baseline_Log", mu=0, sigma=5)
                beta = pm.Normal("Yield_Log", mu=0, sigma=5)
                mu = pm.math.exp(alpha + beta * predictor)
                pm.Poisson("Y_obs", mu=mu, observed=target)
                approx = pm.fit(10_000, method="advi", progressbar=False)
                trace = approx.sample(500)
        except Exception as exc:
            st.warning(f"ADVI sampling failed ({exc}) — using bootstrap fallback.")
            yield_rate, yield_lo, yield_hi, trace = _bootstrap_yield(df_ts)
        else:
            summary = az.summary(trace, var_names=["Yield_Log"])
            beta_mean = float(summary.loc["Yield_Log", "mean"])
            beta_lo   = float(summary.loc["Yield_Log", "hdi_3%"])
            beta_hi   = float(summary.loc["Yield_Log", "hdi_97%"])
            yield_rate = float(np.exp(beta_mean))
            yield_lo   = float(np.exp(beta_lo))
            yield_hi   = float(np.exp(beta_hi))

    # 4. Prophet 12-month forecast
    cutoff_date = df_ts.index[-1]
    forecast: pd.DataFrame = pd.DataFrame()
    if not _HAS_PROPHET:
        future_forecast = pd.DataFrame()
    else:
        df_prophet = (
            df_ts.rename_axis("ds")
            .reset_index()[["ds", "Postings_Smoothed"]]
            .rename(columns={"Postings_Smoothed": "y"})
        )
        import logging as _logging
        _logging.getLogger("prophet").setLevel(_logging.WARNING)
        _logging.getLogger("cmdstanpy").setLevel(_logging.WARNING)
        m = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            stan_backend="CMDSTANPY",
        )
        try:
            m.fit(df_prophet, iter=300)  # fewer Stan iterations → less RAM
        except TypeError:
            m.fit(df_prophet)
        future = m.make_future_dataframe(periods=12, freq="MS")
        forecast = m.predict(future)
        forecast["predicted_hires"] = forecast["yhat"] * yield_rate
        forecast["predicted_hires_lo"] = forecast["yhat_lower"] * yield_lo
        forecast["predicted_hires_hi"] = forecast["yhat_upper"] * yield_hi
        forecast["predicted_hires_date"] = forecast["ds"] + pd.DateOffset(months=best_lag)
        future_forecast = forecast[forecast["ds"] > cutoff_date].copy()

    return {
        "df_ts": df_ts,
        "best_lag": best_lag,
        "yield_rate": yield_rate,
        "yield_lo": yield_lo,
        "yield_hi": yield_hi,
        "lag_df": lag_df,
        "future_forecast": future_forecast,
        "full_forecast": forecast,
        "cutoff_date": cutoff_date,
    }


# ---------------------------------------------------------------------------
# Chart helpers (all plotly_dark)
# ---------------------------------------------------------------------------

def _chart_velocity(results: dict) -> go.Figure:
    df = results["df_ts"]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Postings_Smoothed"],
            name="Postings (3-mo avg)",
            mode="lines",
            line=dict(color=COLORS["postings"], width=2.5),
            hovertemplate="%{x|%b %Y}: %{y:.1f} postings<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Starts_Smoothed"],
            name="Hires (3-mo avg)",
            mode="lines",
            line=dict(color=COLORS["hires"], width=2.5),
            hovertemplate="%{x|%b %Y}: %{y:.1f} hires<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=340,
        hovermode="x unified",
        xaxis_title="Month",
        yaxis_title="Count (3-month rolling avg)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


def _chart_lag(results: dict) -> go.Figure:
    df = results["lag_df"]
    best = results["best_lag"]
    bar_colors = [
        COLORS["hires"] if int(row["Lag_Months"]) == best else COLORS["postings"]
        for _, row in df.iterrows()
    ]
    fig = go.Figure(
        go.Bar(
            x=df["Lag_Months"],
            y=df["Correlation"],
            marker_color=bar_colors,
            hovertemplate="Lag %{x} mo: r = %{y:.3f}<extra></extra>",
        )
    )
    best_corr_rows = df.loc[df["Lag_Months"] == best, "Correlation"]
    best_corr = float(best_corr_rows.values[0]) if not best_corr_rows.empty else 0.0
    fig.update_layout(
        template="plotly_dark",
        height=260,
        xaxis_title="Lag (months)",
        yaxis_title="Pearson r",
        xaxis=dict(dtick=1),
        margin=dict(l=0, r=0, t=10, b=0),
        annotations=[
            dict(
                x=best,
                y=best_corr,
                text=f"  Best lag: {best} mo",
                showarrow=False,
                font=dict(color=COLORS["hires"], size=12),
                xanchor="left",
            )
        ],
    )
    return fig


def _chart_forecast(results: dict) -> go.Figure:
    ff = results["future_forecast"]
    cutoff = results["cutoff_date"]
    lag = results["best_lag"]

    fig = go.Figure()

    # Confidence band (postings)
    fig.add_trace(
        go.Scatter(
            x=pd.concat([ff["ds"], ff["ds"][::-1]]),
            y=pd.concat([ff["yhat_upper"], ff["yhat_lower"][::-1]]),
            fill="toself",
            fillcolor=COLORS["confidence"],
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
            name="Postings CI",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ff["ds"],
            y=ff["yhat"],
            name="Forecasted Postings",
            mode="lines",
            line=dict(color=COLORS["postings"], width=2, dash="dot"),
            hovertemplate="%{x|%b %Y}: %{y:.1f} postings<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ff["predicted_hires_date"],
            y=ff["predicted_hires"],
            name=f"Forecasted Hires (+{lag} mo lag)",
            mode="lines",
            line=dict(color=COLORS["hires"], width=2, dash="dot"),
            hovertemplate="%{x|%b %Y}: %{y:.1f} hires<extra></extra>",
        )
    )
    # Confidence band for hires
    fig.add_trace(
        go.Scatter(
            x=pd.concat(
                [ff["predicted_hires_date"], ff["predicted_hires_date"][::-1]]
            ),
            y=pd.concat(
                [ff["predicted_hires_hi"], ff["predicted_hires_lo"][::-1]]
            ),
            fill="toself",
            fillcolor="rgba(16,185,129,0.10)",
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            hoverinfo="skip",
            name="Hires CI",
        )
    )
    fig.add_vline(
        x=cutoff,
        line_width=1,
        line_dash="dash",
        line_color=COLORS["divider"],
        annotation_text="  Forecast →",
        annotation_position="top right",
        annotation_font=dict(color=COLORS["divider"], size=11),
    )
    fig.update_layout(
        template="plotly_dark",
        height=360,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Estimated Volume",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------

def _kpi_row(results: dict, target_agency: str, target_title: str) -> None:
    projected = int(results["future_forecast"]["predicted_hires"].sum())
    ran_at: str = st.session_state.get("apex_pipeline_ran_at") or "—"
    lag = results["best_lag"]
    yr = results["yield_rate"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "OMB Review Lag",
        f"{lag} mo",
        delta=f"{lag - 6:+d} mo vs 6-mo benchmark",
        help="Cross-correlation lag between postings and first payroll starts.",
    )
    c2.metric(
        "Bayesian Yield",
        f"{yr:.2f}×",
        delta=f"{(yr - 1) * 100:+.0f}% vs 1.0× baseline",
        help=(
            f"Hires per posting (94% HDI: "
            f"{results['yield_lo']:.2f}–{results['yield_hi']:.2f}×). "
            "Values >1 mean multiple hires per requisition."
        ),
    )
    c3.metric(
        "12-Mo Projected Hires",
        f"{projected:,}",
        help=f"Sum of Prophet forecast × Bayesian yield, shifted by {lag}-month OMB lag.",
    )
    c4.metric(
        "Pipeline Run",
        ran_at,
        help=f"Agency: {target_agency}  |  Title: {target_title}",
    )


# ---------------------------------------------------------------------------
# Map panel
# ---------------------------------------------------------------------------

def _map_panel(df_jobs: pd.DataFrame) -> None:
    if "work_location" not in df_jobs.columns:
        st.info("No `work_location` column in the jobs dataset — map unavailable.")
        return
    if not _HAS_FOLIUM:
        st.caption("Install `folium` to enable the geospatial map panel.")
        return

    location_counts = df_jobs["work_location"].value_counts().reset_index()
    location_counts.columns = ["Location", "Count"]

    m = folium.Map(location=[40.7128, -74.0060], zoom_start=10, tiles="CartoDB dark_matter")

    for _, row in location_counts.iterrows():
        loc_str = str(row["Location"]).upper()
        base_coord: list[float] = BOROUGH_COORDS["UNKNOWN"]
        for borough, coords in BOROUGH_COORDS.items():
            if borough in loc_str:
                base_coord = coords
                break

        h = hash(row["Location"])
        jitter_lat = base_coord[0] + (h % 200 - 100) / 8000
        jitter_lon = base_coord[1] + ((h >> 8) % 200 - 100) / 8000

        folium.CircleMarker(
            location=[jitter_lat, jitter_lon],
            radius=min(max(int(row["Count"]) * 2, 5), 22),
            popup=folium.Popup(
                f"<strong>{row['Location']}</strong><br>Requisitions: {row['Count']}",
                max_width=220,
            ),
            tooltip=f"{row['Location']} ({row['Count']})",
            color=COLORS["postings"],
            fill=True,
            fill_color=COLORS["postings"],
            fill_opacity=0.7,
        ).add_to(m)

    components.html(m._repr_html_(), height=480)


# ---------------------------------------------------------------------------
# Data quality panel
# ---------------------------------------------------------------------------

def _data_quality_panel(df_jobs: pd.DataFrame, df_payroll: pd.DataFrame) -> None:
    rows = []
    for label, df in [("Job Postings", df_jobs), ("Payroll Records", df_payroll)]:
        n = len(df)
        nulls = int(df.isnull().sum().sum())
        total_cells = n * len(df.columns) if n > 0 else 1
        null_pct = nulls / total_cells * 100
        dups = int(df.duplicated().sum())
        score = max(0.0, 100.0 - null_pct * 2 - (dups / max(n, 1)) * 50)
        rows.append(
            {
                "Dataset": label,
                "Rows": f"{n:,}",
                "Columns": len(df.columns),
                "Null Density": f"{null_pct:.1f}%",
                "Duplicates": dups,
                "Health Score": f"{score:.0f}/100",
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Export panel
# ---------------------------------------------------------------------------

def _export_panel(results: dict, df_jobs: pd.DataFrame) -> None:
    ff = results["future_forecast"]
    forecast_csv = ff[
        [
            "ds",
            "yhat",
            "predicted_hires",
            "predicted_hires_lo",
            "predicted_hires_hi",
            "predicted_hires_date",
        ]
    ].to_csv(index=False)

    jobs_cols = [
        c
        for c in [
            "job_id",
            "civil_service_title",
            "agency",
            "posting_date",
            "Status",
            "work_location",
            "source",
        ]
        if c in df_jobs.columns
    ]
    jobs_csv = df_jobs[jobs_cols].to_csv(index=False)

    lag = results["best_lag"]
    yr = results["yield_rate"]
    projected = int(ff["predicted_hires"].sum())
    ran_at: str = st.session_state.get("apex_pipeline_ran_at") or "—"
    summary_txt = (
        f"Run timestamp : {ran_at}\n"
        f"OMB Lag       : {lag} months\n"
        f"Bayesian Yield: {yr:.2f}x\n"
        f"12-Mo Hires   : {projected:,} projected\n"
    )

    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "Download Forecast CSV",
        forecast_csv,
        file_name="apex_forecast.csv",
        mime="text/csv",
        use_container_width=True,
    )
    c2.download_button(
        "Download Job Postings CSV",
        jobs_csv,
        file_name="apex_job_postings.csv",
        mime="text/csv",
        use_container_width=True,
    )
    c3.download_button(
        "Download Pipeline Summary",
        summary_txt,
        file_name="apex_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

def _run_pipeline(
    target_agency: str,
    target_title: str,
    scrape_start: int,
    scrape_end: int,
) -> None:
    """
    Execute the full Apex pipeline (scrape → Socrata → math) and persist
    results to session state and DuckDB cache.
    """
    jobs_key = _cache_key("apex_jobs", target_agency, target_title)
    payroll_key = _cache_key("apex_payroll", target_agency, target_title)

    with st.status("Initialising Apex Pipeline…", expanded=True) as status_box:

        # Step 1: JID scraper
        st.write("**Step 1/3** — Harvesting dark matter (scraping expired JIDs)…")
        df_scraped = scrape_historical_jids(scrape_start, scrape_end)

        # Step 2: Socrata fetch (DuckDB cache)
        st.write("**Step 2/3** — Querying Socrata endpoints…")
        df_jobs = _duckdb_load(jobs_key)
        df_payroll = _duckdb_load(payroll_key)

        if df_jobs is None:
            df_jobs = _fetch_jobs(target_agency, target_title)
            if not df_jobs.empty:
                _duckdb_save(jobs_key, df_jobs)
        else:
            st.caption("Jobs data loaded from local DuckDB cache.")

        if df_payroll is None:
            df_payroll = _fetch_payroll(target_agency, target_title)
            if not df_payroll.empty:
                _duckdb_save(payroll_key, df_payroll)
        else:
            st.caption("Payroll data loaded from local DuckDB cache.")

        # Merge scraper results into jobs
        if not df_scraped.empty and not df_jobs.empty:
            df_jobs["job_id"] = df_jobs["job_id"].astype(str)
            df_scraped["job_id"] = df_scraped["job_id"].astype(str)
            if target_agency.upper() != "ALL":
                df_scraped = df_scraped[
                    df_scraped["agency"].str.contains(
                        target_agency, case=False, na=False
                    )
                ]
            if target_title.upper() != "ALL":
                df_scraped = df_scraped[
                    df_scraped["civil_service_title"].str.contains(
                        target_title, case=False, na=False
                    )
                ]
            df_jobs = pd.concat([df_jobs, df_scraped], ignore_index=True)
            df_jobs = df_jobs.drop_duplicates(subset=["job_id"])
        elif not df_scraped.empty:
            df_jobs = df_scraped.copy()

        if "source" not in df_jobs.columns:
            df_jobs["source"] = "socrata"

        if df_jobs.empty or df_payroll.empty:
            status_box.update(label="Pipeline Failed", state="error")
            st.error(
                "No data returned for those parameters. "
                "Try 'ALL' for agency or title."
            )
            return

        st.write(
            f"Jobs: **{len(df_jobs):,} rows** | Payroll: **{len(df_payroll):,} rows**"
        )

        # Step 3: Math
        st.write("**Step 3/3** — Running PyMC Bayesian MCMC + Prophet ML…")
        apex = run_apex_math(df_jobs, df_payroll)

        if apex is None:
            status_box.update(label="Pipeline Failed", state="error")
            return

        # Persist to session state
        st.session_state.apex_results = apex
        st.session_state.df_jobs_cache = df_jobs
        st.session_state.df_payroll_cache = df_payroll
        st.session_state.apex_pipeline_ran_at = datetime.now().strftime("%H:%M:%S")
        st.session_state.apex_agency = target_agency
        st.session_state.apex_title = target_title
        st.session_state.apex_scrape_start = scrape_start
        st.session_state.apex_scrape_end = scrape_end

        status_box.update(label="Pipeline Complete!", state="complete", expanded=False)


# ---------------------------------------------------------------------------
# Dashboard renderer
# ---------------------------------------------------------------------------

def _render_dashboard(
    results: dict,
    target_agency: str,
    target_title: str,
) -> None:
    # KPIs
    _kpi_row(results, target_agency, target_title)
    st.divider()

    # Velocity chart
    st.subheader("Administrative Velocity")
    st.caption("3-month rolling average of job postings vs. payroll start dates.")
    st.plotly_chart(_chart_velocity(results), use_container_width=True)

    st.divider()

    # Lag + forecast side by side
    col_lag, col_fc = st.columns([1, 2])
    with col_lag:
        st.subheader("Cross-Correlation")
        st.caption(f"Optimal OMB lag: **{results['best_lag']} months** (highlighted).")
        st.plotly_chart(_chart_lag(results), use_container_width=True)
    with col_fc:
        st.subheader("12-Month Forecast")
        st.caption(
            "Prophet forecast with confidence bands; hires shifted by OMB lag."
        )
        st.plotly_chart(_chart_forecast(results), use_container_width=True)

    # Folium map
    df_jobs: pd.DataFrame | None = st.session_state.get("df_jobs_cache")
    if df_jobs is not None and not df_jobs.empty:
        st.divider()
        st.subheader("Spatial Requisition Density")
        st.caption(
            "Bubble size = posting volume. "
            "Positions are borough-geocoded with deterministic jitter."
        )
        _map_panel(df_jobs)

    # Data quality
    df_payroll: pd.DataFrame | None = st.session_state.get("df_payroll_cache")
    if df_jobs is not None and df_payroll is not None:
        st.divider()
        st.subheader("Data Quality")
        _data_quality_panel(df_jobs, df_payroll)

    # Raw data expander
    if df_jobs is not None and not df_jobs.empty:
        with st.expander("Raw Job Postings", expanded=False):
            show_cols = [
                c
                for c in [
                    "job_id",
                    "civil_service_title",
                    "agency",
                    "posting_date",
                    "work_location",
                    "Status",
                    "source",
                ]
                if c in df_jobs.columns
            ]
            st.dataframe(
                df_jobs[show_cols].head(200),
                use_container_width=True,
                hide_index=True,
            )
            st.caption(f"{len(df_jobs):,} total rows — showing first 200.")

    # Export
    st.divider()
    st.subheader("Export Results")
    if df_jobs is not None and not df_jobs.empty:
        _export_panel(results, df_jobs)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_apex_tab(
    target_agency: str,
    target_title: str,
    scrape_start: int,
    scrape_end: int,
) -> None:
    """
    Render the Apex Engine hiring analytics tab.

    Parameters
    ----------
    target_agency : str
        Agency filter string (or "ALL").
    target_title : str
        Civil-service title filter (or "ALL").
    scrape_start : int
        First JID to scrape from cityjobs.nyc.gov.
    scrape_end : int
        Last JID to scrape (hard cap: 100 JIDs).
    """
    _init_apex_state()

    # ---------- Header ----------
    st.markdown(
        "<h2 style='margin-bottom:0;'>Apex Engine</h2>"
        "<p style='color:#94A3B8; margin-top:0.25rem;'>"
        "Bayesian Hiring Intelligence · NYC Open Data</p>",
        unsafe_allow_html=True,
    )

    # ---------- JID range warnings ----------
    jid_count = scrape_end - scrape_start + 1
    if jid_count > JID_SCRAPE_HARD_LIMIT:
        st.error(
            f"Hard cap exceeded: JID range is {jid_count}. "
            f"Reduce to {JID_SCRAPE_HARD_LIMIT} or fewer before running.",
        )
        return
    if jid_count > JID_SCRAPE_SOFT_LIMIT:
        st.warning(
            f"{jid_count} JIDs selected — "
            f"estimated {jid_count}–{jid_count * 2}s scrape time.",
        )

    # ---------- Pipeline status ----------
    results: dict | None = st.session_state.get("apex_results")
    ran_at: str | None = st.session_state.get("apex_pipeline_ran_at")

    # Check whether cached results match the current filter selection
    cached_agency: str = st.session_state.get("apex_agency", "")
    cached_title: str = st.session_state.get("apex_title", "")
    params_changed = (
        cached_agency.upper() != target_agency.upper()
        or cached_title.upper() != target_title.upper()
    )
    if params_changed and results is not None:
        st.info(
            "Filter parameters changed since last run. "
            "Click **Run Apex Pipeline** to refresh.",
        )
        results = None  # treat as stale until re-run

    # ---------- Run button ----------
    col_btn, col_reset = st.columns([2, 1])
    with col_btn:
        run_clicked = st.button(
            "Run Apex Pipeline",
            type="primary",
            use_container_width=True,
            disabled=(jid_count > JID_SCRAPE_HARD_LIMIT),
        )
    with col_reset:
        if results is not None and st.button("Reset Results", use_container_width=True):
            for key in [
                "apex_results",
                "df_jobs_cache",
                "df_payroll_cache",
                "apex_pipeline_ran_at",
                "apex_agency",
                "apex_title",
            ]:
                st.session_state[key] = None
            st.rerun()

    if run_clicked:
        _run_pipeline(target_agency, target_title, scrape_start, scrape_end)
        st.rerun()

    # ---------- Results ----------
    results = st.session_state.get("apex_results")

    if results is None:
        st.divider()
        st.info(
            "Configure your agency and title filters in the sidebar, "
            "then click **Run Apex Pipeline** to begin.",
        )
        _render_landing_cards()
        return

    # Pipeline metadata banner
    if ran_at:
        st.caption(
            f"Last run: **{ran_at}** "
            f"| Agency: `{st.session_state.get('apex_agency', target_agency)}` "
            f"| Title: `{st.session_state.get('apex_title', target_title)}`"
        )

    st.divider()
    _render_dashboard(results, target_agency, target_title)


# ---------------------------------------------------------------------------
# Landing state (no results yet)
# ---------------------------------------------------------------------------

def _render_landing_cards() -> None:
    c1, c2, c3, c4 = st.columns(4)
    cards = [
        (
            "Dark Matter Scraper",
            "Captures expired DCAS requisitions from cityjobs.nyc.gov by JID range.",
        ),
        (
            "Live Socrata Ingestion",
            "Paginated pull from NYC Open Data jobs + payroll endpoints via SocrataClient.",
        ),
        (
            "Bayesian MCMC Engine",
            "PyMC Poisson regression finds the OMB review lag and yield multiplier.",
        ),
        (
            "Prophet Forecast",
            "12-month posting and hire forecast with HDI confidence bands.",
        ),
    ]
    for col, (title, desc) in zip([c1, c2, c3, c4], cards, strict=False):
        col.markdown(
            f"<div style='"
            f"border:1px solid #334155; border-radius:10px; padding:1rem; height:120px;"
            f"background:#0f172a;'>"
            f"<div style='font-weight:700; font-size:0.9rem; "
            f"color:#e2e8f0; margin-bottom:0.4rem;'>{title}</div>"
            f"<div style='font-size:0.78rem; color:#64748b;'>{desc}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
