"""Program Metrics Tracker for DOT Sidewalk Inspection & Management.

Centralized tracking of program-level KPIs, personnel budget codes,
and operational dashboards for sidewalk repair and pedestrian ramp
capital programs.

Key capabilities:
- Define and track custom KPIs with targets and thresholds
- Personnel and budget code tracking
- Automated red/yellow/green status computation
- Metric snapshots for trend analysis over time
- Dashboard-ready metric summaries

Example::

    from socrata_toolkit.analysis.program import (
        MetricDefinition,
        MetricsTracker,
        compute_program_dashboard,
    )

    tracker = MetricsTracker()
    tracker.define("defect_density", target=2.0, direction="lower_is_better")
    tracker.record("defect_density", 1.8)
    dashboard = tracker.dashboard()
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MetricDefinition:
    """Definition of a program metric."""
    name: str
    description: str
    unit: str
    target: float
    warning_threshold: float  # yellow zone boundary
    critical_threshold: float  # red zone boundary
    direction: str = "lower_is_better"  # or "higher_is_better"
    category: str = "general"  # "construction", "budget", "personnel", "safety"


@dataclass
class MetricSnapshot:
    """A point-in-time snapshot of a metric value."""
    name: str
    value: float
    timestamp: str
    status: str  # "green", "yellow", "red"
    target: float
    delta_from_target: float


@dataclass
class BudgetCode:
    """A personnel or program budget code."""
    code: str
    description: str
    category: str  # "personnel", "materials", "equipment", "subcontractor"
    allocated: float
    spent: float
    remaining: float
    pct_used: float


@dataclass
class ProgramDashboard:
    """Complete program dashboard with all metrics and budget summary."""
    timestamp: str
    metrics: List[MetricSnapshot]
    budget_codes: List[BudgetCode]
    overall_health: str  # "green", "yellow", "red"
    green_count: int
    yellow_count: int
    red_count: int


# ---------------------------------------------------------------------------
# Standard DOT Sidewalk KPI Definitions
# ---------------------------------------------------------------------------

STANDARD_KPIS: List[MetricDefinition] = [
    MetricDefinition(
        name="defect_density",
        description="Violations per curb-mile of inspected sidewalk",
        unit="violations/mile",
        target=2.0,
        warning_threshold=3.0,
        critical_threshold=5.0,
        direction="lower_is_better",
        category="safety",
    ),
    MetricDefinition(
        name="throughput_velocity",
        description="Linear feet of sidewalk built per working day",
        unit="ft/day",
        target=200.0,
        warning_threshold=150.0,
        critical_threshold=100.0,
        direction="higher_is_better",
        category="construction",
    ),
    MetricDefinition(
        name="budget_burn_variance",
        description="Actual spend minus planned spend (negative = under budget)",
        unit="USD",
        target=0.0,
        warning_threshold=50000.0,
        critical_threshold=100000.0,
        direction="lower_is_better",
        category="budget",
    ),
    MetricDefinition(
        name="first_pass_yield",
        description="Percentage of inspections passing on first attempt",
        unit="%",
        target=90.0,
        warning_threshold=80.0,
        critical_threshold=70.0,
        direction="higher_is_better",
        category="construction",
    ),
    MetricDefinition(
        name="rework_factor",
        description="Rework spend as percentage of total actual spend",
        unit="%",
        target=5.0,
        warning_threshold=10.0,
        critical_threshold=15.0,
        direction="lower_is_better",
        category="construction",
    ),
    MetricDefinition(
        name="ada_compliance_rate",
        description="Percentage of pedestrian ramps meeting ADA standards",
        unit="%",
        target=100.0,
        warning_threshold=95.0,
        critical_threshold=90.0,
        direction="higher_is_better",
        category="safety",
    ),
    MetricDefinition(
        name="contract_on_time_rate",
        description="Percentage of contracts completing on or before planned end date",
        unit="%",
        target=90.0,
        warning_threshold=80.0,
        critical_threshold=70.0,
        direction="higher_is_better",
        category="construction",
    ),
]


# ---------------------------------------------------------------------------
# Metrics Tracker
# ---------------------------------------------------------------------------

class MetricsTracker:
    """Track and evaluate program metrics over time.

    Provides methods to define KPIs, record values, compute status
    (red/yellow/green), and generate dashboard summaries.

    Usage::

        tracker = MetricsTracker()
        tracker.load_standard_kpis()
        tracker.record("defect_density", 2.5)
        tracker.record("throughput_velocity", 180)
        dashboard = tracker.dashboard()
    """

    def __init__(self) -> None:
        self.definitions: Dict[str, MetricDefinition] = {}
        self.history: Dict[str, List[MetricSnapshot]] = {}
        self.budget_codes: List[BudgetCode] = []

    def load_standard_kpis(self) -> None:
        """Load the standard DOT sidewalk program KPI definitions."""
        for kpi in STANDARD_KPIS:
            self.definitions[kpi.name] = kpi

    def define(
        self,
        name: str,
        description: str = "",
        unit: str = "",
        target: float = 0.0,
        warning_threshold: float = 0.0,
        critical_threshold: float = 0.0,
        direction: str = "lower_is_better",
        category: str = "general",
    ) -> MetricDefinition:
        """Define a custom metric."""
        defn = MetricDefinition(
            name=name,
            description=description,
            unit=unit,
            target=target,
            warning_threshold=warning_threshold,
            critical_threshold=critical_threshold,
            direction=direction,
            category=category,
        )
        self.definitions[name] = defn
        return defn

    def record(self, name: str, value: float) -> MetricSnapshot:
        """Record a metric value and compute its status.

        Args:
            name: Metric name (must be defined first).
            value: Current measured value.

        Returns:
            MetricSnapshot with computed status.

        Raises:
            KeyError: If the metric name is not defined.
        """
        if name not in self.definitions:
            raise KeyError(f"Metric '{name}' is not defined. Call define() or load_standard_kpis() first.")

        defn = self.definitions[name]
        status = _compute_status(value, defn)
        delta = value - defn.target

        snapshot = MetricSnapshot(
            name=name,
            value=round(value, 4),
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            target=defn.target,
            delta_from_target=round(delta, 4),
        )

        if name not in self.history:
            self.history[name] = []
        self.history[name].append(snapshot)
        return snapshot

    def latest(self, name: str) -> Optional[MetricSnapshot]:
        """Get the most recent snapshot for a metric."""
        snapshots = self.history.get(name, [])
        return snapshots[-1] if snapshots else None

    def trend(self, name: str, last_n: int = 10) -> List[MetricSnapshot]:
        """Get the last N snapshots for a metric."""
        return self.history.get(name, [])[-last_n:]

    def add_budget_code(
        self,
        code: str,
        description: str = "",
        category: str = "general",
        allocated: float = 0.0,
        spent: float = 0.0,
    ) -> BudgetCode:
        """Register a personnel or program budget code."""
        remaining = allocated - spent
        pct_used = round((spent / allocated * 100) if allocated > 0 else 0.0, 2)
        bc = BudgetCode(
            code=code, description=description, category=category,
            allocated=allocated, spent=spent, remaining=remaining, pct_used=pct_used,
        )
        self.budget_codes.append(bc)
        return bc

    def dashboard(self) -> ProgramDashboard:
        """Generate a complete program dashboard.

        Returns a ProgramDashboard with the latest value for every defined
        metric and overall health status.
        """
        snapshots = []
        for name in self.definitions:
            snap = self.latest(name)
            if snap:
                snapshots.append(snap)

        green = sum(1 for s in snapshots if s.status == "green")
        yellow = sum(1 for s in snapshots if s.status == "yellow")
        red = sum(1 for s in snapshots if s.status == "red")

        if red > 0:
            health = "red"
        elif yellow > 0:
            health = "yellow"
        else:
            health = "green"

        return ProgramDashboard(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics=snapshots,
            budget_codes=list(self.budget_codes),
            overall_health=health,
            green_count=green,
            yellow_count=yellow,
            red_count=red,
        )

    def save(self, path: str) -> None:
        """Persist all definitions, history, and budget codes to JSON."""
        data = {
            "definitions": {
                k: v.__dict__ for k, v in self.definitions.items()
            },
            "history": {
                k: [s.__dict__ for s in v] for k, v in self.history.items()
            },
            "budget_codes": [b.__dict__ for b in self.budget_codes],
        }
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def load(self, path: str) -> None:
        """Load definitions, history, and budget codes from JSON."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for name, d in data.get("definitions", {}).items():
            self.definitions[name] = MetricDefinition(**d)
        for name, snapshots in data.get("history", {}).items():
            self.history[name] = [MetricSnapshot(**s) for s in snapshots]
        self.budget_codes = [BudgetCode(**b) for b in data.get("budget_codes", [])]


