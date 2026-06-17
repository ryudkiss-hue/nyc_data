"""CLI integration snippet for Dataset Health & Monitoring workflow.

This snippet shows how to integrate the dataset_health_workflow module
into the main CLI (socrata_toolkit/core/cli.py).

Location in CLI:
Add this under the @dataset_group section (after the existing 'health' command).

Integration pattern:
- Keep the existing 'dataset health' command for quick status checks
- Add 'dataset health --workflow' flag to run the full LangGraph workflow
- Add 'dataset health --monitor' flag for continuous monitoring
"""

import logging

logger = logging.getLogger(__name__)

# ----- Integration Snippet: Add to cli.py after @dataset_group -----

# Option 1: Extend existing dataset health command (Recommended)
# Add these parameters to the existing @dataset_group.command("health") function:

CLI_EXTENSION_1 = '''
@dataset_group.command(name="health")
@click.option("--key", "dataset_key", default=None, help="Specific dataset key")
@click.option("--all", "show_all", is_flag=True, help="Show all 26 registered datasets")
@click.option("--stale", "stale_days", type=int, default=7, help="Staleness threshold (days)")
@click.option("--empty", "show_empty", is_flag=True, help="Show only empty datasets")
@click.option("--sort-by", type=click.Choice(["staleness", "size"]), default="staleness")
@click.option("--workflow", "use_workflow", is_flag=True, help="Run full LangGraph workflow with Claude")
@click.option("--monitor", is_flag=True, help="Continuous monitoring mode (check every 24h)")
@click.option("--output", "output_path", type=click.Path(), help="Write report to file (JSON)")
def dataset_health_cmd(
    dataset_key: str | None,
    show_all: bool,
    stale_days: int,
    show_empty: bool,
    sort_by: str,
    use_workflow: bool,
    monitor: bool,
    output_path: str | None,
) -> None:
    """Report dataset health and freshness.

    Examples:
        socrata dataset health --all                    # Quick status
        socrata dataset health --workflow               # Full analysis + Claude
        socrata dataset health --workflow --output report.json
        socrata dataset health --monitor                # Continuous monitoring
    """
    if use_workflow:
        # Delegate to LangGraph workflow
        report = run_dataset_health_workflow()

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            click.echo(f"Report written to {output_path}")
        else:
            click.echo(json.dumps(report, indent=2))

        # Print summary to console
        summary = report.get("summary", {})
        click.echo(f"\\nSummary:")
        click.echo(f"  Healthy: {summary.get('healthy', 0)}")
        click.echo(f"  Stale: {summary.get('stale', 0)}")
        click.echo(f"  Schema Drift: {summary.get('schema_drift', 0)}")
        click.echo(f"  Empty/Error: {summary.get('empty_or_error', 0)}")

        critical = report.get("critical_alerts", [])
        if critical:
            click.echo(f"\\nCritical Issues ({len(critical)}):")
            for alert in critical:
                click.echo(f"  - {alert['key']}: {alert['status']}")

        return

    if monitor:
        # Continuous monitoring loop
        import time
        interval = 86400  # 24 hours
        click.echo(f"Starting continuous monitoring (interval: {interval}s)")
        try:
            while True:
                click.echo(f"[{datetime.now()}] Running health check...")
                report = run_dataset_health_workflow()

                critical = report.get("critical_alerts", [])
                if critical:
                    click.echo(f"ALERT: {len(critical)} critical issues detected")
                    for alert in critical:
                        click.echo(f"  - {alert['key']}: {alert['status']}")

                click.echo(f"Next check in {interval}s...")
                time.sleep(interval)
        except KeyboardInterrupt:
            click.echo("Monitoring stopped")
            return

    # Otherwise, fall back to quick health check (existing behavior)
    # ... [rest of existing dataset_health_cmd implementation]
'''

# Option 2: Create separate workflow command (Alternative)

