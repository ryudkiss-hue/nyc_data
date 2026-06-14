"""Agency service layer tests."""

from __future__ import annotations

from pathlib import Path

from app.services import agency


def test_repo_root_exists():
    root = agency.repo_root()
    assert (root / "app" / "main.py").exists()
    assert (root / "config" / "datasets.yaml").exists()

def test_completeness_items_parsed():
    items = agency.load_completeness_items()
    assert len(items) >= 3

def test_system_health_structure():
    health = agency.system_health()
    assert "score" in health
    assert "checks" in health
    assert len(health["checks"]) >= 5

def test_onboarding_steps():
    steps = agency.onboarding_steps()
    assert len(steps) >= 5

def test_publish_dry_run_missing_pack(tmp_path: Path):
    """Dry-run publish against example profile should not require live destinations."""
    root = agency.repo_root()
    example = root / "config" / "publish_profile.example.yaml"
    if not example.exists():
        return
    pack = tmp_path / "demo_pack"
    pack.mkdir()
    (pack / "manifest.json").write_text('{"run_date":"2099-01-01"}', encoding="utf-8")
    (pack / "executive_summary.md").write_text("# Demo", encoding="utf-8")
    report = agency.publish_pack_ui(pack_dir=pack, profile_path=example, dry_run=True)
    assert report["dry_run"] is True
    assert "actions" in report
