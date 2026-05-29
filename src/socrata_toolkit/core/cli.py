from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor

import click
import pandas as pd

from ..analysis import generate_text_insights, profile_dataframe, quality_report
from ..llm.duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm
from ..spatial.core import spatial_intersects_join
from .config import get_default, load_local_config
from .logging_utils import get_logger, write_run_report

try:
    from ..nlp.advanced import analyze_text, translate_text  # type: ignore
except Exception:  # pragma: no cover
    analyze_text = None  # type: ignore
    translate_text = None  # type: ignore
from ..pipeline.streaming import stream_pipeline
from ..quality.validation import validate_required_columns
from .client import SocrataClient, SocrataConfig
from .exporters import MongoExporter, PostgresExporter, XLSXExporter
from .state import load_state, save_state

try:
    from ..sql.builder import in_clause  # type: ignore
    from ..sql.conflict import ConflictResolver, PostGISConflictResolver  # type: ignore
except Exception:  # pragma: no cover
    ConflictResolver = None  # type: ignore
    PostGISConflictResolver = None  # type: ignore
    in_clause = None  # type: ignore
from ..alerts.manager import Alert, AlertManager, CLINotifier, DBNotifier, EmailNotifier
from ..discovery.schema import BackwardCompatibilityChecker, SchemaRegistry, SchemaValidator


def _client() -> SocrataClient:
    return SocrataClient(SocrataConfig())


CFG = load_local_config()
LOGGER = get_logger()


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-v", "--verbose", count=True, help="Increase verbosity (-v for INFO, -vv for DEBUG)")
@click.option("--log-level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), default=None, help="Explicit log level")
@click.pass_context
def main(ctx, verbose: int, log_level: str | None) -> None:
    """Socrata toolkit CLI."""
    # Configure logging level based on flags (default INFO)
    level = logging.INFO
    if log_level:
        level = getattr(logging, log_level, logging.INFO)
    else:
        if verbose >= 2:
            level = logging.DEBUG
        elif verbose == 1:
            level = logging.INFO
        else:
            level = logging.INFO
    LOGGER.setLevel(level)
    ctx.ensure_object(dict)
    ctx.obj["log_level"] = level


@main.command()
@click.argument("query", required=False)
@click.option("--domain")
@click.option("--category")
@click.option("--tags")
@click.option("--order")
@click.option("--limit", type=int, default=10)
@click.option("--json-out", type=click.Path())
def search(query, domain, category, tags, order, limit, json_out):
    results = _client().search(query, domain, category, tags, order, limit)
    payload = [r.__dict__ for r in results]
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return
    click.echo(json.dumps(payload, indent=2))


@main.command("meta")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--columns-only", is_flag=True)
@click.option("--json-out", type=click.Path())
def meta_cmd(domain, fourfour, columns_only, json_out):
    meta = _client().get_metadata(domain, fourfour)
    payload = meta.column_dict() if columns_only else {"summary": meta.summary(), "columns": meta.column_dict()}
    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return
    click.echo(json.dumps(payload, indent=2))


@main.command("fetch")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--format", "fmt", type=click.Choice(["json", "geojson", "xlsx"]), default="json")
@click.option("--out", required=True, type=click.Path())
@click.option("--where")
@click.option("--select")
@click.option("--order")
@click.option("--q")
@click.option("--max-rows", type=int)
@click.option("--include-meta", is_flag=True)
def fetch_cmd(domain, fourfour, fmt, out, where, select, order, q, max_rows, include_meta):
    c = _client()
    if fmt == "json":
        rows = []
        for batch in c.fetch_json(domain, fourfour, where=where, select=select, order=order, q=q, max_rows=max_rows):
            rows.extend(batch)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rows, f)
    elif fmt == "geojson":
        gj = c.fetch_geojson(domain, fourfour, where=where, max_rows=max_rows)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(gj, f)
    else:
        df = c.fetch_dataframe(domain, fourfour, where=where, select=select, order=order, q=q, max_rows=max_rows)
        meta = c.get_metadata(domain, fourfour) if include_meta else None
        XLSXExporter().write(df, out, meta=meta)


@main.command("upsert-pg")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--dsn", envvar="PG_DSN", required=True)
@click.option("--table", required=True)
@click.option("--conflict-col", required=True)
@click.option("--save-meta", is_flag=True)
def upsert_pg(domain, fourfour, dsn, table, conflict_col, save_meta):
    c = _client()
    with PostgresExporter(dsn) as pg:
        total = pg.upsert_batches(c.fetch_json(domain, fourfour), table=table, conflict_column=conflict_col)
        if save_meta:
            pg.upsert_metadata(c.get_metadata(domain, fourfour))
    click.echo(f"Upserted {total} rows")


@main.command("upsert-mongo")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--uri", envvar="MONGO_URI", required=True)
@click.option("--db", "db_name", required=True)
@click.option("--collection", required=True)
@click.option("--conflict-field", required=True)
@click.option("--geojson", is_flag=True)
def upsert_mongo(domain, fourfour, uri, db_name, collection, conflict_field, geojson):
    c = _client()
    with MongoExporter(uri, db_name) as mongo:
        if geojson:
            total = mongo.upsert_geojson(c.fetch_geojson(domain, fourfour), collection=collection, conflict_field=conflict_field)
        else:
            total = mongo.upsert_batches(c.fetch_json(domain, fourfour), collection=collection, conflict_field=conflict_field)
    click.echo(f"Upserted {total} rows")


@main.command("pipeline")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--where")
@click.option("--select")
@click.option("--order")
@click.option("--q")
@click.option("--max-rows", type=int)
@click.option("--pg-dsn", envvar="PG_DSN")
@click.option("--pg-table")
@click.option("--pg-conflict-col")
@click.option("--mongo-uri", envvar="MONGO_URI")
@click.option("--mongo-db")
@click.option("--mongo-collection")
@click.option("--mongo-conflict-field")
@click.option("--xlsx-out", type=click.Path())
@click.option("--json-out", type=click.Path())
@click.option("--geojson-out", type=click.Path())
@click.option("--report-path", type=click.Path(), default="outputs/pipeline_run_report.json")
@click.option("--state-path", type=click.Path(), default="outputs/pipeline_state.json")
@click.option("--required-col", multiple=True)
@click.option("--dry-run", is_flag=True, default=False, help="Preview the pipeline without performing writes")
@click.option("--stream", "use_stream", is_flag=True, default=False, help="Use streaming (low-memory) mode")
@click.option("--chunk-size", type=int, default=None, help="Chunk size (overrides client page_size) for streaming mode")
def pipeline(domain, fourfour, where, select, order, q, max_rows, pg_dsn, pg_table, pg_conflict_col, mongo_uri, mongo_db, mongo_collection, mongo_conflict_field, xlsx_out, json_out, geojson_out, report_path, state_path, required_col, dry_run, use_stream, chunk_size):
    c = _client()
    LOGGER.info("Starting analysis for %s/%s", domain, fourfour)
    # If user requested required-column checks in streaming mode, validate via metadata (no full fetch)
    if use_stream and required_col:
        try:
            meta = c.get_metadata(domain, fourfour)
            meta_cols = [col.get("name") for col in (meta.columns or [])]
            missing = [rc for rc in required_col if rc not in meta_cols]
            if missing:
                raise click.ClickException(f"Required columns not found in metadata: {missing}")
        except click.ClickException:
            raise
        except Exception as exc:
            raise click.ClickException(f"Failed to validate required columns: {exc}")
    # If streaming mode requested, delegate to streaming pipeline
    if use_stream:
        targets = {
            "postgres": {"enabled": bool(pg_dsn and pg_table and pg_conflict_col), "dsn": pg_dsn, "table": pg_table, "conflict_column": pg_conflict_col},
            "mongo": {"enabled": bool(mongo_uri and mongo_db and mongo_collection and mongo_conflict_field), "uri": mongo_uri, "db": mongo_db, "collection": mongo_collection, "conflict_field": mongo_conflict_field},
            "xlsx": {"enabled": bool(xlsx_out), "path": xlsx_out},
        }
        report = stream_pipeline(c, domain, fourfour, targets, dry_run=dry_run, chunk_size=chunk_size, max_rows=max_rows)
        # write report and state
        prev_state = load_state(state_path)
        run_payload = {"domain": domain, "fourfour": fourfour, "rows": report.get("rows", 0), "outputs": {"postgres": bool(pg_dsn and pg_table and pg_conflict_col), "mongo": bool(mongo_uri and mongo_db and mongo_collection and mongo_conflict_field), "xlsx": bool(xlsx_out)}, "prev_state": prev_state, "report": report}
        write_run_report(report_path, run_payload)
        save_state(state_path, {"domain": domain, "fourfour": fourfour, "last_rows": report.get("rows", 0)})
        click.echo(json.dumps(report, indent=2))
        return

    # Standard (non-streaming) pipeline
    rows = []
    for batch in c.fetch_json(domain, fourfour, where=where, select=select, order=order, q=q, max_rows=max_rows):
        rows.extend(batch)

    df = pd.DataFrame(rows)
    if required_col:
        vr = validate_required_columns(df, list(required_col))
        if not vr.valid:
            raise click.ClickException("; ".join(vr.errors))

    def _write_json():
        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(rows, f)

    def _write_xlsx():
        if xlsx_out:
            XLSXExporter().write(rows, xlsx_out, meta=c.get_metadata(domain, fourfour))

    def _write_geojson():
        if geojson_out:
            with open(geojson_out, "w", encoding="utf-8") as f:
                json.dump(c.fetch_geojson(domain, fourfour, where=where, max_rows=max_rows), f)

    def _upsert_pg():
        if pg_dsn and pg_table and pg_conflict_col:
            with PostgresExporter(pg_dsn) as pg:
                pg.upsert_batches([rows], table=pg_table, conflict_column=pg_conflict_col)

    def _upsert_mongo():
        if mongo_uri and mongo_db and mongo_collection and mongo_conflict_field:
            with MongoExporter(mongo_uri, mongo_db) as mongo:
                mongo.upsert_batches([rows], collection=mongo_collection, conflict_field=mongo_conflict_field)

    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(fn) for fn in (_write_json, _write_xlsx, _write_geojson, _upsert_pg, _upsert_mongo)]
        for fut in futures:
            fut.result()
    # load previous state (if any) and write a run report
    prev_state = load_state(state_path)
    run_payload = {
        "domain": domain,
        "fourfour": fourfour,
        "rows": len(rows),
        "outputs": {
            "json": bool(json_out),
            "xlsx": bool(xlsx_out),
            "geojson": bool(geojson_out),
            "postgres": bool(pg_dsn and pg_table and pg_conflict_col),
            "mongo": bool(mongo_uri and mongo_db and mongo_collection and mongo_conflict_field),
        },
        "prev_state": prev_state,
    }
    write_run_report(report_path, run_payload)
    save_state(state_path, {"domain": domain, "fourfour": fourfour, "last_rows": len(rows)})
    LOGGER.info("Pipeline complete for %s rows. Report: %s", len(rows), report_path)
    click.echo(f"Pipeline complete for {len(rows)} rows")


