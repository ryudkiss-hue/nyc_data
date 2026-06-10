# CDC and SCD Type 2 Implementation Guide

## Overview

This guide covers the Change Data Capture (CDC) and Slowly Changing Dimension Type 2 (SCD Type 2) system implemented for the NYC Data toolkit. These systems provide:

- **Historical tracking**: Understand how data evolved over time
- **Audit compliance**: Track who changed what, when, and why
- **Temporal queries**: Query data as it existed at any point in time
- **Data integrity**: Immutable history with effective dates
- **Regulatory compliance**: Complete audit trails and retention policies

## Architecture

### Core Components

1. **SCD Type 2 (`scd_type2.py`)**: Manages slowly changing dimensions with effective dates
2. **Audit Trail (`audit_trail.py`)**: Immutable log of all operations
3. **CDC Engine (`cdc_engine.py`)**: Processes change events
4. **Temporal Queries (`temporal_queries.py`)**: Query historical data
5. **Soft Delete (`soft_delete.py`)**: GDPR-compliant deletion with retention
6. **CDC Export (`cdc_export.py`)**: Export to data lakes and downstream systems
7. **Compliance (`cdc_compliance.py`)**: Verify system integrity

### Database Schema

The system uses PostgreSQL with these main tables:

- `audit_trail`: Immutable audit events
- `cdc_events`: Immutable CDC event log
- `cdc_watermarks`: Track processing position
- `soft_delete_log`: Track soft deletions
- `{dataset}_scd`: SCD Type 2 tables (auto-created per dataset)

## Getting Started

### 1. Initialize SCD Type 2 for a Dataset

```python
from socrata_toolkit.scd_type2 import SCDType2Manager

manager = SCDType2Manager(
    dsn="postgresql://user:pass@localhost/nyc_data",
    table="sidewalk_conditions_scd"
)

# Create initial record
record_id = manager.manage_record(
    business_key="sidewalk_123",
    new_data={
        "condition": "excellent",
        "material": "concrete",
        "last_inspected": "2026-03-15"
    }
)
print(f"Created SCD record: {record_id}")
```

### 2. Set Up Audit Trail

```python
from socrata_toolkit.audit_trail import AuditTrail

audit = AuditTrail(dsn="postgresql://...")

# Log an operation
audit_id = audit.log_update(
    table="sidewalk_conditions",
    entity_id="sidewalk_123",
    old={"condition": "fair"},
    new={"condition": "excellent"},
    user="inspector@nyc.gov",
    reason="Monthly inspection - conditions improved"
)
print(f"Logged audit event: {audit_id}")
```

### 3. Process CDC Events

```python
from socrata_toolkit.cdc_engine import CDCEvent, CDCProcessor

processor = CDCProcessor(dsn="postgresql://...")

event = CDCEvent(
    event_id="evt-001",
    source_dataset="sidewalk_conditions",
    operation="UPDATE",
    record_id="sidewalk_123",
    timestamp_ms=1609459200000,
    before={"condition": "fair"},
    after={"condition": "excellent"}
)

result = processor.process_cdc_event(event)
if result.success:
    print(f"Processed event: {result.event_id}")
```

### 4. Query Historical Data

```python
from socrata_toolkit.temporal_queries import TemporalQuery
from datetime import datetime

tq = TemporalQuery(
    dsn="postgresql://...",
    table="sidewalk_conditions_scd"
)

# Get data as it existed on a specific date
record = tq.get_as_of(
    business_key="sidewalk_123",
    as_of=datetime(2026, 3, 1)
)
print(f"Condition on 3/1: {record['data']['condition']}")

# Get all versions
versions = tq.get_versions("sidewalk_123")
for v in versions:
    print(f"{v['start_date']} - {v['end_date']}: {v['data']}")
```

### 5. Soft Delete with Retention

