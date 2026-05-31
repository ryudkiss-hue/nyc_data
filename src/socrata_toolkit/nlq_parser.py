from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryIntent:
    """Structured representation of a natural language query."""

    intent: str  # e.g., 'show', 'count', 'compare'
    target: str  # e.g., 'defects', 'inspections', 'cost'
    group_by: str | None = None
    filters: dict[str, Any] = field(default_factory=dict)


def parse_query(text: str) -> QueryIntent | None:
    """
    A simple, keyword-based parser to translate natural language into a structured intent.
    This is more reliable and predictable for a domain-specific tool than a full LLM.
    """
    lower_text = text.lower()

    # --- Define Keywords ---
    intents = {
        "show": "show",
        "map": "show",
        "plot": "show",
        "count": "count",
        "compare": "compare",
        "what is": "get",
    }
    targets = {
        "defect": "defects",
        "inspection": "inspections",
        "cost": "cost",
        "rate": "rate",
        "compliance": "compliance",
    }
    groupers = {"by borough": "borough", "by material": "material_type"}

    # --- Extract Entities ---
    parsed_intent = next((v for k, v in intents.items() if k in lower_text), "show")
    parsed_target = next((v for k, v in targets.items() if k in lower_text), "defects")
    parsed_groupby = next((v for k, v in groupers.items() if k in lower_text), None)

    # --- Extract Filters ---
    parsed_filters = {}
    boroughs = ["manhattan", "brooklyn", "queens", "bronx", "staten island"]
    severities = ["hazardous", "critical", "severe"]

    for b in boroughs:
        if b in lower_text:
            parsed_filters["borough"] = b.upper()

    for s in severities:
        if s in lower_text:
            parsed_filters["severity"] = s

    # --- Handle special cases ---
    if "ada" in lower_text and "compliance" in lower_text:
        parsed_target = "ada_compliance_rate"
        parsed_intent = "get"

    if "cost" in lower_text:
        parsed_target = "cost"

    return QueryIntent(
        intent=parsed_intent, target=parsed_target, group_by=parsed_groupby, filters=parsed_filters
    )
