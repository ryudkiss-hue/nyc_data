import pytest
from app.services.roi_service import ROIAggregator, ProductivityROI

def test_roi_aggregator_variations():
    """Verify ROI logic with varying inputs and boundary conditions."""
    # Zero case
    roi_zero = ROIAggregator.compute(
        lots_validated=0,
        spatial_conflicts_checked=0,
        contracts_cleared=0,
        joins_automated=0,
        actionable_discrepancies=0,
        quality_flags=0,
        datasets_profiled=0
    )
    assert roi_zero.hours_reclaimed == 0.0
    assert roi_zero.overall_health == "STABLE"
    
    # High volume case
    roi_high = ROIAggregator.compute(
        lots_validated=100,        # 300 min
        spatial_conflicts_checked=10, # 150 min
        contracts_cleared=20,      # 100 min
        joins_automated=50,
        actionable_discrepancies=10,
        quality_flags=100,         # 200 min
        datasets_profiled=26
    )
    # Total = 300 + 150 + 100 + 200 = 750 min
    # Hours = 750 / 60 = 12.5
    assert roi_high.hours_reclaimed == 12.5
    
    # Negative input handling (should be treated as 0 or handled gracefully)
    roi_neg = ROIAggregator.compute(
        lots_validated=-10,
        spatial_conflicts_checked=-5,
        contracts_cleared=0,
        joins_automated=0,
        actionable_discrepancies=0,
        quality_flags=0,
        datasets_profiled=0
    )
    assert roi_neg.hours_reclaimed == 0.0

def test_overall_health_thresholds():
    """Verify health status based on reclaimed hours."""
    # Low health (< 5 hours)
    assert ROIAggregator.compute(lots_validated=10).overall_health == "STABLE"
    
    # Peak health (> 10 hours)
    assert ROIAggregator.compute(lots_validated=250).overall_health == "PEAK"
