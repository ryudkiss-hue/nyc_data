from __future__ import annotations

import json
import os
import re
from typing import Any

# Try importing anthropic
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# Existing SYSTEM_PROMPT
SYSTEM_PROMPT = """You are a Socrata SoQL query assistant for NYC Open Data.
Given a natural language question about NYC sidewalk inspection data, output ONLY a valid SoQL query fragment.
Output format: JSON with keys: select, where, group, order, limit (omit keys not needed).
Example: {"select": "borough, count(*) as n", "group": "borough", "order": "n desc", "limit": "10"}
Use only columns provided in the user message. Do not explain."""

# NEW SYSTEM PROMPTS
COMPLAINT_PARSER_SYSTEM_PROMPT = """You are a Socrata assistant for NYC Open Data 311 complaints.
Given a citizen complaint text, classify it and output JSON.
Output format: {"severity": "high/medium/low", "category": "street-condition/waste-management/noise/other", "summary": "brief summary"}"""

TRIAGE_SYSTEM_PROMPT = """You are a Socrata triage assistant for NYC Open Data 311 complaints.
Analyze citizen frustration.
Output format: {"frustration_score": 1-10, "escalate": true/false, "reason": "brief reason"}"""

_INJECTION_PATTERNS = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE)\b|--|;",
    re.IGNORECASE,
)

def _get_anthropic_client() -> Any:
    """Helper to get Anthropic client."""
    if not HAS_ANTHROPIC:
        raise RuntimeError("anthropic package not installed.")
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set.")
    import anthropic as _anthropic
    return _anthropic.Anthropic(api_key=api_key)

def _call_llm(user_content: str, system_prompt: str, model: str = "claude-haiku-4-5-20251001") -> dict[str, Any]:
    """Helper to call LLM."""
    client = _get_anthropic_client()
    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    raw_text = response.content[0].text.strip()
    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)
    return json.loads(raw_text)

def nl_to_soql(
    question: str,
    dataset_key: str,
    columns: list[str],
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Translates NL question to SoQL params dict."""
    user_content = (
        f"Question: {question}\n"
        f"Dataset: {dataset_key}\n"
        f"Columns: {', '.join(columns)}"
    )
    try:
        parsed = _call_llm(user_content, SYSTEM_PROMPT, model)
        allowed_keys = {"select", "where", "group", "order", "limit"}
        return {k: v for k, v in parsed.items() if k in allowed_keys}
    except (json.JSONDecodeError, ValueError, RuntimeError):
        return {"select": "*", "limit": "100"}

def parse_complaint_to_json(complaint_text: str) -> dict[str, Any]:
    """Parses 311 complaint text to structured JSON."""
    try:
        return _call_llm(complaint_text, COMPLAINT_PARSER_SYSTEM_PROMPT)
    except (json.JSONDecodeError, ValueError, RuntimeError):
        return {"severity": "medium", "category": "other", "summary": "Unable to parse"}

def triage_complaint(complaint_text: str) -> dict[str, Any]:
    """Triages 311 complaint for frustration."""
    try:
        return _call_llm(complaint_text, TRIAGE_SYSTEM_PROMPT)
    except (json.JSONDecodeError, ValueError, RuntimeError):
        return {"frustration_score": 5, "escalate": False, "reason": "Unable to triage"}

def validate_soql(params: dict[str, Any], valid_columns: list[str]) -> list[str]:
    """Returns list of validation error strings. Empty list = valid."""
    errors: list[str] = []
    # Check for SQL injection patterns in all values
    for key, value in params.items():
        if isinstance(value, str) and _INJECTION_PATTERNS.search(value):
            errors.append(
                f"Potentially unsafe pattern detected in '{key}': {value!r}"
            )

    # Validate limit is a numeric string if present
    if "limit" in params:
        limit_val = str(params["limit"]).strip()
        if not limit_val.isdigit():
            errors.append(
                f"'limit' must be a numeric string, got: {limit_val!r}"
            )

    # Validate columns referenced in select (skip *, count(*), and expressions)
    if "select" in params and valid_columns:
        select_str = params["select"]
        # Skip wildcard
        if select_str.strip() == "*":
            return errors

        # Extract bare column names: split by comma, strip aliases and functions
        for token in select_str.split(","):
            token = token.strip()
            # Skip aggregate/function expressions like count(*), avg(col) as alias
            if re.search(r"\(", token):
                continue
            # Strip alias (e.g. "col as alias")
            col_part = re.split(r"\s+as\s+", token, flags=re.IGNORECASE)[0].strip()
            # Skip if empty, *, or contains arithmetic operators
            if not col_part or col_part == "*" or re.search(r"[+\-*/]", col_part):
                continue
            if col_part not in valid_columns:
                errors.append(
                    f"Column '{col_part}' not found in dataset columns."
                )

    return errors