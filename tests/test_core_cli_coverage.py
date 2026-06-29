"""Tests for core.cli module."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_help():
    """Test the main CLI help command."""
    root_dir = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "socrata_toolkit.core.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=root_dir
    )
    assert result.returncode == 0
    assert "NYC DOT SIM" in result.stdout

def test_cli_query_help():
    """Test the query CLI help command."""
    root_dir = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "socrata_toolkit.core.cli", "query", "--help"],
        capture_output=True,
        text=True,
        cwd=root_dir
    )
    assert result.returncode == 0
    assert "question" in result.stdout

def test_cli_evaluate_help():
    """Test the evaluate CLI help command."""
    root_dir = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "socrata_toolkit.core.cli", "evaluate", "--help"],
        capture_output=True,
        text=True,
        cwd=root_dir
    )
    assert result.returncode == 0
    assert "variants" in result.stdout

def test_cli_train_help():
    """Test the train CLI help command."""
    root_dir = Path(__file__).parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "socrata_toolkit.core.cli", "train", "--help"],
        capture_output=True,
        text=True,
        cwd=root_dir
    )
    assert result.returncode == 0
    assert "iterations" in result.stdout