def _compute_status(value: float, defn: MetricDefinition) -> str:
    """Compute green/yellow/red status for a metric value."""
    if defn.direction == "lower_is_better":
        if value <= defn.target:
            return "green"
        elif value <= defn.warning_threshold:
            return "yellow" if defn.warning_threshold > defn.target else "green"
        elif value <= defn.critical_threshold:
            return "yellow"
        else:
            return "red"
    else:  # higher_is_better
        if value >= defn.target:
            return "green"
        elif value >= defn.warning_threshold:
            return "yellow"
        elif value >= defn.critical_threshold:
            return "yellow"
        else:
            return "red"


# ---------------------------------------------------------------------------
# Convenience: Compute from DataFrame
# ---------------------------------------------------------------------------

def compute_program_dashboard(
    df: pd.DataFrame,
    violations_col: str = "violations",
    curb_miles_col: str = "curb_miles",
    built_lf_col: str = "built_linear_feet",
    days_col: str = "days",
    actual_spend_col: str = "actual_spend",
    planned_spend_col: str = "planned_spend",
    first_pass_col: str = "first_pass",
    total_inspections_col: str = "total_inspections",
    rework_spend_col: str = "rework_spend",
) -> ProgramDashboard:
    """Compute a program dashboard directly from a DataFrame.

    This is a convenience function that computes KPIs from raw data
    and returns a ready-to-use dashboard.
    """
    tracker = MetricsTracker()
    tracker.load_standard_kpis()

    # defect density
    violations = float(df[violations_col].fillna(0).sum()) if violations_col in df.columns else 0
    miles = float(df[curb_miles_col].fillna(0).sum()) if curb_miles_col in df.columns else 1
    if miles > 0:
        tracker.record("defect_density", violations / miles)

    # throughput velocity
    built = float(df[built_lf_col].fillna(0).sum()) if built_lf_col in df.columns else 0
    days = float(df[days_col].fillna(0).sum()) if days_col in df.columns else 1
    if days > 0:
        tracker.record("throughput_velocity", built / days)

    # budget burn variance
    actual = float(df[actual_spend_col].fillna(0).sum()) if actual_spend_col in df.columns else 0
    planned = float(df[planned_spend_col].fillna(0).sum()) if planned_spend_col in df.columns else 0
    tracker.record("budget_burn_variance", actual - planned)

    # first pass yield
    fp = float(df[first_pass_col].fillna(0).sum()) if first_pass_col in df.columns else 0
    ti = float(df[total_inspections_col].fillna(0).sum()) if total_inspections_col in df.columns else 1
    if ti > 0:
        tracker.record("first_pass_yield", (fp / ti) * 100)

    # rework factor
    rework = float(df[rework_spend_col].fillna(0).sum()) if rework_spend_col in df.columns else 0
    if actual > 0:
        tracker.record("rework_factor", (rework / actual) * 100)

    return tracker.dashboard()
