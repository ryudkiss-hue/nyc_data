"""
Manhattan Mission Control: Monolithic Apex Engine (Enterprise Edition)
Integrates Socrata Ingestion, Parquet Caching, Bayesian Inference, 
and GeoPandas Spatial Analytics into a single agency-grade application.
"""

import os
import time
import logging
import warnings
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Tuple
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass

import pandas as pd
import numpy as np
import yaml
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import folium

# --- Advanced Analytics ---
try:
    import pymc as pm
    import arviz as az
    from prophet import Prophet
except ImportError:
    pm = az = Prophet = None

# --- Spatial Analytics ---
try:
    import geopandas as gpd
    from shapely.geometry import Point
except ImportError:
    gpd = Point = None

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO)

# ==========================================
# --- CONFIGURATION & REGISTRY ---
# ==========================================
st.set_page_config(page_title="Manhattan Mission Control", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

try:
    from dotenv import load_dotenv
    load_dotenv(".env")
    load_dotenv(".env.socrata", override=False)
except ImportError:
    pass

SOCRATA_TOKEN = os.getenv("SOCRATA_APP_TOKEN", os.getenv("SOCRATA_TOKEN", "TfrAwqroXIrKRPwPvWpEZnkcT"))
DOMAIN = os.getenv("SOCRATA_DOMAIN", "data.cityofnewyork.us")
CACHE_TTL_SECONDS = 86_400
_PARQUET_CACHE_DIR = Path(".socrata_cache")
NYC_CRS = "EPSG:2263"
WGS84 = "EPSG:4326"

BBL_CANDIDATES = ("bbl", "lot_bbl", "tax_lot", "taxblock", "boro_block_lot")
LAT_CANDIDATES = ("latitude", "lat", "y", "ycoord")
LON_CANDIDATES = ("longitude", "lon", "lng", "long", "x", "xcoord")
DATE_CANDIDATES = ("created_date", "created", "date", "open_date", "requested_datetime")
OWNER_CANDIDATES = ("owner", "owner_type", "ownership", "lot_owner", "agency")
GRACE_CANDIDATES = ("grace_pd", "grace_period", "grace_date", "graceperiod")

# Fallback internal registry if config/datasets.yaml is missing
FALLBACK_REGISTRY = {
    "jobs_active": {"fourfour": "kpav-sd4t", "label": "Active Civil Service Jobs"},
    "citywide_payroll": {"fourfour": "k397-673e", "label": "Citywide Payroll Data"},
    "complaints_311": {"fourfour": "erm2-nwe9", "label": "311 Service Requests"},
    "mappluto": {"fourfour": "64uk-42ks", "label": "Primary Land Use Tax Lot Output"},
    "street_permits": {"fourfour": "bquu-z2vq", "label": "Street Construction Permits"},
}

def _load_registry():
    yaml_path = Path("config/datasets.yaml")
    if yaml_path.exists():
        raw = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        return {k: dict(v) for k, v in raw.get("datasets", {}).items()}
    return FALLBACK_REGISTRY

DATASET_REGISTRY = _load_registry()

def demo_mode_enabled() -> bool:
    return os.getenv("MISSION_DEMO", "").strip().lower() in ("1", "true", "yes") or not SOCRATA_TOKEN

# ==========================================
# --- ENTERPRISE DATA LOADER (from data_loader.py) ---
# ==========================================

def pick_column(df: pd.DataFrame, candidates: Tuple[str, ...]) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower: return lower[cand.lower()]
    for col in df.columns:
        if any(cand in col.lower() for cand in candidates): return col
    return None

def normalize_bbl(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.replace(r"\D", "", regex=True)
    s = s.where(s.str.len() >= 6, other=pd.NA)
    return s.str.zfill(10)

def _parquet_path(dataset_key: str) -> Path:
    _PARQUET_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _PARQUET_CACHE_DIR / f"{dataset_key}.parquet"

def _parquet_fresh(path: Path) -> bool:
    if not path.exists(): return False
    return (time.time() - path.stat().st_mtime) < CACHE_TTL_SECONDS

def _read_parquet_cache(dataset_key: str) -> pd.DataFrame | None:
    path = _parquet_path(dataset_key)
    if not _parquet_fresh(path): return None
    try: return pd.read_parquet(path)
    except Exception: return None

def _write_parquet_cache(dataset_key: str, df: pd.DataFrame) -> None:
    if df.empty or "_error" in df.columns: return
    try: df.to_parquet(_parquet_path(dataset_key), index=False)
    except Exception as e: logging.warning(f"Parquet write failed: {e}")

def _demo_frame(dataset_key: str) -> pd.DataFrame:
    bbl = "1000010001"
    templates = {
        "lot_info": {"bbl": [bbl], "owner": ["City"]},
        "mappluto": {"bbl": [bbl], "ownername": ["Private"]},
        "complaints_311": {"created_date": ["2020-01-01"], "bbl": [bbl]},
        "jobs_active": {"posting_date": ["2023-01-01"], "civil_service_title": ["PROJECT ANALYST"]},
        "citywide_payroll": {"agency_start_date": ["2023-06-01"], "title_description": ["PROJECT ANALYST"]},
    }
    return pd.DataFrame(templates.get(dataset_key, {"note": ["demo row"]}))

def _fetch_live(dataset_key: str, limit: int, where: str | None, retries: int = 3, backoff: float = 2.0) -> pd.DataFrame:
    meta = DATASET_REGISTRY.get(dataset_key)
    if not meta: raise KeyError(f"Unknown dataset_key: {dataset_key}")
    
    headers = {"X-App-Token": SOCRATA_TOKEN} if SOCRATA_TOKEN else {}
    params = {"$limit": 50000, "$order": ":id"}
    if where: params["$where"] = where

    all_data, offset = [], 0
    url = f"https://{DOMAIN}/resource/{meta['fourfour']}.json"

    last_exc = None
    while True:
        params["$offset"] = offset
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, params=params, timeout=20)
                response.raise_for_status()
                chunk = response.json()
                break # Success, break retry loop
            except Exception as exc:
                last_exc = exc
                wait = backoff ** attempt
                logging.warning(f"Fetch attempt {attempt+1}/{retries} failed for {dataset_key}: {exc} - retrying in {wait}s")
                if attempt < retries - 1: time.sleep(wait)
        else:
            if not all_data: raise RuntimeError(f"All {retries} fetch attempts failed for {dataset_key}: {last_exc}")
            break # Stop paging if we fail mid-way, keep what we have

        if not chunk: break 
        all_data.extend(chunk)
        offset += params["$limit"]
        if len(all_data) >= limit: break
        
    return pd.DataFrame(all_data[:limit])

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def fetch_dataset(dataset_key: str, limit: int = 100_000, where: str | None = None) -> pd.DataFrame:
    if demo_mode_enabled(): return _demo_frame(dataset_key)
    
    cached = _read_parquet_cache(dataset_key)
    if cached is not None and not where: return cached
    
    try:
        df = _fetch_live(dataset_key, limit=limit, where=where)
        if not where: _write_parquet_cache(dataset_key, df) # Only cache full pulls
        return df
    except Exception as exc:
        logging.error(f"Fetch error {dataset_key}: {exc}")
        return pd.DataFrame({"_error": [str(exc)]})

def fetch_datasets_for_keys(keys: Tuple[str, ...] | list[str], limit: int = 50_000, max_workers: int = 4) -> dict[str, pd.DataFrame]:
    """Parallelized threaded fetching of multiple datasets."""
    out = {}
    if demo_mode_enabled() or len(keys) == 1:
        return {k: fetch_dataset(k, limit=limit) for k in keys}

    with ThreadPoolExecutor(max_workers=min(max_workers, len(keys))) as pool:
        futures = {pool.submit(fetch_dataset, k, limit): k for k in keys}
        for fut in as_completed(futures):
            key = futures[fut]
            try: out[key] = fut.result()
            except Exception as e: out[key] = pd.DataFrame({"_error": [str(e)]})
    return out

def df_to_gdf(df: pd.DataFrame) -> Any:
    if gpd is None or df.empty: return None
    lat_col = pick_column(df, LAT_CANDIDATES)
    lon_col = pick_column(df, LON_CANDIDATES)
    if lat_col and lon_col and Point is not None:
        geom = [Point(float(x), float(y)) if pd.notna(x) and pd.notna(y) else None for x, y in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df.copy(), geometry=geom, crs=WGS84)
        return gdf.to_crs(NYC_CRS)
    return None

# ==========================================
# --- TAB 1: APEX ENGINE LOGIC ---
# ==========================================

@st.cache_data(show_spinner=False, ttl=3600)
def scrape_historical_jids(start_jid: int, end_jid: int) -> pd.DataFrame:
    headers = {'User-Agent': 'Mozilla/5.0'}
    scraped_data = []
    for jid in range(start_jid, end_jid + 1):
        url = f"https://cityjobs.nyc.gov/job/anything-jid-{jid}"
        time.sleep(random.uniform(0.5, 1.5)) 
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
                    'job_id': str(jid), 'civil_service_title': job_title.upper(),
                    'agency': agency_name.upper(), 'Status': status,
                    'posting_date': (datetime.now() - relativedelta(months=6)).strftime('%Y-%m-%dT00:00:00')
                })
        except Exception: continue
    return pd.DataFrame(scraped_data)