CLI_EXTENSION_2 = '''
@dataset_group.command(name="health-workflow")
@click.option("--output", "output_path", type=click.Path(), help="Write JSON report to file")
@click.option("--format", "fmt", type=click.Choice(["json", "table", "markdown"]), default="json")
def dataset_health_workflow_cmd(output_path: str | None, fmt: str) -> None:
    """Run full dataset health workflow with Claude analysis.

    This command:
    1. Fetches metadata for all 57 datasets (parallelized)
    2. Classifies health status (HEALTHY/STALE/SCHEMA_DRIFT/EMPTY_OR_ERROR)
    3. Routes high-severity datasets to Claude for decision-making
    4. Generates alerts and remediation steps
    5. Returns structured JSON output

    Examples:
        socrata dataset health-workflow
        socrata dataset health-workflow --output health_report.json
        socrata dataset health-workflow --format markdown
    """
    import json
    from datetime import datetime
    from ..analysis.dataset_health_workflow import run_dataset_health_workflow

    click.echo("Starting dataset health workflow...")
    report = run_dataset_health_workflow()

    if fmt == "json":
        output = json.dumps(report, indent=2)
    elif fmt == "markdown":
        output = _format_health_report_markdown(report)
    else:
        output = _format_health_report_table(report)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(output)
        click.echo(f"Report written to {output_path}")
    else:
        click.echo(output)

def _format_health_report_markdown(report: dict) -> str:
    """Format health report as Markdown."""
    lines = [
        f"# Dataset Health Report",
        f"Generated: {report.get('timestamp', 'Unknown')}",
        f"",
        f"## Summary",
        f"- **Total Datasets**: {report['summary']['healthy'] + report['summary']['stale'] + report['summary']['schema_drift'] + report['summary']['empty_or_error']}",
        f"- **Healthy**: {report['summary'].get('healthy', 0)}",
        f"- **Stale**: {report['summary'].get('stale', 0)}",
        f"- **Schema Drift**: {report['summary'].get('schema_drift', 0)}",
        f"- **Empty/Error**: {report['summary'].get('empty_or_error', 0)}",
        f"",
    ]

    critical = report.get("critical_alerts", [])
    if critical:
        lines.extend([
            f"## Critical Issues ({len(critical)})",
            f"",
        ])
        for alert in critical:
            lines.extend([
                f"### {alert['key']} ({alert['fourfour']})",
                f"- **Status**: {alert['status']}",
                f"- **Alerts**: {'; '.join(alert.get('alerts', []))}",
                f"",
            ])

    return "\\n".join(lines)

def _format_health_report_table(report: dict) -> str:
    """Format health report as ASCII table."""
    lines = [
        f"Dataset Health Report — {report.get('timestamp', 'Unknown')}",
        "=" * 80,
        f"Total: {len(report.get('datasets', {}))} | "
        f"Healthy: {report['summary'].get('healthy', 0)} | "
        f"Stale: {report['summary'].get('stale', 0)} | "
        f"Schema Drift: {report['summary'].get('schema_drift', 0)} | "
        f"Error: {report['summary'].get('empty_or_error', 0)}",
        "",
    ]

    # Show critical alerts
    critical = report.get("critical_alerts", [])
    if critical:
        lines.append("CRITICAL ISSUES:")
        lines.append(f"{'Key':<30} {'Status':<20} {'Issue':<30}")
        lines.append("-" * 80)
        for alert in critical:
            issue = alert.get("alerts", ["Unknown"])[0][:30]
            lines.append(f"{alert['key']:<30} {alert['status']:<20} {issue:<30}")

    return "\\n".join(lines)
'''

# Option 3: Integration test / demo

INTEGRATION_TEST = '''
def test_dataset_health_workflow():
    """Integration test for dataset health workflow."""
    from socrata_toolkit.analysis.dataset_health_workflow import (
        DatasetHealthWorkflow,
        run_dataset_health_workflow
    )

    # Test 1: Run with minimal registry
    mini_registry = {
        "violations": {"fourfour": "6kbp-uz6m"},
        "inspection": {"fourfour": "dntt-gqwq"},
    }

    workflow = DatasetHealthWorkflow(registry=mini_registry)
    report = workflow.run()

    assert "timestamp" in report
    assert "datasets" in report
    assert "summary" in report
    assert len(report["datasets"]) >= 0

    # Test 2: Check classification
    for key, classification in report.get("datasets", {}).items():
        assert classification["key"] == key
        assert classification["status"] in ["healthy", "stale", "schema_drift", "empty_or_error"]
        assert 0 <= classification["severity"] <= 100

    # Test 3: Summary calculations
    summary = report["summary"]
    total = sum(summary.values())
    assert total == len(report.get("datasets", {}))

    print(f"✓ Workflow executed successfully")
    print(f"  - {len(report['datasets'])} datasets classified")
    print(f"  - {len(report.get('critical_alerts', []))} critical alerts")
'''

if __name__ == "__main__":
    # Quick demo
    print("Dataset Health & Monitoring Workflow CLI Integration")
    print("=" * 60)
    print()
    print("Option 1: Extend existing 'dataset health' command")
    print("  Usage: socrata dataset health --workflow")
    print()
    print("Option 2: Create separate 'health-workflow' command")
    print("  Usage: socrata dataset health-workflow")
    print()
    print("Both options support:")
    print("  - JSON output (--output file.json)")
    print("  - Multiple formats (--format json|table|markdown)")
    print("  - Continuous monitoring (--monitor)")