@main.command("analyze")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--where")
@click.option("--select")
@click.option("--order")
@click.option("--q")
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
@click.option("--key-column", multiple=True)
@click.option("--state-path", type=click.Path(), default="outputs/pipeline_state.json")
def analyze_cmd(domain, fourfour, where, select, order, q, max_rows, key_column, state_path):
    c = _client()
    LOGGER.info("Starting pipeline for %s/%s", domain, fourfour)
    try:
        prev_state = load_state(state_path)
    except Exception:
        prev_state = None
    rows = []
    for batch in c.fetch_json(domain, fourfour, where=where, select=select, order=order, q=q, max_rows=max_rows):
        rows.extend(batch)
    import pandas as pd

    df = pd.DataFrame(rows)
    profile = profile_dataframe(df)
    quality = quality_report(df, list(key_column))
    payload = {
        "profile": {
            "row_count": profile.row_count,
            "column_count": profile.column_count,
            "dtypes": profile.dtypes,
            "null_counts": profile.null_counts,
            "numeric_summary": profile.numeric_summary,
        },
        "quality": quality,
    }
    click.echo(json.dumps(payload, indent=2))


@main.command("text-insights")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--text-column", multiple=True, required=True)
@click.option("--geo-column")
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
@click.option("--out", type=click.Path())
@click.option("--state-path", type=click.Path(), default="outputs/pipeline_state.json")
def text_insights_cmd(domain, fourfour, text_column, geo_column, max_rows, out, state_path):
    c = _client()
    LOGGER.info("Starting pipeline for %s/%s", domain, fourfour)
    try:
        prev_state = load_state(state_path)
    except Exception:
        prev_state = None
    rows = []
    for batch in c.fetch_json(domain, fourfour, max_rows=max_rows):
        rows.extend(batch)
    import pandas as pd

    df = pd.DataFrame(rows)
    tagged, insights = generate_text_insights(df, list(text_column), geo_column=geo_column)
    payload = {
        "row_count": insights.row_count,
        "top_terms": insights.top_terms,
        "regex_hits": insights.regex_hits,
        "tags": insights.tags,
    }
    if out:
        tagged.to_json(out, orient="records")
    click.echo(json.dumps(payload, indent=2))


@main.command("llm-augment")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--text-column", required=True)
@click.option("--endpoint", default="http://localhost:1234/v1/chat/completions")
@click.option("--model", default="local-model")
@click.option("--temperature", type=float, default=0.1)
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
@click.option("--out", type=click.Path(), required=True)
def llm_augment_cmd(domain, fourfour, text_column, endpoint, model, temperature, max_rows, out):
    c = _client()
    rows = []
    for batch in c.fetch_json(domain, fourfour, max_rows=max_rows):
        rows.extend(batch)
    import pandas as pd

    df = pd.DataFrame(rows)
    cfg = LLMAugmentConfig(endpoint=endpoint, model=model, temperature=temperature)
    tagged = augment_dataframe_with_llm(df, text_column=text_column, cfg=cfg)
    tagged.to_json(out, orient="records")
    click.echo(f"LLM-augmented rows written to {out}")


@main.command("spatial-join")
@click.option("--left-json", type=click.Path(exists=True), required=True)
@click.option("--right-json", type=click.Path(exists=True), required=True)
@click.option("--left-geom-col", required=True)
@click.option("--right-geom-col", required=True)
@click.option("--out", type=click.Path(), required=True)
def spatial_join_cmd(left_json, right_json, left_geom_col, right_geom_col, out):
    import pandas as pd

    left = pd.read_json(left_json)
    right = pd.read_json(right_json)
    result = spatial_intersects_join(left, right, left_geom_col=left_geom_col, right_geom_col=right_geom_col)
    result.joined.to_json(out, orient="records")
    click.echo(json.dumps({"conflict_rate": result.conflict_rate, "overlap_count": result.overlap_count, "out": out}, indent=2))


@main.command("nlp-analyze")
@click.option("--text", required=True)
@click.option("--translate", "translate_lang", default="")
def nlp_analyze_cmd(text, translate_lang):
    out = analyze_text(text)
    payload = {
        "tokens": out.tokens,
        "lemmas": out.lemmas,
        "entities": out.entities,
        "pos_tags": out.pos_tags,
        "sentiment": out.sentiment,
        "summary": out.summary,
    }
    if translate_lang:
        payload["translation"] = translate_text(text, target_lang=translate_lang)
    click.echo(json.dumps(payload, indent=2))


@main.command("conflict")
@click.option("--proposed-domain", help="Domain for proposed features (overrides file)")
@click.option("--proposed-fourfour", help="4x4 dataset id for proposed features (overrides file)")
@click.option("--proposed-file", type=click.Path(), help="Local JSON/CSV file with proposed features")
@click.option("--proposed-geom", default="geometry", help="Geometry column name for proposed features")
@click.option("--ref-domain", help="Domain for reference features")
@click.option("--ref-fourfour", help="4x4 dataset id for reference features")
@click.option("--ref-file", type=click.Path(), help="Local JSON/CSV file for reference features")
@click.option("--ref-geom", default="geometry", help="Geometry column name for reference features")
@click.option("--buffer-meters", type=float, default=20.0, help="Buffer distance in meters for conflict detection")
@click.option("--out-geojson", type=click.Path(), help="Write conflict GeoJSON to this file")
@click.option("--out-xlsx", type=click.Path(), help="Write construction list to XLSX")
@click.option("--dry-run", is_flag=True, help="Preview without writing outputs")
def conflict_cmd(proposed_domain, proposed_fourfour, proposed_file, proposed_geom, ref_domain, ref_fourfour, ref_file, ref_geom, buffer_meters, out_geojson, out_xlsx, dry_run):
    """Detect spatial conflicts between a proposed dataset and a reference dataset.

    Provide either domain+fourfour pairs or local files for proposed and reference.
    """
    c = _client()
    import pandas as pd

    # load proposed
    if proposed_file:
        if proposed_file.lower().endswith(".csv"):
            proposed_df = pd.read_csv(proposed_file)
        else:
            proposed_df = pd.read_json(proposed_file)
    elif proposed_domain and proposed_fourfour:
        rows = []
        for batch in c.fetch_json(proposed_domain, proposed_fourfour):
            rows.extend(batch)
        proposed_df = pd.DataFrame(rows)
    else:
        raise click.ClickException("Provide either --proposed-file or --proposed-domain and --proposed-fourfour")

    # load reference
    if ref_file:
        if ref_file.lower().endswith(".csv"):
            ref_df = pd.read_csv(ref_file)
        else:
            ref_df = pd.read_json(ref_file)
    elif ref_domain and ref_fourfour:
        rows = []
        for batch in c.fetch_json(ref_domain, ref_fourfour):
            rows.extend(batch)
        ref_df = pd.DataFrame(rows)
    else:
        raise click.ClickException("Provide either --ref-file or --ref-domain and --ref-fourfour")

    resolver = ConflictResolver()
    annotated, summary = resolver.resolve_conflicts(proposed_df, ref_df, proposed_geom_col=proposed_geom, reference_geom_col=ref_geom, buffer_m=buffer_meters)
    click.echo(json.dumps({"summary": summary.__dict__}, indent=2))

    if dry_run:
        click.echo("Dry-run: no outputs written")
        return

    if out_geojson:
        gj = resolver.export_geojson(annotated, geom_col=proposed_geom)
        with open(out_geojson, "w", encoding="utf-8") as f:
            json.dump(gj, f)
        click.echo(f"Wrote GeoJSON to {out_geojson}")

    if out_xlsx:
        clist = resolver.generate_construction_list(annotated)
        XLSXExporter().write(clist, out_xlsx)
        click.echo(f"Wrote XLSX to {out_xlsx}")


