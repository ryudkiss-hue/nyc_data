# Deduplication Rules Guide

## Overview

Deduplication rules define how to identify duplicates in a specific entity type. Rules combine:
- A matching strategy (how to score pairs)
- Blocking keys (which records to compare)
- Thresholds (confidence needed to mark duplicates)
- Materialization mode (how to apply decisions)

## Rule Components

```python
from socrata_toolkit.deduplication import DeduplicationRule, MaterializationMode
from socrata_toolkit.entity_matching import FuzzyMatch

rule = DeduplicationRule(
    rule_id='sidewalk_segments_v1',
    entity_type='sidewalk_segment',
    matching_strategy=FuzzyMatch(
        fields=['block_id', 'address'],
        threshold=0.85
    ),
    threshold=0.85,                    # Min confidence to mark duplicates
    blocking_keys=['borough', 'block_id'],  # Pre-filter candidates
    materialization=MaterializationMode.SOFT,  # HARD=merge, SOFT=flag, REVIEW=queue
    enabled=True,
    max_group_size=100,
    description='Identify duplicate sidewalk segments by block and address'
)
```

## Built-in Rules

### Sidewalk Segments

```python
from socrata_toolkit.entity_matching import CompositeMatch, ExactMatch, FuzzyMatch, GeographicMatch

sidewalk_rule = DeduplicationRule(
    rule_id='sidewalk_segments',
    entity_type='sidewalk_segment',
    matching_strategy=CompositeMatch([
        (ExactMatch(fields=['block_id']), 0.5),
        (FuzzyMatch(fields=['street_name'], threshold=0.85), 0.3),
        (GeographicMatch(distance_threshold_m=10.0), 0.2)
    ]),
    threshold=0.85,
    blocking_keys=['borough', 'block_id'],
    materialization=MaterializationMode.REVIEW
)
```

**Rationale**: Block ID is most reliable, but street name variations and geographic proximity also indicate duplicates.

### 311 Complaints

```python
complaint_rule = DeduplicationRule(
    rule_id='complaints_311',
    entity_type='complaint',
    matching_strategy=CompositeMatch([
        (GeographicMatch(distance_threshold_m=50.0), 0.4),
        (TemporalMatch(max_gap_days=7), 0.3),
        (FuzzyMatch(fields=['complaint_type', 'description'], threshold=0.8), 0.3)
    ]),
    threshold=0.80,
    blocking_keys=['borough', 'complaint_type'],
    materialization=MaterializationMode.REVIEW
)
```

**Rationale**: Same location + similar time + similar description = likely duplicate complaint.

### Contractors

```python
contractor_rule = DeduplicationRule(
    rule_id='contractors',
    entity_type='contractor',
    matching_strategy=CompositeMatch([
        (PhoneticMatch(fields=['name']), 0.5),
        (ExactMatch(fields=['license_number']), 0.4),
        (FuzzyMatch(fields=['email', 'phone'], threshold=0.9), 0.1)
    ]),
    threshold=0.85,
    blocking_keys=['borough'],
    materialization=MaterializationMode.SOFT
)
```

**Rationale**: Phonetic matching for name variations, exact license match, and contact info confirmation.

### Inspections

```python
inspection_rule = DeduplicationRule(
    rule_id='inspections',
    entity_type='inspection',
    matching_strategy=CompositeMatch([
        (ExactMatch(fields=['property_id']), 0.4),
        (TemporalMatch(max_gap_days=1), 0.3),
        (ExactMatch(fields=['inspection_type']), 0.3)
    ]),
    threshold=0.95,  # Very strict
    blocking_keys=['property_id'],
    materialization=MaterializationMode.HARD
)
```

**Rationale**: Same property + same day + same type = almost certainly duplicate.

## Creating Custom Rules

### Step 1: Identify Key Fields

Determine which fields best identify entities:

