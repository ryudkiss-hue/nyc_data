"""
Manhattan Mission Control: Monolithic Apex Engine
A self-contained Streamlit application for NYC DOT Operations,
featuring native web scraping, Socrata API ingestion, Bayesian Inference,
Facebook Prophet forecasting, and a Gemini AI Copilot.
"""
from __future__ import annotations

import os
import random
import time
import warnings
from datetime import datetime

import agentql
import arviz as az
import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pymc as pm
import requests
import streamlit as st
import streamlit.components.v1 as components
from dateutil.relativedelta import relativedelta
from playwright.sync_api import sync_playwright
from prophet import Prophet

warnings.filterwarnings("ignore")

# ==========================================
# --- CONFIGURATION ---
# ==========================================

st.set_page_config(
    page_title="Manhattan Mission Control",
    page_icon="🗽",
    layout="wide",
    initial_sidebar_state="expanded",
)

SOCRATA_TOKEN = os.getenv("SOCRATA_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AGENTQL_API_KEY = os.getenv("AGENTQL_API_KEY", "")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

COLORS = {
    "postings": "#3B82F6",   # blue
    "hires": "#10B981",      # emerald
    "forecast": "#F59E0B",   # amber
    "confidence": "rgba(59,130,246,0.12)",
    "divider": "#94A3B8",
}

BOROUGH_COORDS = {
    "MANHATTAN": [40.7831, -73.9712],
    "BROOKLYN": [40.6782, -73.9442],
    "QUEENS": [40.7282, -73.7949],
    "BRONX": [40.8448, -73.8648],
    "STATEN ISLAND": [40.5795, -74.1502],
    "UNKNOWN": [40.7128, -74.0060],
}

JID_SCRAPE_SOFT_LIMIT = 20
JID_SCRAPE_HARD_LIMIT = 100

# ==========================================
# --- SESSION STATE BOOTSTRAP ---
# ==========================================

def _init_state():
    defaults = {
        "pipeline_run": False,
        "apex_results": None,
        "df_jobs_cache": None,
        "df_payroll_cache": None,
        "pipeline_ran_at": None,
        "copilot_messages": [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your Manhattan Mission Control AI Copilot — "
                    "hydrated with your active pipeline context. Run the pipeline "
                    "first, then ask me anything: OMB hiring lag analysis, MCMC "
                    "posterior interpretation, PostGIS queries, or forecast anomalies."
                ),
            }
        ],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_state()

# ==========================================
# --- DATA INGESTION ---
# ==========================================

_JOB_QUERY = """
{
    job_title
    agency_name
    is_expired
}
"""

def scrape_historical_jids(start_jid: int, end_jid: int) -> pd.DataFrame:
    """Scrapes cityjobs.nyc.gov for expired/filled requisitions with live progress."""
    if AGENTQL_API_KEY:
        os.environ.setdefault("AGENTQL_API_KEY", AGENTQL_API_KEY)

    scraped_data = []
    total = end_jid - start_jid + 1
    progress_bar = st.progress(0, text="Initializing scraper...")
    status_slot = st.empty()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = agentql.wrap(browser.new_page())

        for i, jid in enumerate(range(start_jid, end_jid + 1)):
            pct = (i + 1) / total
            progress_bar.progress(pct, text=f"Scanning JID {jid}  ({i + 1}/{total})")
            status_slot.caption(f"📡  `GET https://cityjobs.nyc.gov/job/jid-{jid}`")
            time.sleep(random.uniform(0.4, 0.9))

            try:
                page.goto(
                    f"https://cityjobs.nyc.gov/job/anything-jid-{jid}",
                    wait_until="domcontentloaded",
                    timeout=10000,
                )
                data = page.query_data(_JOB_QUERY, wait_for_network_idle=False)
                job_title = (data.get("job_title") or "UNKNOWN TITLE").strip()
                agency_name = (data.get("agency_name") or "UNKNOWN AGENCY").strip()
                is_expired = bool(data.get("is_expired"))
                scraped_data.append({
                    "job_id": str(jid),
                    "civil_service_title": job_title.upper(),
                    "agency": agency_name.upper(),
                    "Status": "Expired" if is_expired else "Active",
                    "posting_date": (datetime.now() - relativedelta(months=6)).strftime("%Y-%m-%dT00:00:00"),
                    "source": "scraper",
                })
            except Exception:
                continue

        browser.close()

    progress_bar.empty()
    status_slot.empty()

    df = pd.DataFrame(scraped_data)
    if not df.empty:
        active = (df["Status"] == "Active").sum()
        expired = (df["Status"] == "Expired").sum()
        st.success(f"Scraper found **{len(df)} postings** — {active} active, {expired} expired.")
    return df


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_socrata_data(url: str, params: dict) -> pd.DataFrame:
    """Paginates through Socrata API to bypass the 50k row limit."""
    headers = {"X-App-Token": SOCRATA_TOKEN} if SOCRATA_TOKEN else {}
    all_data, offset = [], 0
    limit = params.get("$limit", 50000)
    if "$order" not in params:
        params["$order"] = ":id"

    try:
        while True:
            params["$offset"] = offset
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            chunk = resp.json()
            if not chunk:
                break
            all_data.extend(chunk)
            offset += limit
            if len(all_data) >= 200000:
                break
        return pd.DataFrame(all_data)
    except Exception as e:
        st.error(f"Socrata API error: {e}")
        return pd.DataFrame()

