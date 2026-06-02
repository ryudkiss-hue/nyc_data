"""Live integration tests against NYC Open Data Socrata API.

These tests make real HTTP requests and are skipped automatically when
SOCRATA_APP_TOKEN is not set (local dev without credentials).

In CI the token is injected via repository secrets, so the full suite runs.
"""
from __future__ import annotations

import os

import pytest

TOKEN = os.getenv("SOCRATA_APP_TOKEN", "")
# Skip when token is absent or is still the placeholder value from .env.example.
# Tests that call the CLI directly (ramp-analysis, dataset health) require a
# *valid* Socrata token; the Python-level fetch tests fall back to anonymous
# access if the token is rejected, so they still pass with an invalid token.
NEEDS_TOKEN = pytest.mark.skipif(
    not TOKEN or TOKEN in ("your-socrata-app-token-here", ""),
    reason="SOCRATA_APP_TOKEN not configured — skipping live Socrata tests",
)
# CLI tests additionally require that the token is accepted by Socrata (not a
# placeholder/random string). We detect this by checking the token length looks
# real (Socrata app tokens are 23+ chars).
NEEDS_VALID_TOKEN = pytest.mark.skipif(
    not TOKEN or TOKEN in ("your-socrata-app-token-here", "") or len(TOKEN) < 20,
    reason="SOCRATA_APP_TOKEN not a valid Socrata token — skipping CLI live tests",
)

DOMAIN = "data.cityofnewyork.us"
RAMP_FOURFOUR = "e7gc-ub6z"     # Pedestrian Ramp Program Progress
INSPECTION_FOURFOUR = "dntt-gqwq"  # SMD Inspections


@NEEDS_TOKEN
def test_socrata_search_returns_results():
    """Token is valid: search API returns NYC datasets."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    client = SocrataClient(SocrataConfig())
    results = client.search("sidewalk", limit=5)
    assert len(results) > 0, "Live search returned no results"


@NEEDS_TOKEN
def test_ramp_progress_dataset_accessible():
    """Ramp progress dataset (e7gc-ub6z) is reachable and non-empty."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    client = SocrataClient(SocrataConfig())
    df = client.fetch_dataframe(DOMAIN, RAMP_FOURFOUR, max_rows=10)

    assert len(df) > 0, "Ramp progress dataset returned 0 rows"
    assert "borough" in df.columns, "Expected 'borough' column in ramp dataset"


@NEEDS_TOKEN
def test_ramp_progress_expected_boroughs():
    """Ramp dataset contains rows for at least 3 of 5 NYC boroughs."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    client = SocrataClient(SocrataConfig())
    df = client.fetch_dataframe(DOMAIN, RAMP_FOURFOUR, max_rows=500)

    boroughs = set(df["borough"].dropna().unique())
    expected = {"BROOKLYN", "QUEENS", "MANHATTAN", "BRONX", "STATEN ISLAND"}
    found = boroughs & expected
    assert len(found) >= 3, f"Expected ≥3 boroughs, got: {found}"


@NEEDS_TOKEN
def test_inspection_dataset_large():
    """Inspections dataset (dntt-gqwq) has meaningful row counts."""
    from socrata_toolkit.core.client import SocrataClient, SocrataConfig

    client = SocrataClient(SocrataConfig())
    df = client.fetch_dataframe(DOMAIN, INSPECTION_FOURFOUR, max_rows=100)

    assert len(df) >= 100, "Inspections dataset returned fewer rows than expected"


@NEEDS_VALID_TOKEN
def test_dataset_health_cmd_live():
    """CLI dataset health command hits live API and returns tabular output."""
    from click.testing import CliRunner

    from socrata_toolkit.core.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--key", "ramp_progress"])

    # exit_code 1 is expected when dataset is stale/errored — that's the health signal
    assert result.exit_code in (0, 1), f"dataset health crashed: {result.output}"
    assert "ramp_progress" in result.output
    assert "e7gc-ub6z" in result.output


@NEEDS_VALID_TOKEN
def test_ramp_analysis_cmd_live():
    """CLI ramp-analysis command fetches and processes live sample data."""
    from click.testing import CliRunner

    from socrata_toolkit.core.cli import main

    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "ramp-analysis", "--sample", "50"])

    assert result.exit_code == 0, f"ramp-analysis failed: {result.output}"
    # Output should contain borough names or a completion-rate table
    output_lower = result.output.lower()
    assert any(b in output_lower for b in ["brooklyn", "queens", "bronx", "manhattan", "staten"]), (
        f"No borough names found in ramp-analysis output: {result.output[:500]}"
    )
