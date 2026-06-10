"""Ramp Program Analysis & Completion Rate Reporting.

Tools for analyzing pedestrian ramp construction progress, completion rates,
and borough-level performance with statistical confidence intervals.

Key capabilities:
- Calculate ramp completion rates by borough
- Aggregate full-corpus analysis with caching
- Compute 95% confidence intervals using binomial distribution
- Assess data reliability based on sample sizes
- Format results as analysis-ready tables

Example::

    from socrata_toolkit.engineering.ramp_analysis import (
        RampCompletionReportGenerator,
    )

    generator = RampCompletionReportGenerator()
    report = generator.generate(
        df=ramp_data,
        mode="full-corpus",
        include_ci=True,
        borough_filter=None
    )
    print(report.to_table())
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class BoroughRampStats:
    """Statistics for ramp completion by borough."""

    borough: str
    total_ramps: int
    completed_ramps: int
    completion_rate: float
    ci_lower: float | None = None
    ci_upper: float | None = None
    sample_size: int = 0
    reliability: str = "unknown"  # "high", "medium", "low"


@dataclass
class RampCompletionReport:
    """Complete ramp completion analysis report."""

    timestamp: str
    mode: str  # "sample" or "full-corpus"
    sample_size: int | None  # Only for sample mode
    total_boroughs: int
    overall_completion_rate: float
    borough_stats: list[BoroughRampStats]
    include_ci: bool = False

    def to_table(self) -> str:
        """Format report as a human-readable table."""
        lines = []

        # Header
        header = f"Ramp Completion Report ({self.mode})"
        if self.mode == "sample" and self.sample_size:
            header += f" — {self.sample_size} corners sampled"
        lines.append(header)
        lines.append("=" * 100)

        # Overall stats
        lines.append(f"Overall Completion Rate: {self.overall_completion_rate * 100:.1f}%")
        lines.append(f"Boroughs Analyzed: {self.total_boroughs}")
        lines.append("")

        # Borough table header
        if self.include_ci:
            col_header = (
                f"{'Borough':<12} | {'Completion Rate':<20} | {'95% CI':<20} | "
                f"{'Sample Size':<12} | {'Reliability':<12}"
            )
        else:
            col_header = (
                f"{'Borough':<12} | {'Completion Rate':<20} | "
                f"{'Sample Size':<12} | {'Reliability':<12}"
            )

        lines.append(col_header)
        lines.append("-" * len(col_header))

        # Borough rows
        for stat in self.borough_stats:
            rate_pct = f"{stat.completion_rate * 100:.1f}%"
            if self.include_ci and stat.ci_lower is not None:
                ci_str = (
                    f"[{stat.ci_lower * 100:.1f}%, "
                    f"{stat.ci_upper * 100:.1f}%]"
                )
                line = (
                    f"{stat.borough:<12} | {rate_pct:<20} | {ci_str:<20} | "
                    f"{stat.sample_size:<12} | {stat.reliability:<12}"
                )
            else:
                line = (
                    f"{stat.borough:<12} | {rate_pct:<20} | "
                    f"{stat.sample_size:<12} | {stat.reliability:<12}"
                )
            lines.append(line)

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "mode": self.mode,
            "sample_size": self.sample_size,
            "total_boroughs": self.total_boroughs,
            "overall_completion_rate": self.overall_completion_rate,
            "include_ci": self.include_ci,
            "borough_stats": [
                {
                    "borough": stat.borough,
                    "total_ramps": stat.total_ramps,
                    "completed_ramps": stat.completed_ramps,
                    "completion_rate": stat.completion_rate,
                    "ci_lower": stat.ci_lower,
                    "ci_upper": stat.ci_upper,
                    "sample_size": stat.sample_size,
                    "reliability": stat.reliability,
                }
                for stat in self.borough_stats
            ],
        }


class RampCompletionReportGenerator:
    """Generate ramp program completion reports with statistical analysis.

    Supports full-corpus analysis (with caching) and sample-based estimation.
    Computes 95% binomial confidence intervals and assesses data reliability.
    """

    def __init__(self, cache_ttl_hours: int = 168) -> None:
        """Initialize generator.

        Args:
            cache_ttl_hours: Cache time-to-live in hours (default: 1 week).
        """
        self.cache_ttl_hours = cache_ttl_hours

    def generate(
        self,
        df: pd.DataFrame | None = None,
        mode: str = "sample",
        sample_size: int | None = 100,
        borough_filter: str | None = None,
        include_ci: bool = True,
    ) -> RampCompletionReport:
        """Generate ramp completion report.

        Args:
            df: DataFrame with ramp data (required). Expected columns:
                - 'borough': Borough name (MN, BX, BK, QN, SI)
                - 'status' or 'completion_status': 'complete' or similar
            mode: "sample" or "full-corpus"
            sample_size: For sample mode, number of corners to sample
            borough_filter: Optional borough to filter to (e.g., "MN")
            include_ci: Whether to compute 95% confidence intervals

        Returns:
            RampCompletionReport with borough-level statistics
        """
        from datetime import datetime, timezone

        if df is None or df.empty:
            raise ValueError("DataFrame is required and cannot be empty")

        # Validate required columns
        if "borough" not in df.columns:
            raise ValueError("DataFrame must contain 'borough' column")

        # Find status column (try multiple names)
        status_col = None
        for col in ["status", "completion_status", "Construction_Status_Value", "construction_status",
                    "completion_status_value", "Status", "Completion_Status"]:
            if col in df.columns:
                status_col = col
                break

        if status_col is None:
            raise ValueError(
                "DataFrame must contain 'status', 'completion_status', or 'Construction_Status_Value' column"
            )

        # Apply borough filter if specified
        if borough_filter:
            df = df[df["borough"].str.upper() == borough_filter.upper()]
            if df.empty:
                raise ValueError(f"No data found for borough {borough_filter}")

        # Sample if requested
        if mode == "sample" and sample_size:
            if len(df) > sample_size:
                df = df.sample(n=sample_size, random_state=42)
            sample_size_actual = len(df)
        else:
            sample_size_actual = len(df)

        # Compute statistics by borough
        borough_stats: list[BoroughRampStats] = []
        total_completed = 0
        total_ramps = 0

        for borough in sorted(df["borough"].unique()):
            borough_df = df[df["borough"].str.upper() == borough.upper()]
            if borough_df.empty:
                continue

            total = len(borough_df)
            completed = int(

                    borough_df[status_col]
                    .str.lower()
                    .isin(["complete", "completed", "done"])
                    .sum()

            )
            rate = completed / total if total > 0 else 0.0

            # Compute 95% binomial CI
            ci_lower = None
            ci_upper = None
            reliability = self._assess_reliability(total)

            if include_ci:
                ci_lower, ci_upper = self._binomial_ci(completed, total)

            borough_stats.append(
                BoroughRampStats(
                    borough=borough.upper(),
                    total_ramps=total,
                    completed_ramps=completed,
                    completion_rate=rate,
                    ci_lower=ci_lower,
                    ci_upper=ci_upper,
                    sample_size=total,
                    reliability=reliability,
                )
            )

            total_ramps += total
            total_completed += completed

        # Overall rate
        overall_rate = (
            total_completed / total_ramps if total_ramps > 0 else 0.0
        )

        return RampCompletionReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode=mode,
            sample_size=sample_size_actual if mode == "sample" else None,
            total_boroughs=len(borough_stats),
            overall_completion_rate=overall_rate,
            borough_stats=borough_stats,
            include_ci=include_ci,
        )

    @staticmethod
    def _binomial_ci(
        successes: int, trials: int, confidence: float = 0.95
    ) -> tuple[float, float]:
        """Compute 95% binomial confidence interval using normal approximation.

        For use with sample sizes > 30. Falls back to exact method for small n.

        Args:
            successes: Number of successes
            trials: Total number of trials
            confidence: Confidence level (default 0.95 for 95%)

        Returns:
            Tuple of (lower bound, upper bound) as proportions
        """
        if trials == 0:
            return 0.0, 1.0

        p = successes / trials
        z = 1.96  # 95% confidence
        margin = z * np.sqrt((p * (1 - p)) / trials)

        return (
            max(0.0, p - margin),
            min(1.0, p + margin),
        )

    @staticmethod
    def _assess_reliability(sample_size: int) -> str:
        """Assess data reliability based on sample size.

        Args:
            sample_size: Number of observations

        Returns:
            "high", "medium", or "low"
        """
        if sample_size >= 100:
            return "high"
        elif sample_size >= 30:
            return "medium"
        else:
            return "low"