```python
# For sidewalk segments:
# Most reliable: block_id (structural)
# Very reliable: address (reference)
# Fairly reliable: street_name (may have variations)
# Less reliable: condition (changes over time)

important_fields = ['block_id', 'address', 'street_name']
```

### Step 2: Choose Matching Strategy

```python
# Start with simple strategy
simple = FuzzyMatch(fields=['address'], threshold=0.85)

# If not sufficient, use composite
from socrata_toolkit.entity_matching import CompositeMatch

composite = CompositeMatch([
    (ExactMatch(fields=['block_id']), 0.6),
    (FuzzyMatch(fields=['address'], threshold=0.85), 0.4)
])
```

### Step 3: Determine Blocking Keys

Choose fields that partition records without losing duplicates:

```python
# Good: Geographic + categorical blocking
blocking_keys = ['borough', 'zip_code']

# Better: Multiple blocking keys
blocking_keys = ['borough', 'block_id', 'street_id']
```

### Step 4: Set Thresholds

Balance between false positives (mark non-duplicates as duplicates) and false negatives (miss actual duplicates):

```python
# Conservative (fewer false positives, more false negatives)
rule_conservative = DeduplicationRule(
    threshold=0.95,
    materialization=MaterializationMode.SOFT
)

# Moderate (balanced)
rule_moderate = DeduplicationRule(
    threshold=0.85,
    materialization=MaterializationMode.REVIEW
)

# Aggressive (more false positives, fewer false negatives)
rule_aggressive = DeduplicationRule(
    threshold=0.75,
    materialization=MaterializationMode.REVIEW
)
```

### Step 5: Choose Materialization Mode

- **HARD**: Automatically merge records (use after extensive testing)
- **SOFT**: Flag duplicates but don't merge (safest for new rules)
- **REVIEW**: Queue for manual review

```python
# New rule: use REVIEW mode
new_rule = DeduplicationRule(
    rule_id='new_rule',
    entity_type='entity_type',
    matching_strategy=...,
    threshold=0.85,
    blocking_keys=['key1', 'key2'],
    materialization=MaterializationMode.REVIEW
)
```

## Testing Rules

### Unit Test

```python
def test_sidewalk_dedup_rule():
    from socrata_toolkit.deduplication import Deduplicator
    
    dedup = Deduplicator()
    rule = create_sidewalk_rule()  # Your rule
    
    # Test case 1: Obvious duplicates
    records = [
        {'id': '1', 'block_id': '100', 'address': '123 Main St'},
        {'id': '2', 'block_id': '100', 'address': '123 Main Street'},
    ]
    
    groups = dedup.find_duplicates(records, rule)
    assert len(groups) > 0, "Should find obvious duplicates"
    assert groups[0].confidence_score > 0.85
    
    # Test case 2: Non-duplicates
    records = [
        {'id': '1', 'block_id': '100', 'address': '123 Main St'},
        {'id': '3', 'block_id': '200', 'address': '456 Oak Ave'},
    ]
    
    groups = dedup.find_duplicates(records, rule)
    assert len(groups) == 0, "Should not find false positives"
```

### Integration Test

```python
def test_rule_on_sample_dataset():
    from socrata_toolkit.deduplication import Deduplicator
    
    dedup = Deduplicator()
    rule = create_sidewalk_rule()
    
    # Load representative sample
    records = load_sample_data('sidewalk_segments', sample_size=1000)
    
    result = dedup.apply_rule(records, rule)
    
    # Verify reasonable results
    duplicate_rate = result.duplicates_found / result.total_records
    assert 0.01 < duplicate_rate < 0.20, f"Duplicate rate {duplicate_rate} seems unrealistic"
    
    # Check performance
    assert result.execution_time_seconds < 5.0, "Rule should complete quickly"
    
    # Manual review a sample
    print(f"Found {len(result.duplicate_groups)} duplicate groups")
    for i, group in enumerate(result.duplicate_groups[:5]):
        print(f"Group {i}: confidence={group.confidence_score:.3f}, " +
              f"records={len(group.duplicate_record_ids)}")
```

