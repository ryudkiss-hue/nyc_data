from __future__ import annotations

import json

import click

from .analysis import profile_dataframe, quality_report
from .client import SocrataClient, SocrataConfig
from .exporters import MongoExporter, PostgresExporter, XLSXExporter


def _client() -> SocrataClient:
    return SocrataClient(SocrataConfig())


@click.group()
def main() -> None:
    """Socrata toolkit CLI."""


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
def pipeline(domain, fourfour, where, select, order, q, max_rows, pg_dsn, pg_table, pg_conflict_col, mongo_uri, mongo_db, mongo_collection, mongo_conflict_field, xlsx_out, json_out, geojson_out):
    c = _client()
    rows = []
    for batch in c.fetch_json(domain, fourfour, where=where, select=select, order=order, q=q, max_rows=max_rows):
        rows.extend(batch)

    if json_out:
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(rows, f)
    if xlsx_out:
        XLSXExporter().write(rows, xlsx_out, meta=c.get_metadata(domain, fourfour))
    if geojson_out:
        with open(geojson_out, "w", encoding="utf-8") as f:
            json.dump(c.fetch_geojson(domain, fourfour, where=where, max_rows=max_rows), f)
    if pg_dsn and pg_table and pg_conflict_col:
        with PostgresExporter(pg_dsn) as pg:
            pg.upsert_batches([rows], table=pg_table, conflict_column=pg_conflict_col)
    if mongo_uri and mongo_db and mongo_collection and mongo_conflict_field:
        with MongoExporter(mongo_uri, mongo_db) as mongo:
            mongo.upsert_batches([rows], collection=mongo_collection, conflict_field=mongo_conflict_field)

    click.echo(f"Pipeline complete for {len(rows)} rows")


@main.command("analyze")
@click.argument("domain")
@click.argument("fourfour")
@click.option("--where")
@click.option("--select")
@click.option("--order")
@click.option("--q")
@click.option("--max-rows", type=int, default=10000)
@click.option("--key-column", multiple=True)
def analyze_cmd(domain, fourfour, where, select, order, q, max_rows, key_column):
    c = _client()
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


if __name__ == "__main__":
    main()
