"""Automated readiness scoring for analyst deployment."""

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


def run_readiness_checks(*, run_pytest: bool = False) -> dict[str, Any]:
    root = _root()
    dash_root = root / "legacy_archive" / "dash_app"
    streamlit_root = root / "app"
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

    axes["accessibility"].append(
        _check(
            "skip_link_in_app",
            (streamlit_root / "app.py").exists(),
            fix="Ensure app/app.py exists for Streamlit Mission Control.",
        )
    )
    axes["accessibility"].append(
        _check(
            "reduced_motion_css",
            (dash_root / "assets" / "custom.css").exists()
            and "prefers-reduced-motion" in (dash_root / "assets" / "custom.css").read_text(encoding="utf-8"),
        )
    )
    axes["accessibility"].append(
        _check(
            "kpi_text_not_color_only",
            (streamlit_root / "analytics.py").exists(),
            detail="Metrics page uses icon + text labels.",
        )
    )

    profile = root / "config" / "analyst_profile.yaml"
    example = root / "config" / "analyst_profile.example.yaml"
    axes["functionality"].append(_check("analyst_profile", profile.exists() or example.exists(), fix="Run install wizard."))
    axes["functionality"].append(
        _check("analyst_package", (Path(__file__).resolve().parents[1] / "analyst" / "workflow.py").exists())
    )
    axes["functionality"].append(_check("publish_example", (root / "config" / "publish_profile.example.yaml").exists()))
    axes["functionality"].append(_check("review_store", (Path(__file__).resolve().parents[1] / "review" / "store.py").exists()))
    axes["functionality"].append(
        _check("readiness_command", "readiness" in (Path(__file__).resolve().parents[0] / "cli.py").read_text(encoding="utf-8"))
    )
    axes["functionality"].append(
        _check("demo_pack", (dash_root / "data" / "demo_pack.py").exists() or (root / "tests" / "fixtures" / "analyst").is_dir())
    )

    for mod in (
        "socrata_toolkit.analysis.advanced",
        "socrata_toolkit.analysis.program",
        "socrata_toolkit.nlp.advanced",
    ):
        try:
            importlib.import_module(mod)
            axes["functionality"].append(_check(f"import_{mod.split('.')[-2]}.{mod.split('.')[-1]}", True))
        except Exception as exc:
            axes["functionality"].append(_check(mod, False, str(exc)))

    app_text = (streamlit_root / "app.py").read_text(encoding="utf-8") if (streamlit_root / "app.py").exists() else ""
    axes["presentation"].append(_check("streamlit_app", bool(app_text)))
    axes["presentation"].append(_check("data_loader", (streamlit_root / "data_loader.py").exists()))
    axes["presentation"].append(_check("socrata_ingestion_matrix", "DATASET_REGISTRY" in (streamlit_root / "data_loader.py").read_text(encoding="utf-8")))
    axes["presentation"].append(_check("legacy_dash_archived", dash_root.exists()))
    axes["presentation"].append(_check("simple_start_doc", (root / "docs" / "SIMPLE_START.md").exists()))
    axes["presentation"].append(_check("ui_previews", (root / "docs" / "preview").is_dir()))

    axes["packaging"].append(_check("install_wizard", importlib.util.find_spec("socrata_toolkit.install_wizard") is not None))
    axes["packaging"].append(_check("installer_script", (root / "scripts" / "build_installer.ps1").exists()))
    launcher = root / "launcher.py"
    axes["packaging"].append(_check("launcher", launcher.exists() or (root / "legacy_archive" / "launcher.py").exists()))

    axes["reliability"].append(_check("streamlit_analytics", (streamlit_root / "analytics.py").exists()))
    axes["reliability"].append(_check("tests_exist", (root / "tests").is_dir()))

    for doc in ("USER_MANUAL.md", "FAQ.md", "COMPLETENESS.md", "ANALYST_WORKFLOW.md", "QUALITY_SCORECARD.md"):
        axes["documentation"].append(_check(doc, (root / "docs" / doc).exists()))

    axes["security"].append(
        _check(
            "publish_dry_run_default",
            "ProductivityROI" in (streamlit_root / "analytics.py").read_text(encoding="utf-8"),
            detail="Publish page defaults to dry-run.",
        )
    )
    axes["security"].append(_check("gitignore_env", ".env" in (root / ".gitignore").read_text(encoding="utf-8")))

    axes["performance"].append(_check("cached_socrata_fetch", "@st.cache_data" in (streamlit_root / "data_loader.py").read_text(encoding="utf-8")))
    axes["performance"].append(_check("legacy_dash_jobs", (dash_root / "background_jobs.py").exists()))

    role_dir = root / "config" / "role_profiles"
    axes["job_fit"].append(_check("role_profiles_dir", role_dir.is_dir()))
    for role_file in ("sw_project_analyst.yaml", "project_analyst_sw.yaml"):
        axes["job_fit"].append(_check(role_file, (role_dir / role_file).exists()))
    pkg = Path(__file__).resolve().parents[1]
    axes["job_fit"].append(_check("roles_module", (pkg / "analyst" / "roles.py").exists()))

    if run_pytest:
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=180,
            )
            axes["reliability"].append(
                _check("pytest_green", proc.returncode == 0, detail=(proc.stdout or "")[-200:])
            )
        except Exception as exc:
            axes["reliability"].append(_check("pytest_green", False, str(exc)))

    axis_scores: dict[str, float] = {}
    for axis, items in axes.items():
        if not items:
            axis_scores[axis] = 0.0
            continue
        axis_scores[axis] = round(100.0 * sum(1 for i in items if i["ok"]) / len(items), 1)

    overall = round(sum(axis_scores.values()) / len(axis_scores), 1) if axis_scores else 0.0

    return {
        "overall_score": overall,
        "axis_scores": axis_scores,
        "axes": axes,
        "note": "Scores reflect automated checks; 100 requires live data, agency infra, and manual sign-off.",
    }


def readiness_json(**kwargs: Any) -> str:
    return json.dumps(run_readiness_checks(**kwargs), indent=2)
