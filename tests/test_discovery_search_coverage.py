"""Comprehensive tests for discovery.search module.

discovery/search.py is a Streamlit UI script that also exposes two
pure-Python helper functions:  clean_results() and build_catalog_filters().
Streamlit and SocrataClient are mocked at the module level so the module can
be imported without a running Streamlit server or network connection.

Coverage strategy:
- Import the module through sys.modules injection after patching all top-level
  Streamlit calls.
- Test clean_results() and build_catalog_filters() exhaustively with varying inputs.
- Test the module-level SocrataClient instantiation stays isolated.
"""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Module-level Streamlit mock setup
# ---------------------------------------------------------------------------
# discovery.search runs st.set_page_config, st.sidebar.*, st.title, etc. at
# import time.  We inject a comprehensive fake 'streamlit' module before the
# first import so none of those calls raise.


def _make_streamlit_stub() -> types.ModuleType:
    """Build a minimal Streamlit stub that absorbs all attribute accesses."""
    st = types.ModuleType("streamlit")

    class _CtxMock(MagicMock):
        """A MagicMock that also acts as a context manager."""
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    stub = _CtxMock()

    for attr in [
        "set_page_config", "title", "subheader", "text_input", "text_area",
        "button", "checkbox", "radio", "selectbox", "slider", "number_input",
        "spinner", "warning", "success", "dataframe", "json",
        "divider", "write", "status", "empty",
    ]:
        setattr(st, attr, stub)

    # columns(n) must return exactly n context-manager mocks so unpacking
    # `col1, col2 = st.columns(2)` works.
    def _columns(n: int):
        return [_CtxMock() for _ in range(n)]

    st.columns = _columns

    # expander returns a single context-manager mock
    st.expander = lambda *a, **kw: _CtxMock()

    st.sidebar = stub
    return st


# Inject the stub before any import of the target module
if "streamlit" not in sys.modules:
    sys.modules["streamlit"] = _make_streamlit_stub()
else:
    # Ensure it's our stub (re-run scenario)
    pass

# Mock SocrataClient so the module-level `client = SocrataClient()` doesn't
# hit the network.
_client_mock = MagicMock()
with patch("socrata_toolkit.core.client.SocrataClient", return_value=_client_mock):
    # Import after all mocks are in place
    from socrata_toolkit.discovery.search import build_catalog_filters, clean_results  # noqa: E402


# ---------------------------------------------------------------------------
# clean_results
# ---------------------------------------------------------------------------


