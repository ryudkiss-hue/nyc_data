# Entity Reconciliation with External Masters

## Overview

Entity reconciliation links internal master entities to external authoritative data sources (e.g., NYC CARTO, DOT systems, permitting databases) and detects/resolves conflicts.

## Core Concepts

### External Master Link

Links a local entity to an external counterpart:

```python
ExternalMasterLink(
    link_id='link_123',
    local_entity_id='entity_abc',
    external_source='NYC_CARTO',
    external_entity_id='carto_456',
    confidence=0.95,
    status=LinkStatus.ACTIVE,
    created_at=datetime.utcnow(),
    last_verified=datetime.utcnow()
)
```

### Reconciliation Workflow

```
Import External Data
        ↓
Match Local to External (using matching strategies)
        ↓
Link Matched Pairs (confidence > threshold)
        ↓
Detect Conflicts (field mismatches)
        ↓
Flag/Resolve High-Severity Conflicts
        ↓
Generate Report (matched, unlinked, recommendations)
```

## Usage

### Import External Data

```python
from socrata_toolkit.entity_reconciliation import Reconciler

reconciler = Reconciler(master_data_manager)

# Import external master
external_data = [
    {'id': 'ext_1', 'name': 'Sidewalk Segment ABC', ...},
    {'id': 'ext_2', 'name': 'Sidewalk Segment DEF', ...},
]

count = reconciler.import_external_master('NYC_CARTO', external_data)
print(f"Imported {count} external entities")
```

### Run Reconciliation

```python
# Match and link
report = reconciler.reconcile_to_external(
    external_source='NYC_CARTO',
    entity_type='sidewalk_segment',
    match_threshold=0.85
)

# Review report
print(f"Matched: {report.matched_count}/{report.total_internal_entities}")
print(f"Unlinked local: {report.unlinked_local}")
print(f"Unlinked external: {report.unlinked_external}")
print(f"Average confidence: {report.avg_confidence:.3f}")

# Review recommendations
for rec in report.recommendations:
    print(f"- {rec}")
```

### Query Links

```python
# Get links for entity
links = reconciler.get_links_for_entity('entity_abc')

for link in links:
    print(f"Linked to {link.external_source}:{link.external_entity_id}")
    print(f"  Confidence: {link.confidence}")
    print(f"  Status: {link.status.value}")
    print(f"  Last verified: {link.last_verified}")

# Get specific link
carto_link = reconciler.get_link_for_source('entity_abc', 'NYC_CARTO')
if carto_link:
    print(f"CARTO entity: {carto_link.external_entity_id}")
```

### Handle Unlinked Records

```python
# Find local entities with no external match
unlinked_local = reconciler.detect_unlinked_locals('NYC_CARTO')
print(f"Local entities without external match: {len(unlinked_local)}")

for entity_id in unlinked_local:
    entity = mgr.get_master_entity(entity_id)
    print(f"  {entity_id}: {entity.canonical_record.get('name')}")

# Find external records with no local match
unlinked_external = reconciler.detect_unlinked_external('NYC_CARTO')
print(f"External entities without local match: {len(unlinked_external)}")
```

## Conflict Management

### Detect Conflicts

Conflicts are detected during reconciliation when fields mismatch:

```python
# Get conflicts from report
for conflict in report.conflicts:
    print(f"Conflict in {conflict.local_entity_id}:{conflict.field}")
    print(f"  Local: {conflict.field_conflicts[conflict.field][0]}")
    print(f"  External: {conflict.field_conflicts[conflict.field][1]}")
    print(f"  Severity: {conflict.severity}")
```

### Resolve Conflicts

```python
# Manually resolve high-severity conflicts
for conflict in report.conflicts:
    if conflict.severity in ['high', 'critical']:
        # Option 1: Prefer local value (trust internal master)
        # Option 2: Prefer external value (trust authoritative source)
        # Option 3: Merge values
        
        resolution = "Use local value - internal review confirmed"
        reconciler.flag_conflict(conflict.conflict_id, resolution)
```

### Merge External Into Local

```python
# Update local master with external data
success = reconciler.merge_external_into_local(
    local_entity_id='entity_abc',
    external_source='NYC_CARTO',
    external_entity_id='ext_123',
    strategy='merge'  # merge, prefer_local, prefer_external
)

# Strategies:
# - 'prefer_local': Keep local values, use external to fill gaps
# - 'prefer_external': Use external values for everything
# - 'merge': Smart merge (local priority, external fills gaps)
```

## Custom Matching

```python
from socrata_toolkit.entity_matching import CompositeMatch, FuzzyMatch, GeographicMatch

# Customize matching for reconciliation
reconciler = Reconciler(
    master_data_manager,
    matching_strategy=CompositeMatch([
        (FuzzyMatch(fields=['name'], threshold=0.85), 0.4),
        (GeographicMatch(distance_threshold_m=20.0), 0.6)
    ])
)

# Now reconcile uses custom strategy
report = reconciler.reconcile_to_external('NYC_CARTO')
```

