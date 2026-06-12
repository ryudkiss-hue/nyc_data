"""Import shims for analysis.program, analysis.advanced, nlp.advanced."""

from __future__ import annotations

def test_analysis_advanced_outliers():
    from socrata_toolkit.analysis.advanced import detect_all_outliers

    assert callable(detect_all_outliers)

def test_analysis_program_dashboard():
    from socrata_toolkit.analysis.program import compute_program_dashboard

    assert callable(compute_program_dashboard)

def test_nlp_advanced_analyze():
    from socrata_toolkit.nlp.advanced import analyze_text

    out = analyze_text("sidewalk cracked and unsafe")
    assert out["priority"] in ("critical", "high", "medium", "low")

def test_analysis_monolith_via_package():
    from socrata_toolkit.analysis import profile_dataframe

    assert callable(profile_dataframe)
