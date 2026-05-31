# Data Quality Dimensions

Six standard dimensions used to classify and score data quality findings. Every finding in a quality audit should be mapped to one of these dimensions.

---

## 1. Completeness
**Definition:** The degree to which required data is present and not missing.

| Aspect | Description |
|---|---|
| Null rate | % of null values in columns that should be populated |
| Record completeness | Are all expected records present (no missing entities)? |
| Attribute coverage | Are all required attributes populated for each record? |

**Scripts:** `null_counter.py`  
**Severity guide:** Missing mandatory fields (PK, FK, date) → CRITICAL; Optional fields above threshold → HIGH or MEDIUM.

---

## 2. Accuracy
**Definition:** The degree to which data correctly represents the real-world entity or event.

| Aspect | Description |
|---|---|
| Range validity | Values fall within expected business ranges (age 0–120, revenue ≥ 0) |
| Format validity | Dates are dates, emails contain @, codes match expected pattern |
| Cross-field consistency | Derived fields match their source calculation |
| Business logic compliance | Values follow business rules (e.g. end_date ≥ start_date) |

**Scripts:** `value_range_validator.py`  
**Severity guide:** Negative revenue → CRITICAL; Wrong date format → HIGH; Minor rounding error → LOW.

---

## 3. Consistency
**Definition:** The degree to which data is consistent across related datasets and over time.

| Aspect | Description |
|---|---|
| Referential integrity | FK values exist in the parent table |
| Cross-table consistency | Same entity represented consistently across tables |
| Temporal consistency | Historical records match current state for non-mutable attributes |
| Encoding consistency | Same concept encoded the same way (e.g. 'US' vs 'United States') |

**Scripts:** `referential_integrity.py`  
**Severity guide:** Orphaned FK rows in critical tables → CRITICAL; Inconsistent encoding → MEDIUM.

---

## 4. Timeliness (Freshness)
**Definition:** The degree to which data is available within the expected timeframe.

| Aspect | Description |
|---|---|
| Pipeline SLA | Latest record timestamp is within the agreed lag (e.g. < 25h for daily pipelines) |
| Backfill completeness | Historical data has been loaded without gaps |
| Event lag | Time between event occurring and event being recorded in the data warehouse |

**Scripts:** `freshness_check.py`  
**Severity guide:** Data older than 2× SLA → CRITICAL; Data older than 1.5× SLA → HIGH.

---

## 5. Uniqueness
**Definition:** The degree to which records and values appear exactly once where they should be unique.

| Aspect | Description |
|---|---|
| Primary key uniqueness | PK column has no duplicates |
| Natural key uniqueness | Business-natural key (e.g. order number) is unique |
| Full-row duplicates | No exact duplicate rows |
| Entity duplication | Same real-world entity represented as multiple records unintentionally |

**Scripts:** `duplicate_finder.py`  
**Severity guide:** Duplicate PKs → CRITICAL; Soft duplicates (same entity, different ID) → HIGH.

---

## 6. Validity
**Definition:** The degree to which values conform to defined formats, patterns, and value sets.

| Aspect | Description |
|---|---|
| Domain conformance | Values are within the defined set (e.g. status ∈ {active, churned, trial}) |
| Pattern conformance | Format matches expected pattern (e.g. phone numbers, postal codes) |
| Type conformance | Values are the correct data type for the column |

**Scripts:** `value_range_validator.py` (use `allowed` rules)  
**Severity guide:** Invalid values in a dimension used for filtering → HIGH; Display-only field with wrong format → LOW.

---

## Scoring a Data Asset

Use these dimensions to produce an overall quality score:

| Dimension | Weight | Score (0–10) | Weighted Score |
|---|---|---|---|
| Completeness | 20% | | |
| Accuracy | 20% | | |
| Consistency | 20% | | |
| Timeliness | 15% | | |
| Uniqueness | 15% | | |
| Validity | 10% | | |
| **Total** | **100%** | | **/ 10** |

Scoring guide:
- 0 = systematic failure (>50% of checks fail)
- 5 = half of checks pass; significant issues exist
- 8 = minor issues only; data is usable with documented caveats
- 10 = all checks pass; data meets or exceeds all thresholds