```python
from socrata_toolkit.soft_delete import SoftDeleteManager, RetentionPolicy

delete_mgr = SoftDeleteManager(dsn="postgresql://...")

# Set retention policy (90 days before hard delete)
policy = RetentionPolicy(
    table_name="sidewalk_conditions",
    retention_days=90,
    allow_hard_delete=True,
    require_backup=True
)
delete_mgr.set_retention_policy(policy)

# Soft delete a record
delete_mgr.soft_delete(
    table="sidewalk_conditions",
    record_id="sidewalk_123",
    reason="Duplicate entry",
    deleted_by="data_admin@nyc.gov"
)

# Restore if needed
delete_mgr.restore_deleted(
    table="sidewalk_conditions",
    record_id="sidewalk_123"
)

# Hard delete expired records (run nightly)
deleted_count = delete_mgr.hard_delete_expired(retention_days=90)
print(f"Hard deleted {deleted_count} records")
```

### 6. Export CDC Data

```python
from socrata_toolkit.cdc_export import CDCExporter, ExportFormat

exporter = CDCExporter(dsn="postgresql://...")

# Export to CSV
result = exporter.export_to_csv(
    source_dataset="sidewalk_conditions",
    output_path="/data/exports/",
    compress=True
)
print(f"Exported {result.record_count} records to {result.file_path}")

# Export to JSON
result = exporter.export_to_json(
    source_dataset="sidewalk_conditions",
    output_path="/data/exports/",
    format="jsonl"  # newline-delimited JSON
)

# Export compacted CDC (latest version only)
result = exporter.export_compacted_cdc(
    source_dataset="sidewalk_conditions",
    output_path="/data/exports/"
)
```

### 7. Verify Compliance

```python
from socrata_toolkit.cdc_compliance import CDCReconciler

reconciler = CDCReconciler(dsn="postgresql://...")

# Generate compliance report
report = reconciler.generate_compliance_report()
print(reconciler.export_compliance_report(report))

# Check audit trail completeness
result = reconciler.verify_audit_trail_completeness()
if result.passed:
    print("Audit trail is complete and immutable ✓")

# Verify SCD Type 2 integrity
result = reconciler.verify_scd_integrity("sidewalk_conditions_scd")
if result.passed:
    print("SCD Type 2 table integrity verified ✓")
```

## SCD Type 2 Patterns

### Record Lifecycle

1. **INSERT**: New record created
   ```python
   # First insertion
   manager.manage_record("sidewalk_123", {"condition": "fair", "material": "asphalt"})
   # Creates: scd_id=1, start_date=now, end_date=NULL, is_current=TRUE
   ```

2. **UPDATE**: Change detected, old version closed
   ```python
   # Data changed
   manager.manage_record("sidewalk_123", {"condition": "excellent", "material": "asphalt"})
   # Updates: scd_id=1 -> end_date=now, is_current=FALSE
   # Creates: scd_id=2, start_date=now, end_date=NULL, is_current=TRUE
   ```

3. **NO CHANGE**: Hash matches, no new version
   ```python
   # Same data
   manager.manage_record("sidewalk_123", {"condition": "excellent", "material": "asphalt"})
   # No change: returns existing scd_id=2
   ```

4. **DELETE**: Soft delete via empty version
   ```python
   manager.mark_deleted("sidewalk_123", reason="Duplicate")
   # Creates new version with empty data_fields
   ```

### Hash-Based Change Detection

The system uses MD5 hashing to detect actual changes:

```python
import json
import hashlib

data1 = {"field1": "value1", "field2": "value2"}
data2 = {"field2": "value2", "field1": "value1"}  # Same data, different order

hash1 = hashlib.md5(json.dumps(data1, sort_keys=True).encode()).hexdigest()
hash2 = hashlib.md5(json.dumps(data2, sort_keys=True).encode()).hexdigest()

assert hash1 == hash2  # Hashes match despite order difference
```

## Temporal Query Examples

### Query As Of Date

```python
tq = TemporalQuery(dsn="...", table="sidewalk_conditions_scd")

# Show data as it was on March 1, 2026
record = tq.get_as_of("sidewalk_123", datetime(2026, 3, 1))
print(f"Condition on 3/1: {record['data']['condition']}")
print(f"Valid from: {record['start_date']} to {record['end_date']}")
```

### Track Metric Over Time

```python
# Track ADA compliance score for multiple sidewalks throughout 2026
import pandas as pd

dates = pd.date_range("2026-01-01", "2026-12-31", freq="M")
results = tq.track_metric_over_time(
    metric_expr="ada_compliance_score",
    business_keys=["sidewalk_123", "sidewalk_456", "sidewalk_789"],
    dates=[d.date() for d in dates]
)

# Create time series dataframe
df = pd.DataFrame({
    "sidewalk": list(results.keys()),
    "2026-01": [results[k][0][1] for k in results.keys()],
    "2026-02": [results[k][1][1] for k in results.keys()],
    # ... more months
})
```