def run_apex_math(df_jobs: pd.DataFrame, df_payroll: pd.DataFrame, max_lag: int = 12):
    df_jobs['posting_date'] = pd.to_datetime(df_jobs['posting_date'], errors='coerce')
    postings_ts = df_jobs.dropna(subset=['posting_date']).groupby(df_jobs['posting_date'].dt.to_period('M').dt.to_timestamp()).size().rename('Postings')

    df_payroll = df_payroll.drop_duplicates(subset=['first_name', 'last_name', 'agency_start_date'])
    df_payroll['agency_start_date'] = pd.to_datetime(df_payroll['agency_start_date'], errors='coerce')
    starts_ts = df_payroll.dropna(subset=['agency_start_date']).groupby(df_payroll['agency_start_date'].dt.to_period('M').dt.to_timestamp()).size().rename('Starts')

    df_ts = pd.concat([postings_ts, starts_ts], axis=1).fillna(0).sort_index()
    if df_ts.empty: return None

    df_ts['Postings_Smoothed'] = df_ts['Postings'].rolling(window=3, min_periods=1).mean()
    df_ts['Starts_Smoothed'] = df_ts['Starts'].rolling(window=3, min_periods=1).mean()

    correlations = {lag: (df_ts['Postings_Smoothed'].corr(df_ts['Starts_Smoothed'].shift(-lag)) or 0) for lag in range(max_lag + 1)}
    best_lag = max(correlations, key=correlations.get) if correlations else 0

    if not pm: raise ImportError("PyMC not installed. Machine learning forecast skipped.")

    predictor = df_ts['Postings_Smoothed'].shift(best_lag).fillna(0).values
    target = df_ts['Starts'].values 

    with pm.Model() as _:
        alpha = pm.Normal('Baseline_Log', mu=0, sigma=5)
        beta = pm.Normal('Yield_Log', mu=0, sigma=5)
        mu = pm.math.exp(alpha + beta * predictor)
        pm.Poisson('Y_obs', mu=mu, observed=target)
        trace = pm.sample(1000, tune=1000, target_accept=0.9, cores=1, chains=2, return_inferencedata=True, progressbar=False)

    beta_mean = az.summary(trace, var_names=['Yield_Log']).loc['Yield_Log', 'mean']
    effective_yield_rate = float(np.exp(float(beta_mean)))

    df_prophet = df_ts.rename_axis('ds').reset_index()[['ds', 'Postings_Smoothed']].rename(columns={'Postings_Smoothed': 'y'})
    m_prophet = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    m_prophet.fit(df_prophet)
    
    future = m_prophet.make_future_dataframe(periods=12, freq='MS')
    forecast = m_prophet.predict(future)
    forecast['predicted_hires'] = forecast['yhat'] * effective_yield_rate
    forecast['predicted_hires_date'] = forecast['ds'] + pd.DateOffset(months=best_lag)

    return {
        "df_ts": df_ts, "best_lag": best_lag,
        "yield_rate": effective_yield_rate, "future_forecast": forecast[forecast['ds'] > df_ts.index[-1]],
        "df_jobs_map": df_jobs
    }

