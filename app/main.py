"""
Manhattan Mission Control: Monolithic Apex Engine
A self-contained Streamlit application for NYC DOT Operations, 
featuring native web scraping, Socrata API ingestion, Bayesian Inference, 
and Facebook Prophet forecasting in a single namespace.
"""

import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go
import folium
import os
import time
import random
import warnings
import re

# Machine Learning Imports
import pymc as pm
import arviz as az
from prophet import Prophet

warnings.filterwarnings('ignore')

# ==========================================
# --- CONFIGURATION & SECRETS ---
# ==========================================
st.set_page_config(
    page_title="Manhattan Mission Control",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

SOCRATA_TOKEN = os.getenv("SOCRATA_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Initialize Streamlit Session State to prevent the Vanishing Dashboard bug
if "pipeline_run" not in st.session_state:
    st.session_state.pipeline_run = False
if "apex_results" not in st.session_state:
    st.session_state.apex_results = None
if "df_jobs_cache" not in st.session_state:
    st.session_state.df_jobs_cache = None
if "copilot_messages" not in st.session_state:
    st.session_state.copilot_messages = [
        {
            "role": "assistant",
            "content": "Hello! I am your Manhattan Mission Control AI Copilot. Run the pipeline first, then ask me to analyze OMB hiring lag, explain MCMC posteriors, write PostGIS joins, or interpret any forecast results."
        }
    ]

# ==========================================
# --- DATA INGESTION PIPELINES ---
# ==========================================

@st.cache_data(show_spinner=False, ttl=3600)
def scrape_historical_jids(start_jid: int, end_jid: int) -> pd.DataFrame:
    """Politely scrapes cityjobs.nyc.gov to capture expired/filled requisitions."""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    scraped_data = []

    for jid in range(start_jid, end_jid + 1):
        url = f"https://cityjobs.nyc.gov/job/anything-jid-{jid}"
        time.sleep(random.uniform(0.5, 1.5)) # Throttle to prevent IP ban
        
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                title_elem = soup.find('h1', class_='job-title') 
                job_title = title_elem.text.strip() if title_elem else "UNKNOWN TITLE"
                
                agency_elem = soup.find('span', class_='agency-name')
                agency_name = agency_elem.text.strip() if agency_elem else "UNKNOWN AGENCY"
                
                status = "Expired" if soup.find('div', class_='alert-expired') else "Active"
                
                scraped_data.append({
                    'job_id': str(jid),
                    'civil_service_title': job_title.upper(),
                    'agency': agency_name.upper(),
                    'Status': status,
                    'posting_date': (datetime.now() - relativedelta(months=6)).strftime('%Y-%m-%dT00:00:00')
                })
        except Exception:
            continue

    return pd.DataFrame(scraped_data)

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_socrata_data(url: str, params: dict) -> pd.DataFrame:
    """Paginates through Socrata API to bypass the 50k row limit."""
    headers = {"X-App-Token": SOCRATA_TOKEN} if SOCRATA_TOKEN else {}
    all_data, offset = [], 0
    limit = params.get("$limit", 50000)
    if "$order" not in params: params["$order"] = ":id" 
    
    try:
        while True:
            params["$offset"] = offset
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status() 
            chunk = response.json()
            if not chunk: break 
            all_data.extend(chunk)
            offset += limit
            if len(all_data) >= 200000: break # Hard cap for cloud memory limits
        return pd.DataFrame(all_data)
    except Exception as e:
        st.error(f"API Error: {e}")
        return pd.DataFrame()

# ==========================================
# --- MATHEMATICAL ENGINE ---
# ==========================================

def run_apex_math(df_jobs: pd.DataFrame, df_payroll: pd.DataFrame, max_lag: int = 12):
    """Executes the PyMC MCMC simulation and Prophet forecasting."""
    
    # 1. Build Timeseries
    df_jobs['posting_date'] = pd.to_datetime(df_jobs['posting_date'], errors='coerce')
    postings_ts = df_jobs.dropna(subset=['posting_date']).groupby(
        df_jobs['posting_date'].dt.to_period('M').dt.to_timestamp()
    ).size().rename('Postings')

    df_payroll = df_payroll.drop_duplicates(subset=['first_name', 'last_name', 'agency_start_date'])
    df_payroll['agency_start_date'] = pd.to_datetime(df_payroll['agency_start_date'], errors='coerce')
    starts_ts = df_payroll.dropna(subset=['agency_start_date']).groupby(
        df_payroll['agency_start_date'].dt.to_period('M').dt.to_timestamp()
    ).size().rename('Starts')

    df_ts = pd.concat([postings_ts, starts_ts], axis=1).fillna(0).sort_index()
    if df_ts.empty: return None

    df_ts['Postings_Smoothed'] = df_ts['Postings'].rolling(window=3, min_periods=1).mean()
    df_ts['Starts_Smoothed'] = df_ts['Starts'].rolling(window=3, min_periods=1).mean()

    # 2. Calculate Lag
    correlations = {lag: (df_ts['Postings_Smoothed'].corr(df_ts['Starts_Smoothed'].shift(-lag)) or 0) for lag in range(max_lag + 1)}
    best_lag = max(correlations, key=correlations.get) if correlations else 0

    # 3. Bayesian Inference
    predictor = df_ts['Postings_Smoothed'].shift(best_lag).fillna(0).values
    target = df_ts['Starts'].values 

    # Cloud-safe PyMC execution (cores=1 prevents Render threading crashes)
    with pm.Model() as _:
        alpha = pm.Normal('Baseline_Log', mu=0, sigma=5)
        beta = pm.Normal('Yield_Log', mu=0, sigma=5)
        mu = pm.math.exp(alpha + beta * predictor)
        pm.Poisson('Y_obs', mu=mu, observed=target)
        trace = pm.sample(1000, tune=1000, target_accept=0.9, cores=1, chains=2, return_inferencedata=True, progressbar=False)

    beta_mean = az.summary(trace, var_names=['Yield_Log']).loc['Yield_Log', 'mean']
    effective_yield_rate = float(np.exp(float(beta_mean)))

    # 4. Prophet Forecast (Explicit axis renaming prevents KeyError: 'index')
    df_prophet = df_ts.rename_axis('ds').reset_index()[['ds', 'Postings_Smoothed']].rename(columns={'Postings_Smoothed': 'y'})
    
    m_prophet = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m_prophet.fit(df_prophet)
    
    future = m_prophet.make_future_dataframe(periods=12, freq='MS')
    forecast = m_prophet.predict(future)
    forecast['predicted_hires'] = forecast['yhat'] * effective_yield_rate
    forecast['predicted_hires_date'] = forecast['ds'] + pd.DateOffset(months=best_lag)
    future_forecast = forecast[forecast['ds'] > df_ts.index[-1]]

    return {
        "df_ts": df_ts,
        "best_lag": best_lag,
        "yield_rate": effective_yield_rate,
        "future_forecast": future_forecast
    }

# ==========================================
# --- AI COPILOT ENGINE ---
# ==========================================

def build_copilot_system_prompt(results: dict | None, agency: str, title: str) -> str:
    lag = results["best_lag"] if results else "unknown"
    yield_rate = f"{results['yield_rate']:.2f}" if results else "unknown"
    if results:
        projected = int(results["future_forecast"]["predicted_hires"].sum())
    else:
        projected = "unknown"

    return f"""You are the Manhattan Mission Control AI — a Senior Data Architect and Civil Operations Strategist for New York City open datasets.
Your tone is futuristic, precise, and professional, matching an "Enterprise Apex Engine" aesthetic.
You have access to the currently calculated parameters from the Socrata Bayesian pipeline:
- Target Agency: "{agency}"
- Target Civil Service Title: "{title}"
- Optimized OMB Hiring Lag: {lag} months
- Bayesian Yield Multiplier (Postings → Starts): {yield_rate}x
- 12-Month Projected Hires: {projected}

Respond directly to the user's question. Include actual statistics or insights when relevant.
Keep responses highly scannable, Markdown-formatted, and use bullet points where helpful."""


def query_gemini_copilot(user_prompt: str, system_prompt: str, history: list) -> str:
    if not GEMINI_API_KEY:
        return (
            "**[OFFLINE MODE]** No `GEMINI_API_KEY` found in environment. "
            "Set the `GEMINI_API_KEY` secret and restart the app to enable live AI responses.\n\n"
            f"Your question was: *{user_prompt}*"
        )

    contents = []
    for msg in history[1:]:  # skip the initial system greeting
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.7}
    }

    try:
        resp = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            json=payload,
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"⚠️ Gemini API error: {e}"