@main.command("batch-search")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--field", required=True, help="Field name to match against the values in the file")
@click.option("--file", "file_path", required=True, type=click.Path(), help="File with one value per line (IDs or keys)")
@click.option("--out", type=click.Path(), help="Write results to JSON file")
def batch_search_cmd(domain, fourfour, field, file_path, out):
    """Run a batch search against a dataset field using a newline-separated file of values."""
    values: list[str] = []
    with open(file_path, encoding="utf-8") as f:
        for ln in f:
            v = ln.strip()
            if v:
                values.append(v)
    if not values:
        raise click.ClickException("No values found in file")

    clause = in_clause(field, values)
    c = _client()
    rows = []
    for batch in c.fetch_json(domain, fourfour, where=clause):
        rows.extend(batch)
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rows, f)
        click.echo(f"Wrote {len(rows)} results to {out}")
    else:
        click.echo(json.dumps(rows, indent=2))


@main.command("readiness")
@click.option("--pytest", "run_pytest", is_flag=True, help="Run full test suite (slower).")
def readiness_cmd(run_pytest: bool):
    """Automated quality-axis readiness report (JSON)."""
    from .readiness import readiness_json

    click.echo(readiness_json(run_pytest=run_pytest))


@main.command("doctor")
@click.option("--check-db", is_flag=True)
@click.option("--checklist", is_flag=True, help="Include automated readiness axis scores.")
def doctor_cmd(check_db, checklist):
    import importlib
    from pathlib import Path

    checks = {}
    for mod in ["requests", "click", "pandas", "openpyxl", "dash", "plotly"]:
        try:
            importlib.import_module(mod)
            checks[mod] = "ok"
        except Exception as exc:
            checks[mod] = f"missing: {exc}"

    optional = ["psycopg", "pymongo", "shapely", "spacy", "transformers", "textblob", "gensim", "nltk"]
    optional_status = {}
    for mod in optional:
        try:
            importlib.import_module(mod)
            optional_status[mod] = "ok"
        except Exception as exc:
            optional_status[mod] = f"missing: {exc}"

    db_status = {}
    if check_db:
        import os
        pg_dsn = os.getenv("PG_DSN")
        mongo_uri = os.getenv("MONGO_URI")
        if pg_dsn:
            try:
                import psycopg
                with psycopg.connect(pg_dsn) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                        db_status["postgres"] = "ok"
            except Exception as exc:
                db_status["postgres"] = f"fail: {exc}"
        if mongo_uri:
            try:
                from pymongo import MongoClient
                c = MongoClient(mongo_uri)
                c.admin.command("ping")
                db_status["mongo"] = "ok"
            except Exception as exc:
                db_status["mongo"] = f"fail: {exc}"

    # Actionable "fix-it" hints (best-effort, platform-agnostic).
    fixes: list[str] = []
    missing_core = [k for k, v in checks.items() if isinstance(v, str) and v.startswith("missing:")]
    missing_opt = [k for k, v in optional_status.items() if isinstance(v, str) and v.startswith("missing:")]
    if missing_core:
        fixes.append("Install core deps: `pip install -e .` (or `pip install .`) then rerun `socrata doctor`.")
    if missing_opt:
        fixes.append("Install optional extras (examples): `pip install '.[postgres]'`, `pip install '.[pptx]'`, `pip install '.[spatial]'`.")
    fixes.append("If Dash pages look empty, run an Analyst Pack: `socrata analyst run --profile <path>`.")
    fixes.append("Open Mission Control SPA: open app/static/mission_control_v2.html in a browser, or run the Electron desktop app via `cd desktop && npm start`.")

    import_checks: dict[str, str] = {}
    for label, modpath in [
        ("analysis.advanced", "socrata_toolkit.analysis.advanced"),
        ("analysis.program", "socrata_toolkit.analysis.program"),
        ("nlp.advanced", "socrata_toolkit.nlp.advanced"),
    ]:
        try:
            importlib.import_module(modpath)
            import_checks[label] = "ok"
        except Exception as exc:
            import_checks[label] = f"fail: {exc}"

    checklist = {
        "wizard_module": "ok" if __import__("importlib").util.find_spec("socrata_toolkit.install_wizard") else "missing",
        "analyst_module": "ok" if __import__("importlib").util.find_spec("socrata_toolkit.analyst") else "missing",
        "spa_html": "ok"
        if (Path(__file__).resolve().parents[3] / "app" / "static" / "mission_control_v2.html").exists()
        else "missing",
    }
    payload = {
        "core": checks,
        "optional": optional_status,
        "db": db_status,
        "import_shims": import_checks,
        "checklist": checklist,
        "fix_it": fixes,
    }
    if checklist:
        from .readiness import run_readiness_checks

        payload["readiness"] = run_readiness_checks()
    click.echo(
        json.dumps(
            payload,
            indent=2,
        )
    )


# ── Review / decisions store ─────────────────────────────────────────────────


@main.group(name="review")
def review_group() -> None:
    """Review & decision tracking for conflicts and approvals."""


def _default_pack_date() -> str:
    try:
        from ..core.profiles import ensure_profile_exists
        from ..core.state import load_state

        prof = ensure_profile_exists()
        st = load_state(str(prof.state_dir / "last_pack.json"))
        return str(st.get("last_run_date") or st.get("run_date") or "")
    except Exception:
        return ""


@review_group.command("list")
@click.option("--pack-date", default="", help="Pack date (YYYY-MM-DD). Defaults to last run.")
@click.option("--kind", type=click.Choice(["conflict", "approval"]), default="", help="Filter by kind")
@click.option("--status", default="", help="Filter by status")
@click.option("--q", default="", help="Search key/notes/assignee")
@click.option("--limit", type=int, default=2000)
@click.option("--json-out", type=click.Path(), default="")
def review_list(pack_date: str, kind: str, status: str, q: str, limit: int, json_out: str) -> None:
    """List decisions from the local review store."""
    from pathlib import Path

    from ..review.store import ReviewStore

    pd = pack_date or _default_pack_date()
    with ReviewStore() as store:
        df = store.list(
            pack_date=pd or None,
            kind=kind or None,
            status=status or None,
            q=q or None,
            limit=limit,
        )
    if json_out:
        Path(json_out).write_text(df.to_json(orient="records"), encoding="utf-8")
        click.echo(f"Wrote {len(df)} decisions to {json_out}")
        return
    click.echo(df.to_string(index=False) if not df.empty else "(no decisions)")


@review_group.command("set")
@click.option("--pack-date", default="", help="Pack date (YYYY-MM-DD). Defaults to last run.")
@click.option("--kind", type=click.Choice(["conflict", "approval"]), required=True)
@click.option("--key-type", required=True, help="Key type (e.g. location_id, contract_id)")
@click.option("--key", "key_value", required=True, help="Key value")
@click.option("--status", required=True, help="Decision status (resolved/defer/needs_coordination or approved/hold)")
@click.option("--assigned-to", default="", help="Owner/assignee")
@click.option("--reason", default="", help="Reason (approvals)")
@click.option("--notes", default="", help="Freeform notes")
def review_set(pack_date: str, kind: str, key_type: str, key_value: str, status: str, assigned_to: str, reason: str, notes: str) -> None:
    """Set a decision (upsert) in the local store."""
    from ..review.store import ReviewStore

    pd = pack_date or _default_pack_date()
    if not pd:
        raise click.ClickException("Provide --pack-date (YYYY-MM-DD) or run an Analyst Pack first.")
    with ReviewStore() as store:
        if kind == "conflict":
            store.set_conflict(
                pack_date=pd,
                key_type=key_type,
                key_value=key_value,
                status=status,  # validated loosely to avoid tight coupling
                assigned_to=assigned_to,
                notes=notes,
            )
        else:
            store.set_approval(
                pack_date=pd,
                key_type=key_type,
                key_value=key_value,
                status=status,
                reason=reason,
                assigned_to=assigned_to,
                notes=notes,
            )
    click.echo("OK")


@review_group.command("export")
@click.option("--pack", "pack_dir", required=True, type=click.Path(exists=True, file_okay=False))
@click.option("--pack-date", default="", help="Pack date (YYYY-MM-DD). Defaults to pack folder name.")
def review_export(pack_dir: str, pack_date: str) -> None:
    """Export decisions into a pack directory (xlsx + md)."""
    from pathlib import Path

    from ..review.store import ReviewStore

    p = Path(pack_dir)
    pd = pack_date or p.name
    with ReviewStore() as store:
        arts = store.export_for_pack(pack_dir=p, pack_date=pd)
    if not arts:
        click.echo("No decisions found to export.")
        return
    click.echo(json.dumps(arts, indent=2))


@main.command("migrate")
@click.option("--dsn", envvar="PG_DSN", help="Postgres DSN to apply migrations to")
@click.option("--migrations-dir", default="sql/migrations")
def migrate_cmd(dsn, migrations_dir):
    """Apply SQL migrations from `sql/migrations` to a Postgres database."""
    if not dsn:
        raise click.ClickException("Provide a Postgres DSN via --dsn or PG_DSN env var")
    try:
        import psycopg
    except Exception as exc:
        raise click.ClickException("Install postgres extras: pip install '.[postgres]'") from exc
    import glob
    import os
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    if not files:
        click.echo("No migration files found")
        return
    conn = psycopg.connect(dsn)
    cur = conn.cursor()
    for f in files:
        click.echo(f"Applying {f}")
        with open(f, encoding="utf-8") as fh:
            cur.execute(fh.read())
    conn.commit()
    cur.close()
    conn.close()
    click.echo("Migrations applied")


