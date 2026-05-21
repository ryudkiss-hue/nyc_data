"""Core profiling shim — maps to analysis monolith."""

from socrata_toolkit.analysis import profile_dataframe, quality_report  # noqa: F401

__all__ = ["profile_dataframe", "quality_report"]
