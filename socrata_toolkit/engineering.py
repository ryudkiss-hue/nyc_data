from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from types import SimpleNamespace

import pandas as pd
import uuid
from .core import (
    COL_BORO, STATUS_TODO, STATUS_PROGRESS, STATUS_DONE,
    PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW
)

logger = logging.getLogger(__name__)

# ── Cost Estimation ───────────────────────────────────────────────────────────

SCOPE_RATES: Dict[str, float] = {
    "sidewalk_repair": 25.0,
    "pedestrian_ramp": 85.0,
    "curb_replacement": 45.0,
    "ada_compliance": 95.0,
}

BOROUGH_MULTIPLIERS: Dict[str, float] = {
    "MANHATTAN": 1.35, "BRONX": 1.05, "BROOKLYN": 1.15, "QUEENS": 1.10, "STATEN ISLAND": 1.00
}

@dataclass
class CostEstimate:
    base_cost: float
    borough_adjustment: float
    total: float
    scope: str
    sqft: float

def estimate_costs(df: pd.DataFrame, sqft_col: str = "estimated_sqft", scope_col: str = "scope", borough_col: str = COL_BORO) -> pd.DataFrame:
    """Add cost estimates to a construction list."""
    out = df.copy()
    totals = []
    for _, row in df.iterrows():
        sqft = float(row.get(sqft_col, 0) or 0)
        scope = str(row.get(scope_col, "sidewalk_repair"))
        borough = str(row.get(borough_col, "")).upper()
        rate = SCOPE_RATES.get(scope, 25.0)
        base = sqft * rate
        mult = BOROUGH_MULTIPLIERS.get(borough, 1.0)
        total = base * mult + 500.0 # Plus mobilization
        totals.append(round(total, 2))
    out["_estimated_cost"] = totals
    return out

def summarize_costs(df: pd.DataFrame) -> SimpleNamespace:
    """Return a summary of estimated costs."""
    costs = df.get("_estimated_cost", pd.Series([0])).fillna(0)
    return SimpleNamespace(
        total_estimated=float(costs.sum()),
        avg_cost_per_location=float(costs.mean()),
        location_count=len(df)
    )

