import pandas as pd
import pytest

try:
    import shapely  # noqa: F401
except Exception:  # pragma: no cover
    shapely = None

from socrata_toolkit.spatial import spatial_intersects_join


@pytest.mark.skipif(shapely is None, reason="shapely not installed")
def test_spatial_intersects_join_basic():
    left = pd.DataFrame({"id": [1], "geometry": ["POINT (0 0)"]})
    right = pd.DataFrame({"rid": [9], "geometry": ["POLYGON ((-1 -1, -1 1, 1 1, 1 -1, -1 -1))"]})
    res = spatial_intersects_join(left, right, "geometry", "geometry")
    assert res.overlap_count >= 1
    assert res.conflict_rate == 1.0
