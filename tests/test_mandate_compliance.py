import numpy as np
import pandas as pd
import pytest

from socrata_toolkit.analysis.inference import check_normality, run_t_test
from socrata_toolkit.analysis.profiling import profile_dataframe
from socrata_toolkit.engineering.infrastructure import LifeCycleCostAnalysis
from socrata_toolkit.material.standards_v4 import run_vision_zero_audit

def test_four_moments_mandate():
    """Verify that DataProfile explicitly calculates the Four Moments."""
    df = pd.DataFrame({"test": np.random.normal(0, 1, 100)})
    prof = profile_dataframe(df)

    assert "test" in prof.moments
    m = prof.moments["test"]
    assert "mean" in m
    assert "variance" in m
    assert "skewness" in m
    assert "kurtosis" in m

def test_normality_audit_mandate():
    """Verify that normality checks are functional for OLS diagnostic requirements."""
    normal_data = pd.Series(np.random.normal(0, 1, 100))
    non_normal_data = pd.Series(np.random.exponential(1, 100))

    assert check_normality(normal_data)
    assert not check_normality(non_normal_data)

def test_lcca_npv_mandate():
    """Verify that LCCA engine utilizes discounted cash flow logic (NPV)."""
    lcca = LifeCycleCostAnalysis(discount_rate=0.05)
    # 100 initial + 10/yr for 2 years
    # NPV = 100 + 10/1.05 + 10/1.1025 = 118.59
    npv = lcca.calculate_npv(100, [10, 10], {}, 0, 2)
    assert round(npv, 2) == 118.59

def test_vision_zero_geometric_mandate():
    """Verify that Vision Zero audits flag non-compliant lane widths (SDM 4th Ed)."""
    # Standard is 10-11ft. 12ft is a violation for non-truck routes.
    audit = run_vision_zero_audit(lane_width=12.0, corner_radius=10.0, clear_path=8.0)
    assert not audit.is_compliant
    assert any("exceeds standard" in v for v in audit.violations)

def test_no_mocking_mandate():
    """Scan key modules for 'TODO' or 'pass' statements that indicate mocking."""
    import inspect

    from socrata_toolkit.analysis import insights

    source = inspect.getsource(insights.InsightsEngine.generate_report)
    assert "pass" not in source
    assert "TODO" not in source.upper()