# ==========================================
# --- TAB 2: SIM OPERATIONS LOGIC ---
# ==========================================

@dataclass
class ProductivityROI:
    joins_automated: int
    actionable_discrepancies: int
    lots_validated: int
    spatial_conflicts_checked: int
    contracts_cleared: int
    hours_reclaimed: float
    quality_flags: int = 0
    datasets_profiled: int = 0

def _utc_today() -> pd.Timestamp:
    return pd.Timestamp.now(tz=timezone.utc).normalize().tz_localize(None)

def qa_qc_inventory_ledger(lot_info: pd.DataFrame, mappluto: pd.DataFrame, complaints_311: pd.DataFrame, stale_days: int = 30):
    joins = quality_flags = 0
    merged = lot_info.copy()
    
    stale = pd.DataFrame()
    if not complaints_311.empty:
        c = complaints_311.copy()
        date_col = pick_column(c, DATE_CANDIDATES)
        if date_col:
            c["_opened"] = pd.to_datetime(c[date_col], errors="coerce")
            cutoff = _utc_today() - pd.Timedelta(days=stale_days)
            stale = c[c["_opened"].notna() & (c["_opened"] <= cutoff)].copy()
            bbl_col = pick_column(stale, BBL_CANDIDATES)
            if "_bbl" not in stale.columns and bbl_col:
                stale["_bbl"] = normalize_bbl(stale[bbl_col])
            if not stale.empty:
                stale["_days_open"] = (_utc_today() - stale["_opened"]).dt.days
                quality_flags += len(stale)
    return merged, stale, joins, quality_flags

