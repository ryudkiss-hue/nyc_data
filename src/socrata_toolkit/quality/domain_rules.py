"""
Domain Validation Rules for NYC Sidewalk Data

Encodes NYC-specific business logic and domain assumptions as validation rules.
Rules validate material lifespan patterns, permit-inspection relationships,
borough coverage distributions, and other NYC DOT operational constraints.

Standards: Python 3.11+, full type hints, comprehensive docstrings
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class DomainRuleResult:
    """Result of a domain validation rule.

    Attributes:
        rule_name: Name of the rule
        status: PASS, WARNING, or FAIL
        rows_affected: Number of rows affected by the violation
        details: Detailed explanation of the result
        fix_recommendation: Suggested remediation (optional)
    """

    rule_name: str
    status: str  # "PASS", "WARNING", "FAIL"
    rows_affected: int
    details: str
    fix_recommendation: str | None = None

    def __repr__(self) -> str:
        """String representation."""
        return f"DomainRuleResult(rule={self.rule_name}, status={self.status}, affected={self.rows_affected})"

def validate_material_lifespan_rule(df: pd.DataFrame) -> DomainRuleResult:
    """
    Validate that concrete has longer average lifespan than asphalt.

    Domain rule: Concrete sidewalks have longer lifespans (15-20 years) than
    asphalt (10-12 years) based on NYC DOT historical experience.

    Args:
        df: DataFrame with columns: material_type, lifespan_years (or condition-based proxy)

    Returns:
        DomainRuleResult with status (PASS/FAIL), details, and fix recommendation
    """
    try:
        # Handle different column name variations
        lifespan_col = None
        for col in ["lifespan_years", "avg_lifespan", "lifespan", "age_years", "condition_score"]:
            if col in df.columns:
                lifespan_col = col
                break

        if lifespan_col is None:
            return DomainRuleResult(
                rule_name="material_lifespan_rule",
                status="WARNING",
                rows_affected=0,
                details="No lifespan/age column found (expected: lifespan_years, avg_lifespan, or similar)",
                fix_recommendation="Add a lifespan or age column to the dataset",
            )

        # Filter to concrete and asphalt
        df_materials = df[df["material_type"].isin(["concrete", "asphalt"])].copy()

        if df_materials.empty:
            return DomainRuleResult(
                rule_name="material_lifespan_rule",
                status="WARNING",
                rows_affected=0,
                details="No concrete or asphalt records found in dataset",
                fix_recommendation="Ensure dataset contains material_type column with concrete/asphalt values",
            )

        # Compute average lifespan by material
        # For condition-based proxies (where higher = better), invert the logic
        if lifespan_col == "condition_score":
            # Higher condition score = better condition = longer effective lifespan
            avg_concrete = df_materials[df_materials["material_type"] == "concrete"][
                lifespan_col
            ].mean()
            avg_asphalt = df_materials[df_materials["material_type"] == "asphalt"][
                lifespan_col
            ].mean()
        else:
            # Direct lifespan column
            avg_concrete = df_materials[df_materials["material_type"] == "concrete"][
                lifespan_col
            ].mean()
            avg_asphalt = df_materials[df_materials["material_type"] == "asphalt"][
                lifespan_col
            ].mean()

        # Handle NaN values
        if pd.isna(avg_concrete) or pd.isna(avg_asphalt):
            return DomainRuleResult(
                rule_name="material_lifespan_rule",
                status="WARNING",
                rows_affected=0,
                details=f"Missing data: concrete={avg_concrete}, asphalt={avg_asphalt}",
                fix_recommendation="Remove or impute null values in lifespan column",
            )

        # Validate rule: concrete > asphalt
        status = "PASS" if avg_concrete > avg_asphalt else "FAIL"

        # Count affected rows (rows where rule is violated)
        rows_affected = (
            0
            if status == "PASS"
            else len(
                df_materials[
                    (df_materials["material_type"] == "asphalt")
                    & (df_materials[lifespan_col] > avg_concrete)
                ]
            )
        )

        details = (
            f"Concrete avg: {avg_concrete:.1f}, Asphalt avg: {avg_asphalt:.1f} "
            f"(expect concrete > asphalt)"
        )

        fix_recommendation = (
            None
            if status == "PASS"
            else "Review asphalt records for incorrect material classification or anomalies"
        )

        return DomainRuleResult(
            rule_name="material_lifespan_rule",
            status=status,
            rows_affected=rows_affected,
            details=details,
            fix_recommendation=fix_recommendation,
        )

    except Exception as e:
        logger.error(f"Error in material_lifespan_rule: {e}", exc_info=True)
        return DomainRuleResult(
            rule_name="material_lifespan_rule",
            status="WARNING",
            rows_affected=0,
            details=f"Rule evaluation error: {str(e)}",
            fix_recommendation="Check dataset structure and column names",
        )

def validate_borough_coverage_distribution(df: pd.DataFrame) -> DomainRuleResult:
    """
    Validate borough distribution matches historical patterns.

    Domain rule: Manhattan should represent 35-50% of violations (historical
    data shows Manhattan is typically 35-50% due to high density and inspection
    frequency). Deviations outside 30-55% range indicate structural data
    collection changes.

    Args:
        df: DataFrame with 'borough' column

    Returns:
        DomainRuleResult with status PASS/WARNING/FAIL
    """
    try:
        if "borough" not in df.columns:
            return DomainRuleResult(
                rule_name="borough_coverage_distribution",
                status="WARNING",
                rows_affected=0,
                details="No 'borough' column found in dataset",
                fix_recommendation="Add borough column to dataset",
            )

        # Compute Manhattan percentage
        borough_dist = df["borough"].value_counts(normalize=True)
        manhattan_variants = ["MANHATTAN", "Manhattan", "MN", "M"]
        manhattan_pct = 0
        for variant in manhattan_variants:
            if variant in borough_dist.index:
                manhattan_pct = borough_dist[variant] * 100
                break

        # Determine status based on percentage
        if 35 <= manhattan_pct <= 50:
            status = "PASS"
        elif 30 <= manhattan_pct <= 55:
            status = "WARNING"
        else:
            status = "FAIL"

        # Count affected rows: those in "unexpected" boroughs
        rows_affected = 0
        if status == "FAIL":
            # Count non-Manhattan rows that are "unexpected"
            for variant in manhattan_variants:
                if variant in df["borough"].values:
                    manhattan_count = (df["borough"] == variant).sum()
                    expected_max = len(df) * 0.55
                    if manhattan_count < expected_max:
                        rows_affected = len(df) - manhattan_count
                    break

        details = f"Manhattan: {manhattan_pct:.1f}% (expect 35-50%, acceptable 30-55%)"

        fix_recommendation = None
        if status == "FAIL":
            fix_recommendation = (
                "Investigate potential data collection bias or schema changes. "
                "Manhattan coverage outside expected 30-55% range suggests structural data changes."
            )
        elif status == "WARNING":
            fix_recommendation = "Monitor Manhattan coverage trend; verify data collection consistency."

        return DomainRuleResult(
            rule_name="borough_coverage_distribution",
            status=status,
            rows_affected=rows_affected,
            details=details,
            fix_recommendation=fix_recommendation,
        )

    except Exception as e:
        logger.error(f"Error in borough_coverage_distribution: {e}", exc_info=True)
        return DomainRuleResult(
            rule_name="borough_coverage_distribution",
            status="WARNING",
            rows_affected=0,
            details=f"Rule evaluation error: {str(e)}",
            fix_recommendation="Check borough column format and values",
        )

def validate_permit_inspection_relationship(
    permits_df: pd.DataFrame, inspections_df: pd.DataFrame
) -> DomainRuleResult:
    """
    Validate spatial and temporal alignment between permits and inspections.

    Domain rule: Inspections should occur within permit timeline and spatial
    proximity. This rule detects misaligned inspection/permit data.

    Args:
        permits_df: DataFrame with columns: start_date, end_date, latitude, longitude, borough
        inspections_df: DataFrame with columns: inspection_date, latitude, longitude, borough

    Returns:
        DomainRuleResult with spatial/temporal alignment status
    """
    try:
        # Validate required columns
        permit_cols = {"start_date", "end_date", "latitude", "longitude", "borough"}
        inspection_cols = {"inspection_date", "latitude", "longitude", "borough"}

        missing_permit_cols = permit_cols - set(permits_df.columns)
        missing_inspection_cols = inspection_cols - set(inspections_df.columns)

        if missing_permit_cols or missing_inspection_cols:
            return DomainRuleResult(
                rule_name="permit_inspection_relationship",
                status="WARNING",
                rows_affected=0,
                details=(
                    f"Missing columns: permits={missing_permit_cols}, "
                    f"inspections={missing_inspection_cols}"
                ),
                fix_recommendation="Ensure both DataFrames have required date and spatial columns",
            )

        if permits_df.empty or inspections_df.empty:
            return DomainRuleResult(
                rule_name="permit_inspection_relationship",
                status="PASS",
                rows_affected=0,
                details="One or both DataFrames empty; no validation possible",
                fix_recommendation=None,
            )

        # Convert dates
        permits_df = permits_df.copy()
        inspections_df = inspections_df.copy()
        permits_df["start_date"] = pd.to_datetime(permits_df["start_date"], errors="coerce")
        permits_df["end_date"] = pd.to_datetime(permits_df["end_date"], errors="coerce")
        inspections_df["inspection_date"] = pd.to_datetime(
            inspections_df["inspection_date"], errors="coerce"
        )

        # Filter to valid dates
        permits_valid = permits_df.dropna(subset=["start_date", "end_date"])
        inspections_valid = inspections_df.dropna(subset=["inspection_date"])

        if permits_valid.empty or inspections_valid.empty:
            return DomainRuleResult(
                rule_name="permit_inspection_relationship",
                status="WARNING",
                rows_affected=0,
                details="Insufficient valid date data for validation",
                fix_recommendation="Clean date columns and ensure ISO 8601 format",
            )

        # Spatial check: inspections should be in same borough as permits
        borough_mismatches = 0
        for _, permit in permits_valid.iterrows():
            # Check if any inspections in same spatial region
            borough = permit["borough"]
            inspections_in_borough = inspections_valid[
                inspections_valid["borough"] == borough
            ]
            if inspections_in_borough.empty:
                borough_mismatches += 1

        # Temporal check: inspections should occur within permit dates
        temporal_violations = 0
        for _, inspection in inspections_valid.iterrows():
            insp_date = inspection["inspection_date"]
            borough = inspection["borough"]

            # Find permits in same borough
            permits_in_borough = permits_valid[permits_valid["borough"] == borough]
            if permits_in_borough.empty:
                temporal_violations += 1
            else:
                # Check if inspection within any permit timeframe
                in_timeframe = (
                    (permits_in_borough["start_date"] <= insp_date)
                    & (insp_date <= permits_in_borough["end_date"])
                ).any()
                if not in_timeframe:
                    temporal_violations += 1

        # Determine status
        total_violations = borough_mismatches + temporal_violations
        violation_rate = total_violations / len(inspections_valid) if inspections_valid.shape[0] > 0 else 0

        if violation_rate < 0.05:
            status = "PASS"
        elif violation_rate < 0.15:
            status = "WARNING"
        else:
            status = "FAIL"

        details = (
            f"Borough mismatches: {borough_mismatches}, Temporal violations: {temporal_violations} "
            f"({violation_rate:.1%} of inspections)"
        )

        fix_recommendation = None
        if status != "PASS":
            fix_recommendation = (
                "Review inspection records to ensure they align with permit timelines and spatial coverage."
            )

        return DomainRuleResult(
            rule_name="permit_inspection_relationship",
            status=status,
            rows_affected=total_violations,
            details=details,
            fix_recommendation=fix_recommendation,
        )

    except Exception as e:
        logger.error(f"Error in permit_inspection_relationship: {e}", exc_info=True)
        return DomainRuleResult(
            rule_name="permit_inspection_relationship",
            status="WARNING",
            rows_affected=0,
            details=f"Rule evaluation error: {str(e)}",
            fix_recommendation="Check DataFrame structure and date/location columns",
        )

def validate_all_domain_rules(
    df: pd.DataFrame,
    permits_df: pd.DataFrame | None = None,
    inspections_df: pd.DataFrame | None = None,
) -> list[DomainRuleResult]:
    """
    Run all domain validation rules on input data.

    Orchestrator function that applies all domain rules and returns results.

    Args:
        df: Primary DataFrame to validate (e.g., violations or inspections)
        permits_df: Optional DataFrame with permit data for cross-table validation
        inspections_df: Optional DataFrame with inspection data for cross-table validation

    Returns:
        List of DomainRuleResult objects
    """
    results: list[DomainRuleResult] = []

    # Rule 1: Material lifespan validation
    material_result = validate_material_lifespan_rule(df)
    results.append(material_result)
    logger.info(f"Material lifespan rule: {material_result.status}")

    # Rule 2: Borough coverage validation
    borough_result = validate_borough_coverage_distribution(df)
    results.append(borough_result)
    logger.info(f"Borough coverage rule: {borough_result.status}")

    # Rule 3: Permit-inspection relationship (if both DataFrames provided)
    if permits_df is not None and inspections_df is not None:
        permit_result = validate_permit_inspection_relationship(permits_df, inspections_df)
        results.append(permit_result)
        logger.info(f"Permit-inspection rule: {permit_result.status}")

    return results

# Utility function for generating rule summary
def summarize_domain_rule_results(results: list[DomainRuleResult]) -> dict:
    """
    Summarize domain rule results into a structured report.

    Args:
        results: List of DomainRuleResult objects

    Returns:
        Dictionary with summary statistics
    """
    summary = {
        "total_rules": len(results),
        "passed": sum(1 for r in results if r.status == "PASS"),
        "warnings": sum(1 for r in results if r.status == "WARNING"),
        "failures": sum(1 for r in results if r.status == "FAIL"),
        "total_rows_affected": sum(r.rows_affected for r in results),
        "rules": {r.rule_name: r.status for r in results},
    }
    return summary
