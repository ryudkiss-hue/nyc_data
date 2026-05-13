# `socrata_toolkit.governance` — Quality, Audit & Lineage

**File:** `socrata_toolkit/governance.py` | **Pillar:** Governance  
**Dependencies:** `pandas`, `pipeline.CDCEvent`

---

## Quality Scoring

### `QualityScore` (dataclass)
```python
@dataclass
class QualityScore:
    overall: float        # Weighted composite (0–100)
    completeness: float   # 100 × (1 - null_fraction)
    validity: float       # Rule compliance rate (0–100)
    consistency: float    # 100 × (1 - duplicate_fraction)
    freshness: float      # Age-based score (0–100)
    details: dict         # Breakdown by dimension
```

### `compute_quality_score(df, key_columns=None) → QualityScore`
Computes a composite quality score.

**Formula:**
- `completeness = (1 - nulls / total_cells) × 100`
- `consistency = (1 - duplicates / total_rows) × 100` (if `key_columns` provided)
- `overall = completeness × 0.6 + consistency × 0.4`

```python
from socrata_toolkit import compute_quality_score

score = compute_quality_score(df, key_columns=["unique_key", "created_date"])
print(f"Quality: {score.overall:.1f}%")
print(f"Completeness: {score.completeness:.1f}%, Consistency: {score.consistency:.1f}%")
```

### `evaluate_rules(df, rules) → list[str]`
Evaluate a list of business rule definitions against a DataFrame. Returns violation messages.

---

## Data Lineage

### `LineageEntry` (dataclass)
One step in a data processing pipeline.
```python
@dataclass
class LineageEntry:
    step_name: str; timestamp: str; source: str; action: str
    row_count_in: int; row_count_out: int; metadata: dict
```

### `LineageRecord`
Full lineage record for a dataset run.

```python
lineage = create_lineage("erm2-nwe9")
lineage.add_step(
    step_name="ingest",
    source="data.cityofnewyork.us",
    action="fetch_json",
    row_count_in=0,
    row_count_out=5000,
    filter="borough=BROOKLYN"
)
lineage.add_step("deduplicate", "duckdb", "dedup", 5000, 4982)
lineage.save("lineage/run_001.json")
```

| Method | Description |
|--------|-------------|
| `add_step(step_name, source, action, row_count_in, row_count_out, **metadata)` | Append a pipeline step |
| `save(path)` | Persist as JSON |

### `create_lineage(dataset_id) → LineageRecord`
Factory function — creates a new lineage record with a UUID run ID.

---

## Audit Logging

### `ActionType` (enum)
`CREATE | UPDATE | DELETE | READ`

### `AuditEvent` (dataclass)
```python
@dataclass
class AuditEvent:
    timestamp: str; user_name: str; action: str
    entity_id: str; reason: str = ""
```

### `AuditLogger`
In-memory audit logger — logs events to a list.

```python
logger = AuditLogger()
logger.log_event(
    actor="system",
    action="fetch",
    resource="erm2-nwe9",
    rows_fetched=1000
)
print(logger.events[-1])
```

### `AuditTrail`
Interface for persistent audit trail storage (Postgres/file backed).

```python
trail = AuditTrail(dsn="postgresql://...")
events = trail.get_events(entity_type="dataset", entity_id="erm2-nwe9", limit=50)
```

---

## Alerting

### `AlertManager`
Simple in-memory alert manager.

```python
mgr = AlertManager()
mgr.create_alert("Quality score below threshold", severity="high")
print(mgr.alerts)
# → [{"title": "...", "severity": "high"}]
```

---

## Governance Processor

### `GovernanceEvent` (dataclass)
```python
@dataclass
class GovernanceEvent:
    event_id: str; source_dataset: str; operation: str
    record_id: str; timestamp: datetime
    is_compliant: bool = True
    violations: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
```

### `GovernanceProcessor`
Orchestrates schema validation, lineage, and compliance checks. Integrates with `CDCProcessor`.

```python
from socrata_toolkit.governance import GovernanceProcessor
from socrata_toolkit.pipeline import CDCEvent

proc = GovernanceProcessor()
event = CDCEvent(
    event_id="evt-001", source_dataset="erm2-nwe9",
    operation="INSERT", record_id="123",
    timestamp_ms=1715000000000, after={"borough": "BROOKLYN"}
)
gov_event = proc.process_event(event)
print(gov_event.is_compliant)  # True
```

**Integration with `stream_pipeline`:**
```python
from socrata_toolkit import stream_pipeline, SocrataClient
from socrata_toolkit.governance import GovernanceProcessor

result = stream_pipeline(
    client=SocrataClient(),
    domain="data.cityofnewyork.us",
    fourfour="erm2-nwe9",
    targets={"duckdb": {"enabled": True, "db_path": "nyc.db",
                        "table": "complaints", "conflict_column": "unique_key"}},
    dry_run=False,
    governance_processor=GovernanceProcessor()
)
```
