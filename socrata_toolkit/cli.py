"""Command Line Interface for NYC DOT Socrata Toolkit."""
import click
import pandas as pd
from socrata_toolkit.core import SocrataClient
from socrata_toolkit.analysis import compute_program_dashboard
from socrata_toolkit.engineering import prioritize_construction_list

@click.group()
def main():
    """NYC DOT Socrata Toolkit CLI."""
    pass

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
@click.option("--format", "-f", type=click.Choice(["csv", "json"]), default="csv", help="Output format")
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

if __name__ == "__main__":
    main()