# ==========================================
# --- FRONTEND UI ---
# ==========================================

def main():
    st.title("🚀 Manhattan Mission Control: Apex Engine")
    st.markdown("Unified Spatial & Predictive Hiring Pipeline for NYC")
    st.divider()

    # Sidebar Controls
    with st.sidebar:
        st.header("⚙️ Target Parameters")
        target_agency = st.text_input("Agency", value="DEPARTMENT OF TRANSPORTATION")
        target_title = st.text_input("Civil Service Title", value="PROJECT ANALYST")
        
        st.header("🕸️ Dark Matter Scraper")
        st.markdown("Specify a JID range to capture expired DCAS job postings.")
        scrape_start = st.number_input("Start JID", value=35710, step=1)
        scrape_end = st.number_input("End JID", value=35715, step=1)
        
        run_btn = st.button("Initialize Pipeline", type="primary", use_container_width=True)

    if run_btn:
        st.session_state.pipeline_run = True
        st.session_state.apex_results = None # Clear previous results

    if not st.session_state.pipeline_run:
        st.info("👈 Configure parameters in the sidebar and initialize the pipeline to begin.")
        return

    # Pipeline Execution (Only runs if we don't already have results cached in state)
    if st.session_state.apex_results is None:
        with st.status("Initializing Apex Pipeline...", expanded=True) as status:
            st.write("1. Harvesting dark matter (Scraping expired JIDs)...")
            df_scraped = scrape_historical_jids(int(scrape_start), int(scrape_end))
            
            st.write("2. Querying DCAS Socrata endpoints...")
            five_years_ago = (datetime.now() - relativedelta(years=5)).strftime('%Y-%m-%dT00:00:00')
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
                df_jobs['job_id'] = df_jobs['job_id'].astype(str)
                df_scraped['job_id'] = df_scraped['job_id'].astype(str)
                
                if target_agency != "ALL":
                    df_scraped = df_scraped[df_scraped['agency'].str.contains(target_agency, case=False, na=False)]
                if target_title != "ALL":
                    df_scraped = df_scraped[df_scraped['civil_service_title'].str.contains(target_title, case=False, na=False)]
                    
                df_jobs = pd.concat([df_jobs, df_scraped], ignore_index=True).drop_duplicates(subset=['job_id'])

            if df_jobs.empty or df_payroll.empty:
                status.update(label="Pipeline Failed", state="error")
                st.error("Insufficient data found for those parameters.")
                st.session_state.pipeline_run = False
                return

            st.write("3. Running PyMC Bayesian MCMC Simulation & Prophet ML...")
            st.session_state.apex_results = run_apex_math(df_jobs, df_payroll)
            st.session_state.df_jobs_cache = df_jobs # Cache for map plotting
            
            status.update(label="Pipeline Complete!", state="complete", expanded=False)

    results = st.session_state.apex_results

    if not results:
        st.error("Mathematical convergence failed. Timeline intersection may be empty.")
        st.session_state.pipeline_run = False
        return

    # Tab layout: Dashboard | AI Copilot
    tab_dash, tab_copilot = st.tabs(["📊 Dashboard", "🤖 AI Copilot"])

    with tab_dash:
        _render_dashboard(results, target_agency, target_title)

    with tab_copilot:
        _render_copilot(results, target_agency, target_title)