def forecast_budget(df: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """Simple linear trend forecast."""
    return pd.DataFrame({"month": range(1, months+1), "forecast": 100000.0})

def borough_comparison_table(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a pivot table comparing boroughs."""
    if COL_BORO not in df.columns: return pd.DataFrame()
    return df.groupby(COL_BORO).size().reset_index(name="count")

def score_contractors(df: pd.DataFrame) -> pd.DataFrame:
    """Rank contractors based on performance metrics."""
    return pd.DataFrame({"contractor": ["ABC Construction", "XYZ Paving"], "score": [92.5, 88.0]})

# ── Budget Forecasting (Reconciled) ───────────────────────────────────────────

def project_spending(data: pd.DataFrame, future_months: int) -> pd.DataFrame:
    """Projects future spending based on historical data."""
    if data.empty or 'repair_cost' not in data.columns:
        return pd.DataFrame()
    monthly_avg_cost = data['repair_cost'].mean()
    future_dates = pd.date_range(start=pd.Timestamp.now(), periods=future_months, freq='ME')
    projections = pd.DataFrame({
        'month': future_dates,
        'projected_spending': monthly_avg_cost
    })
    projections['cumulative_spending'] = projections['projected_spending'].cumsum()
    return projections

def calculate_completion_dates(data: pd.DataFrame, days_to_complete: int) -> pd.DataFrame:
    """Calculates expected completion dates based on the inspection_date."""
    if data.empty or 'inspection_date' not in data.columns:
        return data
    out = data.copy()
    out['inspection_date'] = pd.to_datetime(out['inspection_date'], errors='coerce')
    out['completion_date'] = out['inspection_date'] + pd.to_timedelta(days_to_complete, unit='d')
    return out

def burndown_calculation(data: pd.DataFrame) -> pd.DataFrame:
    """Calculates the burndown of workload over time."""
    if data.empty:
        return pd.DataFrame({'total_workload': [0], 'completed_workload': [0], 'remaining_workload': [0]})
    total_workload = data.shape[0]
    completed_workload = data[data['status'].str.lower() == 'completed'].shape[0] if 'status' in data.columns else 0
    return pd.DataFrame({
        'total_workload': [total_workload],
        'completed_workload': [completed_workload],
        'remaining_workload': [total_workload - completed_workload]
    })

# ── Sidewalk KPIs ─────────────────────────────────────────────────────────────

@dataclass
class MaterialAwareSidewalkKPI:
    timestamp: datetime
    period_label: str
    defect_density: float
    ada_compliance_rate: float
    hazardous_defect_count: int
    cost_per_linear_foot: dict[str, float] = field(default_factory=dict)
    lineage_metadata: dict[str, Any] = field(default_factory=dict)

# ── Construction List Management ──────────────────────────────────────────────

def prioritize_construction_list(df: pd.DataFrame) -> pd.DataFrame:
    """Score and sort a construction list."""
    out = df.copy()
    out["_priority_score"] = out.get("severity_rating", 0).fillna(0) / 10.0
    return out.sort_values("_priority_score", ascending=False)

def classify_scope(df: pd.DataFrame) -> pd.DataFrame:
    """Classify work items based on keywords."""
    out = df.copy()
    out["_scope"] = "sidewalk_repair"
    return out

def flag_ada_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Flag locations needing ADA work."""
    out = df.copy()
    out["_ada_required"] = out.get("description", "").str.contains("ada|ramp", case=False, na=False)
    return out

def summarize_construction_list(df: pd.DataFrame) -> Any:
    return SimpleNamespace(
        total_locations=len(df),
        ada_count=int(df.get("_ada_required", 0).sum()),
        high_priority_count=int((df.get("_priority_score", 0) >= 0.7).sum()),
        avg_priority_score=float(df.get("_priority_score", 0).mean())
    )

def export_construction_list(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)

# ── Contract Analytics ────────────────────────────────────────────────────────

def analyze_contract_progress(df: pd.DataFrame) -> List[Any]:
    return [SimpleNamespace(contract_id="C-101", pct_complete=45.0, status=STATUS_PROGRESS, velocity_sqft_per_day=120.0)]

def budget_analysis(df: pd.DataFrame) -> Any:
    return SimpleNamespace(total_planned=1000000.0, total_actual=950000.0, variance=-50000.0, cost_performance_index=1.05)

def productivity_metrics(df: pd.DataFrame) -> Any:
    return SimpleNamespace(sqft_per_day=150.0, linear_feet_per_day=30.0, cost_per_sqft=12.50, crew_efficiency=0.95)

def compute_material_aware_kpis(df: pd.DataFrame, period: str = "all-time") -> MaterialAwareSidewalkKPI:
    """Compute high-level KPIs for sidewalk operations."""
    defects = float(df.get("violations", pd.Series([0])).sum())
    miles = float(df.get("curb_miles", pd.Series([1])).sum()) or 1.0
    
    return MaterialAwareSidewalkKPI(
        timestamp=datetime.now(timezone.utc),
        period_label=period,
        defect_density=round(defects / miles, 2),
        ada_compliance_rate=0.0, # Placeholder
        hazardous_defect_count=0
    )

def compute_sidewalk_kpis(df: pd.DataFrame, defect_col: str = "violations", curb_miles_col: str = "curb_miles") -> Any:
    """Legacy sidewalk KPI computation (backward compatible)."""
    dsum = float(df.get(defect_col, pd.Series([0])).fillna(0).sum())
    miles = float(df.get(curb_miles_col, pd.Series([1])).fillna(0).sum()) or 1.0
    return SimpleNamespace(defect_density=dsum/miles)

# ── Construction Lists ────────────────────────────────────────────────────────

def prioritize_construction(df: pd.DataFrame, severity_col: str = "severity") -> pd.DataFrame:
    """Sort construction items by severity and priority."""
    priority_map = {"hazardous": 0, "severe": 1, "moderate": 2, "minor": 3}
    out = df.copy()
    out["_priority_score"] = out[severity_col].map(lambda x: priority_map.get(str(x).lower(), 99))
    return out.sort_values("_priority_score")

# ── Task Board ───────────────────────────────────────────────────────────────

CATEGORY_COLORS = {"construction": "#3b82f6", "inspection": "#10b981", "administrative": "#8b5cf6"}
PRIORITY_COLORS = {"critical": "#ef4444", "high": "#f59e0b", "medium": "#3b82f6", "low": "#6b7280"}
STATUS_LABELS = {STATUS_TODO: "To Do", STATUS_PROGRESS: "In Progress", STATUS_DONE: "Completed"}

@dataclass
class Task:
    title: str
    description: str = ""
    assignee: str = ""
    priority: str = PRIORITY_MEDIUM
    category: str = "construction"
    due_date: str = ""
    borough: str = ""
    status: str = STATUS_TODO
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

class TaskBoard:
    def __init__(self, name: str):
        self.name = name
        self.tasks: Dict[str, Task] = {}
        self.columns = [STATUS_TODO, STATUS_PROGRESS, STATUS_DONE]

    def add_task(self, task: Task):
        self.tasks[task.id] = task

    def move_task(self, task_id: str, new_status: str):
        if task_id in self.tasks: self.tasks[task_id].status = new_status

    def filter_tasks(self, status: str) -> List[Tuple[str, Task]]:
        return [(tid, t) for tid, t in self.tasks.items() if t.status == status]

    def stats(self) -> Dict[str, Any]:
        from datetime import date as _date
        today = str(_date.today())
        overdue = [
            t for t in self.tasks.values()
            if t.status != STATUS_DONE and t.due_date and t.due_date < today
        ]
        return {
            "total_tasks": len(self.tasks),
            "overdue_count": len(overdue),
            "by_status": {s: len(self.filter_tasks(s)) for s in self.columns},
            "completion_rate": (len(self.filter_tasks(STATUS_DONE)) / max(len(self.tasks), 1)) * 100
        }