class TestCleanResults:
    """Tests for the clean_results() DataFrame helper."""

    def test_returns_dataframe(self):
        """Return type is always a pandas DataFrame."""
        df = pd.DataFrame({"id": [1], "name": ["test"]})
        result = clean_results(df)
        assert isinstance(result, pd.DataFrame)

    def test_preferred_columns_come_first(self):
        """Columns in the preferred list appear before unrecognised ones."""
        df = pd.DataFrame({
            "zzz_extra": ["x"],
            "name": ["Test Dataset"],
            "id": ["abc1-2345"],
            "description": ["A dataset"],
        })
        result = clean_results(df)
        first_cols = list(result.columns[:3])
        for col in ["id", "name", "description"]:
            assert col in first_cols

    def test_extra_columns_appended_after_preferred(self):
        """Extra columns not in the preferred list appear at the end."""
        df = pd.DataFrame({
            "id": ["x"],
            "name": ["y"],
            "custom_field": ["z"],
        })
        result = clean_results(df)
        assert "custom_field" in result.columns
        assert list(result.columns).index("custom_field") > list(result.columns).index("id")

    def test_only_present_preferred_columns_included(self):
        """Preferred columns absent from the DataFrame are skipped."""
        df = pd.DataFrame({"id": ["a"], "type": ["table"]})
        result = clean_results(df)
        assert "id" in result.columns
        assert "type" in result.columns
        assert "description" not in result.columns

    def test_all_preferred_columns_present(self):
        """When all preferred columns exist they all appear in order."""
        preferred = [
            "id", "name", "description", "domain", "category",
            "type", "updatedAt", "rowsUpdatedAt", "downloads", "provenance",
        ]
        df = pd.DataFrame({col: ["val"] for col in preferred})
        result = clean_results(df)
        assert list(result.columns[:10]) == preferred

    def test_empty_dataframe_returns_empty(self):
        """An empty DataFrame is returned as-is (no columns to reorder)."""
        df = pd.DataFrame()
        result = clean_results(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_row_count_preserved(self):
        """Row count is unchanged after column reordering."""
        df = pd.DataFrame({
            "id": ["a", "b", "c"],
            "name": ["X", "Y", "Z"],
            "downloads": [10, 20, 30],
        })
        result = clean_results(df)
        assert len(result) == 3

    def test_single_column_dataframe(self):
        """A DataFrame with only one column works without error."""
        df = pd.DataFrame({"name": ["Dataset A"]})
        result = clean_results(df)
        assert "name" in result.columns
        assert len(result.columns) == 1


# ---------------------------------------------------------------------------
# build_catalog_filters
# ---------------------------------------------------------------------------


class TestBuildCatalogFilters:
    """Tests for the build_catalog_filters() expression builder."""

    def test_all_none_returns_empty_string(self):
        """With no filters an empty string is returned."""
        result = build_catalog_filters(None, None, None, False)
        assert result == ""

    def test_domain_only(self):
        """Domain filter produces a quoted clause."""
        result = build_catalog_filters("data.cityofnewyork.us", None, None, False)
        assert 'domain="data.cityofnewyork.us"' in result

    def test_category_only(self):
        """Category filter produces a quoted clause."""
        result = build_catalog_filters(None, "Transportation", None, False)
        assert 'category="Transportation"' in result

    def test_dataset_type_only(self):
        """Dataset type filter produces a quoted clause."""
        result = build_catalog_filters(None, None, "table", False)
        assert 'type="table"' in result

    def test_only_public_flag(self):
        """only_public=True appends a publication_stage clause."""
        result = build_catalog_filters(None, None, None, True)
        assert 'publication_stage="published"' in result

    def test_domain_and_category_combined_with_and(self):
        """Multiple filters are joined with AND."""
        result = build_catalog_filters("data.cityofnewyork.us", "Transportation", None, False)
        assert " AND " in result
        assert 'domain="data.cityofnewyork.us"' in result
        assert 'category="Transportation"' in result

    def test_all_filters_combined(self):
        """All four filters produce a four-clause AND expression."""
        result = build_catalog_filters(
            "data.cityofnewyork.us", "Health", "dataset", True
        )
        assert 'domain="data.cityofnewyork.us"' in result
        assert 'category="Health"' in result
        assert 'type="dataset"' in result
        assert 'publication_stage="published"' in result
        assert result.count(" AND ") == 3

    def test_empty_string_domain_treated_as_none(self):
        """An empty string domain is falsy and not included."""
        result = build_catalog_filters("", None, None, False)
        assert result == ""

    def test_empty_string_category_treated_as_none(self):
        """An empty string category is falsy and not included."""
        result = build_catalog_filters(None, "", None, False)
        assert result == ""

    def test_empty_string_dataset_type_treated_as_none(self):
        """An empty string dataset_type is falsy and not included."""
        result = build_catalog_filters(None, None, "", False)
        assert result == ""

    def test_only_public_false_no_extra_clause(self):
        """only_public=False does not add a publication_stage clause."""
        result = build_catalog_filters("example.com", None, None, False)
        assert "publication_stage" not in result

    def test_result_is_always_string(self):
        """Return value is always a str regardless of input."""
        result = build_catalog_filters(None, None, None, False)
        assert isinstance(result, str)

    def test_domain_with_special_characters(self):
        """Domains with dots and hyphens are quoted correctly."""
        result = build_catalog_filters("data.ny.gov", None, None, False)
        assert 'domain="data.ny.gov"' in result

    def test_type_map_chart_story_variants(self):
        """Type values like 'map', 'chart', 'story' are passed through."""
        for t in ("map", "chart", "story"):
            result = build_catalog_filters(None, None, t, False)
            assert f'type="{t}"' in result
