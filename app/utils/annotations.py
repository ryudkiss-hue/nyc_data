"""Session-scoped annotations / notes attached to datasets.

Lets analysts capture institutional knowledge alongside the data. Notes live
in ``st.session_state`` (no backend persistence) and can be exported as JSON
or a flat CSV. The store functions are thin wrappers so the core add/list/
delete logic stays simple and the data shape is stable for export.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

try:
    import streamlit as st
    _HAS_ST = True
except ImportError:  # pragma: no cover
    st = None  # type: ignore
    _HAS_ST = False

_KEY = "_annotations"


def _store() -> dict[str, list[dict[str, Any]]]:
    if not _HAS_ST:
        return {}
    if _KEY not in st.session_state:
        st.session_state[_KEY] = {}
    return st.session_state[_KEY]


def add_note(dataset: str, text: str, *, author: str = "analyst", tag: str = "") -> bool:
    """Add a note to a dataset. Returns True if stored."""
    text = (text or "").strip()
    if not text:
        return False
    store = _store()
    store.setdefault(dataset, []).append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "author": author,
            "tag": tag,
            "text": text,
        }
    )
    return True


def list_notes(dataset: str | None = None) -> list[dict[str, Any]]:
    """All notes for a dataset, or every note (with a `dataset` field) if None."""
    store = _store()
    if dataset is not None:
        return list(store.get(dataset, []))
    flat: list[dict[str, Any]] = []
    for ds, notes in store.items():
        for n in notes:
            flat.append({"dataset": ds, **n})
    return flat


def delete_note(dataset: str, index: int) -> bool:
    """Delete the note at `index` for a dataset. Returns True if removed."""
    store = _store()
    notes = store.get(dataset, [])
    if 0 <= index < len(notes):
        notes.pop(index)
        return True
    return False


def count(dataset: str | None = None) -> int:
    """Total note count, optionally scoped to one dataset."""
    if dataset is not None:
        return len(_store().get(dataset, []))
    return sum(len(v) for v in _store().values())


def export_json() -> str:
    """Serialize all annotations to pretty JSON."""
    return json.dumps(_store(), indent=2, default=str)


def export_csv() -> bytes:
    """Flatten all annotations to CSV bytes."""
    flat = list_notes(None)
    if not flat:
        return b""
    return pd.DataFrame(flat).to_csv(index=False).encode("utf-8")
