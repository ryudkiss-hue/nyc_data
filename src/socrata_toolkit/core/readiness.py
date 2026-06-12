"""Automated readiness scoring for agency-grade Mission Control deployment."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _root() -> Path:
    return Path(__file__).resolve().parents[3]

def _check(name: str, ok: bool, detail: str = "", fix: str = "") -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail, "fix": fix}

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""

def run_readiness_checks(*, run_pytest: bool = False) -> dict[str, Any]:
    root = _root()
    app_root = root / "app"
    axes: dict[str, list[dict[str, Any]]] = {
        "accessibility": [],
        "functionality": [],
        "presentation": [],
        "packaging": [],
        "reliability": [],
        "documentation": [],
        "security": [],
        "performance": [],
        "job_fit": [],
    }

    spa_html = app_root / "static" / "mission_control_v2.html"
    spa_text = _read(spa_html)
    sidecar_text = _read(app_root / "sidecar_api.py")

    axes["accessibility"].append(_check("spa_entry", spa_html.exists(), detail="SPA HTML entry point."))
    axes["accessibility"].append(
        _check("skip_link", "skip-to-content" in spa_text or "mc-skip" in spa_text,
               detail="Keyboard skip to main content.")
    )
    axes["accessibility"].append(
        _check("reduced_motion", "prefers-reduced-motion" in spa_text)
    )
    axes["accessibility"].append(
        _check("aria_tablist", 'role="tablist"' in spa_text or "role=tablist" in spa_text)
    )
    axes["accessibility"].append(
        _check("aria_live_region", "aria-live" in spa_text)
    )

    profile = root / "config" / "analyst_profile.yaml"
    example = root / "config" / "analyst_profile.example.yaml"
    axes["functionality"].append(_check("analyst_profile", profile.exists() or example.exists()))
    axes["functionality"].append(
        _check("analyst_workflow", (Path(__file__).resolve().parents[1] / "analyst" / "workflow.py").exists())
    )
    axes["functionality"].append(_check("publish_module", (Path(__file__).resolve().parents[1] / "analyst" / "publish.py").exists()))
    axes["functionality"].append(_check("datasets_yaml", (root / "config" / "datasets.yaml").exists()))
    axes["functionality"].append(_check("sidecar_api", (app_root / "sidecar_api.py").exists()))
    axes["functionality"].append(_check("sidecar_health", "/health" in sidecar_text))

    for mod in (
        "socrata_toolkit.analysis.advanced",
        "socrata_toolkit.analysis.program",
        "socrata_toolkit.nlp.advanced",
    ):
        try:
            importlib.import_module(mod)
            axes["functionality"].append(_check(f"import_{mod.split('.')[-1]}", True))
        except Exception as exc:
            axes["functionality"].append(_check(mod, False, str(exc)))

    axes["presentation"].append(_check("spa_dark_theme", "bg-gray-900" in spa_text or "brand-" in spa_text))
    axes["presentation"].append(_check("multi_tab_nav", 'role="tablist"' in spa_text))
    axes["presentation"].append(_check("command_palette", "command-palette" in spa_text or "Ctrl+P" in spa_text))
    axes["presentation"].append(_check("mission_control_doc", (root / "docs" / "MISSION_CONTROL.md").exists()))
    axes["presentation"].append(_check("agency_runbook", (root / "docs" / "AGENCY_RUNBOOK.md").exists()))
    axes["presentation"].append(_check("faq_doc", (root / "docs" / "FAQ.md").exists()))
    axes["presentation"].append(_check("improvements_plan", (root / "docs" / "IMPROVEMENTS_PLAN.md").exists()))

    axes["packaging"].append(_check("docker_compose", (root / "docker-compose.yml").exists()))
    axes["packaging"].append(_check("build_unix_script", (root / "scripts" / "build_unix.sh").exists()))
    axes["packaging"].append(_check("electron_main", (root / "desktop" / "main.js").exists()))
    axes["packaging"].append(_check("electron_package", (root / "desktop" / "package.json").exists()))
    axes["packaging"].append(_check("install_wizard", importlib.util.find_spec("socrata_toolkit.install_wizard") is not None))
    axes["packaging"].append(_check("installer_script", (root / "scripts" / "build_installer.ps1").exists()))
    axes["packaging"].append(_check("launcher_shim", (root / "launcher.py").exists()))
    axes["packaging"].append(_check("dockerfile_mission", (root / "Dockerfile.mission").exists()))
    axes["packaging"].append(_check("nightly_sync_script", (root / "scripts" / "nightly_analyst_sync.ps1").exists()))

    axes["reliability"].append(_check("sidecar_tests", (root / "tests" / "test_sidecar_api.py").exists()))
    axes["reliability"].append(_check("fair_tests", (root / "tests" / "test_fair.py").exists()))
    axes["reliability"].append(_check("privacy_tests", (root / "tests" / "test_privacy.py").exists()))

    for doc in (
        "USER_MANUAL.md",
        "FAQ.md",
        "COMPLETENESS.md",
        "ANALYST_WORKFLOW.md",
        "QUALITY_SCORECARD.md",
        "MISSION_CONTROL.md",
        "AGENCY_RUNBOOK.md",
        "SIMPLE_START.md",
        "PUBLISHING.md",
    ):
        axes["documentation"].append(_check(doc, (root / "docs" / doc).exists()))

    axes["security"].append(_check("gitignore_env", ".env" in _read(root / ".gitignore")))
    axes["security"].append(
        _check("socrata_token_env", "SOCRATA_APP_TOKEN" in _read(root / ".env.example"))
    )
    axes["security"].append(
        _check("cors_localhost_only", "127.0.0.1" in sidecar_text and "allow_origin_regex" in sidecar_text)
    )
    axes["security"].append(
        _check("no_secrets_in_code", "SOCRATA_APP_TOKEN" not in sidecar_text)
    )

    axes["performance"].append(_check("spa_lru_cache", "mmcCachedFetch" in spa_text or "mmc_cache_" in spa_text))
    axes["performance"].append(_check("spa_virtual_table", "mmcVirtualTable" in spa_text))
    axes["performance"].append(_check("spa_web_worker", "Worker" in spa_text))
    axes["performance"].append(_check("spa_lazy_init", "mmcLazy" in spa_text))
    axes["performance"].append(_check("spa_infinite_scroll", "IntersectionObserver" in spa_text))

    role_dir = root / "config" / "role_profiles"
    axes["job_fit"].append(_check("role_profiles_dir", role_dir.is_dir()))
    for role_file in ("sw_project_analyst.yaml", "project_analyst_sw.yaml"):
        axes["job_fit"].append(_check(role_file, (role_dir / role_file).exists()))
    axes["job_fit"].append(
        _check("roles_module", (Path(__file__).resolve().parents[1] / "analyst" / "roles.py").exists())
    )
    axes["job_fit"].append(_check("completeness_checklist", (root / "docs" / "COMPLETENESS.md").exists()))

    if run_pytest:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no", "-m", "not legacy"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            axes["reliability"].append(
                _check("pytest_green", proc.returncode == 0, detail=(proc.stdout or "")[-300:])
            )
        except Exception as exc:
            axes["reliability"].append(_check("pytest_green", False, str(exc)))

    axis_scores: dict[str, float] = {}
    for axis, items in axes.items():
        axis_scores[axis] = round(100.0 * sum(1 for i in items if i["ok"]) / len(items), 1) if items else 0.0

    overall = round(sum(axis_scores.values()) / len(axis_scores), 1) if axis_scores else 0.0

    return {
        "overall_score": overall,
        "axis_scores": axis_scores,
        "axes": axes,
        "grade": "agency_ready" if overall >= 95 else ("production_candidate" if overall >= 85 else "in_progress"),
        "note": "Automated checks only; agency sign-off requires live data and COMPLETENESS checklist.",
    }

def readiness_json(**kwargs: Any) -> str:
    return json.dumps(run_readiness_checks(**kwargs), indent=2)
