from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from socrata_toolkit.analysis import profile_dataframe, quality_report
from socrata_toolkit.text_analytics import generate_text_insights
from socrata_toolkit.dot_sidewalk import compute_sidewalk_kpis, python_templates, sql_templates
from socrata_toolkit.llm_duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm
from socrata_toolkit.spatial import spatial_intersects_join
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
from socrata_toolkit.conflict import ConflictResolver
from socrata_toolkit.nlp_advanced import analyze_text, translate_text
from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import MongoExporter, PostgresExporter, XLSXExporter
from socrata_toolkit.pipeline import run_from_rows
from socrata_toolkit.persistence import save_pipeline, load_pipelines, delete_pipeline
from socrata_toolkit.streaming_pipeline import stream_pipeline
=======
from socrata_toolkit.nlp_advanced import analyze_text, translate_text
from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import MongoExporter, PostgresExporter, XLSXExporter
>>>>>>> theirs
=======
from socrata_toolkit.nlp_advanced import analyze_text, translate_text
from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import MongoExporter, PostgresExporter, XLSXExporter
>>>>>>> theirs
=======
from socrata_toolkit.nlp_advanced import analyze_text, translate_text
from socrata_toolkit.client import SocrataClient, SocrataConfig
from socrata_toolkit.exporters import MongoExporter, PostgresExporter, XLSXExporter
>>>>>>> theirs


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
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    mode = st.radio("Workflow", ["Search", "Metadata", "Fetch & Export", "Analysis Studio", "DOT Sidewalk Dashboard", "Conflict & Reporting", "Code Export Studio", "LLM Augmentation", "NLP Studio", "Automated Upsert"])
=======
    mode = st.radio("Workflow", ["Search", "Metadata", "Fetch & Export", "Analysis Studio", "DOT Sidewalk Dashboard", "Code Export Studio", "LLM Augmentation", "NLP Studio", "Automated Upsert"])
>>>>>>> theirs
=======
    mode = st.radio("Workflow", ["Search", "Metadata", "Fetch & Export", "Analysis Studio", "DOT Sidewalk Dashboard", "Code Export Studio", "LLM Augmentation", "NLP Studio", "Automated Upsert"])
>>>>>>> theirs
=======
    mode = st.radio("Workflow", ["Search", "Metadata", "Fetch & Export", "Analysis Studio", "DOT Sidewalk Dashboard", "Code Export Studio", "LLM Augmentation", "NLP Studio", "Automated Upsert"])
