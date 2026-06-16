from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from socrata_toolkit.analyst.data_dictionary import build_data_dictionary, render_data_dictionary_md
from socrata_toolkit.core.profiles import profile_paths
from socrata_toolkit.review.store import ReviewStore


def test_profile_paths_resolve_state_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TOOLKIT_PROFILE", "team-a")
    monkeypatch.setenv("TOOLKIT_STATE_ROOT", str(tmp_path / "state_root"))
    pp = profile_paths()
    assert pp.name == "team-a"
    assert str(pp.state_dir).startswith(str(tmp_path / "state_root"))


def test_review_store_upsert_and_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TOOLKIT_PROFILE", "qa")
    monkeypatch.setenv("TOOLKIT_STATE_ROOT", str(tmp_path / "state"))
    with ReviewStore() as store:
        store.set_conflict(
            pack_date="2099-01-01",
            key_type="location_id",
            key_value="L1",
            status="resolved",
            notes="ok",
        )
        store.set_conflict(
            pack_date="2099-01-01",
            key_type="location_id",
            key_value="L1",
            status="defer",
            notes="later",
        )
        df = store.list(pack_date="2099-01-01", kind="conflict")
        assert len(df) == 1
        assert df.iloc[0]["status"] == "defer"


def test_data_dictionary_builds_and_renders() -> None:
    frames = {"inspections": pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "y"]})}
    dd = build_data_dictionary(frames)
    assert "sources" in dd and "inspections" in dd["sources"]
    md = render_data_dictionary_md(dd)
    assert "# Data Dictionary" in md
    assert "`a`" in md
