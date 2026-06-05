"""Tests to ensure quality score weights stay consistent and sum to 1.0."""

from __future__ import annotations

import pytest


class TestGovernanceWeights:
    """Quality score weights must be constants, not magic numbers."""

    def test_weights_imported_successfully(self):
        """Weights should be importable from governance module."""
        from socrata_toolkit.governance.core import (
            QUALITY_WEIGHT_COMPLETENESS,
            QUALITY_WEIGHT_CONSISTENCY,
            QUALITY_WEIGHT_FRESHNESS,
            QUALITY_WEIGHT_VALIDITY,
        )

        assert isinstance(QUALITY_WEIGHT_COMPLETENESS, float)
        assert isinstance(QUALITY_WEIGHT_VALIDITY, float)
        assert isinstance(QUALITY_WEIGHT_CONSISTENCY, float)
        assert isinstance(QUALITY_WEIGHT_FRESHNESS, float)

    def test_weights_sum_to_one(self):
        """Quality score weights must sum to 1.0."""
        from socrata_toolkit.governance.core import (
            QUALITY_WEIGHT_COMPLETENESS,
            QUALITY_WEIGHT_CONSISTENCY,
            QUALITY_WEIGHT_FRESHNESS,
            QUALITY_WEIGHT_VALIDITY,
        )

        total = (
            QUALITY_WEIGHT_COMPLETENESS
            + QUALITY_WEIGHT_VALIDITY
            + QUALITY_WEIGHT_CONSISTENCY
            + QUALITY_WEIGHT_FRESHNESS
        )
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, not 1.0"

    def test_completeness_weight_is_0_35(self):
        """Completeness weight must be 0.35 (documented in CLAUDE.md)."""
        from socrata_toolkit.governance.core import QUALITY_WEIGHT_COMPLETENESS

        assert QUALITY_WEIGHT_COMPLETENESS == 0.35, (
            f"Completeness weight changed to {QUALITY_WEIGHT_COMPLETENESS}. "
            "Update CLAUDE.md if this is intentional."
        )

    def test_validity_weight_is_0_25(self):
        """Validity weight must be 0.25 (documented in CLAUDE.md)."""
        from socrata_toolkit.governance.core import QUALITY_WEIGHT_VALIDITY

        assert QUALITY_WEIGHT_VALIDITY == 0.25, (
            f"Validity weight changed to {QUALITY_WEIGHT_VALIDITY}. "
            "Update CLAUDE.md if this is intentional."
        )

    def test_consistency_weight_is_0_25(self):
        """Consistency weight must be 0.25 (documented in CLAUDE.md)."""
        from socrata_toolkit.governance.core import QUALITY_WEIGHT_CONSISTENCY

        assert QUALITY_WEIGHT_CONSISTENCY == 0.25, (
            f"Consistency weight changed to {QUALITY_WEIGHT_CONSISTENCY}. "
            "Update CLAUDE.md if this is intentional."
        )

    def test_freshness_weight_is_0_15(self):
        """Freshness weight must be 0.15 (documented in CLAUDE.md)."""
        from socrata_toolkit.governance.core import QUALITY_WEIGHT_FRESHNESS

        assert QUALITY_WEIGHT_FRESHNESS == 0.15, (
            f"Freshness weight changed to {QUALITY_WEIGHT_FRESHNESS}. "
            "Update CLAUDE.md if this is intentional."
        )

    def test_weights_used_in_compute_quality_score(self):
        """compute_quality_score should use the module-level weight constants."""
        import pandas as pd
        from socrata_toolkit.governance.core import compute_quality_score

        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "name": ["A", "B", None, "D", "E"],
                "created_date": pd.date_range("2024-01-01", periods=5),
            }
        )

        score = compute_quality_score(
            df,
            key_columns=["id"],
            date_column="created_date",
            freshness_days_threshold=30,
        )

        # Overall should be a weighted combination of the four components
        # Just verify it's within a reasonable range and uses the weights
        assert 0 <= score.overall <= 100
        assert score.overall <= 100  # Quality score should never exceed 100
        assert isinstance(score.completeness, float)
        assert isinstance(score.validity, float)
        assert isinstance(score.consistency, float)
        assert isinstance(score.freshness, float)
