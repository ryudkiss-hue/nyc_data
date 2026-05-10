# Entity Matching Strategies Guide

## Overview

Matching strategies are algorithms that compare two records and produce a confidence score (0.0-1.0) indicating similarity. Different strategies excel at different types of comparisons.

## Strategy Comparison Matrix

| Strategy | Field Types | Typo Tolerant | Word Order | Speed | Confidence |
|----------|------------|---------------|-----------|-------|------------|
| ExactMatch | All | No | No | ⚡⚡⚡ | Very High |
| FuzzyMatch | Text | Yes | Yes | ⚡⚡ | High |
| PhoneticMatch | Names | Yes | N/A | ⚡⚡ | Medium |
| GeographicMatch | Coordinates | N/A | N/A | ⚡⚡⚡ | Very High |
| TemporalMatch | Dates | N/A | N/A | ⚡⚡⚡ | High |
| SemanticMatch | Standardized | No | No | ⚡⚡ | Medium |
| CompositeMatch | Multiple | Varies | Varies | ⚡ | Very High |

## Exact Match

**Best for**: Primary keys, IDs, exact values

Matches only when field values are identical (after normalization).

### Usage

```python
from socrata_toolkit.entity_matching import ExactMatch

matcher = ExactMatch(
    fields=['block_id', 'condo_id'],
    case_sensitive=False,
    normalize=True
)

score = matcher.score(record1, record2)
# Returns 1.0 if all fields match, 0.0 otherwise
```

### Parameters

- `fields`: List of fields to match on
- `case_sensitive`: Whether comparison is case-sensitive (default: False)
- `normalize`: Remove diacritics and extra whitespace (default: True)
- `field_weights`: Optional weights for each field (must sum to 1.0)

### Examples

```python
# Sidewalk segment matching by block ID
exact_match = ExactMatch(
    fields=['block_id'],
    threshold=1.0
)

# Multi-field exact match with weights
multi_exact = ExactMatch(
    fields=['block_id', 'street_name'],
    field_weights={'block_id': 0.8, 'street_name': 0.2}
)
```

## Fuzzy Match

**Best for**: Names, addresses, text with typos and variations

Uses token-based string similarity (Jaro-Winkler, token set ratio) to handle spelling variations.

### Usage

```python
matcher = FuzzyMatch(
    fields=['name', 'address'],
    threshold=0.85,
    algorithm='token_set_ratio'
)
```

### Algorithms

- `ratio`: Simple character-based Levenshtein ratio
- `token_set_ratio`: Token-based, handles word order variations
- `jaro_winkler`: Jaro-Winkler distance (built-in implementation)

### Examples

```python
# Address matching
address_match = FuzzyMatch(
    fields=['address'],
    algorithm='token_set_ratio',
    threshold=0.8
)

# Name matching with lower threshold
name_match = FuzzyMatch(
    fields=['first_name', 'last_name'],
    field_weights={'first_name': 0.6, 'last_name': 0.4},
    threshold=0.75
)

# Composite matching on address
composite = FuzzyMatch(
    fields=['street_address', 'borough', 'zip_code'],
    threshold=0.82
)
```

## Phonetic Match

**Best for**: Names, addresses with spelling variations

Uses Soundex algorithm to match names with similar pronunciations.

### Usage

```python
matcher = PhoneticMatch(
    fields=['name'],
    threshold=0.8
)
```

### Examples

```python
# Matches: Smith, Smythe, Smyth
phonetic = PhoneticMatch(
    fields=['last_name'],
    threshold=1.0
)

# Matches: John, Jon, Jean
first_name_phonetic = PhoneticMatch(
    fields=['first_name'],
    threshold=0.8
)
```

### Limitations

- Best for English names
- Works on first word only for multi-word fields
- Limited to ~50% false negative rate

## Geographic Match

**Best for**: Location-based matching (coordinates, addresses)

Uses Haversine distance formula to match records within geographic proximity.

### Usage

```python
matcher = GeographicMatch(
    lat_field='latitude',
    lon_field='longitude',
    distance_threshold_m=10.0
)
```

### Parameters

- `lat_field`: Field name for latitude
- `lon_field`: Field name for longitude
- `distance_threshold_m`: Maximum distance in meters
- `threshold`: Confidence threshold

### Examples

```python
# Exact location match (within 5m)
geo_strict = GeographicMatch(
    distance_threshold_m=5.0
)

# Fuzzy location match (within 50m)
geo_loose = GeographicMatch(
    distance_threshold_m=50.0,
    threshold=0.5
)

# Sidewalk segment matching
segment_match = GeographicMatch(
    lat_field='midpoint_latitude',
    lon_field='midpoint_longitude',
    distance_threshold_m=20.0
)
```

### Coordinate Systems

- Supports WGS84 (latitude/longitude)
- Handles pole wrap (e.g., longitude -180 to 180)
- Returns 0.0 for invalid coordinates (null, 0,0)

## Temporal Match

**Best for**: Activity periods, event times, date ranges

Matches records with overlapping or proximate time periods.

### Usage

```python
matcher = TemporalMatch(
    start_field='start_date',
    end_field='end_date',
    max_gap_days=30
)
```

### Parameters

- `start_field`: Field with range start
- `end_field`: Field with range end
- `max_gap_days`: Maximum gap between ranges
- `threshold`: Confidence threshold

### Examples

