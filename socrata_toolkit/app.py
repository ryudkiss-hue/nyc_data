from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from socrata_toolkit.analysis import profile_dataframe, quality_report
from socrata_toolkit.text_analytics import generate_text_insights
from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis, python_templates, sql_templates
from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import MongoExporter, PostgresExporter, XLSXExporter


st.set_page_config(page_title="Socrata Toolkit", page_icon="🗂", layout="wide")
st.title("🗂 Socrata Toolkit Workbench")
st.caption("Search Socrata portals, inspect metadata, fetch data, and export/upsert from one UI.")


@st.cache_resource
def get_client(token: str | None) -> SocrataClient:
    return SocrataClient(SocrataConfig(app_token=token or None))


def save_uploaded(uploaded) -> Path:
    tmpdir = Path(tempfile.gettempdir()) / "socrata_toolkit"
    tmpdir.mkdir(parents=True, exist_ok=True)
    path = tmpdir / uploaded.name
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())
    return path


with st.sidebar:
    st.header("Connection")
    token = st.text_input("Socrata App Token", type="password", help="Optional but recommended.")
    domain = st.text_input("Domain", value="data.cityofnewyork.us")
    dataset_id = st.text_input("Dataset ID (4x4)", value="h9gi-nx95")
    mode = st.radio("Workflow", ["Search", "Metadata", "Fetch & Export", "Analysis Studio", "DOT Sidewalk Dashboard", "Code Export Studio", "Automated Upsert"])

client = get_client(token)

if mode == "Search":
    st.subheader("Catalog Search")
    c1, c2, c3 = st.columns(3)
    query = c1.text_input("Query", value="restaurant inspections")
    category = c2.text_input("Category")
    tags = c3.text_input("Tags (comma-separated)")
    order = st.selectbox("Order", ["", "relevance", "page_views_last_month", "updated_at"])
    limit = st.slider("Limit", 1, 100, 10)

    if st.button("Run Search", type="primary"):
        with st.spinner("Searching catalog..."):
            results = client.search(query=query, domain=domain or None, category=category or None, tags=tags or None, order=order or None, limit=limit)
        rows = [r.__dict__ for r in results]
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        st.download_button("Download results.json", data=json.dumps(rows, indent=2), file_name="search_results.json", mime="application/json")

elif mode == "Metadata":
    st.subheader("Dataset Metadata & Column Dictionary")
    if st.button("Load Metadata", type="primary"):
        with st.spinner("Fetching metadata..."):
            meta = client.get_metadata(domain, dataset_id)
        st.json(meta.summary())
        cols_df = pd.DataFrame(meta.column_dict())
        st.dataframe(cols_df, use_container_width=True, height=360)
        st.download_button("Download metadata.json", data=json.dumps({"summary": meta.summary(), "columns": meta.column_dict()}, indent=2), file_name=f"{dataset_id}_metadata.json", mime="application/json")

