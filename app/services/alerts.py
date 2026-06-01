"""Alert and integration services for NYC DOT SIM Toolkit."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Item 88 — Slack webhook
# ---------------------------------------------------------------------------


def send_slack_alert(
    webhook_url: str,
    title: str,
    message: str,
    severity: str = "info",  # info | warning | critical
    fields: dict[str, str] | None = None,
) -> tuple[bool, str]:
    """POST a Slack Block Kit message to a webhook URL."""
    color_map = {"info": "#36a64f", "warning": "#ff9800", "critical": "#d32f2f"}
    color = color_map.get(severity, "#36a64f")

    icon = "🔴" if severity == "critical" else "⚠️" if severity == "warning" else "ℹ️"
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{icon} {title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]
    if fields:
        field_elements = [
            {"type": "mrkdwn", "text": f"*{k}*\n{v}"} for k, v in fields.items()
        ]
        blocks.append({"type": "section", "fields": field_elements[:10]})
    blocks.append(
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": "NYC DOT SIM Toolkit"}],
        }
    )

    payload = {"blocks": blocks, "attachments": [{"color": color}]}
    try:
        r = requests.post(webhook_url, json=payload, timeout=10)
        if r.status_code == 200:
            return True, "Alert sent"
        return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Item 89 — ArcGIS Online push
# ---------------------------------------------------------------------------


def push_to_arcgis_online(
    org_url: str,
    username: str,
    password: str,
    title: str,
    geojson_str: str,
    tags: list[str] | None = None,
) -> tuple[bool, str]:
    """Publish a GeoJSON string as a hosted feature layer on ArcGIS Online.

    Requires requests. Returns (success, item_url_or_error).
    """
    # 1. Authenticate
    token_url = f"{org_url.rstrip('/')}/sharing/rest/generateToken"
    try:
        r = requests.post(
            token_url,
            data={
                "username": username,
                "password": password,
                "referer": org_url,
                "f": "json",
            },
            timeout=30,
        )
        token_data = r.json()
        token = token_data.get("token")
        if not token:
            return False, f"Auth failed: {token_data.get('error', token_data)}"
    except Exception as e:
        return False, f"Auth error: {e}"

    # 2. Add item
    add_url = f"{org_url.rstrip('/')}/sharing/rest/content/users/{username}/addItem"
    try:
        r = requests.post(
            add_url,
            data={
                "f": "json",
                "token": token,
                "title": title,
                "type": "GeoJson",
                "text": geojson_str,
                "tags": ",".join(tags or ["NYC DOT", "SIM", "Sidewalk"]),
                "description": "Published from NYC DOT SIM Toolkit",
            },
            timeout=60,
        )
        result = r.json()
    except Exception as e:
        return False, f"Add item error: {e}"

    if result.get("success"):
        item_id = result.get("id", "")
        return True, f"{org_url}/home/item.html?id={item_id}"
    return False, str(result.get("error", result))


# ---------------------------------------------------------------------------
# Item 91 — NYC 311 polling (simplified)
# ---------------------------------------------------------------------------


def poll_311_new_complaints(
    domain: str = "data.cityofnewyork.us",
    fourfour: str = "erm2-nwe9",
    app_token: str = "",
    since_iso: str = "",
    limit: int = 100,
) -> list[dict]:
    """Poll 311 dataset for complaints created after since_iso.

    Returns list of new complaint dicts.
    """
    where = (
        "complaint_type IN ('Sidewalk Condition','Curb Condition','Damaged Tree',"
        "'Root/Sewer/Sidewalk Condition')"
    )
    if since_iso:
        where += f" AND created_date > '{since_iso}'"

    url = f"https://{domain}/resource/{fourfour}.json"
    params: dict[str, Any] = {
        "$where": where,
        "$limit": limit,
        "$order": "created_date DESC",
    }
    headers: dict[str, str] = {}
    if app_token:
        headers["X-App-Token"] = app_token

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("311 poll failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Item 92 — DOB Jobs cross-reference
# ---------------------------------------------------------------------------


def fetch_dob_jobs_near_address(
    block: str,
    lot: str,
    boro_num: str = "1",
    domain: str = "data.cityofnewyork.us",
    app_token: str = "",
    limit: int = 50,
) -> list[dict]:
    """Fetch active DOB job applications for a given block/lot.

    Uses DOB Job Application Filings dataset: w9ak-ipjd.
    The boro_num parameter is accepted for future SoQL filtering extensions.
    """
    fourfour = "w9ak-ipjd"
    where = f"block='{block}' AND lot='{lot}'"
    url = f"https://{domain}/resource/{fourfour}.json"
    params: dict[str, Any] = {"$where": where, "$limit": limit}
    headers: dict[str, str] = {"X-App-Token": app_token} if app_token else {}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("DOB jobs fetch failed: %s", e)
        return []