```python
# Construction projects with overlapping periods
project_match = TemporalMatch(
    start_field='construction_start',
    end_field='construction_end'
)

# Inspections within 30 days
inspection_match = TemporalMatch(
    start_field='inspection_date',
    end_field='inspection_date',  # Same-day comparison
    max_gap_days=30
)

# Complaint period overlap
complaint_match = TemporalMatch(
    start_field='issue_start_date',
    end_field='issue_end_date',
    max_gap_days=7
)
```

## Semantic Match

**Best for**: Standardized field variations (street names, material types)

Matches based on synonym mapping and standardization rules.

### Usage

```python
matcher = SemanticMatch(
    fields=['street_name'],
    synonym_map={
        '1st': ['first', '1', '1st'],
        'street': ['st', 'str', 'street']
    }
)
```

### Examples

```python
# Street name standardization
street_match = SemanticMatch(
    fields=['street_name'],
    synonym_map={
        '1st': ['first', '1', '1st'],
        '2nd': ['second', '2', '2nd'],
        '3rd': ['third', '3', '3rd'],
        'avenue': ['ave', 'av', 'avenue'],
        'boulevard': ['blvd', 'boulevard'],
    }
)

# Material type standardization
material_match = SemanticMatch(
    fields=['surface_material'],
    synonym_map={
        'concrete': ['conc', 'concrete', 'cement'],
        'asphalt': ['asph', 'asphalt', 'blacktop'],
        'brick': ['brick', 'pavers', 'paver']
    }
)

# Borough standardization
borough_match = SemanticMatch(
    fields=['borough'],
    synonym_map={
        'manhattan': ['manhattan', 'ny', '1'],
        'brooklyn': ['brooklyn', 'bk', '3'],
        'queens': ['queens', 'qns', '4'],
    }
)
```

## Composite Match

**Best for**: Complex matching combining multiple signals

Weighted combination of multiple matching strategies for high-confidence results.

### Usage

```python
from socrata_toolkit.entity_matching import CompositeMatch, ExactMatch, FuzzyMatch

composite = CompositeMatch([
    (ExactMatch(fields=['block_id']), 0.4),
    (FuzzyMatch(fields=['address']), 0.6)
])
```

### Examples

```python
# Sidewalk segment matching
segment_match = CompositeMatch([
    (ExactMatch(fields=['block_id']), 0.5),
    (GeographicMatch(distance_threshold_m=10.0), 0.3),
    (FuzzyMatch(fields=['street_name'], threshold=0.85), 0.2)
])

# Person/contractor matching
person_match = CompositeMatch([
    (PhoneticMatch(fields=['last_name']), 0.4),
    (FuzzyMatch(fields=['first_name'], threshold=0.85), 0.3),
    (ExactMatch(fields=['phone_number']), 0.3)
])

# Complaint matching
complaint_match = CompositeMatch([
    (ExactMatch(fields=['complaint_id']), 0.3),
    (GeographicMatch(distance_threshold_m=50.0), 0.3),
    (TemporalMatch(max_gap_days=7), 0.2),
    (FuzzyMatch(fields=['description'], threshold=0.8), 0.2)
])
```

## Choosing Strategies

### For Sidewalk Segments

```python
# Strict matching: exact block_id
exact = ExactMatch(fields=['block_id'])

# Flexible matching: block_id + fuzzy street name + nearby geography
composite = CompositeMatch([
    (ExactMatch(fields=['block_id']), 0.5),
    (FuzzyMatch(fields=['street_name'], threshold=0.85), 0.3),
    (GeographicMatch(distance_threshold_m=10.0), 0.2)
])
```

### For Contractors

```python
# Name-based matching with phonetic tolerance
composite = CompositeMatch([
    (PhoneticMatch(fields=['name']), 0.5),
    (ExactMatch(fields=['license_number']), 0.4),
    (SemanticMatch(fields=['borough']), 0.1)
])
```

### For 311 Complaints

```python
# Location + time + description
composite = CompositeMatch([
    (GeographicMatch(distance_threshold_m=50.0), 0.4),
    (TemporalMatch(max_gap_days=7), 0.3),
    (FuzzyMatch(fields=['complaint_type', 'description'], threshold=0.8), 0.3)
])
```

## Performance Considerations

- **ExactMatch**: O(1) per comparison, fastest
- **FuzzyMatch**: O(n·m) where n,m = string lengths
- **GeographicMatch**: O(1) per comparison
- **CompositeMatch**: Sum of component strategies

### Optimization Tips

1. **Use exact matching first**: Eliminates 80%+ of pairs
2. **Chain simpler strategies**: ExactMatch → FuzzyMatch → Manual Review
3. **Filter before fuzzy**: Geographic or blocking filters reduce fuzzy work
4. **Cache similarity scores**: Avoid recomputing same pairs
5. **Parallel matching**: Score multiple pairs concurrently

## Testing Strategies

```python
# Unit test a matcher
def test_fuzzy_match():
    matcher = FuzzyMatch(fields=['name'], threshold=0.85)
    
    # Should match
    assert matcher.score(
        {'name': 'John Doe'},
        {'name': 'Jon Doe'}
    ) > 0.85
    
    # Should not match
    assert matcher.score(
        {'name': 'John Doe'},
        {'name': 'Jane Smith'}
    ) < 0.85

# Benchmark matcher performance
import time
start = time.time()
for record1, record2 in test_pairs:
    matcher.score(record1, record2)
elapsed = time.time() - start
print(f"{len(test_pairs)} comparisons in {elapsed:.3f}s")
```

## See Also

- [`entity_resolution.md`](entity_resolution.md) - Overall entity resolution guide
- [`master_data_management.md`](master_data_management.md) - Master data patterns
- [`deduplication_rules.md`](deduplication_rules.md) - Creating rules