### Detect Change Patterns

```python
pattern = tq.detect_change_patterns("sidewalk_123")

print(f"Total versions: {pattern.total_versions}")
print(f"Fields changed: {pattern.fields_changed}")
print(f"Change frequency: {pattern.change_frequency:.2f} per day")
print(f"Most recent: {pattern.most_recent_change}")
print(f"Operations: {pattern.change_types}")
```

## Audit Trail Use Cases

### Find All Changes by User

```python
audit = AuditTrail(dsn="...")

events = audit.get_events_by_user(
    user="inspector@nyc.gov",
    start_date=date(2026, 3, 1),
    end_date=date(2026, 3, 31)
)

for event in events:
    print(f"{event.timestamp} - {event.action} on {event.entity_id}")
    if event.diff:
        for field, (old, new) in event.diff.items():
            print(f"  {field}: {old} → {new}")
```

### Search by Reason

```python
events = audit.search_events({
    "entity_type": "sidewalk_conditions",
    "reason_contains": "inspection",
    "start_date": date(2026, 3, 1),
    "end_date": date(2026, 3, 31),
})

print(f"Found {len(events)} inspections in March")
```

### Generate Compliance Report

```python
report = audit.generate_compliance_report()

print(f"Total audit entries: {report['total_events']}")
print(f"Date range: {report['date_range']['start']} to {report['date_range']['end']}")
print(f"Users: {', '.join(report['users'])}")
print(f"Operations: {report['actions']}")
```

### Export for Compliance

```python
import csv

# Export to CSV
with open("audit_export.csv", "w") as f:
    count = audit.export_csv(f, criteria={
        "start_date": date(2026, 3, 1),
        "end_date": date(2026, 3, 31),
    })
    print(f"Exported {count} audit entries")

# Export to JSON
events_json = audit.export_json(criteria={
    "entity_type": "sidewalk_conditions",
})
```

## CDC Processing Pipeline

### Watermarking for Exactly-Once Processing

```python
processor = CDCProcessor(dsn="...")

# Get last processed position
watermark = processor.get_watermark("sidewalk_conditions")
if watermark:
    last_event_id, last_ts = watermark
    print(f"Resume from: {last_event_id} at {last_ts}")
else:
    print("Starting fresh")

# Process events
events = fetch_events_from_source(since=last_ts)
result = processor.batch_process_cdc(events)

# Update watermark after successful processing
if result['processed'] > 0:
    processor.track_watermark(
        source_dataset="sidewalk_conditions",
        event_id=events[-1].event_id,
        timestamp_ms=events[-1].timestamp_ms
    )
```

### Deduplication

```python
# Remove duplicate consecutive updates
events = [
    CDCEvent(..., record_id="rec1", after={"val": "A"}),
    CDCEvent(..., record_id="rec1", after={"val": "A"}),  # Duplicate
    CDCEvent(..., record_id="rec1", after={"val": "B"}),  # New state
]

deduped = CDCProcessor.deduplicate_events(events)
# Result: first and third events kept, middle duplicate removed
```

### Ordering Validation

```python
report = CDCProcessor.validate_event_order(events)

if report.valid:
    print("Events are in correct order ✓")
else:
    print("Issues found:")
    for issue in report.issues:
        print(f"  - {issue}")
```

## Retention Policies

### Configure Retention

```python
from socrata_toolkit.soft_delete import SoftDeleteManager, RetentionPolicy

mgr = SoftDeleteManager(dsn="...")

# 90-day retention for sidewalk conditions
mgr.set_retention_policy(RetentionPolicy(
    table_name="sidewalk_conditions",
    retention_days=90,
    allow_hard_delete=True,
    require_backup=True,
))

# Immediate deletion for test data
mgr.set_retention_policy(RetentionPolicy(
    table_name="test_data",
    retention_days=0,
    allow_hard_delete=True,
    require_backup=False,
))
```

### Monitoring Expiration

