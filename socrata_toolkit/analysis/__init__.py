"""Analysis package — transparent proxy to legacy ``analysis.py`` monolith."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_MONOLITH_PATH = Path(__file__).resolve().parent.parent / "analysis.py"


def _load_monolith() -> ModuleType:
    name = "socrata_toolkit._analysis_monolith"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _MONOLITH_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load analysis monolith at {_MONOLITH_PATH}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_monolith = _load_monolith()

# Eager export of common symbols for static analysis / star imports
profile_dataframe = _monolith.profile_dataframe
quality_report = _monolith.quality_report
generate_text_insights = _monolith.generate_text_insights
InsightsEngine = _monolith.InsightsEngine
DataProfile = _monolith.DataProfile
detect_all_outliers = _monolith.detect_all_outliers
correlation_analysis = _monolith.correlation_analysis
MetricsTracker = getattr(_monolith, "MetricsTracker", None)
DashboardSummary = getattr(_monolith, "DashboardSummary", None)
compute_program_dashboard = getattr(_monolith, "compute_program_dashboard", None)
TfidfVectorizer = getattr(_monolith, "TfidfVectorizer", None)
parse_sim_complaints = _monolith.parse_sim_complaints


_VIZ_MAP_NAMES = frozenset({"create_map", "save_map", "cluster_map", "heatmap_map"})


def __getattr__(name: str):
    if name in _VIZ_MAP_NAMES:
        from socrata_toolkit.viz import map as _viz_map

        return getattr(_viz_map, name)
    return getattr(_monolith, name)


def __dir__():
    return sorted(set(dir(_monolith) + list(globals().keys())))