@main.command("alerts")
@click.option("--preview", is_flag=True, help="Preview alerts without sending or persisting")
@click.option("--send", is_flag=True, help="Send email notifications for alerts")
@click.option("--persist", is_flag=True, help="Persist alerts to DB")
@click.option("--pg-dsn", envvar="PG_DSN", help="Postgres DSN to query for conflicts and optionally persist alerts")
@click.option("--table", default="sidewalk_complaints", help="Table to scan for high-priority conditions")
@click.option("--corridor-table", default="smart_spine", help="Corridor table to check intersections against")
@click.option("--buffer-m", type=float, default=0.0, help="Buffer in meters for ST_DWithin checks")
@click.option("--recipients", help="Comma-separated list of email recipients for --send")
@click.option("--smtp-host", help="SMTP host for sending emails")
@click.option("--smtp-port", type=int, default=25, help="SMTP port")
@click.option("--smtp-username", help="SMTP username (also used as from address if provided)")
@click.option("--smtp-password", help="SMTP password")
def alerts_cmd(preview, send, persist, pg_dsn, table, corridor_table, buffer_m, recipients, smtp_host, smtp_port, smtp_username, smtp_password):
    """Generate operational alerts by running spatial checks and dispatching them via registered notifiers."""
    mgr = AlertManager(batch_mode=False)
    cli_notifier = CLINotifier()
    mgr.register(cli_notifier)

    if send:
        if not recipients:
            raise click.ClickException("--recipients required when --send is used")
        smtp_cfg = {"host": smtp_host or "localhost", "port": smtp_port, "username": smtp_username, "password": smtp_password, "from_addr": smtp_username or "alerts@localhost", "recipients": [r.strip() for r in recipients.split(",") if r.strip()]}
        mgr.register(EmailNotifier(smtp_cfg))

    db_notifier = None
    if persist:
        if not pg_dsn:
            raise click.ClickException("--pg-dsn is required to persist alerts")
        db_notifier = DBNotifier(pg_dsn)
        mgr.register(db_notifier)

    alerts_created = []
    # If we have a Postgres DSN, prefer running a DB-based spatial join for scale
    if pg_dsn:
        try:
            resolver = PostGISConflictResolver(pg_dsn)
            df, summary = resolver.resolve_conflicts(proposed_table=table, reference_table=corridor_table, proposed_id_col="id", proposed_geom_col="geom", reference_id_col="id", reference_geom_col="geom", buffer_m=buffer_m)
            # create Alert objects for rows which have conflicts
            if not df.empty:
                for _, row in df.iterrows():
                    if int(row.get("_conflict_count", 0)) > 0:
                        a = Alert(severity="critical", message=f"Spatial conflict for id={row.get('id')}", payload={"id": row.get("id"), "conflict_count": int(row.get("_conflict_count")), "conflict_ids": row.get("_conflict_ids")})
                        alerts_created.append(a)
            resolver.close()
        except Exception as exc:
            mgr.emit(Alert(severity="warning", message="Alerts generation failed", payload={"error": str(exc)}))

    # If no PG connection or no alerts found, create a sample alert for preview/demo
    if not alerts_created and preview:
        alerts_created.append(Alert(severity="info", message="Preview alert: no DB alerts found or running in demo mode", payload={}))

    # Dispatch alerts according to options
    for a in alerts_created:
        if preview:
            # just print
            cli_notifier.notify(a)
        else:
            mgr.emit(a)

    # shutdown manager and close DB notifier if used
    mgr.shutdown()
    if db_notifier:
        try:
            db_notifier.close()
        except Exception:
            pass

    click.echo(json.dumps({"alerts": len(alerts_created)}))


@main.command("outliers")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--method", type=click.Choice(["iqr", "zscore"]), default="iqr")
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
@click.option("--out", type=click.Path())
def outliers_cmd(domain, fourfour, method, max_rows, out):
    """Detect outliers in numeric columns of a dataset."""
    from ..analysis.advanced import detect_all_outliers
    c = _client()
    df = c.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    reports = detect_all_outliers(df, method=method)
    payload = [
        {"column": r.column, "method": r.method, "outlier_count": r.outlier_count,
         "outlier_pct": r.outlier_pct, "lower_bound": r.lower_bound, "upper_bound": r.upper_bound}
        for r in reports
    ]
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    click.echo(json.dumps(payload, indent=2))


@main.command("correlations")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--method", type=click.Choice(["pearson", "spearman", "kendall"]), default="pearson")
@click.option("--threshold", type=float, default=0.5)
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
@click.option("--out", type=click.Path())
def correlations_cmd(domain, fourfour, method, threshold, max_rows, out):
    """Compute pairwise correlations above a threshold."""
    from ..analysis.advanced import correlation_analysis
    c = _client()
    df = c.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    result = correlation_analysis(df, method=method, threshold=threshold)
    payload = {"method": result.method, "threshold": result.threshold, "pairs": result.pairs}
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    click.echo(json.dumps(payload, indent=2))


@main.command("quality-score")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--key-column", multiple=True)
@click.option("--date-column")
@click.option("--freshness-days", type=int, default=30)
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
def quality_score_cmd(domain, fourfour, key_column, date_column, freshness_days, max_rows):
    """Compute a composite data quality score for a dataset."""
    from ..governance.core import compute_quality_score
    c = _client()
    df = c.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    score = compute_quality_score(
        df,
        key_columns=list(key_column) if key_column else None,
        date_column=date_column,
        freshness_days_threshold=freshness_days,
    )
    payload = {
        "overall": score.overall,
        "completeness": score.completeness,
        "validity": score.validity,
        "consistency": score.consistency,
        "freshness": score.freshness,
        "details": score.details,
    }
    click.echo(json.dumps(payload, indent=2))


@main.command("schema-drift")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--baseline", type=click.Path(exists=True), required=True, help="Path to baseline schema JSON")
@click.option("--save-snapshot", type=click.Path(), help="Save current schema snapshot to this path")
@click.option("--max-rows", type=int, default=100)
def schema_drift_cmd(domain, fourfour, baseline, save_snapshot, max_rows):
    """Detect schema drift between a dataset and a baseline schema."""
    from ..governance.core import detect_schema_drift, load_schema_snapshot, save_schema_snapshot
    c = _client()
    df = c.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    baseline_schema = load_schema_snapshot(baseline)
    diff = detect_schema_drift(df, baseline_schema)
    payload = {
        "is_compatible": diff.is_compatible,
        "added_columns": diff.added_columns,
        "removed_columns": diff.removed_columns,
        "type_changes": diff.type_changes,
    }
    click.echo(json.dumps(payload, indent=2))
    if save_snapshot:
        save_schema_snapshot(df, save_snapshot)
        click.echo(f"Schema snapshot saved to {save_snapshot}")


@main.command("visualize")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--chart", type=click.Choice(["histogram", "bar", "heatmap", "quality"]), required=True)
@click.option("--column", help="Column to visualize (for histogram/bar)")
@click.option("--out", type=click.Path(), required=True, help="Output image path")
@click.option("--max-rows", type=int, default=get_default(CFG, "preferences", "default_max_rows", default=10000))
def visualize_cmd(domain, fourfour, chart, column, out, max_rows):
    """Generate a chart from a dataset and save to a file."""
    from . import visualization as viz
    c = _client()
    df = c.fetch_dataframe(domain, fourfour, max_rows=max_rows)
    if chart == "histogram":
        if not column:
            raise click.ClickException("--column is required for histogram")
        viz.histogram(df, column, path=out)
    elif chart == "bar":
        if not column:
            raise click.ClickException("--column is required for bar chart")
        viz.bar_chart(df, column, path=out)
    elif chart == "heatmap":
        viz.correlation_heatmap(df, path=out)
    elif chart == "quality":
        viz.quality_dashboard(df, path_prefix=out.replace(".png", ""))
    click.echo(f"Chart saved to {out}")


@main.group(name="schema")
@click.pass_context
def schema_group(ctx):
    """Manage dataset schemas and versioning."""
    ctx.ensure_object(dict)
    ctx.obj["registry"] = SchemaRegistry()


@schema_group.command(name="list")
@click.argument("dataset_id")
@click.option("--json-out", type=click.Path())
@click.pass_context
def schema_list_cmd(ctx, dataset_id, json_out):
    """List all schema versions for a dataset."""
    registry = ctx.obj["registry"]
    history = registry._load_schema_history(dataset_id)

    if not history:
        click.echo(f"No schema versions found for {dataset_id}")
        return

    payload = []
    for schema in history:
        payload.append({
            "version": schema.version,
            "captured_at": schema.captured_at.isoformat(),
            "columns": len(schema.columns),
            "row_count": schema.row_count,
        })

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        click.echo(f"Schema versions exported to {json_out}")
    else:
        click.echo(json.dumps(payload, indent=2))


