# Missing Exports Diagnostic Report
## NYC Data Project - Stub Module Analysis

**Generated:** May 11, 2026  
**Analysis Tool:** Custom Python import scanner  
**Scope:** socrata_toolkit/ stub modules + all import locations

---

## EXECUTIVE SUMMARY

### Critical Findings
- **11 missing symbols** identified across **6 stub modules**
- **100% of missing symbols** are being actively imported (not theoretical)
- Stubs were created with placeholder implementations but incomplete public APIs
- All missing symbols are actively being imported by test files and internal modules

### Error Impact
- **BEFORE stub creation:** 357 errors
- **AFTER stub creation:** 408 errors (+51)
- **Root cause:** Stubs export wrong symbols; imports reference different names

---

## DETAILED MODULE-BY-MODULE MAPPING

### 1. socrata_toolkit.scd_type2
**Status:** ❌ CRITICAL - 3 missing symbols  
**Import Location:** `tests/test_cdc.py` (line 21)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `SCDRecord` | Class | ❌ NO | CDC record wrapper |
| `SCDType2Manager` | Class | ❌ NO | Main SCD Type 2 manager |
| `DMLType` | Enum/Class | ❌ NO | DML operation type enum |

#### Current Stub Exports
```python
__all__ = ["SCDType2Handler", "generate_scd_type2_changes"]
```

#### What's Being Imported
```python
# tests/test_cdc.py (line 21)
from socrata_toolkit.scd_type2 import SCDRecord, SCDType2Manager, DMLType
```

#### Diagnosis
The stub was created with generic `SCDType2Handler` but test expects specific `SCDType2Manager` and supporting classes. The naming mismatch suggests:
- Original module had `SCDType2Manager` (manager pattern)
- Stub wrongly created `SCDType2Handler` (handler pattern)
- `SCDRecord` dataclass missing entirely
- `DMLType` enum missing entirely

---

### 2. socrata_toolkit.temporal_queries
**Status:** ❌ CRITICAL - 3 missing symbols  
**Import Location:** `tests/test_cdc.py` (line 24)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `TemporalQuery` | Class | ❌ NO | Query object class |
| `ChangeSummary` | Class | ❌ NO | Summary of changes |
| `ChangePattern` | Class | ❌ NO | Pattern of changes |

#### Current Stub Exports
```python
__all__ = ["TemporalQueryEngine", "get_historical_states"]
```

#### What's Being Imported
```python
# tests/test_cdc.py (line 24)
from socrata_toolkit.temporal_queries import TemporalQuery, ChangeSummary, ChangePattern
```

#### Diagnosis
The stub created `TemporalQueryEngine` but test expects `TemporalQuery` object class. Missing:
- `TemporalQuery` - main query object class
- `ChangeSummary` - data class for summarizing changes
- `ChangePattern` - data class for change patterns

---

### 3. socrata_toolkit.soft_delete
**Status:** ❌ CRITICAL - 2 missing symbols  
**Import Location:** `tests/test_cdc.py` (line 25)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `SoftDeleteManager` | Class | ❌ NO | Main deletion manager |
| `RetentionPolicy` | Class | ❌ NO | Retention configuration |

#### Current Stub Exports
```python
__all__ = ["SoftDeleteHandler", "restore_deleted_record"]
```

#### What's Being Imported
```python
# tests/test_cdc.py (line 25)
from socrata_toolkit.soft_delete import SoftDeleteManager, RetentionPolicy
```

#### Diagnosis
Naming pattern mismatch:
- Stub has `SoftDeleteHandler` but test expects `SoftDeleteManager`
- `RetentionPolicy` class completely missing
- Handler vs Manager pattern suggests refactoring mismatch

---

### 4. socrata_toolkit.quality_expectations
**Status:** ❌ HIGH - 1 missing symbol  
**Import Location:** `socrata_toolkit/quality_integration.py` (line 18)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `ExpectationSuite` | Class | ❌ NO | Suite/collection of expectations |

#### Current Stub Exports
```python
__all__ = ["QualityExpectation", "define_expectation", "validate_against_expectation"]
```

#### What's Being Imported
```python
# socrata_toolkit/quality_integration.py (line 18)
from socrata_toolkit.quality_expectations import ExpectationSuite
```

#### Diagnosis
`ExpectationSuite` is a container class that aggregates multiple `QualityExpectation` objects. Currently missing from stub. Stub has individual expectation but not the suite container.

---

### 5. socrata_toolkit.quality_validator
**Status:** ❌ HIGH - 1 missing symbol  
**Import Location:** `socrata_toolkit/quality_integration.py` (line 19)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `ValidationResult` | Class | ❌ NO | Result object from validation |

#### Current Stub Exports
```python
__all__ = ["QualityValidator", "run_validation"]
```

#### What's Being Imported
```python
# socrata_toolkit/quality_integration.py (line 19)
from socrata_toolkit.quality_validator import QualityValidator, ValidationResult
```

#### Diagnosis
`ValidationResult` dataclass missing. Stub only has validator but not result object that validator produces.

---

### 6. socrata_toolkit.qgis_compatibility
**Status:** ❌ HIGH - 1 missing symbol  
**Import Location:** `tests/test_spatial.py` (line 37)

#### Missing Exports Required
| Symbol | Type | Current Stub Has | Usage |
|--------|------|-----------------|-------|
| `QGISCompatibilityManager` | Class | ❌ NO | Manager class for QGIS operations |

