# Entity Resolution and Deduplication System

## Overview

The entity resolution system provides production-grade deduplication and master data management for identifying duplicate records, creating canonical entities, and reconciling to external data sources.

### Key Capabilities

- **Multi-strategy matching**: Exact, fuzzy, phonetic, geographic, temporal, semantic, and composite
- **Scalable deduplication**: Blocking algorithms reduce O(n²) comparisons to near-linear
- **Master data management**: Canonical entity creation with field-level provenance
- **Manual review workflow**: Human validation and override of automated decisions
- **Incremental matching**: New records matched against existing masters
- **Reconciliation**: Link to external systems (NYC CARTO, etc.)
- **Entity relationships**: Track contains/belongs_to/adjacent_to relationships
- **Comprehensive audit trail**: All decisions logged for compliance

## Architecture

### Core Modules

```
socrata_toolkit/
├── entity_matching.py       # Matching strategies
├── deduplication.py          # Deduplication engine with blocking
├── master_data.py            # Master data management
├── entity_blocking.py        # Blocking algorithms for scalability
├── entity_incremental.py     # Incremental matching for new records
├── entity_review.py          # Manual review workflow
├── entity_reconciliation.py  # Reconciliation with external masters
└── entity_relationships.py   # Entity relationship graph
```

### Data Flow

```
Raw Records
    ↓
Blocking (O(n) candidate pairs)
    ↓
Matching (score all candidates)
    ↓
Clustering (group matches into duplicate groups)
    ↓
Master Data Creation (canonical entities)
    ↓
Manual Review (if confidence < threshold)
    ↓
Audit Trail (record all decisions)
```

## Usage Examples

### Basic Deduplication

```python
from socrata_toolkit.deduplication import Deduplicator, DeduplicationRule
from socrata_toolkit.entity_matching import FuzzyMatch

# Create deduplicator
dedup = Deduplicator()

# Define rule
rule = DeduplicationRule(
    rule_id='sidewalk_segments',
    entity_type='sidewalk_segment',
    matching_strategy=FuzzyMatch(
        fields=['block_id', 'address'],
        threshold=0.85
    ),
    blocking_keys=['borough', 'block_id'],
    threshold=0.85
)

# Find duplicates
duplicate_groups = dedup.find_duplicates(records, rule)

for group in duplicate_groups:
    print(f"Found {len(group.duplicate_record_ids)} duplicates")
    print(f"Confidence: {group.confidence_score:.3f}")
```

### Master Data Creation

```python
from socrata_toolkit.master_data import MasterDataManager, EntityMergeStrategy

mgr = MasterDataManager()

# Create master entity from duplicates
entity_id = mgr.create_master_entity(
    entity_type='sidewalk_segment',
    record1={'id': '1', 'block_id': '100', 'address': '1st Street'},
    record2={'id': '2', 'block_id': '100', 'address': 'First Street'},
    merge_strategy=EntityMergeStrategy.PICK_LATEST
)

# Query master
entity = mgr.get_master_entity(entity_id)
print(f"Master: {entity.canonical_record}")
print(f"Sources: {entity.source_record_ids}")
print(f"Confidence: {entity.confidence_by_field}")
```

### Incremental Matching

```python
from socrata_toolkit.entity_incremental import IncrementalMatcher

matcher = IncrementalMatcher(
    mgr,
    auto_assign_threshold=0.95,
    review_threshold=0.70
)

# Match new record
result = matcher.match_against_existing(new_record)

if result.decision == MatchDecision.AUTO_ASSIGNED:
    print(f"Auto-assigned to {result.matched_entity_id}")
elif result.decision == MatchDecision.QUEUED_FOR_REVIEW:
    print(f"Queued for review with candidates: {result.candidate_matches}")
else:
    print(f"No match found, will create new entity")
```

### Manual Review

```python
from socrata_toolkit.entity_review import ReviewWorkflow, ReviewDecision

workflow = ReviewWorkflow()

# Get pending cases
cases = workflow.get_unresolved_cases()

for case in cases:
    # Assign to reviewer
    workflow.assign_case(case.case_id, reviewer='alice')
    
    # Reviewer makes decision
    workflow.submit_decision(
        case.case_id,
        ReviewDecision.MATCH,
        reviewer='alice',
        notes='Names are clearly the same'
    )

# Get metrics
stats = workflow.get_statistics()
print(f"Reviewed: {stats.completed_cases}")
print(f"Match rate: {stats.match_rate:.1f}%")
```

### Reconciliation with External Masters

```python
from socrata_toolkit.entity_reconciliation import Reconciler

reconciler = Reconciler(mgr)

# Import external data
external_data = [...]  # From NYC CARTO, DOT systems, etc.
reconciler.import_external_master('NYC_CARTO', external_data)

# Reconcile
report = reconciler.reconcile_to_external('NYC_CARTO')
print(f"Matched: {report.matched_count}")
print(f"Unlinked local: {report.unlinked_local}")
print(f"Unlinked external: {report.unlinked_external}")

# Handle recommendations
for rec in report.recommendations:
    print(f"- {rec}")
```

### Entity Relationships