elif mode == "Fetch & Export":
    st.subheader("Fetch, Preview, and Export")
    c1, c2 = st.columns(2)
    where = c1.text_area("SoQL WHERE", placeholder="crash_date >= '2024-01-01'")
    select = c2.text_area("SoQL SELECT", placeholder="collision_id, crash_date, borough")
    c3, c4, c5 = st.columns(3)
    order = c3.text_input("ORDER BY", placeholder="crash_date DESC")
    q = c4.text_input("Full-text q")
    max_rows = c5.number_input("Max rows", min_value=1, value=5000)

    output_formats = st.multiselect("Output formats", ["JSON", "GeoJSON", "XLSX"], default=["JSON", "XLSX"])

    if st.button("Fetch Data", type="primary"):
        with st.spinner("Fetching dataset rows..."):
            rows = []
            for batch in client.fetch_json(domain, dataset_id, where=where or None, select=select or None, order=order or None, q=q or None, max_rows=int(max_rows)):
                rows.extend(batch)
        st.success(f"Fetched {len(rows)} rows")
        df = pd.DataFrame(rows)
        st.dataframe(df.head(1000), use_container_width=True, height=380)

        if "JSON" in output_formats:
            st.download_button("Download JSON", data=json.dumps(rows, default=str), file_name=f"{dataset_id}.json", mime="application/json")

        if "GeoJSON" in output_formats:
            geojson = client.fetch_geojson(domain, dataset_id, where=where or None, max_rows=int(max_rows))
            st.download_button("Download GeoJSON", data=json.dumps(geojson), file_name=f"{dataset_id}.geojson", mime="application/geo+json")

        if "XLSX" in output_formats:
            meta = client.get_metadata(domain, dataset_id)
            tmp = Path(tempfile.gettempdir()) / f"{dataset_id}.xlsx"
            XLSXExporter().write(df, str(tmp), meta=meta)
            st.download_button("Download XLSX", data=tmp.read_bytes(), file_name=f"{dataset_id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif mode == "Analysis Studio":
    st.subheader("Analysis Studio")
    where = st.text_input("WHERE", placeholder="Optional SoQL filter")
    max_rows = st.number_input("Rows to profile", min_value=100, value=5000)
    key_columns = st.text_input("Key columns (comma-separated)", value="")
    if st.button("Run Analysis", type="primary"):
        rows = []
        with st.spinner("Fetching data for profiling..."):
            for batch in client.fetch_json(domain, dataset_id, where=where or None, max_rows=int(max_rows)):
                rows.extend(batch)
        df = pd.DataFrame(rows)
        profile = profile_dataframe(df)
        quality = quality_report(df, [c.strip() for c in key_columns.split(",") if c.strip()])

        a, b, c = st.columns(3)
        a.metric("Rows", profile.row_count)
        b.metric("Columns", profile.column_count)
        c.metric("Missing cells", quality["missing_cells"])

        st.markdown("#### Data Types")
        st.dataframe(pd.DataFrame({"column": list(profile.dtypes.keys()), "dtype": list(profile.dtypes.values())}), use_container_width=True)

        st.markdown("#### Null Counts")
        null_df = pd.DataFrame({"column": list(profile.null_counts.keys()), "nulls": list(profile.null_counts.values())}).sort_values("nulls", ascending=False)
        st.bar_chart(null_df.set_index("column").head(20))
        st.dataframe(null_df, use_container_width=True)

        if profile.numeric_summary:
            st.markdown("#### Numeric Summary")
            st.dataframe(pd.DataFrame(profile.numeric_summary).T, use_container_width=True)

        st.markdown("#### Quality Report")
        st.json(quality)

        st.markdown("#### NLP / FTS / Regex Insights")
        text_cols = st.multiselect("Text columns for NLP", options=list(df.columns))
        geo_col = st.selectbox("Geo column (optional)", options=[""] + list(df.columns))
        if st.button("Generate Text Insights") and text_cols:
            tagged_df, t_ins = generate_text_insights(df, text_cols, geo_column=geo_col or None)
            st.write("Top terms", t_ins.top_terms[:20])
            st.write("Regex hits", t_ins.regex_hits)
            st.write("Tag vocabulary", t_ins.tags[:100])
            st.dataframe(tagged_df.head(200), use_container_width=True)



elif mode == "DOT Sidewalk Dashboard":
    st.subheader("DOT Sidewalk Program Dashboard")
    st.caption("KPI dashboard aligned to contract planning, progress, budget, and quality responsibilities.")
    where = st.text_input("WHERE filter for DOT dataset")
    max_rows = st.number_input("Rows", min_value=100, value=5000)
    if st.button("Load DOT Data", type="primary"):
        rows = []
        for batch in client.fetch_json(domain, dataset_id, where=where or None, max_rows=int(max_rows)):
            rows.extend(batch)
        df = pd.DataFrame(rows)
        kpi = compute_sidewalk_kpis(df)
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Defect Density", round(kpi.defect_density, 4))
        c2.metric("Throughput Velocity", round(kpi.throughput_velocity, 2))
        c3.metric("Burn Variance", round(kpi.burn_variance, 2))
        c4.metric("First-Pass Yield", round(kpi.first_pass_yield, 4))
        c5.metric("Rework Factor", round(kpi.rework_factor, 4))
        st.dataframe(df.head(500), use_container_width=True)

elif mode == "Code Export Studio":
    st.subheader("Exportable SQL/Python Methods")
    st.markdown("Generate reusable SQL and Python templates driven by current analytical framework.")
    st.markdown("#### SQL Templates")
    st.json(sql_templates())
    st.download_button("Download SQL templates", data="\n".join(sql_templates().values()), file_name="dot_sidewalk_templates.sql")

    st.markdown("#### Python Templates")
    py_payload = python_templates()
    st.json(py_payload)
    st.download_button("Download Python templates", data="\n\n".join(py_payload.values()), file_name="dot_sidewalk_templates.py")

else:
    st.subheader("Automated Upsert / Pipeline")
    st.write("Choose source: live Socrata fetch or upload JSON/GeoJSON file.")
    source = st.radio("Source", ["Fetch from Socrata", "Upload file"])

    rows: list[dict] = []
    geojson_payload: dict | None = None

    if source == "Fetch from Socrata":
        where = st.text_input("WHERE filter")
        max_rows = st.number_input("Max rows", min_value=1, value=10000)
        if st.button("Load Source Data", type="primary"):
            for batch in client.fetch_json(domain, dataset_id, where=where or None, max_rows=int(max_rows)):
                rows.extend(batch)
            st.success(f"Loaded {len(rows)} records from Socrata")
    else:
        uploaded = st.file_uploader("Upload JSON or GeoJSON", type=["json", "geojson"])
        if uploaded is not None:
            path = save_uploaded(uploaded)
            payload = json.loads(path.read_text())
            if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
                geojson_payload = payload
                rows = [f.get("properties", {}) for f in payload.get("features", [])]
            elif isinstance(payload, list):
                rows = payload
            st.success(f"Loaded {len(rows)} records from file")

    if rows:
        st.dataframe(pd.DataFrame(rows).head(500), use_container_width=True)

    st.markdown("### Targets")
    t1, t2, t3 = st.columns(3)
    do_pg = t1.checkbox("PostgreSQL")
    do_mongo = t2.checkbox("MongoDB")
    do_xlsx = t3.checkbox("XLSX backup")

    pg_dsn = pg_table = pg_conflict = ""
    if do_pg:
        pg_dsn = st.text_input("Postgres DSN", type="password")
        pg_table = st.text_input("Postgres table", value="socrata_data")
        pg_conflict = st.text_input("Postgres conflict column", value="id")

    m_uri = m_db = m_col = m_conflict = ""
    if do_mongo:
        m_uri = st.text_input("Mongo URI", type="password")
        m_db = st.text_input("Mongo DB", value="socrata")
        m_col = st.text_input("Mongo collection", value="socrata_data")
        m_conflict = st.text_input("Mongo conflict field", value="id")

    if do_xlsx:
        xlsx_name = st.text_input("XLSX filename", value=f"{dataset_id}_backup.xlsx")
    else:
        xlsx_name = ""

    if st.button("Run Automated Upsert Pipeline", type="primary", disabled=not rows):
        report = []
        if do_pg and pg_dsn and pg_table and pg_conflict:
            with PostgresExporter(pg_dsn) as pg:
                total = pg.upsert_batches([rows], table=pg_table, conflict_column=pg_conflict)
            report.append(f"PostgreSQL upserted: {total}")

        if do_mongo and m_uri and m_db and m_col and m_conflict:
            with MongoExporter(m_uri, m_db) as mg:
                if geojson_payload:
                    total = mg.upsert_geojson(geojson_payload, collection=m_col, conflict_field=m_conflict)
                else:
                    total = mg.upsert_batches([rows], collection=m_col, conflict_field=m_conflict)
            report.append(f"MongoDB upserted: {total}")

        if do_xlsx and xlsx_name:
            out = Path(tempfile.gettempdir()) / xlsx_name
            XLSXExporter().write(rows, str(out))
            st.download_button("Download XLSX backup", data=out.read_bytes(), file_name=xlsx_name)
            report.append(f"XLSX created: {xlsx_name}")

        if not report:
            st.warning("No targets configured.")
        else:
            st.success(" | ".join(report))
