from __future__ import annotations

"""Natural language → SoQL query translation using Claude API."""

try:
    import anthropic  # noqa: F401
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

import json
import os
import re
from typing import Any

SYSTEM_PROMPT = """You are a Socrata SoQL query assistant for NYC Open Data.
Given a natural language question about NYC sidewalk inspection data, output ONLY a valid SoQL query fragment.
Output format: JSON with keys: select, where, group, order, limit (omit keys not needed).
Example: {"select": "borough, count(*) as n", "group": "borough", "order": "n desc", "limit": "10"}
Use only columns provided in the user message. Do not explain."""

_INJECTION_PATTERNS = re.compile(
    r"\b(DROP|DELETE|INSERT|UPDATE)\b|--|;",
    re.IGNORECASE,
)


def nl_to_soql(
    question: str,
    dataset_key: str,
    columns: list[str],
    model: str = "claude-haiku-4-5-20251001",
) -> dict[str, Any]:
    """Translates NL question to SoQL params dict via Claude API.

    Returns dict with keys: select, where, group, order, limit (subset).
    Raises RuntimeError if ANTHROPIC_API_KEY not set or anthropic not installed.
    """
    if not HAS_ANTHROPIC:
        raise RuntimeError(
            "anthropic package is not installed. Run: pip install anthropic"
        )

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY environment variable is not set."
        )

    import anthropic as _anthropic  # local import after guard

    client = _anthropic.Anthropic(api_key=api_key)

    user_content = (
        f"Question: {question}\n"
        f"Dataset: {dataset_key}\n"
        f"Columns: {', '.join(columns)}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        parsed: dict[str, Any] = json.loads(raw_text)
        # Keep only the expected keys
        allowed_keys = {"select", "where", "group", "order", "limit"}
        return {k: v for k, v in parsed.items() if k in allowed_keys}
    except (json.JSONDecodeError, ValueError):
        return {"select": "*", "limit": "100"}


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