# ==========================================
# --- MATHEMATICAL ENGINE ---
# ==========================================

def run_apex_math(df_jobs: pd.DataFrame, df_payroll: pd.DataFrame, max_lag: int = 12) -> dict | None:
    """Executes the PyMC MCMC simulation and Prophet forecasting."""

    # 1. Build time series
    df_jobs["posting_date"] = pd.to_datetime(df_jobs["posting_date"], errors="coerce")
    postings_ts = (
        df_jobs.dropna(subset=["posting_date"])
        .groupby(df_jobs["posting_date"].dt.to_period("M").dt.to_timestamp())
        .size()
        .rename("Postings")
    )

    df_payroll = df_payroll.drop_duplicates(subset=["first_name", "last_name", "agency_start_date"])
    df_payroll["agency_start_date"] = pd.to_datetime(df_payroll["agency_start_date"], errors="coerce")
    starts_ts = (
        df_payroll.dropna(subset=["agency_start_date"])
        .groupby(df_payroll["agency_start_date"].dt.to_period("M").dt.to_timestamp())
        .size()
        .rename("Starts")
    )

    df_ts = pd.concat([postings_ts, starts_ts], axis=1).fillna(0).sort_index()
    if df_ts.empty:
        return None

    if len(df_ts) < 6:
        st.warning(
            "⚠️  Not enough historical data to run the Bayesian model — "
            "need at least 6 months. Try broadening your agency/title filter.",
            icon="⚠️",
        )
        return None

    df_ts["Postings_Smoothed"] = df_ts["Postings"].rolling(window=3, min_periods=1).mean()
    df_ts["Starts_Smoothed"] = df_ts["Starts"].rolling(window=3, min_periods=1).mean()

    # 2. Cross-correlation to find optimal lag
    correlations = {
        lag: (df_ts["Postings_Smoothed"].corr(df_ts["Starts_Smoothed"].shift(-lag)) or 0)
        for lag in range(max_lag + 1)
    }
    best_lag = max(correlations, key=correlations.get) if correlations else 0
    lag_df = pd.DataFrame(
        [(k, v) for k, v in correlations.items()], columns=["Lag_Months", "Correlation"]
    )

    # 3. Bayesian inference (cloud-safe: cores=1)
    predictor = df_ts["Postings_Smoothed"].shift(best_lag).fillna(0).values
    target = df_ts["Starts"].values

    try:
        with pm.Model():
            alpha = pm.Normal("Baseline_Log", mu=0, sigma=5)
            beta = pm.Normal("Yield_Log", mu=0, sigma=5)
            mu = pm.math.exp(alpha + beta * predictor)
            pm.Poisson("Y_obs", mu=mu, observed=target)
            trace = pm.sample(
                1000, tune=1000, target_accept=0.9,
                cores=1, chains=2, return_inferencedata=True, progressbar=False,
            )
    except Exception as e:
        st.error(f"PyMC sampling failed: {e}")
        return None

    summary = az.summary(trace, var_names=["Yield_Log"])
    beta_mean = float(summary.loc["Yield_Log", "mean"])
    beta_hdi_lo = float(summary.loc["Yield_Log", "hdi_3%"])
    beta_hdi_hi = float(summary.loc["Yield_Log", "hdi_97%"])
    effective_yield = float(np.exp(beta_mean))
    yield_lo = float(np.exp(beta_hdi_lo))
    yield_hi = float(np.exp(beta_hdi_hi))

    # 4. Prophet forecast with confidence interval
    df_prophet = (
        df_ts.rename_axis("ds")
        .reset_index()[["ds", "Postings_Smoothed"]]
        .rename(columns={"Postings_Smoothed": "y"})
    )
    m_prophet = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m_prophet.fit(df_prophet)
    future = m_prophet.make_future_dataframe(periods=12, freq="MS")
    forecast = m_prophet.predict(future)
    forecast["predicted_hires"] = forecast["yhat"] * effective_yield
    forecast["predicted_hires_lo"] = forecast["yhat_lower"] * yield_lo
    forecast["predicted_hires_hi"] = forecast["yhat_upper"] * yield_hi
    forecast["predicted_hires_date"] = forecast["ds"] + pd.DateOffset(months=best_lag)
    future_forecast = forecast[forecast["ds"] > df_ts.index[-1]].copy()

    return {
        "df_ts": df_ts,
        "best_lag": best_lag,
        "yield_rate": effective_yield,
        "yield_lo": yield_lo,
        "yield_hi": yield_hi,
        "lag_df": lag_df,
        "future_forecast": future_forecast,
        "full_forecast": forecast,
        "cutoff_date": df_ts.index[-1],
    }

