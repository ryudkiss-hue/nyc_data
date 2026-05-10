# Master Data Management Guide

## Overview

Master Data Management (MDM) creates and maintains canonical "master" entities from deduplicated source records. Each master entity represents a single real-world object with the best-known values for each field.

## Core Concepts

### Master Entity

A master entity is the authoritative version of a real-world object:

```python
MasterEntity(
    entity_id='entity_abc123',
    entity_type='sidewalk_segment',
    canonical_record={
        'block_id': '100',
        'address': '123 First Street',
        'material': 'concrete',
        'condition': 'fair'
    },
    source_record_ids=['rec1', 'rec2', 'rec3'],
    confidence_by_field={
        'block_id': 1.0,
        'address': 0.95,
        'material': 0.85,
        'condition': 0.75
    },
    field_provenance={
        'block_id': 'rec1',
        'address': 'rec2',
        'material': 'rec3',
        'condition': 'rec1'
    }
)
```

### Field Confidence

Each field has a confidence score (0-1) indicating how certain we are of that value:

- **1.0**: All source records agree, or single authoritative source
- **0.95**: Strong agreement (e.g., 95% of sources)
- **0.85**: Good agreement with some variance
- **0.70**: Moderate agreement, reconciliation recommended
- **< 0.70**: Low confidence, manual review needed

### Merge Strategies

Different strategies for resolving conflicts when multiple source records have different values:

#### PICK_FIRST
Use the first record's value (stable but may miss updates):
```python
mgr.create_master_entity(
    entity_type='person',
    record1, record2, record3,
    merge_strategy=EntityMergeStrategy.PICK_FIRST
)
# Uses record1's values for all fields
```

#### PICK_LATEST
Use most recently updated value (assumes timestamps reflect reality):
```python
mgr.create_master_entity(
    entity_type='sidewalk_segment',
    record1, record2, record3,
    merge_strategy=EntityMergeStrategy.PICK_LATEST
)
# Uses newest record's values
```

#### PICK_MOST_COMMON
Use most frequently occurring value across all sources (consensus):
```python
mgr.create_master_entity(
    entity_type='contractor',
    *records,  # Multiple records
    merge_strategy=EntityMergeStrategy.PICK_MOST_COMMON
)
# Each field uses the most common value
```

#### WEIGHTED_AVERAGE
Average numeric fields, pick latest for text:
```python
mgr.create_master_entity(
    entity_type='inspection',
    *inspection_records,
    merge_strategy=EntityMergeStrategy.WEIGHTED_AVERAGE
)
# Numeric fields (scores, measurements) are averaged
# Text fields use most recent value
```

#### CUSTOM
Implement custom merge logic:
```python
def custom_merge(records):
    canonical = {}
    confidence = {}
    provenance = {}
    
    # Custom logic per field
    canonical['block_id'] = records[0]['block_id']  # Always first
    confidence['block_id'] = 1.0
    provenance['block_id'] = records[0]['id']
    
    # ... more fields
    
    return canonical, confidence, provenance

mgr = MasterDataManager(custom_merge_func=custom_merge)
entity_id = mgr.create_master_entity(
    entity_type='sidewalk_segment',
    *records,
    merge_strategy=EntityMergeStrategy.CUSTOM
)
```

## Usage Patterns

### Creating Master Entities from Duplicates

```python
from socrata_toolkit.master_data import MasterDataManager, EntityMergeStrategy

mgr = MasterDataManager()

# Create master from duplicate records
entity_id = mgr.create_master_entity(
    entity_type='sidewalk_segment',
    {'id': '1', 'block_id': '100', 'address': '1st Street'},
    {'id': '2', 'block_id': '100', 'address': 'First Street'},
    {'id': '3', 'block_id': '100', 'address': '1 Street'},
    merge_strategy=EntityMergeStrategy.PICK_MOST_COMMON
)

# Query master
entity = mgr.get_master_entity(entity_id)
print(f"Canonical address: {entity.canonical_record['address']}")
print(f"Confidence: {entity.confidence_by_field['address']}")
```

### Adding Records to Existing Master

```python
# When a new matching record arrives
new_record = {'id': '4', 'block_id': '100', 'address': 'First St'}

success = mgr.add_record_to_entity(
    entity_id=entity_id,
    record=new_record,
    merge_strategy=EntityMergeStrategy.PICK_LATEST
)

# Master is re-merged with all source records including new one
```

### Validating Merges

```python
# Check if master meets quality standards
is_valid, issues = mgr.validate_merge(
    entity_id,
    required_fields=['block_id', 'address'],
    min_confidence=0.75
)

if not is_valid:
    for issue in issues:
        print(f"Issue: {issue}")
```

### Resolving Field Conflicts

```python
# When confidence is low, manually override
mgr.resolve_field_conflict(
    entity_id=entity_id,
    field='address',
    value='123 First Street',
    user='data_steward_123'
)

# Field is now marked as manually resolved (confidence = 1.0)
```

### Exporting Master Data