```python
# Find records expiring in next 7 days
expiring = mgr.get_expiring_soon(days=7)

for record in expiring:
    print(f"Will delete {record['record_id']} on {record['hard_delete_at']}")
    print(f"  Reason: {record['reason']}")

# Generate compliance report
report = mgr.get_retention_compliance_report()
print(f"Soft deleted: {report['total_soft_deleted']}")
print(f"Expiring soon: {report['expiring_in_7_days']}")
```

## Compliance and Data Quality

### Run Compliance Checks

```python
from socrata_toolkit.cdc_compliance import CDCReconciler

reconciler = CDCReconciler(dsn="...")

# Check 1: Audit trail immutability
result = reconciler.verify_audit_trail_completeness()
assert result.passed, "Audit trail compromised!"

# Check 2: Event ordering
result = reconciler.verify_cdc_event_ordering()
assert result.passed, "Events are out of order!"

# Check 3: SCD integrity
result = reconciler.verify_scd_integrity("sidewalk_conditions_scd")
assert result.passed, "SCD table has violations!"

# Generate full report
report = reconciler.generate_compliance_report()
print(reconciler.export_compliance_report(report))
```

### Reconciliation

```python
# Verify SCD matches source
result = reconciler.reconcile_scd_with_source(
    table="sidewalk_conditions_scd",
    source_table="sidewalk_conditions"
)

if result.reconciled:
    print(f"✓ SCD in sync with source")
else:
    print(f"Missing events: {result.missing_events}")
    print(f"Extra events: {result.extra_events}")
```

## Performance Considerations

### Indexing Strategy

The system creates indexes for fast queries:

```sql
-- SCD Type 2 indexes
CREATE INDEX idx_scd_business_key ON sidewalk_conditions_scd(business_key);
CREATE INDEX idx_scd_dates ON sidewalk_conditions_scd(business_key, start_date, end_date);
CREATE INDEX idx_scd_current ON sidewalk_conditions_scd(business_key, is_current);

-- Audit trail indexes
CREATE INDEX idx_audit_timestamp ON audit_trail(timestamp DESC);
CREATE INDEX idx_audit_entity ON audit_trail(entity_type, entity_id);
CREATE INDEX idx_audit_user ON audit_trail(user_name);

-- CDC event indexes
CREATE INDEX idx_cdc_dataset ON cdc_events(source_dataset);
CREATE INDEX idx_cdc_timestamp ON cdc_events(timestamp_ms DESC);
```

### Query Optimization

For as-of queries on large tables:

```python
# Good: Uses index on (business_key, start_date, end_date)
record = tq.get_as_of("sidewalk_123", datetime(2026, 3, 15))

# Bad: Scans entire table
all_records = tq.get_versions("*")  # Don't do this
```

### Partitioning

For very large audit trails, partition by month:

```sql
CREATE TABLE audit_trail_202601 PARTITION OF audit_trail
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE audit_trail_202602 PARTITION OF audit_trail
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

## Troubleshooting

### Missing Audit Entries

Check audit trail coverage:

```python
report = reconciler.check_audit_trail_coverage()
if not report.passed:
    print("Gap found:")
    for issue in report.issues:
        print(f"  {issue}")
```

### Out-of-Order Events

Validate CDC event ordering:

```python
report = CDCProcessor.validate_event_order(events)
if not report.valid:
    print("Issues:")
    for issue in report.issues:
        print(f"  {issue}")
```

### Overlapping SCD Versions

Check SCD integrity:

```python
validation = manager.validate_scd()
if not validation['valid']:
    for issue in validation['issues']:
        print(f"  Issue: {issue}")
```

## Best Practices

1. **Always use business keys**: Unique, stable identifiers across time
2. **Include reason field**: Document why changes occur
3. **Audit trail immutability**: Verify regularly with compliance checks
4. **Regular retention cleanup**: Run hard_delete_expired nightly
5. **Temporal query testing**: Verify as-of queries match expectations
6. **Watermark tracking**: Use watermarks to prevent duplicate processing
7. **Hash validation**: Validate hashes match expected changes
8. **Compliance reports**: Generate monthly compliance reports

## Additional Resources

- See `docs/temporal_analytics.md` for time-series analysis examples
- See `docs/audit_compliance.md` for regulatory compliance details
- See `socrata_toolkit/cli.py` for CDC CLI commands
