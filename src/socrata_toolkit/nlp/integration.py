"""Rule-based 311 complaint triage for offline pipelines.

Sets ``_triage_priority`` (critical / high / medium / low) from complaint text.
For LLM-backed triage, use ``socrata_toolkit.ai.triage_complaints`` instead.
"""

from __future__ import annotations

import pandas as pd

_CRITICAL_KEYWORDS = ("collapse", "hole", "trip hazard", "unsafe", "emergency", "cave-in")
_HIGH_KEYWORDS = ("cracked", "broken", "raised", "damaged", "blocked", "uneven", "missing")

def triage_complaints(df: pd.DataFrame, text_col: str = "description") -> pd.DataFrame:
    """Assign ``_triage_priority`` from keyword rules (no network calls)."""
    out = df.copy()
    priorities: list[str] = []
    for _, row in out.iterrows():
        text = str(row.get(text_col, "")).lower()
        if not text.strip():
            priorities.append("medium")
            continue
        if any(k in text for k in _CRITICAL_KEYWORDS):
            priorities.append("critical")
        elif any(k in text for k in _HIGH_KEYWORDS):
            priorities.append("high")
        elif "sidewalk" in text or "curb" in text:
            priorities.append("medium")
        else:
            priorities.append("low")
    out["_triage_priority"] = priorities
    return out
