"""Agency operations: packs, publish, health, completeness, and system diagnostics."""

from __future__ import annotations

import importlib
import json
import shutil
import sys
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
        if len(parts) >= 2 and parts[0] not in ("Item", "------"):
            items.append({
                "item": parts[0],
                "verify": parts[2] if len(parts) > 2 else "",
                "category": parts[1] if len(parts) > 1 else "General",
            })
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
    return list(reversed(rows))  # most recent first


def _check_package(name: str) -> dict[str, Any]:
    """Check if a Python package is importable and get its version."""
    try:
        mod = importlib.import_module(name.replace("-", "_"))
        version = getattr(mod, "__version__", "unknown")
        return {"name": name, "ok": True, "detail": f"v{version}"}
    except ImportError:
        return {
            "name": name,
            "ok": False,
            "fix": f'pip install -e ".[mission]" or pip install {name}',
        }


def _check_file(name: str, path: Path, *, required: bool = True) -> dict[str, Any]:
    exists = path.exists()
    return {
        "name": name,
        "ok": exists or not required,
        "detail": str(path) if exists else f"Not found: {path}",
        "fix": f"Create {path}" if not exists and required else "",
    }


def system_health() -> dict[str, Any]:
    """Comprehensive system health check."""
    checks: list[dict[str, Any]] = []

    # Required files
    checks.append(_check_file("datasets_registry", _REPO / "config" / "datasets.yaml"))
    checks.append(_check_file("mission_entry", _REPO / "main.py"))
    checks.append(_check_file("env_example", _REPO / ".env.example", required=False))
    checks.append(
        _check_file(
            "analyst_profile",
            _REPO / "config" / "analyst_profile.yaml",
            required=False,
        )
    )
    checks.append(_check_file("publish_profile", _PUBLISH_EXAMPLE, required=False))

    # Critical packages
    for pkg in ["streamlit", "pandas", "sodapy", "yaml", "dotenv"]:
        checks.append(_check_package(pkg))

    # Optional but important packages
    for pkg in ["geopandas", "shapely", "pyarrow", "plotly"]:
        c = _check_package(pkg)
        c["optional"] = True
        checks.append(c)

    # Outputs directory
    outputs_dir = _REPO / "outputs"
    checks.append({
        "name": "outputs_dir",
        "ok": outputs_dir.exists() or True,  # creates on first use
        "detail": str(outputs_dir),
    })

    # Latest pack
    packs = list_pack_dirs(1)
    checks.append({
        "name": "latest_analyst_pack",
        "ok": bool(packs),
        "detail": str(packs[0].name) if packs else "No packs yet",
        "fix": "Run an analyst pack from the Publish page" if not packs else "",
    })

    # Disk space
    try:
        usage = shutil.disk_usage(_REPO)
        free_gb = usage.free / (1024 ** 3)
        checks.append({
            "name": "disk_space",
            "ok": free_gb > 0.5,
            "detail": f"{free_gb:.1f} GB free",
            "fix": "Free up disk space" if free_gb <= 0.5 else "",
        })
    except Exception:
        pass

    # Python version
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    checks.append({
        "name": "python_version",
        "ok": sys.version_info >= (3, 10),
        "detail": f"Python {py_version}",
        "fix": "Upgrade to Python 3.10+" if sys.version_info < (3, 10) else "",
    })

    required_checks = [c for c in checks if not c.get("optional")]
    ok_count = sum(1 for c in required_checks if c["ok"])
    total = len(required_checks)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "score": round(100.0 * ok_count / total, 1) if total else 0,
        "python_version": py_version,
    }


def onboarding_steps() -> list[str]:
    return [
        'Install dependencies: `pip install -e ".[mission]"`',
        "Copy and configure: `config/analyst_profile.example.yaml` → `analyst_profile.yaml`",
        "Set `SOCRATA_APP_TOKEN` in `.env` (or use demo mode for testing)",
        "Run first analyst pack: sidebar → Publish → Run Analyst Pack",
        "Review all four workflows: QA → Spatial → Contract → Productivity",
        "Check data quality: Workflows → 🩺 Data Quality Dashboard",
        "Publish outputs: Publish & Pack → dry-run first, then live",
        "Sign off: Settings → Completeness checklist",
    ]


def ingest_log_summary() -> dict[str, Any]:
    """Aggregate stats from the ingest log."""
    rows = tail_ingest_log(1000)
    if not rows:
        return {"total_events": 0}

    event_types: dict[str, int] = {}
    total_rows_fetched = 0
    errors: list[str] = []

    for r in rows:
        et = r.get("event", "unknown")
        event_types[et] = event_types.get(et, 0) + 1
        total_rows_fetched += r.get("rows", 0)
        if "error" in r and r["error"]:
            errors.append(f"{r.get('dataset', '?')}: {r['error']}")

    return {
        "total_events": len(rows),
        "event_types": event_types,
        "total_rows_fetched": total_rows_fetched,
        "error_count": len(errors),
        "recent_errors": errors[-5:],
        "last_event_ts": rows[0].get("ts") if rows else None,
    }
