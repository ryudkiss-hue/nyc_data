"""Bookmarkable filter state via Streamlit query params (saved views).

Serializes filter/sort/selection state into ``st.query_params`` so any view is
shareable by URL, survives a reload, and works with the browser back button.
Also supports named saved-views persisted in ``st.session_state``.
"""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

_PREFIX = "v_"  # namespace query-param keys to avoid clobbering app params


def sync_to_url(state: dict[str, Any]) -> None:
    """Write a flat dict of view state into the URL query params."""
    for key, val in state.items():
        qkey = f"{_PREFIX}{key}"
        if val is None or val == "" or (isinstance(val, list | tuple) and not val):
            st.query_params.pop(qkey, None)
        elif isinstance(val, list | tuple):
            st.query_params[qkey] = ",".join(str(v) for v in val)
        else:
            st.query_params[qkey] = str(val)


def read_from_url(defaults: dict[str, Any]) -> dict[str, Any]:
    """Read view state back from URL params, falling back to defaults.

    The type of each default determines coercion: lists split on comma,
    ints/floats are parsed, bools accept truthy strings.
    """
    out: dict[str, Any] = {}
    for key, default in defaults.items():
        raw = st.query_params.get(f"{_PREFIX}{key}")
        if raw is None:
            out[key] = default
            continue
        try:
            if isinstance(default, bool):
                out[key] = raw.lower() in ("1", "true", "yes", "on")
            elif isinstance(default, int):
                out[key] = int(raw)
            elif isinstance(default, float):
                out[key] = float(raw)
            elif isinstance(default, list | tuple):
                out[key] = [s for s in raw.split(",") if s]
            else:
                out[key] = raw
        except (ValueError, TypeError):
            out[key] = default
    return out


# ---------------------------------------------------------------------------
# Named saved views (session-scoped)
# ---------------------------------------------------------------------------
_SAVED_KEY = "_saved_views"


def _store() -> dict[str, dict[str, Any]]:
    if _SAVED_KEY not in st.session_state:
        st.session_state[_SAVED_KEY] = {}
    return st.session_state[_SAVED_KEY]


def save_view(name: str, state: dict[str, Any]) -> None:
    """Persist a named view in session state."""
    if name.strip():
        _store()[name.strip()] = dict(state)


def list_views() -> list[str]:
    """Return the names of all saved views."""
    return sorted(_store().keys())


def load_view(name: str) -> dict[str, Any] | None:
    """Return the state for a saved view, or None."""
    return _store().get(name)


def delete_view(name: str) -> None:
    """Remove a saved view."""
    _store().pop(name, None)


def share_url(state: dict[str, Any], base: str = "") -> str:
    """Build a shareable URL fragment encoding the given state."""
    parts = []
    for key, val in state.items():
        if isinstance(val, list | tuple):
            val = ",".join(str(v) for v in val)
        parts.append(f"{_PREFIX}{key}={val}")
    query = "&".join(parts)
    return f"{base}?{query}" if base else f"?{query}"


def export_views_json() -> str:
    """Serialize all saved views to JSON for download."""
    return json.dumps(_store(), indent=2, default=str)
