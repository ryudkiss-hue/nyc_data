import pytest
from app.analytics import ColumnProfile, DatasetProfile
from app.services.roi_service import ProductivityROI, ROIAggregator

def test_column_profile_quality_score():
    """Verify quality score calculation for columns."""
    # Healthy column
    c1 = ColumnProfile(name="c1", dtype="float", null_pct=0, cardinality=100)
    assert c1.quality_score() == 100.0
    
    # Null penalty
    c2 = ColumnProfile(name="c2", dtype="float", null_pct=50, cardinality=50)
    # 100 - (50 * 0.5) = 75
    assert c2.quality_score() == 75.0
    
    # Constant column penalty
    c3 = ColumnProfile(name="c3", dtype="str", null_pct=0, cardinality=1)
    # 100 - 20 = 80
    assert c3.quality_score() == 80.0
    
    # All-null penalty
    c4 = ColumnProfile(name="c4", dtype="str", null_pct=100, cardinality=0)
    # 100 - (100 * 0.5) - 50 = 0
    assert c4.quality_score() == 0.0

def test_roi_aggregator_logic():
    """Verify business value calculation in ROI service."""
    roi = ROIAggregator.compute(
        lots_validated=10,        # 10 * 3 = 30 min
        spatial_conflicts_checked=2, # 2 * 15 = 30 min
        contracts_cleared=4,      # 4 * 5 = 20 min
        joins_automated=5,
        actionable_discrepancies=3,
        quality_flags=10,         # 10 * 2 = 20 min
        datasets_profiled=5
    )
    
    # Total minutes = 30 + 30 + 20 + 20 = 100 min
    # Hours = 100 / 60 = 1.67
    assert roi.hours_reclaimed == 1.67
    assert roi.joins_automated == 5
    assert roi.quality_flags == 10

def test_dataset_profile_pydantic_validation():
    """Verify Pydantic models reject invalid structures."""
    from pydantic import ValidationError
    
    with pytest.raises(ValidationError):
        # Missing required fields
        DatasetProfile(key="test")
    
    # Valid minimal profile
    dp = DatasetProfile(
        key="test",
        row_count=0,
        col_count=0,
        columns=[],
        geo_columns=[],
        date_columns=[],
        pk_candidates=[],
        fk_candidates=[],
        overall_null_pct=0.0,
        duplicate_row_pct=0.0,
        quality_score=0.0
    )
    assert dp.key == "test"
