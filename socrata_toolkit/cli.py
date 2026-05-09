from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import logging

import click

from .analysis import profile_dataframe, quality_report
from .config import get_default, load_local_config
from .text_analytics import generate_text_insights
from .logging_utils import get_logger, write_run_report
from .llm_duck_bridge import LLMAugmentConfig, augment_dataframe_with_llm
from .spatial import spatial_intersects_join
from .nlp_advanced import analyze_text, translate_text
from .state import load_state, save_state
from .validation import validate_required_columns
from .client import SocrataClient, SocrataConfig
from .exporters import MongoExporter, PostgresExporter, XLSXExporter
from .streaming_pipeline import stream_pipeline
from .conflict import ConflictResolver, PostGISConflictResolver
from .query_builder import in_clause
from .alerts import AlertManager, CLINotifier, EmailNotifier, DBNotifier, Alert


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

    import pandas as pd
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
    with open(file_path, "r", encoding="utf-8") as f:
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


@main.command("doctor")
@click.option("--check-db", is_flag=True)
def doctor_cmd(check_db):
    import importlib
    checks = {}
    for mod in ["requests", "click", "pandas", "openpyxl", "streamlit"]:
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

    click.echo(json.dumps({"core": checks, "optional": optional_status, "db": db_status}, indent=2))


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
    import glob, os
    files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))
    if not files:
        click.echo("No migration files found")
        return
    conn = psycopg.connect(dsn)
    cur = conn.cursor()
    for f in files:
        click.echo(f"Applying {f}")
        with open(f, "r", encoding="utf-8") as fh:
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
    from .analysis_advanced import detect_all_outliers
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
    from .analysis_advanced import correlation_analysis
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
    from .governance import compute_quality_score
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
    from .governance import detect_schema_drift, load_schema_snapshot, save_schema_snapshot
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


if __name__ == "__main__":
    main()