```python
from socrata_toolkit.entity_relationships import RelationshipGraph, RelationshipType

graph = RelationshipGraph()

# Add relationships
graph.add_relationship('block_123', 'segment_456', RelationshipType.CONTAINS)
graph.add_relationship('street_456', 'block_123', RelationshipType.CONTAINS)

# Query relationships
segments = graph.get_related_entities('block_123', RelationshipType.CONTAINS)
print(f"Block contains {len(segments)} segments")

# Find paths
path = graph.find_path('street_456', 'segment_456')
print(f"Path: {' -> '.join(path)}")
```

## Matching Strategies

### ExactMatch
Best for: Primary keys, IDs, exact field values
```python
ExactMatch(
    fields=['block_id', 'condo_id'],
    threshold=1.0
)
```

### FuzzyMatch
Best for: Names, addresses, fields with typos
```python
FuzzyMatch(
    fields=['name', 'address'],
    threshold=0.85,
    algorithm='token_set_ratio'
)
```

### PhoneticMatch
Best for: Names with spelling variations (O'Brien, Obrien)
```python
PhoneticMatch(
    fields=['name'],
    threshold=0.8
)
```

### GeographicMatch
Best for: Location-based matching
```python
GeographicMatch(
    lat_field='latitude',
    lon_field='longitude',
    distance_threshold_m=10.0
)
```

### TemporalMatch
Best for: Activity periods, event times
```python
TemporalMatch(
    start_field='start_date',
    end_field='end_date',
    max_gap_days=30
)
```

### SemanticMatch
Best for: Standardized field variations (1st St vs First Street)
```python
SemanticMatch(
    fields=['street_name'],
    synonym_map={'1st': ['first', '1', '1st']}
)
```

### CompositeMatch
Best for: Combining multiple signals
```python
CompositeMatch([
    (ExactMatch(fields=['block_id']), 0.4),
    (FuzzyMatch(fields=['address']), 0.6)
])
```

## Merge Strategies

### PICK_FIRST
Use the first record's value for each field.

### PICK_LATEST
Use the most recently updated value (based on creation/update timestamps).

### PICK_MOST_COMMON
Use the most frequently occurring value across all records in group.

### WEIGHTED_AVERAGE
Average numeric fields, pick latest for strings.

### CUSTOM
Implement custom merge logic.

## Blocking Algorithms

For large datasets, blocking dramatically reduces comparison pairs:

| Algorithm | Complexity | Best For |
|-----------|-----------|----------|
| StandardBlocker | O(n) | Most datasets |
| SortedNeighborhoodBlocker | O(n log n) | Sorted/ordered keys |
| SuffixArrayBlocker | O(n) | Fuzzy blocking |
| CanopyBlocker | O(n) | Very large datasets |
| HybridBlocker | O(n) | Multiple signals |

Example:
```python
from socrata_toolkit.entity_blocking import StandardBlocker

blocker = StandardBlocker(blocking_keys=['borough', 'block_id'])
pairs = blocker.create_candidate_pairs(records)

stats = blocker.get_statistics()
print(f"Reduced {stats.total_possible_pairs} to {stats.candidate_pairs} pairs")
print(f"Reduction ratio: {stats.reduction_ratio:.1%}")
```

## Configuration

### Thresholds

- **auto_assign_threshold** (0.95): Automatically assign new records to masters
- **review_threshold** (0.70): Queue for manual review if >= threshold, < auto_assign
- **duplicate_threshold** (0.85): Minimum confidence to consider records duplicates

### Performance

- Deduplication of 1M records: < 10 minutes
- Memory: O(n) where n = number of records
- Candidate pair reduction: 95%+ typical

## Quality Metrics

```python
stats = dedup.get_statistics()
print(f"Total groups: {stats['total_groups']}")
print(f"Duplicate records: {stats['total_duplicate_records']}")
print(f"Average confidence: {stats['average_confidence']:.3f}")
```

## Best Practices

1. **Use blocking for large datasets**: Reduces execution from days to minutes
2. **Start conservative**: Use higher thresholds, manually review lower-confidence matches
3. **Combine strategies**: Use composite matching for better results
4. **Monitor agreement**: Track reviewer agreement with automation
5. **Test thoroughly**: Run benchmarks on representative samples
6. **Document decisions**: Keep notes on why records were/weren't matched
7. **Handle null values**: Strategies gracefully skip null fields
8. **Incremental updates**: Match new records against stable master data

## Troubleshooting

### High False Positive Rate
- Increase threshold in rule
- Use stricter matching strategy (Exact vs Fuzzy)
- Add more blocking keys
- Manually review and dispute incorrect matches

### High False Negative Rate
- Decrease threshold
- Use more lenient matching strategy
- Reduce blocking keys to catch more pairs
- Combine multiple strategies

### Performance Issues
- Enable blocking (StandardBlocker is usually sufficient)
- Reduce dataset size (process in batches)
- Use CanopyBlocker for very large datasets
- Profile with BlockStatistics

## See Also

- [`entity_matching_strategies.md`](entity_matching_strategies.md) - Detailed matching strategy documentation
- [`master_data_management.md`](master_data_management.md) - Master data best practices
- [`entity_reconciliation.md`](entity_reconciliation.md) - Reconciling to external masters
- [`deduplication_rules.md`](deduplication_rules.md) - Creating custom rules
