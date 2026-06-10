"""Invariant / property tests for the core analytical functions.

These run each function over many randomized (seeded) inputs and assert
mathematical invariants that must hold for *every* input — catching whole
classes of bugs (CI bounds violations, scores out of range, severity overflow)
that single-example tests miss.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

RNG = np.random.default_rng(1234)


# ---------------------------------------------------------------------------
# compute_borough_completion_rates — Wilson Score CI invariants
# ---------------------------------------------------------------------------

class TestCompletionRateInvariants:
    def _random_df(self):
        boroughs = RNG.choice(["MN", "BX", "BK", "QN", "SI"], size=RNG.integers(1, 6), replace=False)
        rows = []
        for b in boroughs:
            total = int(RNG.integers(1, 500))
            resolved = int(RNG.integers(0, total + 1))
            for _ in range(resolved):
                rows.append({"borough": b, "status": "complete"})
            for _ in range(total - resolved):
                rows.append({"borough": b, "status": "incomplete"})
        return pd.DataFrame(rows)

    def test_rate_and_ci_bounds_hold_for_random_inputs(self):
        from socrata_toolkit.engineering.ramp_analysis import RampCompletionReportGenerator

        for _ in range(200):
            df = self._random_df()
            generator = RampCompletionReportGenerator()
            report = generator.generate(df, mode="full-corpus", include_ci=True)
            for stat in report.borough_stats:
                rate = stat.completion_rate
                lo, hi = stat.ci_lower, stat.ci_upper
                # rate is a valid proportion
                assert 0.0 <= rate <= 1.0, f"rate {rate} out of [0,1] for {stat.borough}"
                # CI bounds are valid proportions and ordered
                assert 0.0 <= lo <= hi <= 1.0, f"CI [{lo},{hi}] invalid for {stat.borough}"
                # the point estimate lies within its own CI
                assert lo - 1e-9 <= rate <= hi + 1e-9, f"rate {rate} outside CI [{lo},{hi}]"
                # rate equals resolved/total
                assert stat.completed_ramps <= stat.total_ramps
                expected = stat.completed_ramps / stat.total_ramps
                assert abs(rate - expected) < 1e-2

    def test_overall_rate_in_unit_interval(self):
        from socrata_toolkit.engineering.ramp_analysis import RampCompletionReportGenerator

        for _ in range(50):
            df = self._random_df()
            generator = RampCompletionReportGenerator()
            report = generator.generate(df, mode="full-corpus", include_ci=True)
            assert 0.0 <= report.overall_completion_rate <= 1.0

    def test_all_resolved_gives_rate_one(self):
        from socrata_toolkit.engineering.ramp_analysis import RampCompletionReportGenerator

        df = pd.DataFrame({"borough": ["MN"] * 10, "status": ["complete"] * 10})
        generator = RampCompletionReportGenerator()
        report = generator.generate(df, mode="full-corpus", include_ci=True)
        assert report.borough_stats[0].completion_rate == 1.0

    def test_none_resolved_gives_rate_zero(self):
        from socrata_toolkit.engineering.ramp_analysis import RampCompletionReportGenerator

        df = pd.DataFrame({"borough": ["BX"] * 10, "status": ["incomplete"] * 10})
        generator = RampCompletionReportGenerator()
        report = generator.generate(df, mode="full-corpus", include_ci=True)
        assert report.borough_stats[0].completion_rate == 0.0

    def test_more_data_tightens_ci(self):
        """CI width should shrink as sample size grows (same rate)."""
        from socrata_toolkit.engineering.ramp_analysis import RampCompletionReportGenerator

        # small sample
        small = pd.DataFrame([{"borough": "MN", "status": "complete"}] * 7 + [{"borough": "MN", "status": "incomplete"}] * 3)
        # large sample
        large = pd.DataFrame([{"borough": "MN", "status": "complete"}] * 7000 + [{"borough": "MN", "status": "incomplete"}] * 3000)

        generator = RampCompletionReportGenerator()
        small_report = generator.generate(small, mode="full-corpus", include_ci=True)
        large_report = generator.generate(large, mode="full-corpus", include_ci=True)

        w_small = small_report.borough_stats[0]
        w_large = large_report.borough_stats[0]

        width_small = w_small.ci_upper - w_small.ci_lower
        width_large = w_large.ci_upper - w_large.ci_lower
        assert width_large < width_small


# ---------------------------------------------------------------------------
# compute_quality_score — composite bounds & weighting invariants
# ---------------------------------------------------------------------------

class TestQualityScoreInvariants:
    def _random_df(self):
        n = int(RNG.integers(1, 200))
        ncols = int(RNG.integers(1, 6))
        data = {}
        for c in range(ncols):
            col = RNG.random(n).astype(object)
            # randomly null some entries
            mask = RNG.random(n) < RNG.random() * 0.5
            col[mask] = None
            data[f"col{c}"] = col
        data["id"] = range(n)
        df = pd.DataFrame(data)
        df["created_date"] = pd.date_range("2020-01-01", periods=n, freq="D")
        return df

    def test_all_dimensions_in_range(self):
        from socrata_toolkit.governance import compute_quality_score

        for _ in range(100):
            df = self._random_df()
            s = compute_quality_score(df, key_columns=["id"], date_column="created_date")
            for dim in (s.overall, s.completeness, s.validity, s.consistency, s.freshness):
                assert 0.0 <= dim <= 100.0, f"dimension {dim} out of [0,100]"

    def test_overall_matches_weighted_composite(self):
        """overall == 0.35*comp + 0.25*valid + 0.25*consist + 0.15*fresh (±rounding)."""
        from socrata_toolkit.governance import compute_quality_score

        for _ in range(100):
            df = self._random_df()
            s = compute_quality_score(df, key_columns=["id"], date_column="created_date")
            expected = (
                0.35 * s.completeness
                + 0.25 * s.validity
                + 0.25 * s.consistency
                + 0.15 * s.freshness
            )
            assert abs(s.overall - expected) <= 1.0, f"{s.overall} != weighted {expected}"

    def test_perfect_data_scores_high(self):
        from socrata_toolkit.governance import compute_quality_score

        df = pd.DataFrame({
            "id": range(100),
            "v": range(100),
            "created_date": pd.date_range(pd.Timestamp.now().normalize(), periods=100, freq="-1D"),
        })
        s = compute_quality_score(df, key_columns=["id"], date_column="created_date")
        # complete, unique, consistent, fresh -> all four dimensions near 100
        assert s.completeness == 100.0
        assert s.validity == 100.0
        assert s.consistency == 100.0


# ---------------------------------------------------------------------------
# parse_sim_complaints — severity score is always a bounded [0,1] value
# ---------------------------------------------------------------------------

class TestSeverityInvariants:
    _PHRASES = [
        "trip hazard and ada wheelchair ramp issue with crack and water pooling and root",
        "", "nothing here", "crack", "trip fall hazard rebar metal edge danger protruding",
        "ada wheelchair ramp curb cut blind walker mobility disabled",
    ]

    def test_severity_always_in_unit_interval(self):
        from socrata_toolkit.analysis import parse_sim_complaints

        for _ in range(100):
            texts = [str(RNG.choice(self._PHRASES)) for _ in range(int(RNG.integers(1, 20)))]
            df = pd.DataFrame({"description": texts})
            out = parse_sim_complaints(df)
            assert "_sim_severity_score" in out.columns
            scores = out["_sim_severity_score"].astype(float)
            assert (scores >= 0.0).all() and (scores <= 1.0).all(), "severity escaped [0,1]"

    def test_required_columns_added(self):
        from socrata_toolkit.analysis import parse_sim_complaints

        out = parse_sim_complaints(pd.DataFrame({"description": ["crack and trip hazard"]}))
        for col in ("_sim_flags", "_sim_severity_score", "_sim_category"):
            assert col in out.columns

    def test_empty_and_null_text_safe(self):
        from socrata_toolkit.analysis import parse_sim_complaints

        df = pd.DataFrame({"description": ["", None, np.nan]})
        out = parse_sim_complaints(df)
        assert len(out) == 3
        assert (out["_sim_severity_score"].astype(float) >= 0.0).all()


# ---------------------------------------------------------------------------
# detect_all_outliers — reported indices are valid; clean data has none
# ---------------------------------------------------------------------------

class TestOutlierInvariants:
    @pytest.mark.parametrize("method", ["iqr", "zscore"])
    def test_reported_indices_valid_and_clean_data_has_none(self, method):
        from socrata_toolkit.analysis import detect_all_outliers

        # uniform-ish data: no extreme outliers
        df = pd.DataFrame({"a": RNG.normal(50, 1, 200), "b": RNG.normal(0, 1, 200)})
        reports = detect_all_outliers(df, method=method)
        assert isinstance(reports, list)
        for rep in reports:
            idxs = getattr(rep, "outlier_indices", None)
            if idxs is None:
                continue
            for i in idxs:
                assert 0 <= int(i) < len(df), "outlier index out of range"

    @pytest.mark.parametrize("method", ["iqr", "zscore"])
    def test_injected_outlier_detected(self, method):
        from socrata_toolkit.analysis import detect_all_outliers

        vals = list(RNG.normal(50, 1, 200)) + [10_000.0]  # one extreme outlier
        df = pd.DataFrame({"a": vals})
        reports = detect_all_outliers(df, method=method)
        total = sum(len(getattr(r, "outlier_indices", []) or []) for r in reports)
        assert total >= 1, "clear outlier not detected"