>>>>>>> theirs

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

        st.markdown("#### Spatial Conflict Analysis")
        st.caption("Upload a second geospatial layer to compute intersection conflict rate.")
        upl = st.file_uploader("Upload right-side layer JSON", type=["json"], key="dot_right_layer")
        left_geom = st.text_input("Left geometry column", value="geometry")
        right_geom = st.text_input("Right geometry column", value="geometry")
        if upl is not None and st.button("Run Spatial Intersects Join"):
            right_df = pd.read_json(upl)
            sj = spatial_intersects_join(df, right_df, left_geom_col=left_geom, right_geom_col=right_geom)
            st.metric("Conflict Rate", round(sj.conflict_rate, 4))
            st.metric("Overlap Count", sj.overlap_count)
            st.dataframe(sj.joined.head(300), use_container_width=True)

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
elif mode == "Conflict & Reporting":
    st.subheader("Conflict & Reporting")
    st.caption("Upload a proposed workset or fetch from Socrata and compare against a reference layer.")
    col1, col2 = st.columns(2)
    source_type = col1.radio("Proposed source", ["Upload file", "Fetch from Socrata"])
    proposed_df = None
    if source_type == "Upload file":
        upl = col1.file_uploader("Upload proposed features (GeoJSON or JSON or CSV)", type=["json", "geojson", "csv"])
        if upl is not None:
            p = save_uploaded(upl)
            if p.suffix.lower() == ".csv":
                proposed_df = pd.read_csv(p)
            else:
                payload = json.loads(p.read_text())
                if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
                    proposed_df = pd.DataFrame([f.get("properties", {}) | {"geometry": f.get("geometry")} for f in payload.get("features", [])])
                elif isinstance(payload, list):
                    proposed_df = pd.DataFrame(payload)
    else:
        p_domain = col1.text_input("Proposed domain", value=domain)
        p_ds = col1.text_input("Proposed dataset id", value=dataset_id)
        p_max = col1.number_input("Max rows", min_value=10, value=5000)
        if col1.button("Load proposed from Socrata"):
            rows = []
            with st.spinner("Fetching proposed rows..."):
                for batch in client.fetch_json(p_domain, p_ds, max_rows=int(p_max)):
                    rows.extend(batch)
            proposed_df = pd.DataFrame(rows)

    st.markdown("---")
    st.markdown("### Reference layer")
    r_domain = st.text_input("Reference domain", value=domain)
    r_ds = st.text_input("Reference dataset id", value="")
    r_upload = st.file_uploader("Or upload reference layer", type=["json", "geojson", "csv"], key="ref_upload")
    reference_df = None
    if r_upload is not None:
        p = save_uploaded(r_upload)
        if p.suffix.lower() == ".csv":
            reference_df = pd.read_csv(p)
        else:
            payload = json.loads(p.read_text())
            if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
                reference_df = pd.DataFrame([f.get("properties", {}) | {"geometry": f.get("geometry")} for f in payload.get("features", [])])
            elif isinstance(payload, list):
                reference_df = pd.DataFrame(payload)
    elif r_ds:
        r_max = st.number_input("Reference max rows", min_value=10, value=5000)
        if st.button("Load reference from Socrata"):
            rows = []
            with st.spinner("Fetching reference rows..."):
                for batch in client.fetch_json(r_domain, r_ds, max_rows=int(r_max)):
                    rows.extend(batch)
            reference_df = pd.DataFrame(rows)

    buf_m = st.number_input("Buffer (meters)", min_value=1.0, value=20.0)

    if proposed_df is not None and reference_df is not None and st.button("Run Conflict Analysis"):
        resolver = ConflictResolver()
        annotated, summary = resolver.resolve_conflicts(proposed_df, reference_df, proposed_geom_col="geometry", reference_geom_col="geometry", buffer_m=buf_m)
        st.metric("Conflict Rate", round(summary.conflict_rate, 4))
        st.metric("Total Proposed", summary.total_proposed)
        st.metric("Total Conflicts", summary.total_conflicts)
        st.dataframe(annotated.head(200), use_container_width=True)

        gj = resolver.export_geojson(annotated)
        st.download_button("Download Conflicts GeoJSON", data=json.dumps(gj), file_name="conflicts.geojson", mime="application/geo+json")
        clist = resolver.generate_construction_list(annotated)
        tmp = Path(tempfile.gettempdir()) / "construction_list.xlsx"
        XLSXExporter().write(clist, str(tmp))
        st.download_button("Download Construction List XLSX", data=tmp.read_bytes(), file_name="construction_list.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

=======
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
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


elif mode == "LLM Augmentation":
    st.subheader("LLM Augmentation (llm_duck-style)")
    endpoint = st.text_input("LLM endpoint", value="http://localhost:1234/v1/chat/completions")
    model = st.text_input("Model", value="local-model")
    text_column = st.text_input("Text column to classify", value="description")
    max_rows = st.number_input("Rows", min_value=10, value=1000)
    out_name = st.text_input("Output filename", value="llm_augmented.json")
    if st.button("Run LLM Augmentation", type="primary"):
        rows = []
        for batch in client.fetch_json(domain, dataset_id, max_rows=int(max_rows)):
            rows.extend(batch)
        df = pd.DataFrame(rows)
        if text_column not in df.columns:
            st.error(f"Column '{text_column}' not found")
        else:
            cfg = LLMAugmentConfig(endpoint=endpoint, model=model)
            out_df = augment_dataframe_with_llm(df, text_column=text_column, cfg=cfg)
            st.dataframe(out_df.head(200), use_container_width=True)
            st.download_button("Download LLM-augmented JSON", data=out_df.to_json(orient="records"), file_name=out_name)


elif mode == "NLP Studio":
    st.subheader("NLP Studio")
    txt = st.text_area("Input text", height=160)
    tgt = st.text_input("Translate to language code (optional)", value="")
    if st.button("Run NLP", type="primary") and txt.strip():
        out = analyze_text(txt)
        st.json({
            "tokens": out.tokens,
            "lemmas": out.lemmas,
            "entities": out.entities,
            "pos_tags": out.pos_tags,
            "sentiment": out.sentiment,
            "summary": out.summary,
        })
        if tgt.strip():
            st.write("Translation", translate_text(txt, target_lang=tgt.strip()))

else:
    st.subheader("Automated Upsert / Pipeline")
    st.write("Choose source: live Socrata fetch or upload JSON/GeoJSON file.")
    source = st.radio("Source", ["Fetch from Socrata", "Upload file"])

    rows: list[dict] = []
    geojson_payload: dict | None = None

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    # Source controls
    if source == "Fetch from Socrata":
        where = st.text_input("WHERE filter", value="")
        max_rows = st.number_input("Max rows", min_value=1, value=10000)
        load_btn = st.button("Load Source Data", type="primary")
        if load_btn:
            fetched = 0
            placeholder = st.empty()
            with st.spinner("Fetching rows from Socrata..."):
                for batch in client.fetch_json(domain, dataset_id, where=where or None, max_rows=int(max_rows)):
                    rows.extend(batch)
                    fetched += len(batch)
                    placeholder.text(f"Rows fetched: {fetched}")
            placeholder.empty()
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
    if source == "Fetch from Socrata":
        where = st.text_input("WHERE filter")
        max_rows = st.number_input("Max rows", min_value=1, value=10000)
        if st.button("Load Source Data", type="primary"):
            for batch in client.fetch_json(domain, dataset_id, where=where or None, max_rows=int(max_rows)):
                rows.extend(batch)
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
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
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
        st.markdown("**Preview of source rows (first 200)**")
        st.dataframe(pd.DataFrame(rows).head(200), use_container_width=True)

    st.markdown("### Targets & Options")
    t1, t2, t3 = st.columns([1, 1, 1])
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
        st.dataframe(pd.DataFrame(rows).head(500), use_container_width=True)

    st.markdown("### Targets")
    t1, t2, t3 = st.columns(3)
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
    do_pg = t1.checkbox("PostgreSQL")
    do_mongo = t2.checkbox("MongoDB")
    do_xlsx = t3.checkbox("XLSX backup")

<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
    pg_cfg = {}
    if do_pg:
        pg_cfg["dsn"] = st.text_input("Postgres DSN", type="password")
        pg_cfg["table"] = st.text_input("Postgres table", value="socrata_data")
        pg_cfg["conflict_column"] = st.text_input("Postgres conflict column", value="id")

    mongo_cfg = {}
    if do_mongo:
        mongo_cfg["uri"] = st.text_input("Mongo URI", type="password")
        mongo_cfg["db"] = st.text_input("Mongo DB", value="socrata")
        mongo_cfg["collection"] = st.text_input("Mongo collection", value="socrata_data")
        mongo_cfg["conflict_field"] = st.text_input("Mongo conflict field", value="id")

    xlsx_cfg = {}
    if do_xlsx:
        xlsx_cfg["filename"] = st.text_input("XLSX filename", value=f"{dataset_id}_backup.xlsx")

    st.markdown("### Saved Pipelines")
    saved = load_pipelines()
    saved_names = [""] + list(saved.keys())
    sel = st.selectbox("Load saved pipeline", options=saved_names)
    if sel:
        cfg = saved.get(sel, {})
        st.info(f"Loaded pipeline '{sel}': {cfg.get('description', '')}")
        st.write(cfg)

    st.markdown("### Run Options")
    dry_run = st.checkbox("Dry run / Preview (no writes)", value=True)
    confirm_write = st.checkbox("I confirm I want to perform writes (enable only when ready)")
    streaming_mode = st.checkbox("Use streaming mode (low memory)", value=True)
    chunk_size = st.number_input("Streaming chunk size (rows per request)", min_value=10, value=client.config.page_size)

    # Save pipeline
    save_name = st.text_input("Save current pipeline as... (optional)")
    if st.button("Save pipeline") and save_name:
        config = {
            "domain": domain,
            "dataset_id": dataset_id,
            "where": where if source == "Fetch from Socrata" else "",
            "targets": {"postgres": pg_cfg if do_pg else {}, "mongo": mongo_cfg if do_mongo else {}, "xlsx": xlsx_cfg if do_xlsx else {}},
        }
        save_pipeline(save_name, {"description": f"Saved from UI: {save_name}", "config": config})
        st.success(f"Saved pipeline '{save_name}'")

    st.markdown("### Preview / Run")
    if st.button("Preview Pipeline"):
        targets = {
            "postgres": {**pg_cfg, "enabled": do_pg} if do_pg else {"enabled": False},
            "mongo": {**mongo_cfg, "enabled": do_mongo} if do_mongo else {"enabled": False},
            "xlsx": {"enabled": do_xlsx, "path": str(Path(tempfile.gettempdir()) / xlsx_cfg.get("filename", f"{dataset_id}_backup.xlsx"))} if do_xlsx else {"enabled": False},
        }
        if streaming_mode and source == "Fetch from Socrata":
            report = stream_pipeline(client, domain, dataset_id, targets, dry_run=True, chunk_size=int(chunk_size))
        else:
            report = run_from_rows(rows, targets, dry_run=True)
        st.markdown("**Preview Report**")
        st.json(report)
        if report.get("targets", {}).get("postgres"):
            st.markdown("**Postgres Preview SQL**")
            st.code(report["targets"]["postgres"]["preview"]["create_table"])
            if report["targets"]["postgres"]["preview"].get("index"):
                st.code(report["targets"]["postgres"]["preview"]["index"])
            st.code(report["targets"]["postgres"]["preview"]["insert_example"])

    if st.button("Run Pipeline"):
        if dry_run:
            st.warning("Pipeline configured for dry-run. Uncheck 'Dry run / Preview' to perform writes.")
        elif not confirm_write:
            st.error("Please confirm writes by checking 'I confirm I want to perform writes' before running the pipeline.")
        else:
            targets = {
                "postgres": {**pg_cfg, "enabled": do_pg} if do_pg else {"enabled": False},
                "mongo": {**mongo_cfg, "enabled": do_mongo} if do_mongo else {"enabled": False},
                "xlsx": {"enabled": do_xlsx, "path": str(Path(tempfile.gettempdir()) / xlsx_cfg.get("filename", f"{dataset_id}_backup.xlsx"))} if do_xlsx else {"enabled": False},
            }
            if streaming_mode and source == "Fetch from Socrata":
                progress = st.progress(0)
                status = st.empty()

                def cb(fetched, total):
                    try:
                        if total:
                            pct = int(min(100, (fetched / total) * 100))
                        else:
                            pct = 0
                        progress.progress(pct)
                        status.text(f"Fetched {fetched} rows (total est: {total})")
                    except Exception:
                        pass

                with st.spinner("Running streaming pipeline..."):
                    report = stream_pipeline(client, domain, dataset_id, targets, dry_run=False, chunk_size=int(chunk_size), max_rows=int(max_rows) if max_rows else None, progress_callback=cb)
                st.success("Pipeline run complete")
                st.json(report)
            else:
                with st.spinner("Running pipeline..."):
                    report = run_from_rows(rows, targets, dry_run=False)
                st.success("Pipeline run complete")
                st.json(report)
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
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
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
