"""Tests for core analytics infrastructure — BaseSkill, AnalysisResult, and package structure."""

from __future__ import annotations

import pytest
from socrata_toolkit.analytics import BaseSkill, AnalysisResult

class MockSkill(BaseSkill):
    """A concrete implementation of BaseSkill for testing."""
    def run(self, **kwargs) -> AnalysisResult:
        return AnalysisResult(
            skill_name="MockSkill",
            success=True,
            data={"status": "complete"},
            metadata={"version": "1.0.0"}
        )

class TestAnalyticsInfrastructure:
    def test_package_is_importable(self):
        import socrata_toolkit.analytics
        assert socrata_toolkit.analytics.__name__ == "socrata_toolkit.analytics"

    def test_base_skill_is_abstract(self):
        with pytest.raises(TypeError):
            BaseSkill()

    def test_concrete_skill_execution(self):
        skill = MockSkill()
        result = skill.run()
        assert isinstance(result, AnalysisResult)
        assert result.skill_name == "MockSkill"
        assert result.success is True
        assert result.data["status"] == "complete"

    def test_analysis_result_serialization(self):
        result = AnalysisResult(
            skill_name="Test",
            success=True,
            data={"val": 1},
            metadata={"env": "prod"}
        )
        # Assuming we want a to_dict or similar for unified reporting
        d = result.to_dict()
        assert d["skill_name"] == "Test"
        assert d["success"] is True
        assert d["data"]["val"] == 1
        assert "timestamp" in d
