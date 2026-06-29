"""Test suite for dataset health CLI command (Unit 4)."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from socrata_toolkit.core.cli import main

pytestmark = pytest.mark.skip(reason="Legacy CLI test - command removed")


def test_dataset_health_help() -> None:
    """Test that health command help shows all new options."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--help"])
    assert result.exit_code == 0
    assert "--all" in result.output
    assert "--stale" in result.output
    assert "--empty" in result.output
    assert "--sort-by" in result.output
    assert "staleness" in result.output
    assert "size" in result.output


def test_dataset_health_sort_by_staleness() -> None:
    """Test that --sort-by staleness is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--sort-by", "staleness"])
    # Command will fail due to missing config, but should not fail on option parsing
    assert "no such option" not in result.output.lower()
    assert "invalid choice" not in result.output.lower()


def test_dataset_health_sort_by_size() -> None:
    """Test that --sort-by size is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--sort-by", "size"])
    # Command will fail due to missing config, but should not fail on option parsing
    assert "no such option" not in result.output.lower()
    assert "invalid choice" not in result.output.lower()


def test_dataset_health_sort_by_invalid() -> None:
    """Test that invalid --sort-by value is rejected."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--sort-by", "invalid"])
    assert result.exit_code != 0
    assert "invalid value" in result.output.lower()


def test_dataset_health_stale_option() -> None:
    """Test that --stale option with integer is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--stale", "14"])
    # Should not fail on option parsing
    assert "invalid value" not in result.output.lower()
    assert "no such option" not in result.output.lower()


def test_dataset_health_empty_flag() -> None:
    """Test that --empty flag is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--empty"])
    # Should not fail on option parsing
    assert "no such option" not in result.output.lower()


def test_dataset_health_all_flag() -> None:
    """Test that --all flag is accepted."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--all"])
    # Should not fail on option parsing
    assert "no such option" not in result.output.lower()


def test_dataset_health_key_option() -> None:
    """Test that --key option is still supported (backward compat)."""
    runner = CliRunner()
    result = runner.invoke(main, ["dataset", "health", "--key", "inspection"])
    # Should not fail on option parsing
    assert "no such option" not in result.output.lower()


def test_dataset_health_combined_options() -> None:
    """Test that multiple options can be combined."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "dataset",
            "health",
            "--all",
            "--stale",
            "7",
            "--sort-by",
            "staleness",
        ],
    )
    # Should not fail on option parsing
    assert "no such option" not in result.output.lower()
    assert "invalid choice" not in result.output.lower()