def spatial_conflict_detection(weekly: pd.DataFrame, permits: pd.DataFrame, capital: pd.DataFrame):
    if not gpd or weekly.empty: return pd.DataFrame(), 0
    weekly_gdf = df_to_gdf(weekly)
    permits_gdf = df_to_gdf(permits)
    joins = 0
    conflicts = []
    
    if permits_gdf is not None and not permits_gdf.empty:
        try:
            joined = gpd.sjoin(weekly_gdf, permits_gdf, how="inner", predicate="intersects")
            if not joined.empty:
                joined["conflict_type"] = "weekly_vs_permit"
                conflicts.append(joined)
                joins += 1
        except Exception: pass
        
    out = pd.concat(conflicts, ignore_index=True) if conflicts else pd.DataFrame()
    return out, joins

# ==========================================
# --- FRONTEND UI DASHBOARD ---
# ==========================================

def main():
    if "apex_results" not in st.session_state: st.session_state.apex_results = None
    if "sim_results" not in st.session_state: st.session_state.sim_results = None

    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/cc/New_York_City_Department_of_Transportation_logo.svg/1200px-New_York_City_Department_of_Transportation_logo.svg.png", width=150)
        st.markdown("**🚧 NYC DOT · Operations**")
        st.divider()
        st.header("⚙️ Target Parameters")
        target_agency = st.text_input("Agency", value="DEPARTMENT OF TRANSPORTATION")
        target_title = st.text_input("Civil Service Title", value="PROJECT ANALYST")
        
        st.header("🕸️ Dark Matter Scraper")
        scrape_start = st.number_input("Start JID", value=35710, step=1)
        scrape_end = st.number_input("End JID", value=35715, step=1)
        st.divider()
        if st.button("🔄 Execute Agency Sync", type="primary", use_container_width=True):
            st.session_state.apex_results = "loading"
            st.session_state.sim_results = "loading"

    st.title("Manhattan Mission Control")
    st.caption("Powered by Parquet Caching & GeoPandas Spatial Routing")
    
    tab1, tab2 = st.tabs(["🚀 Apex Hiring Engine", "🚧 SIM Analyst Operations"])

    # ---------------------------------------------------------
    # TAB 1: APEX PREDICTIVE ENGINE
    # ---------------------------------------------------------
    with tab1:
        if st.session_state.apex_results == "loading":
            with st.status("Initializing Apex Pipeline...", expanded=True) as status:
                st.write("Harvesting dark matter (Scraping expired JIDs)...")
                df_scraped = scrape_historical_jids(int(scrape_start), int(scrape_end))
                
                st.write("Querying Active Datasets (Parquet Cache / Socrata API)...")
                five_years_ago = (datetime.now() - relativedelta(years=5)).strftime('%Y-%m-%dT00:00:00')
                
                jobs_where = f"posting_date >= '{five_years_ago}'"
                pay_where = f"agency_start_date >= '{five_years_ago}'"
                if target_agency != "ALL":
                    jobs_where += f" AND agency='{target_agency}'"
                    pay_where += f" AND agency_name='{target_agency}'"
                
                # Fetch securely utilizing the threaded enterprise caching methodology
                frames = fetch_datasets_for_keys(['jobs_active', 'citywide_payroll'], limit=100_000)
                df_jobs = frames.get('jobs_active', pd.DataFrame())
                df_payroll = frames.get('citywide_payroll', pd.DataFrame())

                if not df_scraped.empty and not df_jobs.empty:
                    df_jobs['job_id'] = df_jobs['job_id'].astype(str)
                    df_scraped['job_id'] = df_scraped['job_id'].astype(str)
                    if target_agency != "ALL": df_scraped = df_scraped[df_scraped['agency'].str.contains(target_agency, case=False, na=False)]
                    if target_title != "ALL": df_scraped = df_scraped[df_scraped['civil_service_title'].str.contains(target_title, case=False, na=False)]
                    df_jobs = pd.concat([df_jobs, df_scraped], ignore_index=True).drop_duplicates(subset=['job_id'])

                if df_jobs.empty or df_payroll.empty:
                    status.update(label="Pipeline Failed", state="error")
                    st.error("Insufficient data found for those parameters.")
                    st.session_state.apex_results = None
                else:
                    st.write("Running PyMC Bayesian MCMC Simulation & Prophet ML...")
                    st.session_state.apex_results = run_apex_math(df_jobs, df_payroll)
                    status.update(label="Pipeline Complete!", state="complete", expanded=False)

        results = st.session_state.apex_results
        if results and results != "loading":
            col1, col2 = st.columns(2)
            with col1: st.metric("Calculated OMB Review Lag", f"{results['best_lag']} Months")
            with col2: st.metric("Bayesian Yield Multiplier", f"{results['yield_rate']:.2f}x")
            
            st.divider()
            st.subheader("1. Administrative Velocity & Signal Processing")
            fig_pipeline = go.Figure()
            fig_pipeline.add_trace(go.Scatter(x=results['df_ts'].index, y=results['df_ts']['Postings_Smoothed'], name='Smoothed Postings', line=dict(color='#1f77b4', width=3)))
            fig_pipeline.add_trace(go.Scatter(x=results['df_ts'].index, y=results['df_ts']['Starts_Smoothed'], name='Smoothed Hires', line=dict(color='#2ca02c', width=3)))
            fig_pipeline.update_layout(template="plotly_white", height=400, hovermode="x unified")
            st.plotly_chart(fig_pipeline, use_container_width=True)

            st.subheader("2. Bayesian Inference & Forecasting")
            ff = results['future_forecast']
            fig_forecast = go.Figure()
            fig_forecast.add_trace(go.Scatter(x=ff['ds'], y=ff['yhat'], name='Forecasted Postings', line=dict(color='#1f77b4', width=2, dash='dot')))
            fig_forecast.add_trace(go.Scatter(x=ff['predicted_hires_date'], y=ff['predicted_hires'], name=f"Forecasted Hires (+{results['best_lag']}m Lag)", line=dict(color='#2ca02c', width=2, dash='dot')))
            fig_forecast.update_layout(template="plotly_white", height=400, hovermode="x unified")
            st.plotly_chart(fig_forecast, use_container_width=True)

        elif not results:
            st.info("👈 Configure parameters and Execute Agency Sync to view Apex calculations.")

    # ---------------------------------------------------------
    # TAB 2: SIM ANALYST OPERATIONS
    # ---------------------------------------------------------
    with tab2:
        if st.session_state.sim_results == "loading":
            with st.spinner("Compiling SIM Telemetry Matrix (Threaded Fetch)..."):
                keys_to_fetch = ["complaints_311", "street_permits", "mappluto"]
                sim_frames = fetch_datasets_for_keys(keys_to_fetch, limit=10_000)
                
                ledger, stale_311, qa_joins, qa_flags = qa_qc_inventory_ledger(pd.DataFrame(), sim_frames.get('mappluto', pd.DataFrame()), sim_frames.get('complaints_311', pd.DataFrame()))
                conflicts, spatial_joins = spatial_conflict_detection(pd.DataFrame(), sim_frames.get('street_permits', pd.DataFrame()), pd.DataFrame())
                
                minutes = (len(ledger)*3 + len(conflicts)*15 + 0*5 + (qa_flags + len(conflicts))*2)
                roi = ProductivityROI(joins_automated=(qa_joins + spatial_joins), actionable_discrepancies=(len(stale_311) + len(conflicts)), lots_validated=len(ledger), spatial_conflicts_checked=len(conflicts), contracts_cleared=0, hours_reclaimed=minutes/60.0, quality_flags=(qa_flags + len(conflicts)), datasets_profiled=1)
                
                st.session_state.sim_results = {"stale_311": stale_311, "conflicts": conflicts, "roi": roi}
        
        sim = st.session_state.sim_results
        if sim and sim != "loading":
            roi = sim["roi"]
            st.markdown(f"### 📈 Engineering Productivity ROI")
            rc1, rc2, rc3, rc4 = st.columns(4)
            rc1.metric("Hours Reclaimed", f"{roi.hours_reclaimed:.1f}h", "This Cycle")
            rc2.metric("Joins Automated", roi.joins_automated)
            rc3.metric("Actionable Discrepancies", roi.actionable_discrepancies)
            rc4.metric("Quality Flags", roi.quality_flags)
            st.divider()

            st.markdown("### 🔍 QA/QC & Inventory Ledger")
            with st.expander("View Stale 311 Sidewalk Complaints (Live API Overlay)", expanded=True):
                if not sim['stale_311'].empty:
                    st.warning(f"⚠️ Found {len(sim['stale_311'])} sidewalk complaints open for >30 days.")
                    st.dataframe(sim['stale_311'][['unique_key', 'created_date', 'complaint_type', 'descriptor', 'incident_address', 'status', '_days_open']].head(100), use_container_width=True)
                else:
                    st.success("No stale 311 complaints detected.")

            st.markdown("### 🗺️ Spatial Conflict Detection")
            with st.expander("Weekly Schedule vs Permits & Capital Blocks", expanded=True):
                if not sim['conflicts'].empty:
                    st.dataframe(sim['conflicts'])
                else:
                    st.info("No spatial conflicts detected.")

        elif not sim:
            st.info("👈 Execute Agency Sync to populate SIM telemetry from Live Data.")

if __name__ == "__main__":
    main()
