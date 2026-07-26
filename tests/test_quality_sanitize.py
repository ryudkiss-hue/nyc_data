"""Tests for socrata_toolkit.quality.sanitize — shared data-repair layer."""
from __future__ import annotations

import pandas as pd

from socrata_toolkit.quality.sanitize import sanitize_dataframe


def _dirty_df() -> pd.DataFrame:
    return pd.DataFrame({
        "violationid": ["1", "2", "2", "3"],
        "certi_date": ["2100-01-01", "2025-06-01", "2025-06-01", "1970-05-05"],
        "borough": ["QUEENS", "BRONX", "BRONX", "QUEENS"],
        "mostly_empty": [None, None, None, "x"],
    })


class TestSanitizeDataframe:
    def test_placeholder_future_dates_nulled(self):
        clean, rep = sanitize_dataframe(_dirty_df())
        parsed = pd.to_datetime(clean["certi_date"], errors="coerce")
        assert parsed.max() < pd.Timestamp.now() + pd.Timedelta(days=365)
        assert rep.bad_dates_nulled == 2  # 2100-01-01 and 1970-05-05
        assert any(c.startswith("certi_date") for c in rep.bad_date_cols)

    def test_exact_duplicates_dropped(self):
        clean, rep = sanitize_dataframe(_dirty_df())
        assert rep.dupes_removed == 1
        assert len(clean) == 3

    def test_dead_variables_flagged_but_kept(self):
        df = pd.DataFrame({
            "id": [str(i) for i in range(20)],
            "mostly_empty": [None] * 19 + ["x"],
        })
        clean, rep = sanitize_dataframe(df)
        assert "mostly_empty" in clean.columns
        assert any(v.startswith("mostly_empty") for v in rep.dead_vars)

    def test_geometry_dicts_survive(self):
        df = pd.DataFrame({
            "the_geom": [{"type": "Point", "coordinates": [0, 1]}] * 3,
            "id": ["a", "b", "b"],
        })
        clean, rep = sanitize_dataframe(df)
        assert rep.dupes_removed == 1
        assert isinstance(clean["the_geom"].iloc[0], dict)

    def test_empty_frame_is_noop(self):
        clean, rep = sanitize_dataframe(pd.DataFrame())
        assert clean.empty and rep.rows_in == 0 and rep.dupes_removed == 0

    def test_valid_dates_untouched(self):
        df = pd.DataFrame({"created_date": ["2026-01-15", "2025-11-30"]})
        clean, rep = sanitize_dataframe(df)
        assert rep.bad_dates_nulled == 0
        assert clean["created_date"].notna().all()