# ==========================================
# --- AI COPILOT ---
# ==========================================

def _copilot_system_prompt(results: dict | None, agency: str, title: str) -> str:
    if results:
        lag = results["best_lag"]
        yield_rate = f"{results['yield_rate']:.2f}"
        projected = int(results["future_forecast"]["predicted_hires"].sum())
    else:
        lag = yield_rate = projected = "unknown (pipeline not yet run)"

    return f"""You are the Manhattan Mission Control AI — a Senior Data Architect and Civil Operations Strategist for New York City open datasets.
Your tone is precise, professional, and slightly command-center themed.
You have access to the currently calculated parameters from the live Bayesian pipeline:
- Target Agency: "{agency}"
- Target Civil Service Title: "{title}"
- Optimized OMB Hiring Lag: {lag} months
- Bayesian Yield Multiplier (Postings → Starts): {yield_rate}x
- 12-Month Projected Hires: {projected}

Respond directly to the user's question. Include actual statistics when relevant.
Keep responses highly scannable: Markdown-formatted, bullet points, short paragraphs."""


def _query_gemini(user_prompt: str, system_prompt: str, history: list) -> str:
    if not GEMINI_API_KEY:
        return (
            "**[Offline Mode]** No `GEMINI_API_KEY` found. "
            "Set the secret and restart to enable live AI responses.\n\n"
            f"*Your question:* {user_prompt}"
        )

    contents = []
    for msg in history[1:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7},
    }

    try:
        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"⚠️ Gemini API error: {e}"

# ==========================================
# --- UI HELPERS ---
# ==========================================

