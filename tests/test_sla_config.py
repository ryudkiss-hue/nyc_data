"""Tests to ensure SLA thresholds stay consistent and synchronized."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


class TestSLAConfig:
    """SLA thresholds are single source of truth for freshness monitoring."""

    @pytest.fixture
    def sla_config(self) -> dict:
        """Load SLA config from JSON file."""
        config_path = Path(__file__).parent.parent / "data" / "sla_config.json"
        assert (
            config_path.exists()
        ), f"SLA config not found at {config_path}. Required for tests."
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)

    def test_sla_config_is_valid_json(self, sla_config):
        """SLA config should be valid JSON with expected structure."""
        assert isinstance(sla_config, dict)
        assert "sla_thresholds" in sla_config
        assert "HIGH" in sla_config["sla_thresholds"]
        assert "MEDIUM" in sla_config["sla_thresholds"]
        assert "LOW" in sla_config["sla_thresholds"]

    def test_sla_high_threshold_is_14(self, sla_config):
        """HIGH SLA threshold must be 14 days (documented in CLAUDE.md)."""
        high_days = sla_config["sla_thresholds"]["HIGH"]["days"]
        assert (
            high_days == 14
        ), f"HIGH SLA changed to {high_days}. Update CLAUDE.md if intentional."

    def test_sla_medium_threshold_is_30(self, sla_config):
        """MEDIUM SLA threshold must be 30 days (documented in CLAUDE.md)."""
        medium_days = sla_config["sla_thresholds"]["MEDIUM"]["days"]
        assert (
            medium_days == 30
        ), f"MEDIUM SLA changed to {medium_days}. Update CLAUDE.md if intentional."

    def test_sla_low_threshold_is_60(self, sla_config):
        """LOW SLA threshold must be 60 days (documented in CLAUDE.md)."""
        low_days = sla_config["sla_thresholds"]["LOW"]["days"]
        assert (
            low_days == 60
        ), f"LOW SLA changed to {low_days}. Update CLAUDE.md if intentional."

    def test_sla_thresholds_are_ordered(self, sla_config):
        """SLA thresholds should be ordered: HIGH < MEDIUM < LOW."""
        high = sla_config["sla_thresholds"]["HIGH"]["days"]
        medium = sla_config["sla_thresholds"]["MEDIUM"]["days"]
        low = sla_config["sla_thresholds"]["LOW"]["days"]

        assert (
            high < medium < low
        ), f"SLA ordering incorrect: HIGH={high}, MEDIUM={medium}, LOW={low}"

    def test_sla_thresholds_are_positive(self, sla_config):
        """All SLA thresholds must be positive integers."""
        for level, config in sla_config["sla_thresholds"].items():
            days = config["days"]
            assert isinstance(days, int), f"{level} SLA days should be int, got {type(days)}"
            assert days > 0, f"{level} SLA days must be positive, got {days}"

    def test_sla_config_has_documentation(self, sla_config):
        """SLA config should document where it's used."""
        assert "documentation" in sla_config
        assert "CLAUDE.md" in sla_config["documentation"]

    def test_sla_config_has_note_about_sync(self, sla_config):
        """SLA config should note the need to sync with docs."""
        assert "note" in sla_config
        assert "CLAUDE.md" in sla_config["note"]
        assert "test" in sla_config["note"].lower()

    def test_sla_config_matches_claude_md_reference(self):
        """SLA values in CLAUDE.md should match config file."""
        from pathlib import Path

        claude_md_path = Path(__file__).parent.parent / "CLAUDE.md"
        with open(claude_md_path, encoding="utf-8") as f:
            content = f.read()

        # Check that CLAUDE.md references the correct SLA values
        assert "HIGH=14d" in content or "HIGH: 14" in content
        assert "MED=30d" in content or "MEDIUM: 30" in content
        assert "LOW=60d" in content or "LOW: 60" in content
