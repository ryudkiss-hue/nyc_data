"""NLP advanced shim — keyword triage when spaCy is not installed."""

from __future__ import annotations

from typing import Any


def _priority_from_text(text: str) -> str:
    low = (text or "").lower()
    if not low.strip():
        return "medium"
    critical = ("collapse", "hole", "trip hazard", "unsafe", "emergency", "cave-in")
    high = ("cracked", "broken", "raised", "damaged", "blocked", "uneven", "missing")
    if any(k in low for k in critical):
        return "critical"
    if any(k in low for k in high):
        return "high"
    if "sidewalk" in low or "curb" in low:
        return "medium"
    return "low"


def analyze_text(text: str, **_kwargs: Any) -> dict[str, Any]:
    priority = _priority_from_text(text)
    return {"priority": priority, "summary": (text or "")[:200]}


def translate_text(text: str, target: str = "en", **_kwargs: Any) -> str:
    return text
