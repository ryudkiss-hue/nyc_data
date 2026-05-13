# `socrata_toolkit.engineering` — KPIs, Cost & Construction

**File:** `socrata_toolkit/engineering.py` | **Pillar:** Engineering  
**Dependencies:** `pandas`, `uuid`

---

## Cost Estimation

### Scope Rates (per sq ft)

| Scope | Rate |
|-------|------|
| `sidewalk_repair` | $25.00 |
| `pedestrian_ramp` | $85.00 |
| `curb_replacement` | $45.00 |
| `ada_compliance` | $95.00 |

### Borough Multipliers

| Borough | Multiplier |
|---------|-----------|
| MANHATTAN | 1.35 |
| BROOKLYN | 1.15 |
| QUEENS | 1.10 |
| BRONX | 1.05 |
| STATEN ISLAND | 1.00 |

Formula: `total = (sqft × rate × borough_mult) + $500 mobilization`

### `CostEstimate` (dataclass)
```python
@dataclass
class CostEstimate:
    base_cost: float; borough_adjustment: float
    total: float; scope: str; sqft: float
```

### `estimate_costs(df, sqft_col, scope_col, borough_col) → pd.DataFrame`
Adds `_estimated_cost` column to a construction DataFrame.
```python
df = estimate_costs(df, sqft_col="estimated_sqft", scope_col="scope",
                    borough_col="borough")
```

### `summarize_costs(df) → SimpleNamespace`
```python
summary = summarize_costs(df)
# → {total_estimated, avg_cost_per_location, location_count}
```

### `forecast_budget(df, months=12) → pd.DataFrame`
Linear budget forecast returning `{month, forecast}` DataFrame.

### `borough_comparison_table(df) → pd.DataFrame`
Pivot table of record counts by borough.

### `score_contractors(df) → pd.DataFrame`
Rank contractors by performance score.

---

## Sidewalk KPIs

### `MaterialAwareSidewalkKPI` (dataclass)
```python
@dataclass
class MaterialAwareSidewalkKPI:
    timestamp: datetime; period_label: str
    defect_density: float          # defects per curb mile
    ada_compliance_rate: float     # 0–100
    hazardous_defect_count: int
    cost_per_linear_foot: dict     # by material type
    lineage_metadata: dict
```

### `compute_material_aware_kpis(df, period="all-time") → MaterialAwareSidewalkKPI`
Full KPI computation with material tracking.
```python
kpis = compute_material_aware_kpis(df, period="FY2024")
print(kpis.defect_density)
```

### `compute_sidewalk_kpis(df, defect_col, curb_miles_col) → SimpleNamespace`
Lightweight legacy KPI: returns `{defect_density}`.

---

## Construction List Management

### `prioritize_construction_list(df) → pd.DataFrame`
Adds `_priority_score` (0–1) column based on `severity_rating`. Returns sorted descending.

### `prioritize_construction(df, severity_col="severity") → pd.DataFrame`
Sorts by severity label: `hazardous > severe > moderate > minor`.

### `classify_scope(df) → pd.DataFrame`
Adds `_scope` column classifying work items by keyword analysis.

### `flag_ada_locations(df) → pd.DataFrame`
Adds `_ada_required` boolean column (True if description contains "ada" or "ramp").

### `summarize_construction_list(df) → SimpleNamespace`
```python
summary = summarize_construction_list(df)
# → {total_locations, ada_count, high_priority_count, avg_priority_score}
```

### `export_construction_list(df, path)`
Save construction list to CSV.

---

## Contract Analytics

### `analyze_contract_progress(df) → list[SimpleNamespace]`
Returns contract progress snapshots: `{contract_id, pct_complete, status, velocity_sqft_per_day}`.

### `budget_analysis(df) → SimpleNamespace`
Returns: `{total_planned, total_actual, variance, cost_performance_index}`.

### `productivity_metrics(df) → SimpleNamespace`
Returns: `{sqft_per_day, linear_feet_per_day, cost_per_sqft, crew_efficiency}`.

---

## Task Board

### `Task` (dataclass)
```python
@dataclass
class Task:
    title: str; description: str = ""; assignee: str = ""
    priority: str = "medium"  # critical | high | medium | low
    category: str = "construction"
    due_date: str = ""; borough: str = ""
    status: str = "todo"      # todo | in_progress | done
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

### `TaskBoard`
In-memory task management board.

```python
board = TaskBoard("NYC DOT Q1 Work")
board.add_task(Task(title="Repair 5th Ave crack", priority="high", borough="MANHATTAN"))
board.move_task(task_id, "in_progress")
todo = board.filter_tasks("todo")
stats = board.stats()
# → {total_tasks, overdue_count, by_status: {...}, completion_rate}
```

| Method | Description |
|--------|-------------|
| `add_task(task)` | Add a task |
| `move_task(id, new_status)` | Change task status |
| `filter_tasks(status)` | Get tasks by status |
| `stats()` | Overall board statistics |

### Status Constants
- `STATUS_TODO` = `"todo"`
- `STATUS_PROGRESS` = `"in_progress"`
- `STATUS_DONE` = `"done"`