```python
# Export as records
masters = mgr.export_master_data(
    entity_type='sidewalk_segment',
    include_metadata=True
)

for master in masters:
    print(f"Entity: {master['entity_id']}")
    print(f"Address: {master['address']}")
    print(f"Metadata: {master['_master_metadata']}")
```

## Best Practices

### 1. Start Conservative
Begin with PICK_FIRST or PICK_LATEST (safer), then move to consensus-based strategies:

```python
# Phase 1: Conservative
rule = DeduplicationRule(
    threshold=0.95,  # Very high confidence
    materialization=MaterializationMode.SOFT  # Don't overwrite
)

# Phase 2: Consensus (after manual review)
mgr = MasterDataManager()
for group in duplicate_groups:
    mgr.create_master_entity(
        *source_records,
        merge_strategy=EntityMergeStrategy.PICK_MOST_COMMON
    )
```

### 2. Track Provenance
Always know where each field value came from:

```python
entity = mgr.get_master_entity(entity_id)

for field, value in entity.canonical_record.items():
    source = entity.field_provenance[field]
    confidence = entity.confidence_by_field[field]
    print(f"{field}: {value} (from {source}, confidence={confidence:.2f})")
```

### 3. Monitor Confidence
Flag low-confidence fields for review:

```python
entity = mgr.get_master_entity(entity_id)

low_confidence = [
    f for f, conf in entity.confidence_by_field.items()
    if conf < 0.80
]

if low_confidence:
    print(f"Fields needing review: {low_confidence}")
    # Queue for manual resolution
```

### 4. Implement Reconciliation
Regularly reconcile masters against external sources:

```python
from socrata_toolkit.entity_reconciliation import Reconciler

reconciler = Reconciler(mgr)
reconciler.import_external_master('NYC_CARTO', external_data)

report = reconciler.reconcile_to_external('NYC_CARTO')

for conflict in report.conflicts:
    if conflict.severity in ['high', 'critical']:
        # Manual review needed
        mgr.resolve_field_conflict(
            conflict.local_entity_id,
            conflict.field,
            # ... corrected value
        )
```

### 5. Audit Trail
Keep detailed records of all changes:

```python
entity = mgr.get_master_entity(entity_id)

print(f"Created: {entity.created_at}")
print(f"Last updated: {entity.last_updated}")
print(f"Version: {entity.version}")

for event in entity.merge_history:
    print(f"{event['timestamp']}: {event['action']} by {event.get('user', 'system')}")
```

### 6. Handle Null/Missing Values
Be explicit about missing data:

```python
# When merging, don't fill gaps with wrong values
mgr = MasterDataManager()

# Good: Preserve null when uncertain
entity = mgr.create_master_entity(
    entity_type='person',
    {'id': '1', 'email': 'john@example.com', 'phone': None},
    {'id': '2', 'email': None, 'phone': '555-1234'},
    merge_strategy=EntityMergeStrategy.CUSTOM  # Fill only confident values
)

# Check for nulls
missing = [
    f for f, v in entity.canonical_record.items()
    if v is None
]
```

## Performance Optimization

### Batch Creation

```python
from socrata_toolkit.master_data import MasterDataManager

mgr = MasterDataManager()

# Create many masters efficiently
for duplicate_group in duplicate_groups:
    records = get_source_records(duplicate_group)
    
    mgr.create_master_entity(
        entity_type=duplicate_group.entity_type,
        *records,
        merge_strategy=EntityMergeStrategy.PICK_LATEST
    )

print(f"Created {len(mgr._entities)} masters")
```

### Incremental Updates

```python
# Don't recreate entire master, just add new record
new_record = fetch_new_inspection()

mgr.add_record_to_entity(
    entity_id=existing_master_id,
    record=new_record,
    merge_strategy=EntityMergeStrategy.PICK_LATEST
)
# Much faster than re-merging from scratch
```

## Quality Metrics

```python
stats = mgr.get_statistics()

print(f"Total entities: {stats['total_entities']}")
print(f"Avg merge ratio: {stats['average_merge_ratio']:.2f}")
print(f"Average confidence: {stats['average_confidence']:.3f}")

# Identify weak entities
for entity_id, entity in mgr._entities.items():
    avg_conf = sum(entity.confidence_by_field.values()) / len(entity.confidence_by_field)
    if avg_conf < 0.75:
        print(f"Weak entity {entity_id}: confidence={avg_conf:.2f}")
```

## Integration with Pipelines

```python
# In your data pipeline
@deduplicate(rule='sidewalk_segments')
def process_sidewalk_data(records):
    dedup = Deduplicator()
    groups = dedup.find_duplicates(records, rule)
    
    mgr = MasterDataManager()
    for group in groups:
        sources = [records[i] for i in group.duplicate_record_ids]
        mgr.create_master_entity(
            entity_type='sidewalk_segment',
            *sources,
            merge_strategy=EntityMergeStrategy.PICK_LATEST
        )
    
    return mgr.export_master_data()
```

## See Also

- [`entity_resolution.md`](entity_resolution.md) - Overall approach
- [`entity_matching_strategies.md`](entity_matching_strategies.md) - Matching details
- [`entity_reconciliation.md`](entity_reconciliation.md) - External linking
