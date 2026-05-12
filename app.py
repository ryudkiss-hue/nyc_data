"""
NYC DOT Data Assistant — Full-Coverage Streamlit App
Incorporates every socrata_toolkit module with graceful fallbacks.
"""

# ── Standard lib ─────────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import duckdb, requests, os, json, io, math, textwrap, traceback
import concurrent.futures
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="NYC DOT Data Assistant",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:#0f1117;}
section[data-testid="stSidebar"]{background:#141824;border-right:1px solid #1e2d45;}
.stMetric{background:#1a2235;border-radius:10px;padding:12px;border:1px solid #1e2d45;}
.pill-green{display:inline-block;padding:3px 10px;border-radius:16px;background:#064e3b;color:#6ee7b7;font-size:.8rem;font-weight:600;}
.pill-yellow{display:inline-block;padding:3px 10px;border-radius:16px;background:#78350f;color:#fcd34d;font-size:.8rem;font-weight:600;}
.pill-red{display:inline-block;padding:3px 10px;border-radius:16px;background:#7f1d1d;color:#fca5a5;font-size:.8rem;font-weight:600;}
.card{background:#1a2235;border:1px solid #1e2d45;border-radius:12px;padding:1.2rem;margin:.6rem 0;}
.status-green{border-left:4px solid #10b981;background:#052e16;padding:8px 12px;border-radius:4px;margin:4px 0;}
.status-yellow{border-left:4px solid #f59e0b;background:#451a03;padding:8px 12px;border-radius:4px;margin:4px 0;}
.status-red{border-left:4px solid #ef4444;background:#450a0a;padding:8px 12px;border-radius:4px;margin:4px 0;}
.kanban-col{background:#141824;border-radius:10px;padding:10px;min-height:180px;}
.task-card{border:1px solid #1e2d45;border-radius:8px;padding:10px;margin:6px 0;background:#1a2235;}
.card:hover{border-color:#3b82f6;box-shadow:0 0 15px rgba(59,130,246,0.3);transform:translateY(-2px);transition:all 0.3s ease;}
.vibrant-blue{background:linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);}
.vibrant-green{background:linear-gradient(135deg, #064e3b 0%, #10b981 100%);}
.vibrant-purple{background:linear-gradient(135deg, #4c1d95 0%, #8b5cf6 100%);}
</style>""", unsafe_allow_html=True)

# ── Toolkit imports (all graceful) ────────────────────────────────────────────
def _try(fn):
    try: return fn()
    except Exception: return None

HAS = {}

try:
    from socrata_toolkit.analysis import MetricsTracker, compute_program_dashboard
    HAS["program"] = True
except Exception: HAS["program"] = False

try:
    from socrata_toolkit.analysis import detect_all_outliers, correlation_analysis
    HAS["advanced"] = True
except Exception: HAS["advanced"] = False

try:
    from socrata_toolkit.analysis import InsightsEngine
    HAS["insights"] = True
except Exception: HAS["insights"] = False

try:
    from socrata_toolkit.analysis import extract_term_frequencies, extract_patterns
    HAS["text"] = True
except Exception: HAS["text"] = False

try:
    from socrata_toolkit.analysis import validate_required_columns, validate_geospatial_bounds, profile_dataframe, detect_anomalies
    HAS["validation"] = True
except Exception: HAS["validation"] = False

try:
    from socrata_toolkit.analysis import compute_sla_metrics, flag_sla_violations
    HAS["sla"] = True
except Exception: HAS["sla"] = False

try:
    from socrata_toolkit.analysis import compute_freshness_score
    HAS["freshness"] = True
except Exception: HAS["freshness"] = False

try:
    from socrata_toolkit.governance import compute_quality_score, AuditTrail, AuditEvent, ActionType
    HAS["governance"] = True
    HAS["audit"] = True
except Exception: HAS["governance"] = False; HAS["audit"] = False

try:
    from socrata_toolkit.core import SchemaRegistry, SchemaValidator, search_nyc_datasets, generate_data_dictionary
    HAS["schema"] = True
    HAS["discovery"] = True
except Exception: HAS["schema"] = False; HAS["discovery"] = False

try:
    from socrata_toolkit.engineering import (
        prioritize_construction_list, classify_scope, flag_ada_locations,
        summarize_construction_list, export_construction_list,
        analyze_contract_progress, budget_analysis, productivity_metrics,
        borough_comparison_table, estimate_costs, summarize_costs,
        forecast_budget, score_contractors
    )
    HAS["construction"] = True
    HAS["contracts"] = True
    HAS["borough"] = True
    HAS["cost"] = True
    HAS["forecast"] = True
    HAS["scorecards"] = True
except Exception: HAS["construction"] = False

try:
    from socrata_toolkit.spatial import SpatialVisualization, cluster_locations, compute_hotspots
    from streamlit_folium import st_folium
    HAS["spatial"] = True
    HAS["spatial_analytics"] = True
except Exception: HAS["spatial"] = False

try:
    from socrata_toolkit.pipeline import (
        ingest_311_complaints, detect_changes, deduplicate_dataframe,
        ExcelWorkbookBuilder, create_pivot_table, vlookup,
        export_for_tableau, export_for_powerbi, create_presentation,
        SQLQueryBuilder, dataframe_to_create_table, export_as_sql_file,
        export_graph, generate_contract_report, generate_inquiry_response,
        generate_program_report, generate_pdf_report
    )
    HAS["complaints"] = True
    HAS["cdc"] = True
    HAS["dedupe"] = True
    HAS["excel"] = True
    HAS["bi"] = True
    HAS["sql_int"] = True
    HAS["graph"] = True
    HAS["reports"] = True
    HAS["pdf"] = True
except Exception: HAS["complaints"] = False

try:
    from socrata_toolkit.ai import (
        quantum_search, SearchCriteria, analyze_grover_circuit,
        optimize_crew_assignment, optimize_repair_route, QuantumConfig,
        SocrataLLMChatbot, SQLQueryEngine,
        enrich_construction_list, triage_complaints
    )
    HAS["quantum"] = True
    HAS["llm"] = True
    HAS["nlp"] = True
except Exception: HAS["quantum"] = False

try:
    from socrata_toolkit.governance import AlertManager, evaluate_rules
    HAS["alerts"] = True
except Exception: HAS["alerts"] = False

try:
    from socrata_toolkit.core import SocrataClient
    HAS["client"] = True
except Exception: HAS["client"] = False

try:
    from socrata_toolkit.spatial import detect_construction_conflicts
    HAS["conflict"] = True
except Exception: HAS["conflict"] = False

try:
    import socrata_toolkit.cleaning as clean
    HAS["cleaning"] = True
except Exception: HAS["cleaning"] = False
except Exception: HAS["cleaning"] = False



# ── DB & session helpers ──────────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return duckdb.connect("nyc_data.db")
db = get_db()

def loaded_tables():
    try: return [r[0] for r in db.execute("SHOW TABLES").fetchall()]
    except: return []

def get_df(table=None):
    if table and table in loaded_tables():
        try: return db.execute(f'SELECT * FROM "{table}"').df()
        except: pass
    return st.session_state.get("current_df")

def set_df(df, label="uploaded"):
    st.session_state["current_df"] = df
    st.session_state["current_label"] = label

def upload_widget(label="Upload CSV/Excel", key="up"):
    f = st.file_uploader(label, type=["csv","xlsx"], key=key)
    if f:
        df = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
        set_df(df, f.name)
        st.success(f"Loaded {len(df):,} rows")
        return df
    return st.session_state.get("current_df")

def active_df_selector(key="sel"):
    tables = loaded_tables()
    opts = ["(session/uploaded)"] + tables
    sel = st.selectbox("Dataset", opts, key=key)
    return get_df(sel) if sel != "(session/uploaded)" else st.session_state.get("current_df")

def _badge(s):
    cls = {"green":"pill-green","yellow":"pill-yellow","red":"pill-red"}.get(s,"pill-green")
    return f'<span class="{cls}">{s.upper()}</span>'

# ── Socrata fetch ─────────────────────────────────────────────────────────────
# ── Socrata fetch ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def socrata_search(q, domain="data.cityofnewyork.us", cat=None, lim=50):
    """Search for datasets using SocrataClient."""
    try:
        client = SocrataClient()
        return client.search(query=q, domain=domain, category=cat, limit=lim)
    except Exception as e:
        st.error(f"Search error: {e}")
        return []

def parallel_fetch(ds_id, limit, token="", domain="data.cityofnewyork.us"):
    """Fetch data using SocrataClient's parallel fetch."""
    try:
        from socrata_toolkit.core import SocrataConfig
        config = SocrataConfig(app_token=token)
        client = SocrataClient(config=config)
        def get_odata_url(self, domain: str, fourfour: str) -> str:
            """Generate the OData v4 endpoint for a dataset."""
            return f"https://{domain}/api/odata/v4/{fourfour}"

        def fetch_odata(self, domain: str, fourfour: str, top: int = 100) -> pd.DataFrame:
            """Fetch data using the OData v4 protocol."""
            url = f"{self.get_odata_url(domain, fourfour)}?$top={top}"
            headers = self._get_headers()
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json().get('value', [])
            return pd.DataFrame(data)

        def get_metadata(self, domain: str, fourfour: str) -> DatasetMetadata:
            pass
        df = client.parallel_fetch(domain, ds_id, limit)
        return df
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return pd.DataFrame()

# ── Sidebar ───────────────────────────────────────────────────────────────────
CATEGORIES = {
    "🏠 Overview": ["🏠 Program Dashboard", "ℹ️ About"],
    "📊 Analytics & AI": ["📊 Analytics", "🤖 AI Assistant", "🪄 SoQL Maestro", "⚡ Quantum"],
    "🏗️ Operations": ["🏗️ Engineering", "⚙️ Data Engineering", "✅ Task Board", "📋 Reports"],
    "🗺️ Geo-Spatial": ["🗺️ Spatial & Maps"],
    "🔍 Data Management": ["🔍 Data Explorer", "🛡️ Governance & Quality", "📤 Export"],
    "⚙️ System": ["⚙️ Settings", "🛠️ Developer Tools"]
}

with st.sidebar:
    st.markdown("### 🏙️ NYC DOT Data Assistant")
    st.markdown("---")
    
    # Category selection
    cat = st.selectbox("Category", list(CATEGORIES.keys()))
    page = st.radio("Navigation", CATEGORIES[cat], label_visibility="collapsed")
    
    st.markdown("---")
    token = st.text_input("Socrata Token", value=os.getenv("SOCRATA_APP_TOKEN",""),
                          type="password", key="tok")
    st.caption(f"Modules: {sum(HAS.values())}/{len(HAS)} loaded")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Program Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Program Dashboard":
    st.title("🏠 Program Dashboard")
    
    # ── Quick Start Section ───────────────────────────────────────────────────
    st.markdown("### ⚡ Quick Start")
    st.write("Launch an analysis pipeline with one click using pre-configured NYC datasets.")
    
    q1, q2, q3 = st.columns(3)
    
    with q1:
        st.markdown("""<div class="card">
            <h4>🚧 Sidewalk Violations</h4>
            <p>Analyze 311 sidewalk defects and repair lists.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("🚀 Load Violations", use_container_width=True):
            with st.spinner("Fetching violations..."):
                df = parallel_fetch("h9gi-nx95", 5000, token=token)
                set_df(df, "Sidewalk Violations")
                st.session_state["current_fourfour"] = "h9gi-nx95"
                st.rerun()

    with q2:
        st.markdown("""<div class="card">
            <h4>🚲 Bike Route Projects</h4>
            <p>Explore planned and completed bicycle infrastructure.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("🚀 Load Bike Data", use_container_width=True):
            with st.spinner("Fetching bike projects..."):
                df = parallel_fetch("7vsa-c9r2", 2000, token=token)
                set_df(df, "Bike Projects")
                st.session_state["current_fourfour"] = "7vsa-c9r2"
                st.rerun()

    with q3:
        st.markdown("""<div class="card">
            <h4>📊 Traffic Volume</h4>
            <p>Review daily traffic counts across the 5 boroughs.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("🚀 Load Traffic", use_container_width=True):
            with st.spinner("Fetching traffic data..."):
                df = parallel_fetch("7ym2-wayt", 5000, token=token)
                set_df(df, "Traffic Volume")
                st.session_state["current_fourfour"] = "7ym2-wayt"
                st.rerun()
    
    st.markdown("---")
    
    # ── System Health Summary ─────────────────────────────────────────────────
    h1, h2, h3 = st.columns(3)
    db_status = "✅ Connected" if duckdb else "❌ Offline"
    api_status = "✅ Active" if requests.get("https://data.cityofnewyork.us/resource/h9gi-nx95.json?$limit=1").status_code == 200 else "⚠️ Degraded"
    
    h1.metric("DuckDB Engine", db_status)
    h2.metric("Socrata API", api_status)
    h3.metric("Pillars Loaded", f"{sum(HAS.values())}/{len(HAS)}")
    
    st.markdown("---")
    df = upload_widget("Upload program/inspection data", "dash_up")
    if df is None:
        st.info("Upload data or use Data Explorer to ingest from Socrata.")
        st.subheader("Demo KPIs")
        c1,c2,c3,c4,c5 = st.columns(5)
        for col,(n,v,d) in zip([c1,c2,c3,c4,c5],[
            ("Defect Density","1.8","-0.3"),("Throughput","220 ft/d","+15"),
            ("Budget Variance","+$12K",""),("First-Pass Yield","88%","+2%"),
            ("Rework Factor","4.2%","-0.5%")]):
            col.metric(n,v,d)
    else:
        if HAS["program"]:
            try:
                dash = compute_program_dashboard(df)
                cols = st.columns(min(len(dash.metrics), 6))
                for col, m in zip(cols, dash.metrics):
                    col.metric(m.name.replace("_"," ").title(),
                               f"{m.value:.2f}",
                               f"{m.delta_from_target:+.2f}" if m.delta_from_target else "")
                hc = {"green":"#10b981","yellow":"#f59e0b","red":"#ef4444"}
                st.markdown(f"""<div style="text-align:center;margin:16px 0">
                <span style="background:{hc.get(dash.overall_health,'#6b7280')};
                color:white;padding:8px 24px;border-radius:20px;font-size:1.1em;font-weight:700">
                Program Health: {dash.overall_health.upper()}</span>
                <span style="margin-left:12px">
                🟢 {dash.green_count} &nbsp; 🟡 {dash.yellow_count} &nbsp; 🔴 {dash.red_count}
                </span></div>""", unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Dashboard error: {e}")
        if HAS["borough"] and "borough" in df.columns:
            st.subheader("Borough Comparison")
            try:
                tbl = borough_comparison_table(df)
                if not tbl.empty: st.dataframe(tbl, use_container_width=True)
            except Exception as e:
                st.warning(f"Borough table: {e}")
        numeric = df.select_dtypes("number").columns.tolist()
        if numeric:
            st.subheader("Quick Charts")
            col = st.selectbox("Column", numeric, key="dash_col")
            c1, c2 = st.columns(2)
            c1.plotly_chart(px.histogram(df, x=col, template="plotly_dark",
                            title=f"Distribution: {col}"), use_container_width=True)
            if "borough" in df.columns:
                c2.plotly_chart(px.box(df, x="borough", y=col, template="plotly_dark",
                                title=f"{col} by Borough"), use_container_width=True)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Analytics
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📊 Analytics":
    st.title("📊 Analytics")
    df = active_df_selector("ana_sel")
    if df is None:
        st.info("Load data first via Data Explorer or upload above.")
    else:
        t1,t2,t3,t4,t5 = st.tabs(["Outliers","Correlations","Distributions","Time Series","Text Insights"])

        with t1:
            st.subheader("Outlier Detection")
            if HAS["advanced"]:
                try:
                    rpts = detect_all_outliers(df)
                    found = [r for r in rpts if r.outlier_count > 0]
                    if found:
                        for r in found:
                            st.markdown(f"**{r.column}** — {r.outlier_count} outliers "
                                        f"({r.outlier_pct:.1f}%) via {r.method}")
                            with st.expander("Show outlier rows"):
                                st.dataframe(df.iloc[r.outlier_indices])
                    else:
                        st.success("No outliers detected.")
                except Exception as e:
                    st.warning(f"Outlier detection: {e}")
            else:
                num = df.select_dtypes("number")
                for col in num.columns:
                    q1,q3 = num[col].quantile(.25), num[col].quantile(.75)
                    iqr = q3-q1
                    mask = (num[col]<q1-1.5*iqr)|(num[col]>q3+1.5*iqr)
                    if mask.sum():
                        st.write(f"**{col}**: {mask.sum()} outliers (IQR)")

        with t2:
            st.subheader("Correlation Matrix")
            num = df.select_dtypes("number")
            if num.shape[1] >= 2:
                if HAS["advanced"]:
                    try:
                        res = correlation_analysis(df)
                        if hasattr(res, "pairs") and res.pairs:
                            st.dataframe(pd.DataFrame(res.pairs))
                    except: pass
                corr = num.corr()
                fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r",
                                template="plotly_dark", title="Correlation Matrix")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Need ≥2 numeric columns.")

        with t3:
            st.subheader("Distribution Classification")
            num_cols = df.select_dtypes("number").columns.tolist()
            if num_cols:
                col = st.selectbox("Column", num_cols, key="dist_col")
                fig = px.histogram(df, x=col, marginal="box", template="plotly_dark",
                                   title=f"Distribution: {col}")
                st.plotly_chart(fig, use_container_width=True)
                if HAS["advanced"]:
                    try:
                        dists = classify_all_distributions(df)
                        match = [d for d in dists if d.column == col]
                        if match:
                            d = match[0]
                            st.info(f"Best fit: **{d.best_fit}** | skew={d.skewness:.3f} | kurt={d.kurtosis:.3f}")
                    except: pass

        with t4:
            st.subheader("Time Series Summary")
            date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
            num_cols = df.select_dtypes("number").columns.tolist()
            if date_cols and num_cols:
                dc = st.selectbox("Date column", date_cols, key="ts_date")
                vc = st.selectbox("Value column", num_cols, key="ts_val")
                try:
                    tmp = df[[dc, vc]].copy()
                    tmp[dc] = pd.to_datetime(tmp[dc], errors="coerce")
                    tmp = tmp.dropna().sort_values(dc)
                    fig = px.line(tmp, x=dc, y=vc, template="plotly_dark",
                                  title=f"{vc} over time")
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.warning(str(e))
            else:
                st.info("Need date and numeric columns.")

        with t5:
            st.subheader("Text Insights")
            text_cols = df.select_dtypes("object").columns.tolist()
            if text_cols:
                tc = st.selectbox("Text column", text_cols, key="txt_col")
                if HAS["text"]:
                    try:
                        freqs = extract_term_frequencies(df[tc].dropna().tolist())
                        st.bar_chart(pd.Series(dict(list(freqs.items())[:20])))
                    except Exception as e:
                        st.warning(f"Text insights: {e}")
                else:
                    from collections import Counter
                    import re
                    words = Counter(re.findall(r"\b\w{4,}\b",
                                    " ".join(df[tc].dropna().astype(str)).lower()))
                    st.bar_chart(pd.Series(dict(words.most_common(20))))
            else:
                st.info("No text columns found.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Spatial & Maps
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🗺️ Spatial & Maps":
    st.title("🗺️ Spatial & Maps")
    df = active_df_selector("spa_sel")
    if df is None:
        st.info("Load data first.")
    else:
        lat_cols = [c for c in df.columns if any(x in c.lower() for x in ["lat","latitude","y_coord"])]
        lon_cols = [c for c in df.columns if any(x in c.lower() for x in ["lon","lng","longitude","x_coord"])]
        t1, t2, t3 = st.tabs(["Interactive Map","Spatial Analytics","Geo Validation"])

        with t1:
            if lat_cols and lon_cols:
                lat_col = st.selectbox("Latitude column", lat_cols, key="lat_c")
                lon_col = st.selectbox("Longitude column", lon_cols, key="lon_c")
                color_col = st.selectbox("Color by (optional)", ["None"] + df.columns.tolist(), key="color_c")
                try:
                    plot_df = df[[lat_col, lon_col]].copy()
                    plot_df[lat_col] = pd.to_numeric(plot_df[lat_col], errors="coerce")
                    plot_df[lon_col] = pd.to_numeric(plot_df[lon_col], errors="coerce")
                    plot_df = plot_df.dropna()
                    if color_col != "None": plot_df[color_col] = df[color_col]
                    if HAS["spatial"]:
                        import folium
                        m = folium.Map(location=[plot_df[lat_col].mean(), plot_df[lon_col].mean()], zoom_start=11)
                        from folium.plugins import MarkerCluster
                        mc = MarkerCluster().add_to(m)
                        for _, row in plot_df.head(2000).iterrows():
                            folium.Marker([row[lat_col], row[lon_col]]).add_to(mc)
                        st_folium(m, width=None, height=500)
                    else:
                        fig = px.scatter_mapbox(plot_df, lat=lat_col, lon=lon_col,
                            color=color_col if color_col != "None" else None,
                            mapbox_style="carto-darkmatter", zoom=10,
                            title="NYC Map View", height=500)
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Map error: {e}")
            else:
                st.warning("No latitude/longitude columns detected.")

        with t2:
            st.subheader("Spatial Analytics")
            if lat_cols and lon_cols:
                if HAS["spatial_analytics"]:
                    n_clust = st.slider("Clusters", 2, 20, 5, key="n_clust")
                    try:
                        clust_df = cluster_locations(df, lat_col=lat_cols[0],
                                                     lon_col=lon_cols[0], n_clusters=n_clust)
                        fig = px.scatter_mapbox(clust_df, lat=lat_cols[0], lon=lon_cols[0],
                            color="cluster", mapbox_style="carto-darkmatter", zoom=10,
                            title=f"K-Means Clusters (k={n_clust})", height=450)
                        st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.warning(f"Clustering: {e}")
                else:
                    st.info("spatial_analytics module not available — install scikit-learn.")
            else:
                st.info("Load a dataset with coordinates.")

        with t3:
            st.subheader("Geospatial Validation")
            if HAS["validation"] and lat_cols and lon_cols:
                try:
                    rpt = validate_geospatial_bounds(df, lat_col=lat_cols[0], lon_col=lon_cols[0])
                    pct_ok = 100 - (rpt.affected_records / max(len(df), 1) * 100)
                    st.progress(pct_ok / 100)
                    st.metric("% Within NYC Bounds", f"{pct_ok:.1f}%")
                    if rpt.errors:
                        for e in rpt.errors: st.error(e)
                    else:
                        st.success("All coordinates within NYC bounds.")
                except Exception as e:
                    st.warning(str(e))
            else:
                st.info("Load data with lat/lon columns.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Engineering
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🏗️ Engineering":
    st.title("🏗️ Engineering")
    df = upload_widget("Upload inspection/contract data", "eng_up")
    if df is None:
        df = active_df_selector("eng_sel")

    t1,t2,t3,t4,t5,t6 = st.tabs([
        "Construction Lists","Contract Analytics",
        "Cost Estimator","Budget Forecast",
        "Contractor Scorecards","Conflict Detection"])

    with t1:
        st.subheader("Construction List Manager")
        if df is not None:
            st.dataframe(df.head(20), use_container_width=True)
            if HAS["construction"]:
                c1, c2, c3 = st.columns(3)
                if c1.button("Prioritize & Classify"):
                    try:
                        df = prioritize_construction_list(df)
                        df = classify_scope(df)
                        df = flag_ada_locations(df)
                        set_df(df)
                        st.success("Prioritized!")
                        st.rerun()
                    except Exception as e: st.error(str(e))
                fmt = c2.selectbox("Export format", ["xlsx","csv","json","geojson"], key="cl_fmt")
                if c3.button("Export"):
                    try:
                        out = f"construction_list.{fmt}"
                        export_construction_list(df, out)
                        st.success(f"Saved: {out}")
                    except Exception as e: st.error(str(e))
                if "_priority_score" in df.columns:
                    try:
                        s = summarize_construction_list(df)
                        c1,c2,c3,c4 = st.columns(4)
                        c1.metric("Total", s.total_locations)
                        c2.metric("ADA", s.ada_count)
                        c3.metric("High Priority", s.high_priority_count)
                        c4.metric("Avg Priority", f"{s.avg_priority_score:.2f}")
                    except: pass
            else:
                st.info("construction_list module not available.")
        else:
            st.info("Upload data above.")

    with t2:
        st.subheader("Contract Analytics")
        if df is not None and HAS["contracts"]:
            tabs2 = st.tabs(["Progress","Budget","Productivity"])
            with tabs2[0]:
                try:
                    prog = analyze_contract_progress(df)
                    for p in prog:
                        sc = {"complete":"green","in_progress":"yellow","delayed":"red"}.get(p.status,"yellow")
                        st.markdown(f'<div class="status-{sc}"><b>{p.contract_id}</b>: {p.pct_complete:.0f}% | {p.status.upper()} | {p.velocity_sqft_per_day:.0f} sqft/day</div>', unsafe_allow_html=True)
                except Exception as e: st.warning(str(e))
            with tabs2[1]:
                try:
                    b = budget_analysis(df)
                    for col, (label, val) in zip(st.columns(4), [
                        ("Planned", f"${b.total_planned:,.0f}"), ("Actual", f"${b.total_actual:,.0f}"),
                        ("Variance", f"${b.variance:,.0f}"), ("CPI", f"{b.cost_performance_index:.2f}")]):
                        col.metric(label, val)
                except Exception as e: st.warning(str(e))
            with tabs2[2]:
                try:
                    pr = productivity_metrics(df)
                    for col, (label, val) in zip(st.columns(4), [
                        ("SqFt/Day", f"{pr.sqft_per_day:.1f}"), ("LF/Day", f"{pr.linear_feet_per_day:.1f}"),
                        ("Cost/SqFt", f"${pr.cost_per_sqft:.2f}"), ("Efficiency", f"{pr.crew_efficiency:.2f}")]):
                        col.metric(label, val)
                except Exception as e: st.warning(str(e))
        else:
            st.info("Upload contract data and ensure contracts module is loaded.")

    with t3:
        st.subheader("Cost Estimator")
        if df is not None and HAS["cost"]:
            try:
                est = estimate_costs(df)
                s = summarize_costs(est)
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Estimated", f"${s.total_estimated:,.0f}")
                c2.metric("Locations", s.location_count)
                c3.metric("Avg Cost", f"${s.avg_cost_per_location:,.0f}")
                st.dataframe(est.head(50), use_container_width=True)
            except Exception as e: st.warning(str(e))
        else:
            st.info("Upload construction list data.")

    with t4:
        st.subheader("Budget Forecast")
        if df is not None and HAS["forecast"]:
            try:
                fc = forecast_budget(df)
                st.json(fc if isinstance(fc, dict) else fc.__dict__)
            except Exception as e: st.warning(str(e))
        else:
            st.info("Forecast module not available.")

    with t5:
        st.subheader("Contractor Scorecards")
        if df is not None and HAS["scorecards"]:
            try:
                scores = score_contractors(df)
                st.dataframe(scores, use_container_width=True)
                if "grade" in scores.columns:
                    fig = px.bar(scores, x=scores.columns[0], y="score",
                                 color="grade", template="plotly_dark",
                                 title="Contractor Performance")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception as e: st.warning(str(e))
        else:
            st.info("Scorecard module not available or no data loaded.")

    with t6:
        st.subheader("Conflict Detection")
        if HAS["conflict"]:
            col1, col2 = st.columns(2)
            with col1:
                f1 = st.file_uploader("Proposed works", type=["csv","json"], key="conf1")
            with col2:
                f2 = st.file_uploader("Active permits", type=["csv","json"], key="conf2")
            buffer = st.slider("Buffer (meters)", 5, 100, 20, key="conf_buf")
            if f1 and f2:
                try:
                    d1 = pd.read_csv(f1) if f1.name.endswith(".csv") else pd.read_json(f1)
                    d2 = pd.read_csv(f2) if f2.name.endswith(".csv") else pd.read_json(f2)
                    res = detect_construction_conflicts(d1, d2, buffer_meters=buffer)
                    st.metric("Conflicts Found", res.conflict_count)
                    st.metric("Conflict Rate", f"{res.conflict_rate:.1f}%")
                    if not res.conflicts.empty:
                        st.dataframe(res.conflicts, use_container_width=True)
                except Exception as e: st.error(str(e))
        else:
            st.info("Conflict detection module not available.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Data Explorer
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🔍 Data Explorer":
    st.title("🔍 Data Explorer")
    t1,t2,t3,t4,t5 = st.tabs([
        "Socrata Search","Profile","Data Dictionary",
        "311 Ingestion","Change Detection"])

    with t1:
        st.subheader("Search & Ingest Socrata Datasets")
        with st.expander("Search Parameters", expanded=True):
            c1, c2, c3 = st.columns([3, 2, 1])
            q = c1.text_input("Search term", "sidewalk", key="srch_q")
            dom_srch = c2.text_input("Domain", "data.cityofnewyork.us", key="srch_dom")
            cat_srch = c3.text_input("Category (optional)", "", key="srch_cat")
            lim_srch = st.number_input("Search result limit", 10, 100, 50, key="srch_lim_n")
        
        srch_results = socrata_search(q, domain=dom_srch, cat=cat_srch if cat_srch else None, lim=lim_srch)
        
        if srch_results:
            # Map name to result object for selection
            res_dict = {r.name: r for r in srch_results}
            sel_name = st.selectbox("Select Dataset", list(res_dict.keys()), key="srch_ds")
            sel_res = res_dict[sel_name]
            
            st.markdown(f"**Description**: {sel_res.description}")
            c1, c2, c3 = st.columns(3)
            c1.caption(f"ID: `{sel_res.fourfour}`")
            c2.caption(f"Domain: `{sel_res.domain}`")
            c3.caption(f"Views: `{sel_res.page_views_last_month or 'N/A'}`")
            
            ingest_lim = st.number_input("Rows to ingest", 1000, 1000000, 10000, step=5000, key="ingest_lim")
            
            col1, col2 = st.columns(2)
            if col1.button("📥 Ingest into Session"):
                with st.spinner("Fetching data..."):
                    df = parallel_fetch(sel_res.fourfour, int(ingest_lim), token or "", domain=sel_res.domain)
                if not df.empty:
                    set_df(df, sel_res.name)
                    st.session_state["current_fourfour"] = sel_res.fourfour
                    st.session_state["current_domain"] = sel_res.domain
                    st.success(f"Ingested {len(df):,} rows.")
                    st.dataframe(df.head(20), use_container_width=True)
                    
                    # Store in DuckDB if requested
                    tname = sel_res.fourfour.replace("-","_")
                    try:
                        db.execute(f'DROP TABLE IF EXISTS "{tname}"')
                        db.execute(f'CREATE TABLE "{tname}" AS SELECT * FROM df')
                        st.info(f"Persistent table `{tname}` created in DuckDB.")
                    except Exception as e:
                        st.warning(f"Could not persist to DuckDB: {e}")
                else:
                    st.error("Fetch returned no data.")
            
            if col2.button("💾 Export Search Results (CSV)"):
                data = [{"name": r.name, "id": r.fourfour, "domain": r.domain, "category": r.category} for r in srch_results]
                csv = pd.DataFrame(data).to_csv(index=False)
                st.download_button("Download Search Results", csv, "socrata_search_results.csv", "text/csv")
        else:
            st.info("Enter a search term and domain to find datasets.")

        st.markdown("---")
        st.subheader("Direct Fetch by Dataset ID")
        c1, c2, c3 = st.columns([2, 1, 1])
        direct_id = c1.text_input("Dataset 4x4 ID", "h9gi-nx95", key="dir_id")
        direct_dom = c2.text_input("Domain", "data.cityofnewyork.us", key="dir_dom")
        direct_lim = c3.number_input("Rows", 1000, 1000000, 5000, step=1000, key="dir_lim")
        if st.button("Fetch Direct"):
            with st.spinner("Fetching..."):
                df = parallel_fetch(direct_id, int(direct_lim), token or "", domain=direct_dom)
            if not df.empty:
                set_df(df, direct_id)
                st.session_state["current_fourfour"] = direct_id
                st.session_state["current_domain"] = direct_dom
                st.success(f"{len(df):,} rows fetched")
                st.dataframe(df.head(20), use_container_width=True)
            else:
                st.error("No data returned.")

    with t2:
        st.subheader("Dataset Profiler")
        df = active_df_selector("prof_sel")
        if df is not None:
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Rows", f"{len(df):,}")
            c2.metric("Columns", len(df.columns))
            c3.metric("Null %", f"{df.isnull().mean().mean()*100:.1f}%")
            c4.metric("Duplicates", df.duplicated().sum())
            st.markdown("#### Column Summary")
            summary = pd.DataFrame({
                "dtype": df.dtypes.astype(str),
                "null_pct": (df.isnull().mean()*100).round(1),
                "unique": df.nunique(),
                "sample": [str(df[c].dropna().iloc[0]) if df[c].notna().any() else "" for c in df.columns]
            })
            st.dataframe(summary, use_container_width=True)
            if HAS["governance"]:
                try:
                    score = compute_quality_score(df)
                    st.markdown("#### Quality Score")
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Overall", f"{score.overall:.1f}")
                    c2.metric("Completeness", f"{score.completeness:.1f}%")
                    c3.metric("Validity", f"{score.validity:.1f}%")
                    c4.metric("Consistency", f"{score.consistency:.1f}%")
                except Exception as e:
                    st.warning(f"Quality score: {e}")
        else:
            st.info("Select a dataset above.")

    with t3:
        st.subheader("Data Dictionary Generator")
        df = active_df_selector("dict_sel")
        if df is not None:
            if HAS["discovery"]:
                try:
                    ddict = generate_data_dictionary(df)
                    st.dataframe(pd.DataFrame(ddict), use_container_width=True)
                    csv = pd.DataFrame(ddict).to_csv(index=False)
                    st.download_button("Download Dictionary CSV", csv,
                                       "data_dictionary.csv", "text/csv")
                except Exception as e:
                    st.warning(f"Dictionary: {e}")
            else:
                # Built-in fallback
                ddict = []
                for col in df.columns:
                    s = df[col]
                    ddict.append({
                        "column": col, "dtype": str(s.dtype),
                        "null_pct": f"{s.isnull().mean()*100:.1f}%",
                        "unique_count": s.nunique(),
                        "sample_values": ", ".join(s.dropna().astype(str).unique()[:3])
                    })
                st.dataframe(pd.DataFrame(ddict), use_container_width=True)
        else:
            st.info("Load a dataset first.")

    with t4:
        st.subheader("311 Complaint Ingestion")
        c1,c2 = st.columns(2)
        max_rows_311 = c1.number_input("Max rows", 100, 50000, 1000, key="rows_311")
        borough_311 = c2.selectbox("Borough", ["ALL","MANHATTAN","BROOKLYN","QUEENS","BRONX","STATEN ISLAND"], key="bor_311")
        if st.button("Ingest 311 Sidewalk Complaints"):
            with st.spinner("Fetching 311 data..."):
                if HAS["complaints"]:
                    try:
                        bor = None if borough_311 == "ALL" else borough_311
                        result = ingest_311_complaints(max_rows=int(max_rows_311), borough=bor)
                        df311 = result.df if hasattr(result, "df") else pd.DataFrame(result)
                        set_df(df311, "311_complaints")
                        st.success(f"Ingested {len(df311):,} complaints")
                        if hasattr(result, "critical_count"):
                            st.metric("Critical", result.critical_count)
                        st.dataframe(df311.head(30), use_container_width=True)
                    except Exception as e:
                        st.error(f"311 ingestion: {e}")
                else:
                    # Direct fetch fallback
                    rows = parallel_fetch("erm2-nwe9", int(max_rows_311), token or "")
                    if rows:
                        df311 = pd.DataFrame(rows)
                        if borough_311 != "ALL" and "borough" in df311.columns:
                            df311 = df311[df311["borough"].str.upper() == borough_311]
                        set_df(df311, "311_complaints")
                        st.success(f"Fetched {len(df311):,} complaints")
                        st.dataframe(df311.head(30), use_container_width=True)

    with t5:
        st.subheader("Change Detection (CDC)")
        col1, col2 = st.columns(2)
        with col1:
            f_old = st.file_uploader("Previous snapshot (CSV)", type=["csv"], key="cdc_old")
        with col2:
            f_new = st.file_uploader("Current snapshot (CSV)", type=["csv"], key="cdc_new")
        key_col = st.text_input("Key column", "id", key="cdc_key")
        if f_old and f_new:
            df_old = pd.read_csv(f_old)
            df_new = pd.read_csv(f_new)
            if HAS["cdc"]:
                try:
                    changes = detect_changes(df_old, df_new, key_col=key_col)
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Added", changes.added_count)
                    c2.metric("Modified", changes.modified_count)
                    c3.metric("Removed", changes.removed_count)
                    if not changes.added.empty:
                        with st.expander("Added records"):
                            st.dataframe(changes.added, use_container_width=True)
                    if not changes.modified.empty:
                        with st.expander("Modified records"):
                            st.dataframe(changes.modified, use_container_width=True)
                except Exception as e:
                    st.error(str(e))
            else:
                merged = df_old.merge(df_new, on=key_col, how="outer", indicator=True)
                added = merged[merged["_merge"]=="right_only"]
                removed = merged[merged["_merge"]=="left_only"]
                st.metric("Added", len(added))
                st.metric("Removed", len(removed))

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Governance & Quality
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🛡️ Governance & Quality":
    st.title("🛡️ Governance & Quality")
    df = active_df_selector("gov_sel")
    t1,t2,t3,t4,t5,t6 = st.tabs([
        "Quality Scorecard","Schema Drift","SLA Tracking",
        "Data Freshness","Anomalies","Audit Trail"])

    with t1:
        st.subheader("Data Quality Scorecard")
        if df is not None:
            lat_cols = [c for c in df.columns if "lat" in c.lower()]
            lon_cols = [c for c in df.columns if "lon" in c.lower()]
            completeness = (1 - df.isnull().mean().mean()) * 100
            uniqueness = (df.nunique() / len(df)).mean() * 100 if len(df) else 0
            geo_score = 100.0
            if HAS["validation"] and lat_cols and lon_cols:
                try:
                    rpt = validate_geospatial_bounds(df, lat_col=lat_cols[0], lon_col=lon_cols[0])
                    geo_score = 100 - (rpt.affected_records / max(len(df),1) * 100)
                except: pass
            overall = (completeness + uniqueness + geo_score) / 3
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Overall Score", f"{overall:.1f}/100")
            c2.metric("Completeness", f"{completeness:.1f}%")
            c3.metric("Uniqueness", f"{uniqueness:.1f}%")
            c4.metric("Geo Validity", f"{geo_score:.1f}%")
            st.progress(overall/100)
            st.markdown("#### Per-Column Completeness")
            comp_df = pd.DataFrame({
                "column": df.columns,
                "null_pct": df.isnull().mean().values * 100,
                "unique": df.nunique().values
            }).sort_values("null_pct", ascending=False)
            fig = px.bar(comp_df, x="column", y="null_pct",
                         title="Null % per Column", template="plotly_dark",
                         color="null_pct", color_continuous_scale="Reds")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Load a dataset first.")

    with t2:
        st.subheader("Schema Drift Detection")
        c1, c2 = st.columns(2)
        f_base = c1.file_uploader("Baseline schema (JSON)", type=["json"], key="schema_base")
        f_curr = c2.file_uploader("Current data (CSV)", type=["csv"], key="schema_curr")
        if f_curr:
            df_curr = pd.read_csv(f_curr)
            curr_schema = {col: str(df_curr[col].dtype) for col in df_curr.columns}
            if f_base:
                base_schema = json.load(f_base)
                added = set(curr_schema) - set(base_schema)
                removed = set(base_schema) - set(curr_schema)
                changed = {c for c in curr_schema if c in base_schema and curr_schema[c] != base_schema[c]}
                c1,c2,c3 = st.columns(3)
                c1.metric("Added Columns", len(added))
                c2.metric("Removed Columns", len(removed))
                c3.metric("Type Changes", len(changed))
                if added: st.success(f"New columns: {', '.join(added)}")
                if removed: st.error(f"Missing columns: {', '.join(removed)}")
                if changed: st.warning(f"Type changes: {', '.join(changed)}")
            else:
                st.json(curr_schema)
                st.download_button("Save as Schema Baseline",
                                   json.dumps(curr_schema, indent=2),
                                   "schema_baseline.json", "application/json")

    with t3:
        st.subheader("SLA Tracking")
        if df is not None and HAS["sla"]:
            try:
                metrics = compute_sla_metrics(df)
                c1,c2,c3 = st.columns(3)
                c1.metric("Avg Cycle Days", f"{metrics.avg_total_cycle_days:.1f}")
                c2.metric("SLA Compliance", f"{metrics.sla_compliance_rate:.1f}%")
                c3.metric("Violations", metrics.violation_count)
                violations = flag_sla_violations(df)
                if not violations.empty:
                    st.dataframe(violations, use_container_width=True)
            except Exception as e:
                st.warning(str(e))
        elif df is not None:
            date_cols = [c for c in df.columns if "date" in c.lower()]
            if len(date_cols) >= 2:
                start_col = st.selectbox("Start date", date_cols, key="sla_s")
                end_col = st.selectbox("End date", date_cols, key="sla_e")
                try:
                    tmp = df.copy()
                    tmp[start_col] = pd.to_datetime(tmp[start_col], errors="coerce")
                    tmp[end_col] = pd.to_datetime(tmp[end_col], errors="coerce")
                    tmp["cycle_days"] = (tmp[end_col] - tmp[start_col]).dt.days
                    st.metric("Avg Cycle Days", f"{tmp['cycle_days'].mean():.1f}")
                    st.plotly_chart(px.histogram(tmp, x="cycle_days", template="plotly_dark",
                                                 title="Cycle Time Distribution"), use_container_width=True)
                except Exception as e:
                    st.warning(str(e))
            else:
                st.info("Need at least 2 date columns for SLA tracking.")
        else:
            st.info("Load data first.")

    with t4:
        st.subheader("Data Freshness")
        if df is not None:
            date_cols = [c for c in df.columns if "date" in c.lower() or "time" in c.lower()]
            if date_cols:
                dc = st.selectbox("Date column", date_cols, key="fresh_dc")
                try:
                    dates = pd.to_datetime(df[dc], errors="coerce").dropna()
                    last_updated = dates.max()
                    age_days = (datetime.now() - last_updated.to_pydatetime().replace(tzinfo=None)).days
                    c1,c2,c3 = st.columns(3)
                    c1.metric("Last Updated", str(last_updated.date()))
                    c2.metric("Age (days)", age_days)
                    c3.metric("Records", f"{len(dates):,}")
                    status = "🟢 Fresh" if age_days < 7 else ("🟡 Stale" if age_days < 30 else "🔴 Very Stale")
                    st.markdown(f"### Freshness: {status}")
                except Exception as e:
                    st.warning(str(e))
            else:
                st.info("No date columns found.")
        else:
            st.info("Load data first.")

    with t5:
        st.subheader("Anomaly Detection")
        if df is not None:
            num = df.select_dtypes("number")
            if not num.empty and HAS["validation"]:
                try:
                    anom = detect_anomalies(df)
                    st.dataframe(anom, use_container_width=True)
                except Exception as e:
                    # Fallback
                    z_scores = (num - num.mean()) / num.std()
                    anomalies = (z_scores.abs() > 3).any(axis=1)
                    st.metric("Anomalous Rows", anomalies.sum())
                    st.dataframe(df[anomalies].head(50), use_container_width=True)
            elif not num.empty:
                z_scores = (num - num.mean()) / num.std()
                anomalies = (z_scores.abs() > 3).any(axis=1)
                st.metric("Anomalous Rows (Z>3)", anomalies.sum())
                st.dataframe(df[anomalies].head(50), use_container_width=True)
            else:
                st.info("No numeric columns.")
        else:
            st.info("Load data first.")

    with t6:
        st.subheader("Audit Trail")
        if HAS["audit"]:
            pg_dsn = st.text_input("PostgreSQL DSN", type="password", key="aud_dsn")
            if pg_dsn:
                try:
                    trail = AuditTrail(pg_dsn)
                    entity = st.text_input("Entity type (table)", "sidewalk_conditions")
                    if st.button("Load Audit Events"):
                        events = trail.get_events(entity, "", limit=200)
                        ev_data = [{"time": e.timestamp, "user": e.user_name,
                                    "action": e.action, "entity_id": e.entity_id,
                                    "reason": e.reason} for e in events]
                        st.dataframe(pd.DataFrame(ev_data), use_container_width=True)
                except Exception as e:
                    st.error(f"Audit trail: {e}")
            else:
                st.info("Enter a PostgreSQL DSN to view the audit trail.")
        else:
            st.info("Audit trail requires PostgreSQL (psycopg).")
            if df is not None:
                st.markdown("#### In-session change log")
                log = st.session_state.get("change_log", [])
                if log:
                    st.dataframe(pd.DataFrame(log))
                else:
                    st.caption("No changes logged in this session.")


# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Reports
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📋 Reports":
    st.title("📋 Reports")
    df = active_df_selector("rpt_sel")
    t1,t2,t3 = st.tabs(["Contract Report","Program KPI Report","Inquiry Response"])

    with t1:
        st.subheader("Contract Status Report")
        if df is not None and HAS["reports"]:
            try:
                rpt = generate_contract_report(df)
                st.markdown(rpt.to_markdown())
                c1,c2 = st.columns(2)
                if c1.button("Save HTML"):
                    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
                    rpt.save("outputs/reports/contract_status.html")
                    st.success("Saved HTML")
                if c2.button("Save Markdown"):
                    Path("outputs/reports").mkdir(parents=True, exist_ok=True)
                    rpt.save("outputs/reports/contract_status.md")
                    st.success("Saved Markdown")
                if HAS["pdf"]:
                    if st.button("Export PDF"):
                        try:
                            generate_pdf_report(rpt, "outputs/reports/contract_status.pdf")
                            st.success("PDF saved")
                        except Exception as e:
                            st.warning(f"PDF: {e}")
            except Exception as e:
                st.warning(f"Report generation: {e}")
        else:
            st.info("Load contract data and ensure reports module is available.")

    with t2:
        st.subheader("Program KPI Report")
        if df is not None and HAS["program"] and HAS["reports"]:
            try:
                dash = compute_program_dashboard(df)
                rpt = generate_program_report(dash)
                st.markdown(rpt.to_markdown())
            except Exception as e:
                st.warning(f"KPI report: {e}")
        else:
            st.info("Load program data first.")

    with t3:
        st.subheader("Inquiry Response Generator")
        if df is not None and HAS["reports"]:
            inq_type = st.selectbox("Inquiry type",
                ["borough_overview","contract_status","location_status"], key="inq_type")
            param = st.text_input("Parameter (borough/contract ID/location)", key="inq_param")
            if st.button("Generate Response"):
                try:
                    kwargs = {}
                    if inq_type == "borough_overview": kwargs["borough"] = param
                    elif inq_type == "contract_status": kwargs["contract_id"] = param
                    elif inq_type == "location_status": kwargs["location"] = param
                    rpt = generate_inquiry_response(inq_type, df, **kwargs)
                    st.markdown(rpt.to_markdown())
                except Exception as e:
                    st.warning(str(e))
        else:
            st.info("Load data and ensure reports module is available.")

# ═══════════════════════════════════════════════════════════════════════════════
elif page == "📤 Export":
    st.title("📤 Export & Integrations")
    df = active_df_selector("exp_sel")
    t1,t2,t3,t4,t5 = st.tabs(["Excel/CSV","BI Platforms","SQL Generation","OData Integration","Graph"])

    with t1:
        st.subheader("Excel & Flat File Export")
        if df is not None:
            if HAS["excel"]:
                st.write("Build a multi-sheet workbook with pivot tables.")
                out_path = st.text_input("Output path", "outputs/export.xlsx", key="xl_path")
                pivot_rows = st.selectbox("Pivot rows", ["None"]+df.columns.tolist(), key="pv_rows")
                pivot_vals = st.selectbox("Pivot values", ["None"]+df.select_dtypes("number").columns.tolist(), key="pv_vals")
                if st.button("Build & Download Excel"):
                    try:
                        Path("outputs").mkdir(exist_ok=True)
                        builder = ExcelWorkbookBuilder()
                        builder.add_data_sheet("Data", df)
                        if pivot_rows != "None" and pivot_vals != "None":
                            builder.add_pivot_sheet("Pivot", df, rows=pivot_rows, values=pivot_vals)
                        saved = builder.save(out_path)
                        with open(saved, "rb") as f:
                            st.download_button("Download Excel", f.read(),
                                               Path(saved).name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                        st.success(f"Workbook built: {saved}")
                    except Exception as e:
                        st.error(str(e))
            
            st.markdown("---")
            c1, c2 = st.columns(2)
            csv = df.to_csv(index=False)
            c1.download_button("Download as CSV", csv, "export.csv", "text/csv")
            
            try:
                import io
                parquet_buffer = io.BytesIO()
                df.to_parquet(parquet_buffer, index=False)
                c2.download_button("Download as Parquet", parquet_buffer.getvalue(), "export.parquet", "application/octet-stream")
            except Exception as e:
                c2.info("Parquet export requires `pyarrow` or `fastparquet`.")
        else:
            st.info("Load data first.")

    with t2:
        st.subheader("BI Platform Export")
        if df is not None:
            platform = st.selectbox("Platform", ["Tableau","Power BI","PowerPoint"], key="bi_plat")
            out_dir = st.text_input("Output directory", "outputs/bi", key="bi_dir")
            if st.button(f"Export for {platform}") and HAS["bi"]:
                try:
                    Path(out_dir).mkdir(parents=True, exist_ok=True)
                    if platform == "Tableau":
                        export_for_tableau(df, out_dir)
                    elif platform == "Power BI":
                        export_for_powerbi(df, out_dir)
                    elif platform == "PowerPoint":
                        from socrata_toolkit.integrations.bi import SlideContent, create_presentation
                        slides = [SlideContent(title="NYC DOT Data Export",
                                               body=f"{len(df):,} records exported",
                                               data={"Rows": len(df), "Columns": len(df.columns)})]
                        create_presentation(slides, f"{out_dir}/report.pptx")
                    st.success(f"Exported to {out_dir}")
                except Exception as e:
                    st.error(str(e))
            elif not HAS["bi"]:
                st.info("BI integration module not available.")
        else:
            st.info("Load data first.")

    with t3:
        st.subheader("SQL DDL / DML Generator")
        if df is not None:
            table_name = st.text_input("Table name", "sidewalk_data", key="sql_tbl")
            dialect = st.selectbox("Dialect", ["postgres","sqlite","duckdb"], key="sql_dial")
            if st.button("📜 Generate SQL"):
                type_map = {"int64":"INTEGER","float64":"REAL","object":"TEXT","bool":"BOOLEAN"}
                cols_sql = []
                for col in df.columns:
                    dt = type_map.get(str(df[col].dtype), "TEXT")
                    cols_sql.append(f'  "{col}" {dt}')
                ddl = f'CREATE TABLE "{table_name}" (\n' + ",\n".join(cols_sql) + "\n);"
                st.code(ddl, language="sql")
                st.download_button("Download DDL", ddl, f"{table_name}.sql", "text/plain")
        else:
            st.info("Load data first.")

    with t4:
        st.subheader("🌐 OData v4 Integration")
        st.write("Socrata datasets are accessible via the OData v4 protocol, ideal for Excel, Power BI, and Tableau.")
        domain = st.session_state.get("current_domain", "data.cityofnewyork.us")
        fourfour = st.session_state.get("current_fourfour")
        
        if fourfour:
            odata_url = f"https://{domain}/api/odata/v4/{fourfour}"
            st.info("Use the following URL to connect your BI tool via OData:")
            st.code(odata_url, language="text")
            st.markdown("""
            **How to use:**
            1. **Power BI**: Get Data -> OData Feed -> Paste URL.
            2. **Excel**: Data -> Get Data -> From Other Sources -> From OData Feed.
            3. **Tableau**: Connect -> To a Server -> OData.
            """)
        else:
            st.warning("Please load a Socrata dataset first to generate OData links.")

    with t5:
        st.subheader("Graph / Network Export")
        if df is not None:
            if HAS["graph"]:
                id_col = st.selectbox("Node ID column", df.columns.tolist(), key="g_id")
                rel_col = st.selectbox("Related-to column", ["None"]+df.columns.tolist(), key="g_rel")
                if st.button("Export Graph"):
                    try:
                        out = "outputs/graph.json"
                        Path("outputs").mkdir(exist_ok=True)
                        from socrata_toolkit.integrations.graph import export_graph
                        export_graph(df, id_col=id_col,
                                     relation_col=rel_col if rel_col != "None" else None,
                                     output_path=out)
                        st.success(f"Graph exported: {out}")
                    except Exception as e:
                        st.error(str(e))
            else:
                st.info("Graph module not available.")
        else:
            st.info("Load data first.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: SoQL Maestro
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🪄 SoQL Maestro":
    st.title("🪄 SoQL Maestro")
    st.write("Advanced Socrata Query Builder with Time-Series & Aggregation Flow.")
    
    domain = st.session_state.get("current_domain", "data.cityofnewyork.us")
    fourfour = st.session_state.get("current_fourfour")
    
    if not fourfour:
        st.warning("Please load a dataset first (Home or Data Explorer).")
    else:
        st.markdown(f"**Target Dataset:** `{fourfour}` on `{domain}`")
        
        with st.expander("🛠️ Query Configuration", expanded=True):
            builder = SoQLBuilder()
            
            # Select Columns
            df_cols = st.session_state.get("current_df").columns.tolist() if st.session_state.get("current_df") is not None else []
            sel_cols = st.multiselect("Select Base Columns", df_cols, key="sm_sel")
            if sel_cols: builder.select(*sel_cols)
            
            # Time Series Aggregation
            st.markdown("---")
            st.subheader("📅 Historical Analysis (Flow)")
            use_ts = st.checkbox("Enable Time-Series Aggregation")
            if use_ts:
                ts_col = st.selectbox("Timestamp Column", [c for c in df_cols if "date" in c.lower() or "time" in c.lower()], key="sm_ts_col")
                ts_prec = st.selectbox("Precision", ["year", "quarter", "month", "week", "day"], index=2, key="sm_ts_prec")
                builder.date_trunc(ts_col, ts_prec, alias="period")
                
                agg_func = st.selectbox("Aggregation Function", ["count", "sum", "avg", "min", "max"], key="sm_agg_func")
                agg_col = st.selectbox("Value Column", ["*"] + df_cols, key="sm_agg_col")
                builder.aggregate(agg_func, agg_col, alias="metric")
                
                builder.group("period")
                builder.order("period", desc=True)
            
            # Filters
            st.markdown("---")
            st.subheader("🔍 Filters")
            filter_col = st.selectbox("Filter Column", ["None"] + df_cols, key="sm_filt_col")
            filter_val = st.text_input("Filter Value (e.g. > 100 or = 'BRONX')", key="sm_filt_val")
            if filter_col != "None" and filter_val:
                builder.where(f"{filter_col} {filter_val}")

        # Preview & Execution
        st.markdown("---")
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📜 Generated SoQL")
            query_str = builder.build_query_string()
            st.code(query_str, language="sql")
        
        with col2:
            st.subheader("🚀 Execution")
            limit = st.number_input("Limit", 10, 10000, 1000, key="sm_lim")
            if st.button("Run Master Flow"):
                try:
                    with st.spinner("Executing complex query..."):
                        client = SocrataClient(SocrataConfig(app_token=token))
                        # Use fetch_dataframe with raw params from builder
                        params = builder.build()
                        params["limit"] = limit
                        # SocrataClient uses parallel_fetch for limit, but for complex queries we use direct
                        url = f"https://{domain}/resource/{fourfour}.json"
                        headers = client._headers()
                        resp = requests.get(url, params={f"${k}":v for k,v in params.items()}, headers=headers)
                        resp.raise_for_status()
                        res_df = pd.DataFrame(resp.json())
                        
                        if not res_df.empty:
                            st.success(f"Fetched {len(res_df)} rows.")
                            st.dataframe(res_df, use_container_width=True)
                            
                            if use_ts and "period" in res_df.columns:
                                st.line_chart(res_df.set_index("period")["metric"])
                        else:
                            st.info("No results found for this query.")
                except Exception as e:
                    st.error(f"Query failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Quantum
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚡ Quantum":
    st.title("⚡ Quantum Computing")
    st.info("All algorithms fall back to classical solvers when Qiskit/Cirq are not installed.")
    df = active_df_selector("qnt_sel")
    t1,t2,t3 = st.tabs(["Quantum Search","Crew Optimizer","Route Optimizer"])

    with t1:
        st.subheader("Grover's Algorithm Search")
        if df is not None and HAS["quantum"]:
            c1,c2 = st.columns(2)
            borough_q = c1.text_input("Borough filter", "", key="q_bor")
            min_sev = c2.number_input("Min severity", 0.0, 10.0, 0.0, key="q_sev")
            status_q = st.text_input("Status filter", "", key="q_stat")
            if st.button("Run Quantum Search"):
                criteria = SearchCriteria(
                    borough=borough_q or None,
                    min_severity=min_sev if min_sev > 0 else None,
                    status=status_q or None)
                try:
                    result = quantum_search(df, criteria)
                    st.metric("Matches Found", result.match_count)
                    st.metric("Method", result.method)
                    if result.num_qubits:
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Qubits", result.num_qubits)
                        c2.metric("Grover Iterations", result.grover_iterations)
                        c3.metric("Circuit Depth", result.circuit_depth)
                    st.dataframe(result.matches, use_container_width=True)
                except Exception as e:
                    st.error(str(e))
            st.markdown("---")
            st.subheader("Circuit Analyzer")
            c1, c2 = st.columns(2)
            n_rec = c1.number_input("Total records", 100, 1000000, 10000, key="qa_rec")
            n_sol = c2.number_input("Expected solutions", 1, 10000, 50, key="qa_sol")
            if st.button("Analyze Circuit Requirements"):
                try:
                    info = analyze_grover_circuit(int(n_rec), int(n_sol))
                    c1,c2,c3,c4 = st.columns(4)
                    c1.metric("Qubits Needed", info.num_qubits)
                    c2.metric("Grover Iterations", info.num_grover_iterations)
                    c3.metric("Circuit Depth", info.circuit_depth)
                    c4.metric("Total States", f"{info.total_states:,}")
                except Exception as e:
                    st.warning(str(e))
        else:
            st.info("Load data to use quantum search.")

    with t2:
        st.subheader("Crew Assignment Optimizer")
        if df is not None and HAS["quantum"]:
            c1,c2 = st.columns(2)
            n_crews = c1.slider("Number of crews", 2, 20, 5, key="crew_n")
            backend = c2.selectbox("Backend", ["classical","qiskit","cirq"], key="crew_back")
            if st.button("Optimize Crew Assignment"):
                try:
                    cfg = QuantumConfig(backend=backend)
                    result = optimize_crew_assignment(df, n_crews=n_crews, config=cfg)
                    st.metric("Total Cost", f"{result.total_cost:.2f}")
                    st.metric("Balance Score", f"{result.balance_score:.3f}")
                    st.metric("Method", result.method)
                    assign_df = pd.DataFrame([
                        {"crew": k, "locations": len(v), "location_ids": ", ".join(v[:5])+"..."}
                        for k, v in result.assignments.items()
                    ])
                    st.dataframe(assign_df, use_container_width=True)
                except Exception as e:
                    st.error(str(e))
        else:
            st.info("Load location data first.")

    with t3:
        st.subheader("Route Optimizer (TSP + 2-opt)")
        if df is not None and HAS["quantum"]:
            lat_cols = [c for c in df.columns if "lat" in c.lower()]
            lon_cols = [c for c in df.columns if "lon" in c.lower()]
            if lat_cols and lon_cols:
                subset = st.slider("Max locations to route", 5, 200, 50, key="route_n")
                if st.button("Optimize Route"):
                    try:
                        result = optimize_repair_route(
                            df.head(subset),
                            lat_col=lat_cols[0], lon_col=lon_cols[0])
                        c1,c2,c3 = st.columns(3)
                        c1.metric("Total Distance", f"{result.total_distance} km")
                        c2.metric("Est. Time", f"{result.estimated_time_hours:.1f} hrs")
                        c3.metric("Method", result.method)
                        st.write("Route order:", result.route[:10], "...")
                    except Exception as e:
                        st.error(str(e))
            else:
                st.info("Need latitude/longitude columns.")
        else:
            st.info("Load location data first.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: AI Assistant
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🤖 AI Assistant":
    st.title("🤖 AI Assistant")
    t1, t2 = st.tabs(["NL → SQL Chatbot", "NLP Enrichment"])

    with t1:
        st.subheader("Natural Language to SQL")
        openai_key = st.text_input("OpenAI API Key", type="password",
                                   value=os.getenv("OPENAI_API_KEY",""), key="oai_key")
        if "chat_history" not in st.session_state:
            st.session_state["chat_history"] = []

        for msg in st.session_state["chat_history"]:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        prompt = st.chat_input("Ask about your data...")
        if prompt:
            st.session_state["chat_history"].append({"role":"user","content":prompt})
            with st.chat_message("user"): st.write(prompt)
            df = st.session_state.get("current_df")
            schema_ctx = ""
            if df is not None:
                schema_ctx = f"Dataset columns: {', '.join(df.columns[:20])}\nRows: {len(df)}\n"
            if HAS["llm"] and openai_key:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(model_name="gpt-4o-mini", api_key=openai_key)
                    bot = SocrataLLMChatbot.__new__(SocrataLLMChatbot)
                    bot.llm = llm
                    bot.conversation_history = []
                    bot.max_history = 20
                    bot.dataset_context = None
                    reply = bot.chat(schema_ctx + prompt)
                except Exception as e:
                    reply = f"LLM error: {e}"
            else:
                tables = loaded_tables()
                reply = (f"I can see {len(tables)} tables in the database: {', '.join(tables[:5])}. "
                         f"{'Current dataset has '+str(len(df))+' rows and columns: '+', '.join(df.columns[:10].tolist()) if df is not None else 'No data loaded.'} "
                         "Connect an OpenAI key for full NL→SQL capabilities.")
            with st.chat_message("assistant"): st.write(reply)
            st.session_state["chat_history"].append({"role":"assistant","content":reply})

    with t2:
        st.subheader("NLP Enrichment")
        df = active_df_selector("nlp_sel")
        if df is not None:
            text_cols = df.select_dtypes("object").columns.tolist()
            if text_cols:
                tc = st.selectbox("Text column to enrich", text_cols, key="nlp_tc")
                if st.button("Run NLP Enrichment"):
                    if HAS["nlp"]:
                        try:
                            enriched = enrich_construction_list(df, text_col=tc)
                            set_df(enriched, "nlp_enriched")
                            st.success("Enriched!")
                            st.dataframe(enriched.head(20), use_container_width=True)
                        except Exception as e:
                            st.warning(f"NLP: {e}")
                    else:
                        from collections import Counter
                        import re
                        words = df[tc].dropna().astype(str)
                        common = Counter(re.findall(r"\b\w{5,}\b", " ".join(words).lower()))
                        st.bar_chart(pd.Series(dict(common.most_common(15))))
                        st.info("Install spacy for full NLP enrichment.")
            else:
                st.info("No text columns found.")
        else:
            st.info("Load data first.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Task Board
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "✅ Task Board":
    st.title("✅ Task Board")
    if HAS["tasks"]:
        if "board" not in st.session_state:
            st.session_state["board"] = TaskBoard("DOT Sidewalk Program")
        board = st.session_state["board"]

        with st.expander("➕ Add Task", expanded=False):
            with st.form("new_task_form"):
                title = st.text_input("Title")
                c1,c2,c3,c4 = st.columns(4)
                assignee = c1.text_input("Assignee")
                priority = c2.selectbox("Priority", ["critical","high","medium","low"])
                category = c3.selectbox("Category", list(CATEGORY_COLORS.keys()))
                due = c4.date_input("Due Date")
                desc = st.text_area("Description", height=60)
                borough = st.selectbox("Borough", ["","MANHATTAN","BRONX","BROOKLYN","QUEENS","STATEN ISLAND"])
                if st.form_submit_button("Create Task"):
                    task = Task(title=title, description=desc, assignee=assignee,
                                priority=priority, category=category,
                                due_date=str(due), borough=borough)
                    board.add_task(task)
                    st.success(f"Created: {title}")
                    st.rerun()

        stats = board.stats()
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Tasks", stats.get("total_tasks",0))
        c2.metric("Overdue", stats.get("overdue_count",0))
        c3.metric("Done %", f"{stats.get('completion_rate',0):.0f}%")

        kanban_cols = st.columns(len(board.columns))
        for kcol, status in zip(kanban_cols, board.columns):
            with kcol:
                cnt = stats.get("by_status",{}).get(status, 0)
                st.markdown(f'<div class="kanban-col">', unsafe_allow_html=True)
                st.markdown(f"**{STATUS_LABELS.get(status, status)}** ({cnt})")
                st.markdown("---")
                tasks = board.filter_tasks(status=status)
                for tid, task in tasks:
                    pc = PRIORITY_COLORS.get(task.priority, "#6b7280")
                    st.markdown(f"""<div class="task-card" style="border-left:4px solid {pc}">
                    <b>{task.title}</b><br>
                    <small>{task.assignee or 'Unassigned'} | {task.due_date or 'No due date'}</small>
                    </div>""", unsafe_allow_html=True)
                    other = [s for s in board.columns if s != status]
                    move_cols = st.columns(len(other))
                    for mc, target in zip(move_cols, other):
                        if mc.button(STATUS_LABELS.get(target, target)[:4], key=f"mv_{tid}_{target}"):
                            board.move_task(tid, target)
                            st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Task board module not available.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Settings
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Settings":
    st.title("⚙️ Settings")
    with st.expander("🔑 API Credentials", expanded=True):
        st.text_input("Socrata App Token", value=os.getenv("SOCRATA_APP_TOKEN",""),
                      type="password", key="cfg_token")
        st.text_input("OpenAI API Key", value=os.getenv("OPENAI_API_KEY",""),
                      type="password", key="cfg_oai")
    with st.expander("🗄️ Database"):
        st.text_input("PostgreSQL DSN", type="password", key="cfg_pg")
        st.text_input("MongoDB URI", type="password", key="cfg_mongo")
        st.text_input("DuckDB path", value="nyc_data.db", key="cfg_duck")
        tables = loaded_tables()
        if tables:
            st.markdown(f"**Tables in DuckDB:** {', '.join(tables)}")
    with st.expander("🩺 System Health Check"):
        if st.button("Run Doctor"):
            import importlib
            checks = ["streamlit","pandas","duckdb","plotly","requests","folium",
                      "openpyxl","psycopg","langchain_core","qiskit","numpy","scipy"]
            for mod in checks:
                try:
                    importlib.import_module(mod)
                    st.markdown(f"✅ `{mod}`")
                except ImportError:
                    st.markdown(f"❌ `{mod}` — not installed")
    with st.expander("📦 Toolkit Module Status"):
        for mod, loaded in sorted(HAS.items()):
            icon = "✅" if loaded else "❌"
            st.markdown(f"{icon} `{mod}`")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Data Engineering
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "⚙️ Data Engineering":
    st.title("⚙️ Data Engineering")
    st.write("Clean, transform, and join datasets for analytical readiness.")
    
    t1, t2, t3 = st.tabs(["🧹 Data Cleaning", "🔗 Dataset Joins", "🔄 Automations"])
    
    with t1:
        st.subheader("Automated Cleaning Suite")
        df = active_df_selector("clean_sel")
        if df is not None:
            c1, c2 = st.columns(2)
            if c1.button("✨ Standardize Boroughs"):
                col = st.selectbox("Select Borough Column", df.columns, key="boro_col_sel")
                df_clean = clean.standardize_boroughs(df, col)
                set_df(df_clean, f"{st.session_state.current_label}_clean")
                st.success("Boroughs standardized!")
                st.dataframe(df_clean.head(10))
            
            if c2.button("🐍 Snake_Case Columns"):
                df_clean = clean.clean_column_names(df)
                set_df(df_clean, f"{st.session_state.current_label}_snake")
                st.success("Column names cleaned!")
                st.dataframe(df_clean.head(10))
                
            st.markdown("---")
            if st.button("🧪 Auto-convert Types"):
                df_clean = clean.infer_and_convert_types(df)
                set_df(df_clean, f"{st.session_state.current_label}_typed")
                st.success("Types inferred and converted.")
                st.info(f"Numeric columns: {len(df_clean.select_dtypes(include='number').columns)}")
        else:
            st.info("Select a dataset to clean.")

    with t2:
        st.subheader("Join Datasets")
        st.write("Merge two loaded datasets into one.")
        tables = loaded_tables()
        if len(tables) >= 2:
            c1, c2 = st.columns(2)
            left_tbl = c1.selectbox("Left Table", tables, index=0)
            right_tbl = c2.selectbox("Right Table", tables, index=1)
            
            left_df = db.execute(f'SELECT * FROM "{left_tbl}"').df()
            right_df = db.execute(f'SELECT * FROM "{right_tbl}"').df()
            
            common_cols = list(set(left_df.columns) & set(right_df.columns))
            join_col = st.selectbox("Join on Column", common_cols if common_cols else left_df.columns)
            
            if st.button("🤝 Execute Join"):
                try:
                    from socrata_toolkit.pipeline import join_datasets
                    joined_df = join_datasets(left_df, right_df, on=join_col)
                    set_df(joined_df, f"join_{left_tbl}_{right_tbl}")
                    st.success(f"Joined successfully! Result has {len(joined_df):,} rows.")
                    st.dataframe(joined_df.head(20))
                except Exception as e:
                    st.error(f"Join failed: {e}")
        else:
            st.warning("Load at least two datasets to perform a join.")

    with t3:
        st.subheader("Incremental Sync (Coming Soon)")
        st.info("This feature will allow you to schedule background updates for your DuckDB tables.")

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE: Developer Tools
# ═══════════════════════════════════════════════════════════════════════════════
elif page == "🛠️ Developer Tools":
    st.title("🛠️ Developer Tools")
    
    st.info("💡 **Pro Tip**: For programmatic access in Python, the [`sodapy`](https://github.com/afeld/sodapy) library is highly recommended.")
    
    st.subheader("🔗 SoQL URL Generator")
    st.write("Construct a Socrata Query Language (SoQL) URL for direct API access.")

    with st.expander("Search Datasets", expanded=False):
        c1, c2 = st.columns([3, 1])
        sq = c1.text_input("Keyword search", "sidewalk", key="dev_srch_q")
        sd = c2.text_input("Domain", "data.cityofnewyork.us", key="dev_srch_d")
        if st.button("Search Socrata", key="dev_srch_btn"):
            dev_res = socrata_search(sq, domain=sd)
            if dev_res:
                st.session_state["dev_search_results"] = dev_res
            else:
                st.warning("No datasets found.")
        
        if "dev_search_results" in st.session_state:
            dev_res = st.session_state["dev_search_results"]
            sel_res_dev = st.selectbox("Apply Dataset ID", dev_res, format_func=lambda x: f"{x.name} ({x.fourfour})", key="dev_res_sel")
            if st.button("Use Selected ID"):
                st.session_state["dev_ds_id"] = sel_res_dev.fourfour
                st.session_state["dev_domain"] = sel_res_dev.domain
                st.rerun()

    with st.expander("Configure Query", expanded=True):
        c1, c2 = st.columns(2)
        domain = c1.text_input("Socrata Domain", st.session_state.get("dev_domain", "data.cityofnewyork.us"), key="dev_dom_input")
        ds_id = c2.text_input("Dataset ID (4x4)", st.session_state.get("dev_ds_id", "erm2-nwe9"), key="dev_id_input")

        select = st.text_input("$select (columns)", "*", help="Comma-separated list of columns or functions")
        where = st.text_area("$where (filters)", "", help="Filter conditions (e.g., borough = 'MANHATTAN')")
        order = st.text_input("$order (sorting)", "", help="Column and direction (e.g., date DESC)")
        
        c3, c4 = st.columns(2)
        limit = c3.number_input("$limit", 1, 50000, 1000)
        offset = c4.number_input("$offset", 0, 1000000, 0)

    # Build the URL
    params = []
    if select and select != "*": params.append(f"$select={select}")
    if where: params.append(f"$where={where}")
    if order: params.append(f"$order={order}")
    params.append(f"$limit={limit}")
    if offset > 0: params.append(f"$offset={offset}")

    base_url = f"https://{domain}/resource/{ds_id}.json"
    query_string = "&".join(params)
    full_url = f"{base_url}?{query_string}" if params else base_url

    st.markdown("### 🚀 Generated URL")
    st.code(full_url, language="bash")
    
    c1, c2 = st.columns(2)
    c1.link_button("🌐 Open API JSON in Browser", full_url)
    
    if c2.button("📥 Test Fetch & Preview Data"):
        try:
            with st.spinner("Fetching data from Socrata..."):
                r = requests.get(full_url, timeout=15)
                r.raise_for_status()
                data = r.json()
                if data:
                    st.success(f"Successfully retrieved {len(data)} rows.")
                    st.dataframe(pd.DataFrame(data).head(100), use_container_width=True)
                else:
                    st.warning("Query returned zero results.")
        except Exception as e:
            st.error(f"Fetch failed: {e}")

    st.markdown("---")
    st.subheader("🛠️ Utility Snippets")
    with st.expander("Python (Requests)"):
        st.code(f"""import requests
import pandas as pd

url = "{full_url}"
response = requests.get(url)
data = response.json()
df = pd.DataFrame(data)
print(df.head())""", language="python")

    with st.expander("Python (Sodapy)"):
        st.code(f"""from sodapy import Socrata
import pandas as pd

client = Socrata("{domain}", None) # Add app_token if you have one
results = client.get("{ds_id}", 
                   select="{select}", 
                   where="{where}", 
                   order="{order}", 
                   limit={limit}, 
                   offset={offset})
df = pd.DataFrame.from_records(results)
print(df.head())""", language="python")
