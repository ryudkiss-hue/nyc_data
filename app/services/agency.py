"""Agency operations: packs, publish, health, completeness."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
_PACK_ROOT = _REPO / "outputs" / "analyst_pack"
_PUBLISH_EXAMPLE = _REPO / "config" / "publish_profile.example.yaml"
_ANALYST_EXAMPLE = _REPO / "config" / "analyst_profile.example.yaml"
_COMPLETENESS = _REPO / "docs" / "COMPLETENESS.md"
_INGEST_LOG = _REPO / "outputs" / "logs" / "ingest.jsonl"


def repo_root() -> Path:
    return _REPO


def list_pack_dirs(limit: int = 20) -> list[Path]:
    if not _PACK_ROOT.exists():
        return []
    dirs = [p for p in _PACK_ROOT.iterdir() if p.is_dir()]
    dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return dirs[:limit]


def latest_pack_dir() -> Path | None:
    packs = list_pack_dirs(1)
    return packs[0] if packs else None


def run_analyst_pack(*, profile_path: str | Path, offline: bool = False) -> dict[str, Any]:
    from socrata_toolkit.analyst.workflow import run_analyst_pack as _run

    result = _run(str(profile_path), offline=offline, dry_run=False)
    return {
        "pack_dir": str(result.pack_dir),
        "run_date": result.run_date,
        "profile_name": result.profile_name,
        "warnings": list(result.warnings),
        "artifacts": dict(result.artifacts),
        "partial_failures": list(result.partial_failures),
    }


def publish_pack_ui(
    *,
    pack_dir: str | Path,
    profile_path: str | Path,
    dry_run: bool = True,
) -> dict[str, Any]:
    from socrata_toolkit.analyst.publish import publish_pack

    report = publish_pack(pack_dir=pack_dir, profile_path=profile_path, dry_run=dry_run)
    return report.to_dict()


def load_completeness_items() -> list[dict[str, str]]:
    """Parse COMPLETENESS.md table rows into checklist items."""
    if not _COMPLETENESS.exists():
        return []
    text = _COMPLETENESS.read_text(encoding="utf-8")
    items: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.strip().startswith("|") or "---" in line or "Item" in line:
            continue
        parts = [c.strip() for c in line.split("|") if c.strip()]
        if len(parts) >= 3 and parts[0] not in ("Item", "------"):
            items.append({"item": parts[0], "verify": parts[2] if len(parts) > 2 else ""})
    return items


def tail_ingest_log(lines: int = 30) -> list[dict[str, Any]]:
    if not _INGEST_LOG.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in _INGEST_LOG.read_text(encoding="utf-8", errors="ignore").splitlines()[-lines:]:
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return rows


def system_health() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "analyst_profile",
            "ok": (_REPO / "config" / "analyst_profile.yaml").exists() or _ANALYST_EXAMPLE.exists(),
        }
    )
    checks.append({"name": "publish_profile", "ok": _PUBLISH_EXAMPLE.exists()})
    checks.append({"name": "datasets_registry", "ok": (_REPO / "config" / "datasets.yaml").exists()})
    checks.append({"name": "mission_entry", "ok": (_REPO / "main.py").exists()})
    try:
        import sodapy  # noqa: F401

        checks.append({"name": "sodapy", "ok": True})
    except ImportError:
        checks.append({"name": "sodapy", "ok": False, "fix": 'pip install -e ".[mission]"'})
    try:
        import geopandas  # noqa: F401

        checks.append({"name": "geopandas", "ok": True})
    except ImportError:
        checks.append({"name": "geopandas", "ok": False, "fix": 'pip install -e ".[mission]"'})
    packs = list_pack_dirs(1)
    checks.append({"name": "latest_analyst_pack", "ok": bool(packs), "detail": str(packs[0]) if packs else ""})
    ok_count = sum(1 for c in checks if c["ok"])
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "score": round(100.0 * ok_count / len(checks), 1) if checks else 0,
    }


def onboarding_steps() -> list[str]:
    return [
        "Install: pip install -e \".[mission]\"",
        "Configure: copy config/analyst_profile.example.yaml → analyst_profile.yaml",
        "Token: set SOCRATA_APP_TOKEN in .env (or use demo mode)",
        "Run pack: sidebar → Run Analyst Pack, or scripts/nightly_analyst_sync.ps1",
        "Review workflows: QA → Spatial → Contract → Productivity",
        "Publish: Publish & Pack page → dry-run first",
        "Sign-off: Settings → Completeness checklist",
    ]
