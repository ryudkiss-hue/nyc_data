"""Program metrics shim — KPI dashboard lives in program_metrics."""

from socrata_toolkit.program_metrics import (  # noqa: F401
    MetricsTracker,
    compute_program_dashboard,
)

__all__ = ["MetricsTracker", "compute_program_dashboard"]