@schema_group.command(name="current")
@click.argument("dataset_id")
@click.option("--json-out", type=click.Path())
@click.pass_context
def schema_current_cmd(ctx, dataset_id, json_out):
    """Show the latest schema version for a dataset."""
    registry = ctx.obj["registry"]
    schema = registry.get_schema_version(dataset_id)

    if not schema:
        click.echo(f"No schema found for {dataset_id}")
        return

    payload = {
        "dataset_id": schema.dataset_id,
        "version": schema.version,
        "captured_at": schema.captured_at.isoformat(),
        "row_count": schema.row_count,
        "columns": {
            name: {
                "dtype": col.dtype,
                "nullable": col.nullable,
                "position": col.position,
                "sample_value": col.sample_value,
            }
            for name, col in schema.columns.items()
        },
        "metadata": schema.metadata,
    }

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        click.echo(f"Schema exported to {json_out}")
    else:
        click.echo(json.dumps(payload, indent=2))


@schema_group.command(name="diff")
@click.argument("dataset_id")
@click.argument("version1", type=int)
@click.argument("version2", type=int)
@click.pass_context
def schema_diff_cmd(ctx, dataset_id, version1, version2):
    """Show schema changes between two versions."""
    registry = ctx.obj["registry"]

    schema_v1 = registry.get_schema_version(dataset_id, version1)
    schema_v2 = registry.get_schema_version(dataset_id, version2)

    if not schema_v1:
        click.echo(f"Version {version1} not found for {dataset_id}")
        return
    if not schema_v2:
        click.echo(f"Version {version2} not found for {dataset_id}")
        return

    # Manually detect changes between v1 and v2
    changes = []
    cols_v1 = schema_v1.columns
    cols_v2 = schema_v2.columns

    # Deleted columns
    for col_name in cols_v1:
        if col_name not in cols_v2:
            changes.append({
                "type": "COLUMN_DELETION",
                "field": col_name,
                "description": f"Column '{col_name}' deleted",
                "breaking": True,
            })

    # Added columns
    for col_name in cols_v2:
        if col_name not in cols_v1:
            changes.append({
                "type": "COLUMN_ADDITION",
                "field": col_name,
                "old_type": None,
                "new_type": cols_v2[col_name].dtype,
                "description": f"Column '{col_name}' added",
                "breaking": False,
            })

    # Type changes
    for col_name in cols_v1:
        if col_name in cols_v2:
            if cols_v1[col_name].dtype != cols_v2[col_name].dtype:
                changes.append({
                    "type": "TYPE_CHANGE",
                    "field": col_name,
                    "old_type": cols_v1[col_name].dtype,
                    "new_type": cols_v2[col_name].dtype,
                    "description": f"Column '{col_name}' type changed",
                    "breaking": True,
                })

    if not changes:
        click.echo(f"No changes between v{version1} and v{version2}")
    else:
        click.echo(json.dumps({
            "dataset_id": dataset_id,
            "from_version": version1,
            "to_version": version2,
            "change_count": len(changes),
            "changes": changes,
        }, indent=2))


@schema_group.command(name="validate")
@click.argument("dataset_id")
@click.argument("jsonl_file", type=click.Path(exists=True))
@click.pass_context
def schema_validate_cmd(ctx, dataset_id, jsonl_file):
    """Validate a JSONL file against a schema."""
    registry = ctx.obj["registry"]
    schema = registry.get_schema_version(dataset_id)

    if not schema:
        raise click.ClickException(f"No schema found for {dataset_id}")

    validator = SchemaValidator(schema)

    # Load and validate records
    records = []
    with open(jsonl_file, encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            try:
                record = json.loads(line)
                records.append(record)
            except json.JSONDecodeError as e:
                click.echo(f"Error parsing line {idx}: {e}")

    valid_count, errors = validator.validate_batch(records)

    click.echo(f"Validation results for {dataset_id}:")
    click.echo(f"  Total records: {len(records)}")
    click.echo(f"  Valid records: {valid_count}")
    click.echo(f"  Invalid records: {len(records) - valid_count}")

    if errors:
        click.echo("\nFirst 10 errors:")
        for error in errors[:10]:
            click.echo(f"  - {error}")
        if len(errors) > 10:
            click.echo(f"  ... and {len(errors) - 10} more")


@schema_group.command(name="check-compatibility")
@click.argument("dataset_id")
@click.argument("jsonl_file", type=click.Path(exists=True))
@click.option("--strict", is_flag=True, help="Enable strict mode checking")
@click.pass_context
def schema_check_compat_cmd(ctx, dataset_id, jsonl_file, strict):
    """Check schema backward compatibility."""
    import pandas as pd

    registry = ctx.obj["registry"]
    old_schema = registry.get_schema_version(dataset_id)

    if not old_schema:
        click.echo(f"No previous schema found for {dataset_id}")
        return

    # Load new data and extract schema
    records = []
    with open(jsonl_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    if not records:
        raise click.ClickException("No records found in JSONL file")

    df = pd.DataFrame(records)
    new_schema = SchemaRegistry.extract_schema_from_dataframe(df, dataset_id)

    # Check compatibility
    checker = BackwardCompatibilityChecker(strict_mode=strict)
    is_compatible, violations = checker.check_compatibility(old_schema, new_schema)

    click.echo(f"Backward compatibility check for {dataset_id}:")
    click.echo(f"  Compatible: {is_compatible}")
    click.echo(f"  Violations: {len(violations)}")

    if violations:
        click.echo("\nDetailed violations:")
        for violation in violations:
            click.echo(f"  - {violation}")
    else:
        click.echo("  No violations detected.")


# ============================================================================
# Material Standards and Compliance Commands
# ============================================================================

@main.group(name="material")
@click.pass_context
def material_group(ctx):
    """NYC Street Design Manual material standards and specifications."""
    ctx.ensure_object(dict)


@material_group.command(name="list")
@click.option("--category", type=click.Choice(["asphalt", "concrete", "permeable", "specialty", "brick_stone", "metal", "composite"]), help="Filter by material category")
@click.option("--json-out", type=click.Path(), help="Output to JSON file")
@click.pass_context
def material_list(ctx, category, json_out):
    """List all defined material types."""
    try:
        from socrata_toolkit.material.definitions import (
            MATERIAL_DEFINITIONS,
        )

        materials = []

        for key, spec in MATERIAL_DEFINITIONS.items():
            if category:
                if spec.category.value != category:
                    continue

            materials.append({
                "id": spec.material_id,
                "name": spec.name,
                "category": spec.category.value,
                "lifecycle_years": spec.lifecycle_years,
                "cost_per_sqft": spec.cost_per_sqft,
                "lifecycle_cost_per_sqft": spec.lifecycle_cost_per_sqft,
                "sustainability_score": spec.sustainability_score,
            })

        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(materials, f, indent=2)
            click.echo(f"Wrote {len(materials)} materials to {json_out}")
        else:
            for mat in materials:
                click.echo(f"{mat['id']:<20} {mat['name']:<45} {mat['category']:<12} Lifecycle: {mat['lifecycle_years']}y Cost: ${mat['lifecycle_cost_per_sqft']:.2f}/sqft")
    except Exception as e:
        raise click.ClickException(f"Error listing materials: {e}")


@material_group.command(name="show")
@click.argument("material_id")
@click.option("--json-out", type=click.Path())
def material_show(material_id, json_out):
    """Show complete specification for a material."""
    try:
        from socrata_toolkit.material.definitions import get_material_by_id

        spec = get_material_by_id(material_id)
        if not spec:
            raise click.ClickException(f"Material {material_id} not found")

        output = spec.to_dict()

        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            click.echo(f"Wrote specification to {json_out}")
        else:
            click.echo(f"Material: {spec.name}")
            click.echo(f"  ID: {spec.material_id}")
            click.echo(f"  Category: {spec.category.value}")
            click.echo(f"  Description: {spec.description}")
            click.echo(f"  Lifecycle: {spec.lifecycle_years} years")
            click.echo(f"  Installation cost: ${spec.cost_per_sqft:.2f}/sqft")
            click.echo(f"  Lifecycle cost: ${spec.lifecycle_cost_per_sqft:.2f}/sqft")
            click.echo(f"  Sustainability score: {spec.sustainability_score}/100")
            click.echo(f"  Carbon footprint: {spec.carbon_footprint_kg_per_sqft:.2f} kg CO2e/sqft")
            click.echo("\n  Design Standards:")
            for key, value in spec.design_standards.items():
                click.echo(f"    {key}: {value}")
    except Exception as e:
        raise click.ClickException(f"Error showing material: {e}")


@material_group.command(name="maintenance-schedule")
@click.argument("material_id")
def material_maintenance_schedule(material_id):
    """Show maintenance schedule for a material."""
    try:
        from socrata_toolkit.material.definitions import get_material_by_id

        spec = get_material_by_id(material_id)
        if not spec:
            raise click.ClickException(f"Material {material_id} not found")

        click.echo(f"Maintenance Schedule: {spec.name}")
        click.echo(f"  Routine interval: Every {spec.maintenance_schedule.routine_interval_years} years")
        click.echo(f"  Preventive overlay: Year {spec.maintenance_schedule.preventive_overlay_years}")
        click.echo(f"  Full lifecycle: {spec.maintenance_schedule.lifecycle_years} years")
        click.echo("\n  Activities:")
        for activity, description in spec.maintenance_schedule.activities.items():
            click.echo(f"    {activity}: {description}")
    except Exception as e:
        raise click.ClickException(f"Error showing maintenance schedule: {e}")


@material_group.command(name="ada-rules")
@click.argument("material_id")
def material_ada_rules(material_id):
    """Show ADA compliance rules applicable to a material."""
    try:
        from socrata_toolkit.material.definitions import get_material_by_id
        from socrata_toolkit.standards.design import get_rules_for_material

        spec = get_material_by_id(material_id)
        if not spec:
            raise click.ClickException(f"Material {material_id} not found")

        rules = get_rules_for_material(spec.category)

        click.echo(f"ADA Compliance Rules for {spec.name}:")
        for rule in rules:
            click.echo(f"\n  {rule.rule_id}: {rule.title}")
            click.echo(f"    Severity: {rule.failure_severity.value}")
            click.echo(f"    Requirement: {rule.requirement[:100]}...")
            click.echo(f"    Validation: {rule.validation_method}")
    except Exception as e:
        raise click.ClickException(f"Error showing ADA rules: {e}")


@main.group(name="compliance")
@click.pass_context
def compliance_group(ctx):
    """Material and ADA compliance checking and reporting."""
    ctx.ensure_object(dict)


@compliance_group.command(name="check")
@click.argument("material_id")
@click.option("--condition", type=click.Choice(["excellent", "good", "fair", "poor", "critical"]), default="fair", help="Surface condition")
@click.option("--json-out", type=click.Path())
def compliance_check(material_id, condition, json_out):
    """Check compliance for a material type."""
    try:
        from datetime import datetime

        from socrata_toolkit.material.compliance import MaterialCompliance
        from socrata_toolkit.material.definitions import get_material_by_id
        from socrata_toolkit.material.standards import SurfaceAssessment, SurfaceCondition

        spec = get_material_by_id(material_id)
        if not spec:
            raise click.ClickException(f"Material {material_id} not found")

        # Create dummy assessment
        assessment = SurfaceAssessment(
            location_id="test-location",
            material=spec,
            last_inspected=datetime.now(),
            condition=SurfaceCondition(condition),
        )

        # Check compliance
        checker = MaterialCompliance()
        report = checker.generate_compliance_report(assessment, location_description=spec.name)

        output = report.to_dict()

        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2)
            click.echo(f"Compliance report written to {json_out}")
        else:
            click.echo(f"Compliance Check: {spec.name}")
            click.echo(f"  Status: {report.overall_status.value}")
            click.echo(f"  Score: {report.overall_score:.1f}/100")
            click.echo(f"  ADA Violations: {report.ada_compliance.critical_violations + report.ada_compliance.high_violations}")
            click.echo("\nCritical Actions:")
            for action in report.critical_actions:
                click.echo(f"  - {action}")
    except Exception as e:
        raise click.ClickException(f"Error checking compliance: {e}")


@compliance_group.command(name="ada-violations")
@click.option("--severity", type=click.Choice(["critical", "high", "medium", "low"]), help="Filter by severity")
@click.option("--json-out", type=click.Path())
def compliance_ada_violations(severity, json_out):
    """List all ADA violation rules."""
    try:
        from socrata_toolkit.standards.design import ADA_COMPLIANCE_RULES

        rules = []
        for rule_id, rule in ADA_COMPLIANCE_RULES.items():
            if severity:
                if rule.failure_severity.value != severity:
                    continue

            rules.append({
                "rule_id": rule_id,
                "title": rule.title,
                "severity": rule.failure_severity.value,
                "validation_method": rule.validation_method,
                "description": rule.description[:100],
            })

        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2)
            click.echo(f"Wrote {len(rules)} rules to {json_out}")
        else:
            for rule in rules:
                click.echo(f"{rule['rule_id']:<20} {rule['title']:<40} [{rule['severity']:<8}]")
    except Exception as e:
        raise click.ClickException(f"Error listing ADA violations: {e}")