### Performance Benchmark

```python
def benchmark_rule():
    from socrata_toolkit.deduplication import Deduplicator
    import time
    
    dedup = Deduplicator()
    rule = create_sidewalk_rule()
    
    # Generate large dataset
    records = generate_test_records(n=10000)
    
    start = time.time()
    result = dedup.apply_rule(records, rule)
    elapsed = time.time() - start
    
    # Verify performance
    records_per_second = len(records) / elapsed
    print(f"Processed {records_per_second:.0f} records/second")
    assert records_per_second > 1000, "Performance too slow"
    
    # Check statistics
    stats = dedup.get_statistics()
    print(f"Average confidence: {stats['average_confidence']:.3f}")
    print(f"Largest group: {stats['max_group_size']} records")
```

## Rule Versioning

Rules evolve as understanding improves:

```python
# v1: Initial rule, conservative
rule_v1 = DeduplicationRule(
    rule_id='sidewalk_v1',
    threshold=0.95,
    ...
)

# v2: After manual review, slightly lower threshold
rule_v2 = DeduplicationRule(
    rule_id='sidewalk_v2',
    threshold=0.90,
    # + additional matching field
    ...
)

# v3: After further tuning
rule_v3 = DeduplicationRule(
    rule_id='sidewalk_v3',
    threshold=0.85,
    # + refined strategy
    ...
)

# Track which version is in production
PRODUCTION_RULE = rule_v3
```

## Monitoring Rules

### Track Rule Performance

```python
def monitor_rule_performance():
    dedup = Deduplicator()
    rule = get_production_rule('sidewalk_segments')
    
    # Run on latest data
    result = dedup.apply_rule(new_records, rule)
    
    # Log metrics
    log_metrics({
        'rule_id': rule.rule_id,
        'duplicate_rate': result.duplicates_found / result.total_records,
        'avg_confidence': np.mean([g.confidence_score for g in result.duplicate_groups]),
        'execution_time': result.execution_time_seconds,
        'timestamp': datetime.utcnow()
    })
    
    # Alert on anomalies
    if result.duplicates_found / result.total_records > 0.20:
        alert(f"High duplicate rate: {duplicate_rate:.1%}")
```

### Compare Rules

```python
def compare_rules(rule1, rule2, test_data):
    dedup = Deduplicator()
    
    result1 = dedup.apply_rule(test_data, rule1)
    result2 = dedup.apply_rule(test_data, rule2)
    
    print(f"Rule 1 ({rule1.rule_id})")
    print(f"  Groups: {len(result1.duplicate_groups)}")
    print(f"  Avg confidence: {np.mean([g.confidence_score for g in result1.duplicate_groups]):.3f}")
    print(f"  Time: {result1.execution_time_seconds:.2f}s")
    
    print(f"Rule 2 ({rule2.rule_id})")
    print(f"  Groups: {len(result2.duplicate_groups)}")
    print(f"  Avg confidence: {np.mean([g.confidence_score for g in result2.duplicate_groups]):.3f}")
    print(f"  Time: {result2.execution_time_seconds:.2f}s")
```

## Best Practices

1. **Start Conservative**: Use high threshold and REVIEW mode initially
2. **Test Thoroughly**: Unit test, integration test, performance test
3. **Monitor Production**: Track metrics and alert on anomalies
4. **Document Decisions**: Why these fields? Why this threshold?
5. **Version Rules**: Track evolution as understanding improves
6. **Manual Review**: Always review sample of flagged duplicates
7. **Incremental Rollout**: Test on small sample before full dataset
8. **Feedback Loop**: Use reviewer feedback to improve rules

## See Also

- [`entity_resolution.md`](entity_resolution.md) - Overall approach
- [`entity_matching_strategies.md`](entity_matching_strategies.md) - Matching strategies
- [`master_data_management.md`](master_data_management.md) - Master data patterns
