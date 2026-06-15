import pandas as pd
import pytest
from dash import dcc

from app.services.export_service import ExportCommand, ExportRegistry


def test_export_registry_registration():
    """Verify that commands can be registered and retrieved."""
    registry = ExportRegistry()

    class TestCommand(ExportCommand):
        def execute(self, df, chart_id):
            return "test_success"

    registry.register("test", TestCommand())
    assert "test" in registry.commands

    result = registry.export("test", pd.DataFrame(), "c1")
    assert result == "test_success"


def test_builtin_csv_export():
    """Verify standard CSV export command."""
    registry = ExportRegistry()
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    # Trigger CSV export
    result = registry.export("csv", df, "test_chart")

    assert isinstance(result, dict)  # dcc.send_data_frame returns a dict
    assert "filename" in result
    assert result["filename"].endswith(".csv")


def test_builtin_md_export():
    """Verify Markdown export command."""
    registry = ExportRegistry()
    df = pd.DataFrame({"a": [1], "b": [2]})

    result = registry.export("md", df, "test_chart")
    assert isinstance(result, dict)
    assert result["filename"].endswith(".md")
    # Base64 content check (minimal)
    assert "content" in result


def test_builtin_python_export():
    """Verify Python snippet export command."""
    registry = ExportRegistry()
    result = registry.export("py", pd.DataFrame(), "test_chart")

    assert isinstance(result, dict)
    assert result["filename"].endswith(".py")


def test_unknown_export_mode():
    """Verify handling of unknown export modes."""
    registry = ExportRegistry()
    result = registry.export("unknown", pd.DataFrame(), "c1")
    assert result is None