#### Current Stub Exports
```python
__all__ = ["QGISAdapter", "export_to_qgis"]
```

#### What's Being Imported
```python
# tests/test_spatial.py (line 37)
from socrata_toolkit.qgis_compatibility import QGISCompatibilityManager
```

#### Diagnosis
Same pattern as soft_delete: stub has `QGISAdapter` but test expects `QGISCompatibilityManager`. Adapter vs Manager naming mismatch.

---

## ADDITIONAL MISSING SYMBOLS (Non-stub, non-critical)

These are NOT in stub modules but are still missing:

| Symbol | Module | Count | Why |
|--------|--------|-------|-----|
| `LineageRecorder` | socrata_toolkit.lineage | 3x | Missing from lineage.py |
| `AlertManager` | socrata_toolkit.observability | 3x | Missing from observability.py |
| `DATASETS` | socrata_toolkit.nyc_datasets | 3x | Module doesn't exist |
| `PRIORITY_COLORS` | socrata_toolkit.task_board | 3x | Module doesn't exist |
| `CATEGORY_COLORS` | socrata_toolkit.task_board | 3x | Module doesn't exist |
| `ASPH_STANDARD` | socrata_toolkit.material_definitions | 1x | Not exported |
| `CONC_STANDARD` | socrata_toolkit.material_definitions | 1x | Not exported |

---

## ROOT CAUSE ANALYSIS

### Pattern 1: Naming Mismatch (Handler vs Manager)
Affects: `scd_type2`, `soft_delete`, `qgis_compatibility`

**Issue:** Stubs use `-Handler` naming convention, but imports expect `-Manager`
```python
# Stub creates:
class SCDType2Handler
class SoftDeleteHandler

# But code imports:
SCDType2Manager
SoftDeleteManager
```

### Pattern 2: Missing Data Classes/Results
Affects: `scd_type2`, `temporal_queries`, `soft_delete`, `quality_validator`

**Issue:** Stubs have only one class, but imports expect multiple supporting classes
```python
# Stub has:
class SCDType2Handler

# But test expects:
SCDRecord          # ← Missing data class
SCDType2Manager    # ← Missing manager
DMLType            # ← Missing enum
```

### Pattern 3: Container/Suite Classes Missing
Affects: `quality_expectations`

**Issue:** Stub has individual expectation but not the suite container
```python
# Stub has:
class QualityExpectation

# But test expects:
ExpectationSuite   # ← Container for multiple expectations
```

---

## PRIORITY FIXING ORDER

### Priority 1 - CRITICAL (Fix First)
These block entire test modules:

1. **socrata_toolkit.scd_type2** - 3 missing
   - Required by: `tests/test_cdc.py`
   - Fix: Add `SCDRecord`, `SCDType2Manager` (rename Handler), `DMLType`

2. **socrata_toolkit.temporal_queries** - 3 missing
   - Required by: `tests/test_cdc.py`
   - Fix: Add `TemporalQuery`, `ChangeSummary`, `ChangePattern`

3. **socrata_toolkit.soft_delete** - 2 missing
   - Required by: `tests/test_cdc.py`
   - Fix: Rename `SoftDeleteHandler` → `SoftDeleteManager`, add `RetentionPolicy`

### Priority 2 - HIGH (Fix Next)
These block integration modules:

4. **socrata_toolkit.quality_expectations** - 1 missing
   - Required by: `socrata_toolkit/quality_integration.py`
   - Fix: Add `ExpectationSuite` class

5. **socrata_toolkit.quality_validator** - 1 missing
   - Required by: `socrata_toolkit/quality_integration.py`
   - Fix: Add `ValidationResult` dataclass

6. **socrata_toolkit.qgis_compatibility** - 1 missing
   - Required by: `tests/test_spatial.py`
   - Fix: Rename `QGISAdapter` → `QGISCompatibilityManager` OR add as alias

---

## VERIFICATION CHECKLIST

### scd_type2.py
- [ ] Export `SCDRecord` dataclass
- [ ] Export `SCDType2Manager` class (or rename from Handler)
- [ ] Export `DMLType` enum
- [ ] Update `__all__` to include all three

### temporal_queries.py
- [ ] Export `TemporalQuery` class
- [ ] Export `ChangeSummary` dataclass
- [ ] Export `ChangePattern` dataclass
- [ ] Update `__all__` to include all three

### soft_delete.py
- [ ] Rename or alias `SoftDeleteHandler` → `SoftDeleteManager`
- [ ] Export `RetentionPolicy` class
- [ ] Update `__all__` to reflect correct names

### quality_expectations.py
- [ ] Add `ExpectationSuite` class
- [ ] Update `__all__` to include `ExpectationSuite`

### quality_validator.py
- [ ] Add `ValidationResult` dataclass
- [ ] Update `__all__` to include `ValidationResult`

### qgis_compatibility.py
- [ ] Rename or alias `QGISAdapter` → `QGISCompatibilityManager`
- [ ] Update `__all__` to match expected names

---

## EXPECTED OUTCOME

After adding missing exports:
- **reportAttributeAccessIssue errors should drop** from 321 to ~280 (41 fixed)
- **Total error count should improve** from 408 toward 357 baseline
- **test_cdc.py** will stop blocking on missing scd_type2, temporal_queries, soft_delete imports
- **quality_integration.py** will resolve all expectation/validator import issues
- **test_spatial.py** will resolve QGIS compatibility manager import

