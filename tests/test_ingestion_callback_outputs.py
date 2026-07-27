"""Guards for the init-btn pattern-matching callback's output shape.

The second return value feeds a `dash.ALL` Output. If it is ever a bare
`no_update`, a non-list, or a list whose length differs from the number of
matched components, Dash raises while serializing outputs — outside any
try/except in the callback — and the browser sees an opaque
`InternalServerError`. That failure recurred across several CI runs.
"""
from __future__ import annotations

import pytest

import app.callbacks.ingestion as ing
from app.callbacks.ingestion import initialize_pipeline


@pytest.fixture(autouse=True)
def _no_real_ingestion(monkeypatch):
    """A click spawns a daemon thread that fetches the live corpus. Without
    this the module's own unit tests take ~47 minutes and hit the network."""
    monkeypatch.setattr(ing.threading, "Thread", lambda *a, **k: type(
        "FakeThread", (), {"daemon": False, "start": lambda self: None}
    )())


class TestInitializePipelineReturnShape:
    def setup_method(self):
        ing.ingestion_status.update(
            {"active": False, "progress": 0, "error": None, "finished": False}
        )

    def test_no_clicks_returns_list_not_scalar(self):
        _store, loading = initialize_pipeline([None], [None], [None], [None])
        assert isinstance(loading, list), "wildcard Output must receive a list"
        assert len(loading) == 1

    def test_active_ingestion_returns_list_not_no_update(self):
        ing.ingestion_status["active"] = True
        _store, loading = initialize_pipeline([1, 1], [None], [None], [None])
        assert isinstance(loading, list), (
            "returning a bare no_update for a dash.ALL Output triggers a 500"
        )
        assert len(loading) == 2

    def test_zero_matched_components_returns_empty_list(self):
        _store, loading = initialize_pipeline([], [], [], [])
        assert loading == []

    def test_length_always_tracks_the_inputs(self):
        for n in (1, 3, 5):
            _store, loading = initialize_pipeline([None] * n, [None], [None], [None])
            assert len(loading) == n

    def test_non_numeric_limit_does_not_raise(self):
        _store, loading = initialize_pipeline([1], ["tok"], ["not-a-number"], ["3.0"])
        assert isinstance(loading, list) and len(loading) == 1
        ing.ingestion_status["active"] = False
