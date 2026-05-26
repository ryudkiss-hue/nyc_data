"""SLA Tracking for DOT Sidewalk Toolkit.

Track response times from complaint to inspection to repair,
flag SLA violations, and compute cycle time metrics by borough and scope.

Example::

    from socrata_toolkit.sla_tracking import compute_sla_metrics, flag_sla_violations

    metrics = compute_sla_metrics(df)
    flagged = flag_sla_violations(df, complaint_to_inspection_days=30, inspection_to_repair_days=90)
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class SLAMetrics:
    """SLA performance metrics."""
    avg_complaint_to_inspection_days: float
    avg_inspection_to_repair_days: float
    avg_total_cycle_days: float
    median_total_cycle_days: float
    sla_compliance_rate: float  # percentage meeting target
    violations_count: int
    by_borough: dict[str, dict[str, float]]


@dataclass
class SLATarget:
    """SLA target definition."""
    complaint_to_inspection_days: int = 30
    inspection_to_repair_days: int = 90
    total_cycle_days: int = 120


def compute_cycle_times(
    df: pd.DataFrame,
    complaint_date_col: str = "complaint_date",
    inspection_date_col: str = "inspection_date",
    repair_date_col: str = "repair_date",
) -> pd.DataFrame:
    """Add cycle time columns to the DataFrame.

    Adds: _days_complaint_to_inspection, _days_inspection_to_repair, _days_total_cycle
    """
    out = df.copy()
    complaint = pd.to_datetime(out[complaint_date_col], errors="coerce") if complaint_date_col in out.columns else pd.Series(dtype="datetime64[ns]")
    inspection = pd.to_datetime(out[inspection_date_col], errors="coerce") if inspection_date_col in out.columns else pd.Series(dtype="datetime64[ns]")
    repair = pd.to_datetime(out[repair_date_col], errors="coerce") if repair_date_col in out.columns else pd.Series(dtype="datetime64[ns]")

    out["_days_complaint_to_inspection"] = (inspection - complaint).dt.days
    out["_days_inspection_to_repair"] = (repair - inspection).dt.days
    out["_days_total_cycle"] = (repair - complaint).dt.days
    return out


def compute_sla_metrics(
    df: pd.DataFrame,
    target: SLATarget | None = None,
    borough_col: str = "borough",
    complaint_date_col: str = "complaint_date",
    inspection_date_col: str = "inspection_date",
    repair_date_col: str = "repair_date",
) -> SLAMetrics:
    """Compute SLA performance metrics."""
    t = target or SLATarget()
    tmp = compute_cycle_times(df, complaint_date_col, inspection_date_col, repair_date_col)

    c2i = tmp["_days_complaint_to_inspection"].dropna()
    i2r = tmp["_days_inspection_to_repair"].dropna()
    total = tmp["_days_total_cycle"].dropna()

    violations = int((total > t.total_cycle_days).sum()) if not total.empty else 0
    compliance = round((1 - violations / max(len(total), 1)) * 100, 1) if not total.empty else 100.0

    by_borough: dict[str, dict[str, float]] = {}
    if borough_col in tmp.columns:
        for boro, group in tmp.groupby(borough_col):
            bc2i = group["_days_complaint_to_inspection"].dropna()
            bi2r = group["_days_inspection_to_repair"].dropna()
            btotal = group["_days_total_cycle"].dropna()
            by_borough[str(boro)] = {
                "avg_cycle_days": round(float(btotal.mean()), 1) if not btotal.empty else 0,
                "compliance_rate": round((1 - (btotal > t.total_cycle_days).sum() / max(len(btotal), 1)) * 100, 1) if not btotal.empty else 100,
            }

    return SLAMetrics(
        avg_complaint_to_inspection_days=round(float(c2i.mean()), 1) if not c2i.empty else 0,
        avg_inspection_to_repair_days=round(float(i2r.mean()), 1) if not i2r.empty else 0,
        avg_total_cycle_days=round(float(total.mean()), 1) if not total.empty else 0,
        median_total_cycle_days=round(float(total.median()), 1) if not total.empty else 0,
        sla_compliance_rate=compliance,
        violations_count=violations,
        by_borough=by_borough,
    )


def flag_sla_violations(
    df: pd.DataFrame,
    target: SLATarget | None = None,
    **date_cols: str,
) -> pd.DataFrame:
    """Flag records that violate SLA targets.

    Adds _sla_violation (bool) and _sla_violation_type columns.
    """
    t = target or SLATarget()
    tmp = compute_cycle_times(df, **date_cols)
    violations = []
    for _, row in tmp.iterrows():
        types = []
        c2i = row.get("_days_complaint_to_inspection")
        if c2i is not None and not pd.isna(c2i) and c2i > t.complaint_to_inspection_days:
            types.append("inspection_delay")
        i2r = row.get("_days_inspection_to_repair")
        if i2r is not None and not pd.isna(i2r) and i2r > t.inspection_to_repair_days:
            types.append("repair_delay")
        total = row.get("_days_total_cycle")
        if total is not None and not pd.isna(total) and total > t.total_cycle_days:
            types.append("total_cycle")
        violations.append(types)

    tmp["_sla_violation"] = [bool(v) for v in violations]
    tmp["_sla_violation_type"] = [",".join(v) if v else "" for v in violations]
    return tmp