def _render_dashboard(results: dict, target_agency: str, target_title: str):
    """Renders the main analytics dashboard."""
    # Dashboard Rendering
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Calculated OMB Review Lag", value=f"{results['best_lag']} Months")
    with col2:
        st.metric(label="Bayesian Yield Multiplier", value=f"{results['yield_rate']:.2f}x")

    st.divider()

    # Chart 1: Historical Pipeline
    st.subheader("1. Administrative Velocity & Signal Processing")
    fig_pipeline = go.Figure()
    fig_pipeline.add_trace(go.Scatter(x=results['df_ts'].index, y=results['df_ts']['Postings_Smoothed'], name='Smoothed Postings', line=dict(color='#1f77b4', width=3)))
    fig_pipeline.add_trace(go.Scatter(x=results['df_ts'].index, y=results['df_ts']['Starts_Smoothed'], name='Smoothed Hires', line=dict(color='#2ca02c', width=3)))
    fig_pipeline.update_layout(template="plotly_white", height=400, hovermode="x unified")
    st.plotly_chart(fig_pipeline, use_container_width=True)

    # Chart 2: Machine Learning Forecast
    st.subheader("2. Bayesian Inference & Forecasting")
    ff = results['future_forecast']
    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(x=ff['ds'], y=ff['yhat'], name='Forecasted Postings', line=dict(color='#1f77b4', width=2, dash='dot')))
    fig_forecast.add_trace(go.Scatter(x=ff['predicted_hires_date'], y=ff['predicted_hires'], name=f"Forecasted Hires (+{results['best_lag']}m Lag)", line=dict(color='#2ca02c', width=2, dash='dot')))
    fig_forecast.update_layout(template="plotly_white", height=400, hovermode="x unified")
    st.plotly_chart(fig_forecast, use_container_width=True)

    # Geospatial Map
    df_jobs_map = st.session_state.df_jobs_cache
    if df_jobs_map is not None and 'work_location' in df_jobs_map.columns:
        st.divider()
        st.subheader("3. Spatial Requisition Density")
        st.caption("Aggregated postings parsed from text-based DCAS work location data.")
        
        # Simple Borough Geocoder fallback for Socrata text locations
        borough_coords = {
            "MANHATTAN": [40.7831, -73.9712], "BROOKLYN": [40.6782, -73.9442],
            "QUEENS": [40.7282, -73.7949], "BRONX": [40.8448, -73.8648],
            "STATEN ISLAND": [40.5795, -74.1502], "UNKNOWN": [40.7128, -74.0060]
        }
        
        location_counts = df_jobs_map['work_location'].value_counts().reset_index()
        location_counts.columns = ['Location', 'Count']
        
        m = folium.Map(location=[40.7128, -74.0060], zoom_start=10, tiles="CartoDB dark_matter")
        for _, row in location_counts.iterrows():
            loc_str = str(row['Location']).upper()
            base_coord = borough_coords["UNKNOWN"]
            for b_name, coords in borough_coords.items():
                if b_name in loc_str:
                    base_coord = coords
                    break
            
            # Apply slight jitter so multiple addresses in the same borough don't overlap perfectly
            jitter_lat = base_coord[0] + np.random.uniform(-0.02, 0.02)
            jitter_lon = base_coord[1] + np.random.uniform(-0.02, 0.02)
            
            folium.CircleMarker(
                location=[jitter_lat, jitter_lon],
                radius=min(max(row['Count'] * 2, 5), 20), # Scale bubble by volume
                popup=f"<strong>{row['Location']}</strong><br>Requisitions: {row['Count']}",
                color="#3186cc",
                fill=True,
                fill_color="#3186cc"
            ).add_to(m)
            
        components.html(m._repr_html_(), height=500)