@compliance_group.command(name="report")
@click.option("--material", type=click.Choice(["asphalt", "concrete", "permeable", "specialty", "brick_stone", "metal", "composite"]), help="Filter by material category")
@click.option("--json-out", type=click.Path())
def compliance_report(material, json_out):
    """Generate compliance summary report."""
    try:
        from socrata_toolkit.material.standards import ADAFailureSeverity
        from socrata_toolkit.standards.design import get_critical_rules, get_rules_by_severity

        critical = get_critical_rules()
        high = get_rules_by_severity(ADAFailureSeverity.HIGH)
        medium = get_rules_by_severity(ADAFailureSeverity.MEDIUM)

        report = {
            "total_rules": len(get_critical_rules()) + len(high) + len(medium),
            "critical_rules": len(critical),
            "high_rules": len(high),
            "medium_rules": len(medium),
            "critical_rule_ids": [r.rule_id for r in critical],
        }

        if json_out:
            with open(json_out, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            click.echo(f"Compliance summary written to {json_out}")
        else:
            click.echo("ADA Compliance Rule Summary:")
            click.echo(f"  Total rules: {report['total_rules']}")
            click.echo(f"  CRITICAL severity: {report['critical_rules']}")
            click.echo(f"  HIGH severity: {report['high_rules']}")
            click.echo(f"  MEDIUM severity: {report['medium_rules']}")
    except Exception as e:
        raise click.ClickException(f"Error generating compliance report: {e}")


# Lineage Management Commands
@main.group(name="lineage", help="Data lineage and transformation DAG management")
def lineage_group():
    """Data lineage and DAG tracking commands."""
    pass


@lineage_group.command(name="nodes")
@click.option("--type", type=str, help="Filter by node type (ingestion, transformation, sink, etc.)")
@click.option("--owner", type=str, help="Filter by owner email/user")
@click.option("--tag", type=str, help="Filter by tag")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def lineage_nodes(type, owner, tag, output_json):
    """List all lineage nodes."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        # Search nodes based on criteria
        nodes = query.search_nodes(node_type=type, owner=owner, tag=tag)

        if output_json:
            result = {
                "count": len(nodes),
                "nodes": [
                    {
                        "node_id": nid,
                        "name": dag.nodes[nid].name,
                        "type": dag.nodes[nid].node_type.value,
                        "owner": dag.nodes[nid].owner,
                    }
                    for nid in nodes
                    if nid in dag.nodes
                ]
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Found {len(nodes)} nodes:")
            for node_id in nodes:
                node = dag.nodes.get(node_id)
                if node:
                    click.echo(f"  {node_id:<40} {node.name:<40} [{node.node_type.value:<15}]")
    except Exception as e:
        raise click.ClickException(f"Error listing lineage nodes: {e}")


@lineage_group.command(name="node")
@click.argument("node_id")
@click.option("--full", is_flag=True, help="Show full execution history")
def lineage_node(node_id, full):
    """Show details for a specific node."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        info = query.get_node_info(node_id)
        if not info:
            raise click.ClickException(f"Node {node_id} not found")

        click.echo(f"Node: {info['node_id']}")
        click.echo(f"Name: {info['name']}")
        click.echo(f"Type: {info['type']}")
        click.echo(f"Owner: {info['owner']}")
        click.echo(f"Description: {info['description']}")
        click.echo(f"Created: {info['created_at']}")
        click.echo(f"Upstream Dependencies: {', '.join(info['upstream_dependencies'])}")
        click.echo(f"Downstream Consumers: {', '.join(info['downstream_consumers'])}")
        click.echo(f"Tags: {', '.join(info['tags'])}")

        if full and info['execution_count'] > 0:
            click.echo(f"\nExecution History ({info['execution_count']} total):")
            if info['latest_execution']:
                exec_info = info['latest_execution']
                click.echo(f"  Latest: {exec_info['status']} at {exec_info['started_at']}")
                click.echo(f"    Duration: {exec_info['duration_seconds']}s")
                click.echo(f"    Rows: {exec_info['input_row_count']} -> {exec_info['output_row_count']}")
    except Exception as e:
        raise click.ClickException(f"Error getting node info: {e}")


@lineage_group.command(name="sources")
@click.argument("node_id")
def lineage_sources(node_id):
    """Show upstream data sources for a node."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        sources = query.find_sources(node_id)
        if not sources:
            click.echo(f"No upstream sources found for {node_id}")
            return

        click.echo(f"Upstream sources for {node_id}:")
        for src_id in sources:
            node = dag.nodes.get(src_id)
            if node:
                click.echo(f"  {src_id:<40} {node.name:<40} ({node.node_type.value})")
    except Exception as e:
        raise click.ClickException(f"Error finding sources: {e}")


@lineage_group.command(name="consumers")
@click.argument("node_id")
def lineage_consumers(node_id):
    """Show downstream consumers for a node."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        consumers = query.find_consumers(node_id)
        if not consumers:
            click.echo(f"No downstream consumers found for {node_id}")
            return

        click.echo(f"Downstream consumers of {node_id}:")
        for consumer_id in consumers:
            node = dag.nodes.get(consumer_id)
            if node:
                click.echo(f"  {consumer_id:<40} {node.name:<40} ({node.node_type.value})")
    except Exception as e:
        raise click.ClickException(f"Error finding consumers: {e}")


@lineage_group.command(name="path")
@click.argument("source_id")
@click.argument("target_id")
def lineage_path(source_id, target_id):
    """Find transformation path between two nodes."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        path = query.find_path(source_id, target_id)
        if not path:
            click.echo(f"No path found from {source_id} to {target_id}")
            return

        click.echo(f"Path from {source_id} to {target_id}:")
        for i, node_id in enumerate(path):
            node = dag.nodes.get(node_id)
            if node:
                indent = "  " if i > 0 else ""
                prefix = "→ " if i > 0 else ""
                click.echo(f"{indent}{prefix}{node_id} ({node.name})")
    except Exception as e:
        raise click.ClickException(f"Error finding path: {e}")


@lineage_group.command(name="impact")
@click.argument("node_id")
def lineage_impact(node_id):
    """Analyze impact of changing a node."""
    try:
        from ..lineage.core import DAG
        from ..lineage.impact import ImpactAnalysis

        dag = DAG()
        analyzer = ImpactAnalysis(dag)

        report = analyzer.analyze_change(node_id)

        click.echo(f"Impact Analysis for {node_id}:")
        click.echo(f"  Affected nodes: {report.affected_count}")
        click.echo(f"  Affected users: {', '.join(report.affected_users)}")
        click.echo(f"  Critical paths: {len(report.critical_paths)}")
        click.echo(f"  Risk score: {report.risk_score:.1f}/100")
        click.echo(f"  Estimated effort: {report.estimated_effort_hours:.1f} hours")

        if report.remediation_steps:
            click.echo("\n  Remediation steps:")
            for i, step in enumerate(report.remediation_steps, 1):
                click.echo(f"    {i}. {step}")
    except Exception as e:
        raise click.ClickException(f"Error analyzing impact: {e}")


@lineage_group.command(name="dag")
@click.option("--format", type=click.Choice(["json", "graphml", "mermaid", "dot", "ascii"]), default="ascii", help="Export format")
@click.option("--output", type=click.Path(), help="Output file path")
def lineage_dag(format, output):
    """Export complete DAG."""
    try:
        from ..lineage.core import DAG
        from ..lineage.visualization import LineageVisualizer

        dag = DAG()
        visualizer = LineageVisualizer(dag)

        # Get export based on format
        if format == "json":
            content = visualizer.to_json()
        elif format == "graphml":
            content = visualizer.to_graphml()
        elif format == "mermaid":
            content = visualizer.to_mermaid()
        elif format == "dot":
            content = visualizer.to_dot()
        else:  # ascii
            content = visualizer.to_ascii()

        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
            click.echo(f"Exported DAG to {output}")
        else:
            click.echo(content)
    except Exception as e:
        raise click.ClickException(f"Error exporting DAG: {e}")


@lineage_group.command(name="freshness")
@click.argument("node_id")
@click.option("--stale-hours", type=float, default=24, help="Hours threshold for staleness")
def lineage_freshness(node_id, stale_hours):
    """Check data freshness for a node."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        freshness = query.get_freshness(node_id, stale_threshold_hours=stale_hours)

        click.echo(f"Freshness for {node_id}:")
        if freshness.last_execution_time:
            click.echo(f"  Last execution: {freshness.last_execution_time}")
            click.echo(f"  Age: {freshness.age_seconds / 3600:.1f} hours")
            click.echo(f"  Status: {'STALE' if freshness.is_stale else 'CURRENT'}")
        else:
            click.echo("  Status: NEVER EXECUTED")
    except Exception as e:
        raise click.ClickException(f"Error checking freshness: {e}")


@lineage_group.command(name="stats")
def lineage_stats():
    """Show DAG statistics."""
    try:
        from ..lineage.core import DAG
        from ..lineage.query import LineageQuery

        dag = DAG()
        query = LineageQuery(dag)

        stats = query.get_statistics()

        click.echo("Lineage Statistics:")
        click.echo(f"  Total nodes: {stats['total_nodes']}")
        click.echo(f"  Total edges: {stats['total_edges']}")
        click.echo(f"  DAG depth: {stats['depth']}")

        if stats['nodes_by_type']:
            click.echo("\n  Nodes by type:")
            for node_type, count in stats['nodes_by_type'].items():
                click.echo(f"    {node_type}: {count}")
    except Exception as e:
        raise click.ClickException(f"Error getting statistics: {e}")


# ============================================================================
# Observability Commands
# ============================================================================

@main.group(name="observability")
def observability_group():
    """Observability and monitoring commands."""
    pass


@observability_group.command(name="status")
def observability_status():
    """Show current observability status and metrics summary."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()

        click.echo("\n=== Observability Status ===\n")

        # Health status
        health = obs.health_status()
        click.echo(f"Health Status: {health['status']}")
        click.echo(f"Ready: {health.get('is_ready', False)}")
        click.echo(f"Components: {len(health['components'])}")
        for comp in health['components']:
            status_symbol = "✓" if comp['status'] == 'HEALTHY' else "✗"
            click.echo(f"  {status_symbol} {comp['name']}: {comp['status']}")

        # Metrics summary
        click.echo("\nMetrics Summary:")
        metrics = obs.metrics_summary()
        click.echo(f"  Counters: {metrics['counter_count']}")
        click.echo(f"  Gauges: {metrics['gauge_count']}")
        click.echo(f"  Histograms: {metrics['histogram_count']}")
        click.echo(f"  Summaries: {metrics['summary_count']}")

        # SLA summary
        click.echo("\nSLA Summary:")
        sla_report = obs.sla_report()
        click.echo(f"  Total SLAs: {sla_report['total_slas']}")
        click.echo(f"  Passing: {sla_report['passing_slas']}")
        click.echo(f"  Failing: {sla_report['failing_slas']}")
        click.echo(f"  Compliance: {sla_report['compliance_percent']:.1f}%")

    except Exception as e:
        raise click.ClickException(f"Error getting observability status: {e}")


@observability_group.command(name="logs")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"]), help="Filter by log level")
@click.option("--correlation-id", help="Filter by correlation ID")
@click.option("--limit", type=int, default=10, help="Number of logs to show")
@click.option("--dataset-id", help="Filter by dataset ID")
@click.option("--json", "json_format", is_flag=True, help="Output as JSON")
def observability_logs(level, correlation_id, limit, dataset_id, json_format):
    """Query and display recent logs."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()

        # Build filters
        filters = {}
        if level:
            filters['level'] = level
        if correlation_id:
            filters['correlation_id'] = correlation_id
        if dataset_id:
            filters['dataset_id'] = dataset_id

        logs = obs.query_logs(**filters)
        logs = logs[-limit:] if len(logs) > limit else logs

        if json_format:
            data = [log.to_dict() for log in logs]
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            click.echo(f"\n=== Recent Logs ({len(logs)}) ===\n")
            for log in logs:
                click.echo(f"[{log.timestamp}] {log.level} ({log.logger_name})")
                click.echo(f"  {log.message}")
                if log.context:
                    click.echo(f"  Context: {log.context}")
                click.echo()

    except Exception as e:
        raise click.ClickException(f"Error querying logs: {e}")


@observability_group.command(name="metrics")
@click.option("--metric", help="Specific metric name")
@click.option("--format", type=click.Choice(["text", "json", "prometheus"]), default="text", help="Output format")
@click.option("--output", type=click.Path(), help="Output file")
def observability_metrics(metric, format, output):
    """Show metrics data."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()
        metrics_collector = obs.get_metrics()

        if format == "prometheus":
            data = metrics_collector.export_prometheus()
        elif format == "json":
            data = metrics_collector.export_json()
        else:
            # Text format
            summary = metrics_collector.summary_dict()
            data = f"""Metrics Summary
Counter Metrics: {summary['counter_count']}
Gauge Metrics: {summary['gauge_count']}
Histogram Metrics: {summary['histogram_count']}
Summary Metrics: {summary['summary_count']}
Timestamp: {summary['timestamp']}"""

        if output:
            with open(output, 'w') as f:
                f.write(data)
            click.echo(f"Metrics exported to {output}")
        else:
            click.echo(data)

    except Exception as e:
        raise click.ClickException(f"Error exporting metrics: {e}")


@observability_group.command(name="sla-report")
@click.option("--window", type=click.Choice(["5m", "1h", "1d"]), default="1h", help="Time window")
@click.option("--json", "json_format", is_flag=True, help="Output as JSON")
def observability_sla_report(window, json_format):
    """Show SLA compliance report."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()
        report = obs.sla_report()

        if json_format:
            click.echo(json.dumps(report, indent=2, default=str))
        else:
            click.echo("\n=== SLA Compliance Report ===\n")
            click.echo(f"Window: {window}")
            click.echo(f"Total SLAs: {report['total_slas']}")
            click.echo(f"Passing: {report['passing_slas']}")
            click.echo(f"Failing: {report['failing_slas']}")
            click.echo(f"Compliance: {report['compliance_percent']:.1f}%")
            click.echo(f"Trend: {report.get('trend', 'unknown')}")

            if report.get('violations'):
                click.echo("\nViolations:")
                for v in report['violations']:
                    click.echo(f"  ✗ {v['sla_name']}")
                    click.echo(f"    Target: {v['target']}, Actual: {v['actual']}")
                    click.echo(f"    Severity: {v['severity']}")

    except Exception as e:
        raise click.ClickException(f"Error generating SLA report: {e}")


@observability_group.command(name="health")
@click.option("--detailed", is_flag=True, help="Show detailed component info")
@click.option("--json", "json_format", is_flag=True, help="Output as JSON")
def observability_health(detailed, json_format):
    """Check system health status."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()

        # Get health status
        readiness = obs.readiness_status()
        health = obs.health_status()

        if json_format:
            click.echo(json.dumps(health, indent=2, default=str))
        else:
            click.echo("\n=== Health Check ===\n")
            click.echo(f"Readiness: {'READY ✓' if readiness['ready'] else 'NOT READY ✗'}")
            click.echo(f"Overall Status: {health['status']}")
            click.echo(f"Unhealthy: {health['unhealthy_count']}")
            click.echo(f"Degraded: {health['degraded_count']}")

            if detailed:
                click.echo("\nComponent Details:")
                for comp in health['components']:
                    status_icon = "✓" if comp['status'] == 'HEALTHY' else "✗"
                    click.echo(f"  {status_icon} {comp['name']}: {comp['status']}")
                    if comp.get('message'):
                        click.echo(f"      {comp['message']}")
                    if comp.get('duration_ms'):
                        click.echo(f"      Duration: {comp['duration_ms']:.2f}ms")

    except Exception as e:
        raise click.ClickException(f"Error checking health: {e}")


@observability_group.command(name="export")
@click.argument("format", type=click.Choice(["prometheus", "json", "csv"]))
@click.option("--output", type=click.Path(), required=True, help="Output file path")
@click.option("--type", "export_type", type=click.Choice(["logs", "metrics", "traces"]), default="metrics", help="What to export")
def observability_export(format, output, export_type):
    """Export observability data."""
    try:
        from pathlib import Path

        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()
        output_path = Path(output)

        if export_type == "metrics":
            if format == "prometheus":
                data = obs.export_metrics_prometheus()
            elif format == "json":
                data = obs.export_metrics_json()
            else:
                # CSV for metrics
                obs.get_metrics().export_csv(output_path)
                click.echo(f"Metrics exported to {output}")
                return

            with open(output_path, 'w') as f:
                f.write(data)
            click.echo(f"Metrics exported to {output}")

        elif export_type == "logs":
            if format == "json":
                obs.export_logs_json(output_path)
            elif format == "csv":
                obs.export_logs_csv(output_path)
            else:
                raise click.ClickException("Logs support JSON and CSV formats only")
            click.echo(f"Logs exported to {output}")

        elif export_type == "traces":
            if format == "json":
                data = obs.export_traces_jaeger()
                with open(output_path, 'w') as f:
                    f.write(data)
                click.echo(f"Traces exported to {output}")
            else:
                raise click.ClickException("Traces support JSON format only")

    except Exception as e:
        raise click.ClickException(f"Error exporting data: {e}")


@observability_group.command(name="trace")
@click.argument("trace_id")
@click.option("--json", "json_format", is_flag=True, help="Output as JSON")
def observability_trace(trace_id, json_format):
    """Show detailed trace information."""
    try:
        from ..observability.integration import get_observability_manager

        obs = get_observability_manager()
        trace = obs.get_trace(trace_id)

        if not trace:
            click.echo(f"No trace found with ID: {trace_id}")
            return

        if json_format:
            data = [span.to_dict() for span in trace]
            click.echo(json.dumps(data, indent=2, default=str))
        else:
            click.echo(f"\n=== Trace: {trace_id} ===\n")
            click.echo(f"Spans: {len(trace)}\n")

            for span in trace:
                indent = "  " if span.parent_span_id else ""
                status_icon = "✓" if span.status == "ok" else "✗"
                duration = f"{span.duration_ms:.2f}ms" if span.duration_ms else "running"

                click.echo(f"{indent}{status_icon} {span.operation_name} {duration}")
                if span.attributes:
                    for k, v in span.attributes.items():
                        click.echo(f"{indent}  @{k}={v}")
                if span.error_message:
                    click.echo(f"{indent}  ERROR: {span.error_message}")
                click.echo()

    except Exception as e:
        raise click.ClickException(f"Error retrieving trace: {e}")


# ── Analyst Autopilot ─────────────────────────────────────────────────────────


@click.group("analyst")
def analyst_group() -> None:
    """Analyst Autopilot — weekly pack workflow."""


@analyst_group.command("init-config")
@click.option(
    "--out",
    "out_path",
    type=click.Path(),
    default="config/analyst_profile.yaml",
    show_default=True,
    help="Destination path for example profile",
)
def analyst_init_config(out_path: str) -> None:
    """Write an example analyst profile YAML."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[3] / "config" / "analyst_profile.example.yaml"
    dest = Path(out_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.exists():
        dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        dest.write_text(
            "profile_name: sidewalk_default\nsources: {}\noutputs:\n  dir: outputs/analyst_pack\n",
            encoding="utf-8",
        )
    click.echo(f"Wrote analyst profile template to {dest}")


@analyst_group.command("run")
@click.option("--profile", required=True, type=click.Path(exists=True), help="YAML analyst profile")
@click.option("--dry-run", is_flag=True, help="Validate sources only; do not write pack")
@click.option("--offline", is_flag=True, help="Skip Socrata sources (same as offline: true in profile)")
def analyst_run(profile: str, dry_run: bool, offline: bool) -> None:
    """Run Analyst Autopilot pack workflow."""
    from ..analyst import run_analyst_pack

    result = run_analyst_pack(profile, dry_run=dry_run, offline=offline)
    click.echo(json.dumps({"pack_dir": str(result.pack_dir), "artifacts": result.artifacts, "warnings": result.warnings}, indent=2))


@analyst_group.command("publish")
@click.option("--profile", "publish_profile", required=True, type=click.Path(exists=True), help="YAML publish profile")
@click.option("--pack", "pack_dir", required=True, type=click.Path(exists=True, file_okay=False), help="Analyst pack directory (outputs/analyst_pack/YYYY-MM-DD)")
@click.option("--dry-run", is_flag=True, help="Preview publish actions without side effects")
def analyst_publish(publish_profile: str, pack_dir: str, dry_run: bool) -> None:
    """Publish an existing Analyst Pack to configured destinations."""
    from ..analyst.publish import publish_pack

    report = publish_pack(pack_dir=pack_dir, profile_path=publish_profile, dry_run=dry_run)
    click.echo(json.dumps(report.to_dict(), indent=2, default=str))


@main.command("publish")
@click.option("--profile", "publish_profile", required=True, type=click.Path(exists=True), help="YAML publish profile")
@click.option("--pack", "pack_dir", required=True, type=click.Path(exists=True, file_okay=False), help="Analyst pack directory (outputs/analyst_pack/YYYY-MM-DD)")
@click.option("--dry-run", is_flag=True, help="Preview publish actions without side effects")
def publish_alias(publish_profile: str, pack_dir: str, dry_run: bool) -> None:
    """Alias for `socrata analyst publish`."""
    from ..analyst.publish import publish_pack

    report = publish_pack(pack_dir=pack_dir, profile_path=publish_profile, dry_run=dry_run)
    click.echo(json.dumps(report.to_dict(), indent=2, default=str))


main.add_command(analyst_group)


@main.command("setup")
@click.option("--non-interactive", is_flag=True, help="Use environment variables (WIZARD_NONINTERACTIVE=1)")
@click.option("--skip-checks", is_flag=True, help="Skip connectivity validation")
@click.option("--force-profile", is_flag=True, help="Overwrite analyst profile YAML")
def setup_cmd(non_interactive: bool, skip_checks: bool, force_profile: bool) -> None:
    """Interactive local deployment configuration (writes .env and analyst profile)."""
    from ..install_wizard import _print_summary, run_wizard

    summary = run_wizard(
        non_interactive=non_interactive,
        skip_checks=skip_checks,
        force_profile=force_profile,
    )
    _print_summary(summary)


@main.command("wizard")
@click.option("--non-interactive", is_flag=True, help="Use environment variables")
@click.option("--skip-checks", is_flag=True, help="Skip connectivity validation")
def wizard_cmd(non_interactive: bool, skip_checks: bool) -> None:
    """Alias for `socrata setup` — installation wizard."""
    from ..install_wizard import _print_summary, run_wizard

    summary = run_wizard(non_interactive=non_interactive, skip_checks=skip_checks)
    _print_summary(summary)


# ── Thin CLI commands (search/fetch/sync/status retained for nightly ops) ───


@main.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--domain", "-d", default="data.cityofnewyork.us")
@click.option("--limit", "-l", default=10, type=int)
def toolkit_search(query: str, domain: str, limit: int) -> None:
    """Search NYC Open Data catalog (alias)."""
    c = _client()
    results = c.search(query=query, domain=domain, limit=limit)
    for r in results:
        click.echo(f"{r.name} [{r.fourfour}] — {r.domain}")


@main.command("sync")
@click.option("--dataset", "-i", required=True)
@click.option("--domain", "-d", default="data.cityofnewyork.us")
@click.option("--db-path", default="data/local_db/nyc_mission_control.duckdb")
@click.option("--table", required=True)
@click.option("--updated-col", default="created_date")
def sync_cmd(dataset: str, domain: str, db_path: str, table: str, updated_col: str) -> None:
    """Incremental Socrata → DuckDB sync."""
    from ..pipeline import sync_dataset

    count = sync_dataset(domain, dataset, db_path, table, updated_col)
    click.echo(f"Sync complete: {count} rows processed into {table}")


@main.command("db-status")
@click.option("--db-path", default="data/local_db/nyc_mission_control.duckdb")
def db_status(db_path: str) -> None:
    """Show DuckDB table row counts."""
    from .duckdb_store import DuckDBManager

    mgr = DuckDBManager(db_path)
    try:
        tables = mgr.query("SHOW TABLES").fetchall()
        for t in tables:
            name = t[0]
            count = mgr.query(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            click.echo(f"{name}: {count:,} rows")
    finally:
        mgr.close()


if __name__ == "__main__":
    main()
