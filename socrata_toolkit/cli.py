"""Command Line Interface for NYC DOT Socrata Toolkit."""

import logging
from logging.handlers import RotatingFileHandler

import click
import pandas as pd

from socrata_toolkit.analysis import compute_program_dashboard
from socrata_toolkit.core import SocrataClient


def setup_logging(log_file="nyc_toolkit.log"):
    """Sets up log rotation: max 5MB per file, keeping the last 3 backups."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        # Rotates log files when they reach 5MB. Keeps 3 historical logs (e.g. log.1, log.2, log.3)
        handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def draw_unicode_box(title: str, subtitle: str = ""):
    """Draws a beautiful Unicode UI box."""
    width = 65
    click.echo(f"\n╔{'═' * width}╗")
    click.echo(f"║ {title.center(width - 2)} ║")
    if subtitle:
        click.echo(f"╠{'═' * width}╣")
        click.echo(f"║ {subtitle.center(width - 2)} ║")
    click.echo(f"╚{'═' * width}╝\n")


@click.group()
def main():
    """NYC DOT Socrata Toolkit CLI."""
    setup_logging()


@main.command()
@click.option("--query", "-q", required=True, help="Search query")
@click.option("--domain", "-d", default="data.cityofnewyork.us", help="Socrata domain")
@click.option("--limit", "-l", default=10, help="Max results")
def search(query, domain, limit):
    """Search for datasets on Socrata."""
    client = SocrataClient()
    results = client.search(query=query, domain=domain, limit=limit)
    if not results:
        click.echo("No results found.")
        return

    click.echo(f"\nFound {len(results)} datasets:")
    for i, r in enumerate(results, 1):
        click.echo(f"{i}. {r.name} [{r.fourfour}]")
        click.echo(f"   Domain: {r.domain} | Category: {r.category}")
        click.echo(f"   Description: {r.description[:100]}...")
        click.echo("-" * 40)


@main.command()
@click.option("--dataset", "-i", required=True, help="Dataset ID (4x4)")
@click.option("--domain", "-d", default="data.cityofnewyork.us", help="Socrata domain")
@click.option("--limit", "-l", default=1000, help="Max rows")
@click.option(
    "--format", "-f", type=click.Choice(["csv", "json"]), default="csv", help="Output format"
)
@click.option("--output", "-o", help="Output file path")
def fetch(dataset, domain, limit, format, output):
    """Fetch data from Socrata and save to file."""
    client = SocrataClient()
    click.echo(f"Fetching {dataset} from {domain}...")
    df = client.fetch_dataframe(domain, dataset, max_rows=limit)

    if df.empty:
        click.echo("No data returned.")
        return

    if not output:
        output = f"{dataset}.{format}"

    if format == "csv":
        df.to_csv(output, index=False)
    else:
        df.to_json(output, orient="records", indent=2)

    click.echo(f"Successfully fetched {len(df)} rows and saved to {output}.")


@main.command()
@click.option("--file", required=True, help="Input CSV file")
def analyze(file):
    """Run analysis on a local file."""
    df = pd.read_csv(file)
    summary = compute_program_dashboard(df)
    click.echo(f"Overall Health: {summary.overall_health}")
    for metric in summary.metrics:
        click.echo(f"- {metric.name}: {metric.value} (Target: {metric.target})")


@main.command()
@click.option("--dataset", "-i", required=True, help="Dataset ID (4x4)")
@click.option("--domain", "-d", default="data.cityofnewyork.us", help="Socrata domain")
@click.option("--db-path", default="nyc_mission_control.duckdb", help="DuckDB database path")
@click.option("--table", required=True, help="Target table name")
@click.option("--updated-col", default="created_date", help="Column to track updates")
@click.option(
    "--webhook-url", envvar="WEBHOOK_URL", help="Slack or Teams webhook URL for notifications"
)
@click.option(
    "--optimize",
    is_flag=True,
    default=True,
    help="Run VACUUM/ANALYZE after sync to optimize DuckDB",
)
@click.option("--export-parquet", help="Directory path to export database as Parquet backups")
def sync(dataset, domain, db_path, table, updated_col, webhook_url, optimize, export_parquet):
    """Nightly sync: Incrementally fetch dataset updates into DuckDB."""
    import os
    import shutil

    import requests

    from socrata_toolkit.core import DuckDBManager
    from socrata_toolkit.pipeline import sync_dataset

    draw_unicode_box("NYC DOT DATABASE SYNC", f"Target: {dataset} ➔ Table: {table}")
    # This automatically picks up your SOCRATA_APP_TOKEN from the environment
    count = sync_dataset(domain, dataset, db_path, table, updated_col)
    logging.info(f"Sync complete for {dataset}. {count} new records fetched.")

    click.echo("\n✨ ┌─────────────────────────────────────────────────────────┐")
    click.echo(f"   │ Success! {count} new records securely processed and upserted.│")
    click.echo("   └─────────────────────────────────────────────────────────┘\n")

    if optimize or export_parquet:
        mgr = DuckDBManager(db_path)
        try:
            if optimize:
                click.echo("⚙️  Running deep database optimization (VACUUM/ANALYZE)...")
                mgr.query("VACUUM;")
                mgr.query("ANALYZE;")
                logging.info("DuckDB optimization complete.")

            if export_parquet:
                click.echo(f"📦 Exporting fully compressed Parquet backup to '{export_parquet}'...")
                # DuckDB EXPORT requires an empty or non-existent directory. Overwrite previous backups.
                if os.path.exists(export_parquet):
                    shutil.rmtree(export_parquet)
                # Export entire database as compressed ZSTD Parquet files
                mgr.query(f"EXPORT DATABASE '{export_parquet}' (FORMAT PARQUET, COMPRESSION ZSTD);")
                logging.info("Parquet export complete.")
            click.echo("✅ Post-processing complete.")

        except Exception as e:
            click.echo(f"❌ Database operation failed: {e}")
            logging.error(f"Database operation failed: {e}")
        finally:
            mgr.close()

    if webhook_url:
        try:
            msg = f"✅ *NYC DOT Nightly Sync Complete*\nDataset: `{dataset}`\nTable: `{table}`\nNew Records: `{count}`"
            requests.post(webhook_url, json={"text": msg})
            click.echo("Webhook notification sent.")
        except Exception as e:
            click.echo(f"Failed to send webhook notification: {e}")
            logging.error(f"Failed to send webhook: {e}")


@main.command()
@click.option("--db-path", default="nyc_mission_control.duckdb", help="DuckDB database path")
def status(db_path):
    """View the status, tables, and row counts of the local database."""
    from socrata_toolkit.core import DuckDBManager

    mgr = DuckDBManager(db_path)
    try:
        tables = mgr.query("SHOW TABLES").fetchall()
        if not tables:
            click.echo("📭 Database is currently empty.")
            return

        draw_unicode_box("DATABASE STATUS", f"Database: {db_path}")
        for t in tables:
            table_name = t[0]
            count = mgr.query(f'SELECT count(*) FROM "{table_name}"').fetchone()[0]
            click.echo(f"  📊 {table_name:<30} | {count:>10,} rows")
    except Exception as e:
        click.echo(f"❌ Error reading database: {e}")
    finally:
        mgr.close()


@main.command()
@click.option("--output", default="toolkit_semantic_map.html", help="Output HTML file path")
def map_toolkit(output):
    """Generate an interactive semantic network map of the toolkit's capabilities."""
    try:
        import os
        import webbrowser

        from socrata_toolkit.viz.charts import generate_semantic_network_map

        click.echo("🕸️ Weaving the Semantic Knowledge Graph...")
        fig = generate_semantic_network_map()
        fig.write_html(output)

        click.echo(f"✅ Successfully generated map: {output}")
        webbrowser.open("file://" + os.path.realpath(output))
    except Exception as e:
        click.echo(f"❌ Error generating map: {e}")


if __name__ == "__main__":
    main()