## Multiple External Sources

```python
# Import multiple external masters
reconciler.import_external_master('NYC_CARTO', carto_data)
reconciler.import_external_master('DOT_SYSTEMS', dot_data)
reconciler.import_external_master('PERMITTING_DB', permit_data)

# Reconcile to each
carto_report = reconciler.reconcile_to_external('NYC_CARTO')
dot_report = reconciler.reconcile_to_external('DOT_SYSTEMS')
permit_report = reconciler.reconcile_to_external('PERMITTING_DB')

# Get overall statistics
stats = reconciler.get_statistics()
print(f"Links created: {stats['total_links']}")
print(f"Active links: {stats['active_links']}")
print(f"Average confidence: {stats['avg_link_confidence']:.3f}")
```

## Monitoring Reconciliation

```python
# Get reconciliation history
history = reconciler.get_reconciliation_history(external_source='NYC_CARTO')

for report in history:
    print(f"{report.timestamp}: {report.matched_count} matched")
    print(f"  Match rate: {report.match_rate:.1f}%")
    print(f"  Conflicts: {len(report.conflicts)}")

# Track link status over time
links = reconciler.get_links_for_entity('entity_abc')
for link in links:
    print(f"Link to {link.external_source}")
    print(f"  Status: {link.status.value}")
    print(f"  Last verified: {link.last_verified.isoformat()}")
```

## Bi-directional Reconciliation

```python
# When external system also has master data

# 1. Link our entities to theirs
reconciler.reconcile_to_external('NYC_CARTO')

# 2. Find gaps in coverage
unlinked_local = reconciler.detect_unlinked_locals('NYC_CARTO')
unlinked_external = reconciler.detect_unlinked_external('NYC_CARTO')

# 3. Create new local entities for unlinked external records
for ext_id in unlinked_external:
    external_entity = get_external_by_id('NYC_CARTO', ext_id)
    
    # Create local master
    local_id = mgr.create_master_entity(
        entity_type='sidewalk_segment',
        external_entity  # Use external as source
    )
    
    # Link directly
    reconciler._create_link(local_id, 'NYC_CARTO', ext_id, 0.9)

# 4. Review for potential duplicates among unlinked local records
for local_id in unlinked_local:
    entity = mgr.get_master_entity(local_id)
    print(f"Unlinked: {entity.entity_id} - {entity.canonical_record.get('name')}")
    # May be new entity or matching issue
```

## Best Practices

### 1. Gradual Reconciliation

Don't merge all at once; start with high-confidence matches:

```python
# Phase 1: Link high-confidence matches only
report1 = reconciler.reconcile_to_external('NYC_CARTO', match_threshold=0.95)

# Phase 2: Manual review of medium-confidence
# (Generate report, have team review, add notes)

# Phase 3: Link medium-confidence after review
report2 = reconciler.reconcile_to_external('NYC_CARTO', match_threshold=0.80)
```

### 2. Preserve Discrepancies

Keep both local and external values when they differ:

```python
# Don't blindly trust external source
# Instead: note discrepancies for investigation

for conflict in report.conflicts:
    if conflict.field == 'condition_rating':
        # Keep investigating why external has different rating
        # This might indicate data quality issues in either system
        pass
```

### 3. Audit Trail

Document all reconciliation decisions:

```python
# Each link has created_by, created_at
link = reconciler.get_link_for_source(entity_id, 'NYC_CARTO')
print(f"Linked by {link.created_by} at {link.created_at}")
print(f"Last verified at {link.last_verified}")

# Update verification status when re-reconciling
link.last_verified = datetime.utcnow()
```

### 4. Handle Schema Differences

External sources may have different field names:

```python
# Custom mapping function
def map_carto_to_local(carto_record):
    return {
        'id': carto_record['globalid'],
        'name': carto_record['seg_name'],
        'block_id': carto_record['block_number'],
        'address': f"{carto_record['street_number']} {carto_record['street_name']}"
    }

external_data = [map_carto_to_local(r) for r in carto_raw_data]
reconciler.import_external_master('NYC_CARTO', external_data)
```

### 5. Periodic Re-reconciliation

External data changes over time; re-reconcile periodically:

```python
# Weekly reconciliation check
def reconcile_weekly():
    # Re-import latest external data
    external_data = fetch_latest_carto_data()
    reconciler.import_external_master('NYC_CARTO', external_data)
    
    # Re-reconcile
    report = reconciler.reconcile_to_external('NYC_CARTO')
    
    # Alert on changes
    if report.unlinked_local > previous_unlinked:
        print(f"Alert: More unlinked local entities detected")
    
    return report
```

## See Also

- [`entity_resolution.md`](entity_resolution.md) - Overall approach
- [`master_data_management.md`](master_data_management.md) - Master data patterns
- [`entity_matching_strategies.md`](entity_matching_strategies.md) - Matching strategies
