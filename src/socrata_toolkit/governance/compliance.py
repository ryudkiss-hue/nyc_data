from __future__ import annotations

"""Compliance checks for DCWP licenses and Parks permits.

This module provides small, testable utilities to validate contractor licenses
and permit presence before approving items for the construction list. The
functions are intentionally lightweight wrappers so teams can plug in external
APIs (DCWP, Parks) or local caches as needed.
"""

from typing import Any


def _http_get(*args, **kwargs):
    """HTTP GET via governance.get so tests can monkeypatch the client."""
    from socrata_toolkit.governance import get

    return get(*args, **kwargs)


def check_dcwp_license(license_number: str, api_base: str | None = None) -> dict[str, Any]:
    """Verify basic contractor license metadata.

    This is a placeholder that demonstrates a simple HTTP call to a REST API.
    In production, use an authenticated, rate-limited client and cache results.
    Returns a dictionary with `valid` boolean and `details`.
    """
    if not api_base:
        # No remote API configured; fallback: return unknown status
        return {"valid": False, "details": "No DCWP API configured"}
    url = f"{api_base}/licenses/{license_number}"
    try:
        r = _http_get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {"valid": data.get("active", False), "details": data}
    except Exception as exc:
        return {"valid": False, "details": str(exc)}


def check_parks_permit(permit_number: str, api_base: str | None = None) -> dict[str, Any]:
    """Check Parks permit metadata.

    Placeholder behavior similar to `check_dcwp_license`.
    """
    if not api_base:
        return {"valid": False, "details": "No Parks API configured"}
    url = f"{api_base}/permits/{permit_number}"
    try:
        r = _http_get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        return {"valid": data.get("status") == "APPROVED", "details": data}
    except Exception as exc:
        return {"valid": False, "details": str(exc)}


def validate_contractor_for_list(contractor_id: str, license_number: str, dcwp_api: str | None = None, parks_api: str | None = None, parks_permit: str | None = None) -> dict[str, Any]:
    """Return a combined validation for contractor license and optional parks permit.

    Returns a small summary dict including `ok` boolean and `reasons` if any.
    """
    reasons = []
    lic = check_dcwp_license(license_number, api_base=dcwp_api)
    if not lic.get("valid"):
        reasons.append(f"DCWP license invalid: {lic.get('details')}")

    if parks_permit:
        pr = check_parks_permit(parks_permit, api_base=parks_api)
        if not pr.get("valid"):
            reasons.append(f"Parks permit invalid: {pr.get('details')}")

    return {"ok": len(reasons) == 0, "reasons": reasons}