def _render_copilot(results: dict | None, target_agency: str, target_title: str):
    """Renders the Gemini AI Copilot chat panel."""
    system_prompt = build_copilot_system_prompt(results, target_agency, target_title)

    if not GEMINI_API_KEY:
        st.warning(
            "**AI Copilot is in offline mode.** "
            "Set the `GEMINI_API_KEY` environment variable to enable live responses.",
            icon="⚠️"
        )

    st.caption("Ask me to analyze OMB lag, explain MCMC posteriors, write PostGIS joins, or interpret any forecast data.")

    # Quick-action chips
    chips = [
        ("OMB Latency Analysis", "Can you analyze why there is an OMB hiring lag bottleneck on the active data records?"),
        ("Explain MCMC Priors", "Explain what prior distributions and parameter bounds are used in our Bayesian model."),
        ("PostGIS Join Code", "Write a high-performance PostGIS query to join city jobs location with complaint borough coordinates."),
        ("Forecast Interpretation", "Interpret the 12-month hire forecast and flag any anomalies I should be aware of."),
    ]

    chip_cols = st.columns(len(chips))
    for col, (label, query) in zip(chip_cols, chips):
        if col.button(label, key=f"chip_{label}", use_container_width=True):
            st.session_state.copilot_messages.append({"role": "user", "content": query})
            with st.spinner("Thinking..."):
                reply = query_gemini_copilot(query, system_prompt, st.session_state.copilot_messages)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})

    st.divider()

    # Render message history
    for msg in st.session_state.copilot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ask about the pipeline, data quality, MCMC, or write custom queries..."):
        st.session_state.copilot_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Contacting Gemini..."):
                reply = query_gemini_copilot(user_input, system_prompt, st.session_state.copilot_messages)
            st.markdown(reply)
            st.session_state.copilot_messages.append({"role": "assistant", "content": reply})

    # Clear chat button
    if st.button("🗑️ Clear Chat", key="clear_copilot"):
        st.session_state.copilot_messages = [
            {"role": "assistant", "content": "Chat cleared. Ready for new queries."}
        ]
        st.rerun()


if __name__ == "__main__":
    main()