def _kpi_row(results: dict, target_agency: str, target_title: str):
    projected = int(results["future_forecast"]["predicted_hires"].sum())
    ran_at = st.session_state.pipeline_ran_at or "—"
    lag = results["best_lag"]
    yield_rate = results["yield_rate"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "OMB Review Lag",
        f"{lag} mo",
        delta=f"{lag - 6:+d} mo vs 6-mo benchmark",
        help="Cross-correlation lag between postings and first payroll starts.",
    )
    c2.metric(
        "Bayesian Yield",
        f"{yield_rate:.2f}×",
        delta=f"{(yield_rate - 1) * 100:+.0f}% vs 1.0× baseline",
        help=(
            f"Hires per posting (94% HDI: {results['yield_lo']:.2f}–{results['yield_hi']:.2f}×). "
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


def _chart_velocity(results: dict) -> go.Figure:
    df = results["df_ts"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Postings_Smoothed"],
        name="Postings (3-mo avg)", mode="lines",
        line=dict(color=COLORS["postings"], width=2.5),
        hovertemplate="%{x|%b %Y}: %{y:.1f} postings<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Starts_Smoothed"],
        name="Hires (3-mo avg)", mode="lines",
        line=dict(color=COLORS["hires"], width=2.5),
        hovertemplate="%{x|%b %Y}: %{y:.1f} hires<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=340,
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
    colors = [COLORS["postings"] if i != best else COLORS["hires"] for i in df["Lag_Months"]]
    fig = go.Figure(go.Bar(
        x=df["Lag_Months"], y=df["Correlation"],
        marker_color=colors,
        hovertemplate="Lag %{x} mo: r = %{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", height=260,
        xaxis_title="Lag (months)", yaxis_title="Pearson r",
        xaxis=dict(dtick=1),
        margin=dict(l=0, r=0, t=10, b=0),
        annotations=[dict(
            x=best, y=df.loc[df["Lag_Months"] == best, "Correlation"].values[0],
            text=f"  Best lag: {best} mo", showarrow=False,
            font=dict(color=COLORS["hires"], size=12), xanchor="left",
        )],
    )
    return fig


def _chart_forecast(results: dict) -> go.Figure:
    ff = results["future_forecast"]
    cutoff = results["cutoff_date"]
    lag = results["best_lag"]

    fig = go.Figure()

    # Confidence band for postings
    fig.add_trace(go.Scatter(
        x=pd.concat([ff["ds"], ff["ds"][::-1]]),
        y=pd.concat([ff["yhat_upper"], ff["yhat_lower"][::-1]]),
        fill="toself", fillcolor=COLORS["confidence"],
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="skip",
        name="Postings CI",
    ))

    # Forecast lines
    fig.add_trace(go.Scatter(
        x=ff["ds"], y=ff["yhat"],
        name="Forecasted Postings", mode="lines",
        line=dict(color=COLORS["postings"], width=2, dash="dot"),
        hovertemplate="%{x|%b %Y}: %{y:.1f} postings<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=ff["predicted_hires_date"], y=ff["predicted_hires"],
        name=f"Forecasted Hires (+{lag} mo lag)", mode="lines",
        line=dict(color=COLORS["hires"], width=2, dash="dot"),
        hovertemplate="%{x|%b %Y}: %{y:.1f} hires<extra></extra>",
    ))

    # "Today" divider
    fig.add_vline(
        x=cutoff, line_width=1, line_dash="dash",
        line_color=COLORS["divider"],
        annotation_text="  Forecast →", annotation_position="top right",
        annotation_font=dict(color=COLORS["divider"], size=11),
    )

    fig.update_layout(
        template="plotly_white", height=360,
        hovermode="x unified",
        xaxis_title="Date", yaxis_title="Estimated Volume",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=10, b=0),
    )
    return fig


def _map_panel(df_jobs: pd.DataFrame):
    if "work_location" not in df_jobs.columns:
        st.info("No `work_location` column in the jobs dataset — map unavailable.")
        return

    location_counts = df_jobs["work_location"].value_counts().reset_index()
    location_counts.columns = ["Location", "Count"]

    m = folium.Map(location=[40.7128, -74.0060], zoom_start=10, tiles="CartoDB dark_matter")
    for _, row in location_counts.iterrows():
        loc_str = str(row["Location"]).upper()
        base_coord = BOROUGH_COORDS["UNKNOWN"]
        for b_name, coords in BOROUGH_COORDS.items():
            if b_name in loc_str:
                base_coord = coords
                break

        h = hash(row["Location"])
        jitter_lat = base_coord[0] + (h % 200 - 100) / 8000
        jitter_lon = base_coord[1] + ((h >> 8) % 200 - 100) / 8000

        folium.CircleMarker(
            location=[jitter_lat, jitter_lon],
            radius=min(max(row["Count"] * 2, 5), 22),
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


def _data_quality_panel(df_jobs: pd.DataFrame, df_payroll: pd.DataFrame):
    rows = []
    for label, df in [("Job Postings", df_jobs), ("Payroll Records", df_payroll)]:
        n = len(df)
        nulls = df.isnull().sum().sum()
        total_cells = n * len(df.columns) if n else 1
        null_pct = nulls / total_cells * 100
        dups = df.duplicated().sum()
        score = max(0, 100 - null_pct * 2 - (dups / max(n, 1)) * 50)
        rows.append({
            "Dataset": label, "Rows": f"{n:,}", "Columns": len(df.columns),
            "Null Density": f"{null_pct:.1f}%", "Duplicates": int(dups),
            "Health Score": f"{score:.0f}/100",
        })

    df_q = pd.DataFrame(rows)
    st.dataframe(df_q, use_container_width=True, hide_index=True)


def _export_panel(results: dict, df_jobs: pd.DataFrame):
    ff = results["future_forecast"]
    forecast_csv = ff[["ds", "yhat", "predicted_hires", "predicted_hires_lo",
                        "predicted_hires_hi", "predicted_hires_date"]].to_csv(index=False)
    jobs_cols = [c for c in ["job_id", "civil_service_title", "agency", "posting_date",
                              "Status", "work_location", "source"] if c in df_jobs.columns]
    jobs_csv = df_jobs[jobs_cols].to_csv(index=False)

    lag = results["best_lag"]
    yr = results["yield_rate"]
    projected = int(ff["predicted_hires"].sum())
    summary_txt = (
        f"Run timestamp : {st.session_state.pipeline_ran_at}\n"
        f"OMB Lag       : {lag} months\n"
        f"Bayesian Yield: {yr:.2f}x\n"
        f"12-Mo Hires   : {projected:,} projected\n"
    )

    c1, c2, c3 = st.columns(3)
    c1.download_button(
        "📥  Forecast CSV", forecast_csv,
        file_name="mmc_forecast.csv", mime="text/csv", use_container_width=True,
    )
    c2.download_button(
        "📥  Job Postings CSV", jobs_csv,
        file_name="mmc_job_postings.csv", mime="text/csv", use_container_width=True,
    )
    c3.download_button(
        "📄  Pipeline Summary", summary_txt,
        file_name="mmc_summary.txt", mime="text/plain", use_container_width=True,
    )

# ==========================================
# --- LANDING PAGE ---
# ==========================================

def _render_landing():
    st.markdown("""
<div style="text-align:center; padding: 2rem 0 1rem;">
  <h1 style="font-size:2.4rem; font-weight:800; margin-bottom:0.25rem;">
    🗽 Manhattan Mission Control
  </h1>
  <p style="font-size:1.1rem; color:#64748b; margin-top:0;">
    Unified Bayesian Hiring Intelligence for NYC Government Operations
  </p>
</div>
""", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    cards = [
        ("🕸️", "Dark Matter Scraper", "Captures expired DCAS requisitions from cityjobs.nyc.gov by JID range."),
        ("📡", "Live Socrata Ingestion", "Paginated pull from NYC Open Data jobs + payroll endpoints."),
        ("🧮", "Bayesian MCMC Engine", "PyMC Poisson regression finds the OMB review lag and yield multiplier."),
        ("🤖", "AI Copilot", "Gemini-powered assistant pre-loaded with your pipeline results."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3, c4], cards):
        col.markdown(
            f"""<div style="border:1px solid #e2e8f0; border-radius:12px; padding:1.1rem; height:130px;">
            <div style="font-size:1.6rem;">{icon}</div>
            <div style="font-weight:700; font-size:0.9rem; margin:0.3rem 0 0.2rem;">{title}</div>
            <div style="font-size:0.78rem; color:#64748b;">{desc}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈  Configure your agency and title in the sidebar, then click **Initialize Pipeline** to begin.", icon="ℹ️")

# ==========================================
# --- DASHBOARD TAB ---
# ==========================================

def _render_dashboard(results: dict, target_agency: str, target_title: str):
    _kpi_row(results, target_agency, target_title)
    st.divider()

    # Section 1: Velocity
    st.subheader("Administrative Velocity")
    st.caption("3-month rolling average of job postings vs. payroll start dates.")
    st.plotly_chart(_chart_velocity(results), use_container_width=True)

    # Section 2: Lag correlation + forecast side by side
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Cross-Correlation")
        st.caption(f"Optimal lag: **{results['best_lag']} months** (highlighted).")
        st.plotly_chart(_chart_lag(results), use_container_width=True)
    with col_b:
        st.subheader("12-Month Forecast")
        st.caption("Prophet forecast with confidence bands; hires shifted by OMB lag.")
        st.plotly_chart(_chart_forecast(results), use_container_width=True)

    # Section 3: Map
    df_jobs = st.session_state.df_jobs_cache
    if df_jobs is not None:
        st.divider()
        st.subheader("Spatial Requisition Density")
        st.caption("Bubble size = posting volume. Positions are borough-geocoded + deterministic offset.")
        _map_panel(df_jobs)

    # Section 4: Data quality
    st.divider()
    st.subheader("Data Quality")
    df_payroll = st.session_state.df_payroll_cache
    if df_jobs is not None and df_payroll is not None:
        _data_quality_panel(df_jobs, df_payroll)

    # Section 5: Raw data explorer
    with st.expander("🗂️  Raw Job Postings", expanded=False):
        if df_jobs is not None:
            show_cols = [c for c in ["job_id", "civil_service_title", "agency",
                                     "posting_date", "work_location", "Status", "source"]
                         if c in df_jobs.columns]
            st.dataframe(df_jobs[show_cols].head(200), use_container_width=True, hide_index=True)
            st.caption(f"{len(df_jobs):,} total rows — showing first 200.")

    # Section 6: Export
    st.divider()
    st.subheader("Export Results")
    if df_jobs is not None:
        _export_panel(results, df_jobs)

# ==========================================
# --- COPILOT TAB ---
# ==========================================

def _render_copilot(results: dict | None, target_agency: str, target_title: str):
    sys_prompt = _copilot_system_prompt(results, target_agency, target_title)

    if not GEMINI_API_KEY:
        st.warning(
            "**AI Copilot is in offline mode.** "
            "Set `GEMINI_API_KEY` in your environment to enable live responses.",
            icon="⚠️",
        )
    elif results is None:
        st.info("Run the pipeline first to hydrate the copilot with your data context.", icon="ℹ️")

    st.caption("Pre-loaded with your active pipeline context — agency, title, lag, yield, and projected hires.")

    # Quick-action chips
    chips = [
        ("OMB Latency", "Analyze the OMB hiring lag bottleneck in the active dataset."),
        ("MCMC Priors", "Explain the prior distributions and convergence in our Bayesian model."),
        ("PostGIS Join", "Write a PostGIS query joining city jobs locations with complaint borough coordinates."),
        ("Forecast Anomalies", "Interpret the 12-month hire forecast and flag any anomalies."),
    ]
    cols = st.columns(len(chips))
    for col, (label, query) in zip(cols, chips):
        if col.button(label, key=f"chip_{label}", use_container_width=True):
            st.session_state.copilot_messages.append({"role": "user", "content": query})
            with st.spinner("Contacting Gemini..."):
                reply = _query_gemini(query, sys_prompt, st.session_state.copilot_messages)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})
            st.rerun()

    st.divider()

    for msg in st.session_state.copilot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask about the pipeline, MCMC, PostGIS, or forecast results..."):
        st.session_state.copilot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = _query_gemini(user_input, sys_prompt, st.session_state.copilot_messages)
            st.markdown(reply)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})

    if st.button("🗑️  Clear Chat", key="clear_copilot"):
        st.session_state.copilot_messages = [
            {"role": "assistant", "content": "Chat cleared. Ready for new queries."}
        ]
        st.rerun()

# ==========================================
# --- MAIN ---
# ==========================================

def main():
    # URL param persistence
    qp = st.query_params
    agency_default = qp.get("agency", "DEPARTMENT OF TRANSPORTATION")
    title_default = qp.get("title", "PROJECT ANALYST")

    # Sidebar
    with st.sidebar:
        st.markdown("## 🗽 Mission Control")
        st.divider()

        st.markdown("### 🎯 Target Parameters")
        target_agency = st.text_input("Agency", value=agency_default)
        target_title = st.text_input("Civil Service Title", value=title_default)

        st.markdown("### 🕸️ JID Scraper")
        jid_range = st.slider(
            "JID Range", min_value=30000, max_value=50000,
            value=(35710, 35715), step=1,
        )
        scrape_start, scrape_end = jid_range
        jid_count = scrape_end - scrape_start + 1

        if jid_count > JID_SCRAPE_SOFT_LIMIT:
            st.warning(
                f"⚠️  {jid_count} JIDs selected — estimated **{jid_count * 1:.0f}–{jid_count * 2:.0f}s** scrape time.",
                icon="⏱️",
            )
        if jid_count > JID_SCRAPE_HARD_LIMIT:
            st.error(f"Hard cap: reduce range to ≤{JID_SCRAPE_HARD_LIMIT} JIDs.", icon="🛑")

        st.divider()
        run_btn = st.button(
            "🚀  Initialize Pipeline",
            type="primary",
            use_container_width=True,
            disabled=(jid_count > JID_SCRAPE_HARD_LIMIT),
        )

        if st.session_state.pipeline_run:
            if st.button("🔄  Reset", use_container_width=True):
                for key in ["pipeline_run", "apex_results", "df_jobs_cache", "df_payroll_cache", "pipeline_ran_at"]:
                    st.session_state[key] = None if key != "pipeline_run" else False
                st.rerun()

    # Header
    st.markdown(
        "## 🗽 Manhattan Mission Control"
        "<span style='font-size:0.9rem; color:#64748b; margin-left:1rem;'>"
        "Bayesian Hiring Intelligence · NYC Open Data</span>",
        unsafe_allow_html=True,
    )
    st.divider()

    if run_btn:
        st.session_state.pipeline_run = True
        st.session_state.apex_results = None
        st.query_params["agency"] = target_agency
        st.query_params["title"] = target_title

    if not st.session_state.pipeline_run:
        _render_landing()
        return

    # Pipeline execution
    if st.session_state.apex_results is None:
        with st.status("🚀  Initializing Apex Pipeline...", expanded=True) as status:
            st.write("**Step 1/3** — Harvesting dark matter (scraping expired JIDs)...")
            df_scraped = scrape_historical_jids(scrape_start, scrape_end)

            st.write("**Step 2/3** — Querying Socrata endpoints...")
            five_years_ago = (datetime.now() - relativedelta(years=5)).strftime("%Y-%m-%dT00:00:00")
            jobs_params = {"$where": f"posting_date >= '{five_years_ago}'", "$limit": 50000}
            payroll_params = {"$where": f"agency_start_date >= '{five_years_ago}'", "$limit": 50000}

            if target_agency.strip().upper() != "ALL":
                jobs_params["agency"] = target_agency.strip().upper()
                payroll_params["agency_name"] = target_agency.strip().upper()
            if target_title.strip().upper() != "ALL":
                jobs_params["civil_service_title"] = target_title.strip().upper()
                payroll_params["title_description"] = target_title.strip().upper()

            df_jobs = fetch_socrata_data("https://data.cityofnewyork.us/resource/kpav-sd4t.json", jobs_params)
            df_payroll = fetch_socrata_data("https://data.cityofnewyork.us/resource/k397-673e.json", payroll_params)

            if not df_scraped.empty and not df_jobs.empty:
                df_jobs["job_id"] = df_jobs["job_id"].astype(str)
                df_scraped["job_id"] = df_scraped["job_id"].astype(str)
                if target_agency.upper() != "ALL":
                    df_scraped = df_scraped[df_scraped["agency"].str.contains(target_agency, case=False, na=False)]
                if target_title.upper() != "ALL":
                    df_scraped = df_scraped[df_scraped["civil_service_title"].str.contains(target_title, case=False, na=False)]
                df_jobs = pd.concat([df_jobs, df_scraped], ignore_index=True).drop_duplicates(subset=["job_id"])
                if "source" not in df_jobs.columns:
                    df_jobs["source"] = "socrata"

            if df_jobs.empty or df_payroll.empty:
                status.update(label="Pipeline Failed", state="error")
                st.error("No data returned for those parameters. Try 'ALL' for agency or title.")
                st.session_state.pipeline_run = False
                return

            st.write("**Step 3/3** — Running PyMC Bayesian MCMC + Prophet ML...")
            apex = run_apex_math(df_jobs, df_payroll)

            if apex is None:
                status.update(label="Pipeline Failed", state="error")
                st.session_state.pipeline_run = False
                return

            st.session_state.apex_results = apex
            st.session_state.df_jobs_cache = df_jobs
            st.session_state.df_payroll_cache = df_payroll
            st.session_state.pipeline_ran_at = datetime.now().strftime("%H:%M:%S")
            status.update(label="✅  Pipeline Complete!", state="complete", expanded=False)

    results = st.session_state.apex_results
    if not results:
        st.error("Results are empty — please reset and re-run the pipeline.")
        return

    tab_dash, tab_copilot = st.tabs(["📊  Dashboard", "🤖  AI Copilot"])
    with tab_dash:
        _render_dashboard(results, target_agency, target_title)
    with tab_copilot:
        _render_copilot(results, target_agency, target_title)


if __name__ == "__main__":
    main()
