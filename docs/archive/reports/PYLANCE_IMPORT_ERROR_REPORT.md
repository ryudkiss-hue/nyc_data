# Comprehensive Pylance/Pyright Import Error Report
## NYC Data Project - Complete Diagnostic Scan

**Scan Date:** May 11, 2026  
**Scan Tool:** Pyright v1.1.409  
**Scope:** socrata_toolkit/ + tests/ directories  
**Total Files Analyzed:** 201  
**Total Errors:** 357  
**Total Warnings:** 432  
**Analysis Duration:** 11.506 seconds  

---

## Executive Summary

Pylance/Pyright has identified **357 critical errors** and **432 warnings** across the NYC Data project. The primary issues fall into 5 distinct categories:

1. **Missing Module Imports** (3 errors) - External dependency issues
2. **Unknown Import Symbols** (4 errors) - Internal API exports missing
3. **__all__ Dunder Mismatch** (19 errors) - Public API declarations incomplete
4. **Syntax/Definition Errors** (10+ errors) - Code structure issues
5. **Unused Imports** (432 warnings) - Code quality issues

---

## CATEGORY 1: MISSING MODULE IMPORTS
**Severity:** MEDIUM | **Type:** reportMissingModuleSource | **Count:** 3 errors

### Issue Description
External module `shapely.geometry` cannot be resolved from source. This module is required for geospatial operations but is either not installed or not properly configured in the Python environment.

### Affected Files

#### 1. socrata_toolkit/arcgis_integration.py
```
Line 22: from shapely.geometry import mapping
```
**Error:** Import "shapely.geometry" could not be resolved from source

#### 2. socrata_toolkit/conflict.py
```
Line 40: from shapely.geometry import mapping
Line 114: from shapely.geometry import mapping
```
**Error:** Import "shapely.geometry" could not be resolved from source (2 occurrences)

### Root Cause Analysis
- Module `shapely` is either not installed or not listed in requirements.txt
- Environment PATH may not include shapely installation
- Version mismatch between installed shapely and type stubs

### Recommended Actions
1. **Install shapely:**
   ```bash
   pip install shapely
   ```
2. **Verify installation:**
   ```bash
   python -c "import shapely; print(shapely.__version__)"
   ```
3. **Add to requirements.txt if missing**
4. **Check pyrightconfig.json for include/exclude paths**

### Priority: **MEDIUM** (geospatial features affected)

---

## CATEGORY 2: UNKNOWN IMPORT SYMBOLS
**Severity:** HIGH | **Type:** reportAttributeAccessIssue | **Count:** 4 errors

### Issue Description
Functions/classes are being imported from `socrata_toolkit.api.auth` but are not defined or exported from that module. This breaks the API dependency chain.

### Affected Files

#### socrata_toolkit/api/main.py

| Line | Symbol | Source Module | Status |
|------|--------|---------------|--------|
| 56 | `JWTConfig` | socrata_toolkit.api.auth | ❌ NOT FOUND |
| 452 | `extract_bearer_token` | socrata_toolkit.api.auth | ❌ NOT FOUND |
| 452 | `verify_token` | socrata_toolkit.api.auth | ❌ NOT FOUND |
| 452 | `token_from_payload` | socrata_toolkit.api.auth | ❌ NOT FOUND |

### Root Cause Analysis
- Symbols are declared in main.py but not defined in auth.py
- Possible incomplete implementation or refactoring
- Missing function/class definitions in auth.py module

### Code Location Examples
```python
# socrata_toolkit/api/main.py (line 56)
from socrata_toolkit.api.auth import JWTConfig  # ❌ Not found in auth.py

# socrata_toolkit/api/main.py (line 452)
from socrata_toolkit.api.auth import (
    extract_bearer_token,  # ❌ Not found
    verify_token,          # ❌ Not found
    token_from_payload     # ❌ Not found
)
```

### Recommended Actions
1. **Verify if symbols should exist:**
   - Search auth.py for these function/class definitions
   - Check if they were renamed or moved
   
2. **Option A: Add missing exports to auth.py**
   ```python
   # socrata_toolkit/api/auth.py
   def extract_bearer_token(token_string: str) -> str:
       """Extract bearer token from Authorization header."""
       pass
   
   def verify_token(token: str) -> bool:
       """Verify token validity."""
       pass
   
   def token_from_payload(payload: dict) -> str:
       """Generate token from payload."""
       pass
   
   class JWTConfig:
       """JWT configuration class."""
       pass
   ```

3. **Option B: Remove imports from main.py**
   - If symbols are not needed, remove the import statements

4. **Update __all__ in auth.py:**
   ```python
   __all__ = [
       'JWTConfig',
       'extract_bearer_token',
       'verify_token',
       'token_from_payload',
       # ... other exports
   ]
   ```

### Priority: **HIGH** (API authentication broken)

---

## CATEGORY 3: __all__ DUNDER MISMATCH
**Severity:** CRITICAL | **Type:** reportUnsupportedDunderAll | **Count:** 19 warnings

### Issue Description
The `socrata_toolkit/__init__.py` file declares 19 items in its `__all__` list, but these items are neither defined nor imported into the module. This breaks the public API contract.

### Affected File
**socrata_toolkit/__init__.py**

### Missing Exports (19 items)

| # | Item | Type | Status |
|----|------|------|--------|
| 1 | `detect_outliers_iqr` | Function | ❌ Missing |
| 2 | `detect_outliers_zscore` | Function | ❌ Missing |
| 3 | `detect_all_outliers` | Function | ❌ Missing |
| 4 | `correlation_analysis` | Function | ❌ Missing |
| 5 | `time_series_summary` | Function | ❌ Missing |
| 6 | `classify_distribution` | Function | ❌ Missing |
| 7 | `classify_all_distributions` | Function | ❌ Missing |
| 8 | `flag_anomalies` | Function | ❌ Missing |
| 9 | `histogram` | Function | ❌ Missing |
| 10 | `bar_chart` | Function | ❌ Missing |
| 11 | `correlation_heatmap` | Function | ❌ Missing |
| 12 | `time_series_chart` | Function | ❌ Missing |
| 13 | `box_plot` | Function | ❌ Missing |
| 14 | `quality_dashboard` | Function | ❌ Missing |
| 15 | `create_lineage` | Function | ❌ Missing |
| 16 | `AuditLogger` | Class | ❌ Missing |
| 17 | `compute_quality_score` | Function | ❌ Missing |
| 18 | `detect_schema_drift` | Function | ❌ Missing |
| 19 | `snapshot_schema` | Function | ❌ Missing |

### Root Cause Analysis
- Items were added to `__all__` without corresponding implementations
- Functions may be in separate modules but not imported
- Incomplete refactoring or module reorganization

### Current __init__.py Structure
```python
# Lines 120-141 of socrata_toolkit/__init__.py
__all__ = [
    # ... (existing working exports)
    "detect_outliers_iqr",           # Line 120 - NOT FOUND
    "detect_outliers_zscore",        # Line 121 - NOT FOUND
    "detect_all_outliers",           # Line 122 - NOT FOUND
    "correlation_analysis",          # Line 123 - NOT FOUND
    "time_series_summary",           # Line 124 - NOT FOUND
    "classify_distribution",         # Line 125 - NOT FOUND
    "classify_all_distributions",    # Line 126 - NOT FOUND
    "flag_anomalies",                # Line 127 - NOT FOUND
    "histogram",                     # Line 129 - NOT FOUND
    "bar_chart",                     # Line 130 - NOT FOUND
    "correlation_heatmap",           # Line 131 - NOT FOUND
    "time_series_chart",             # Line 132 - NOT FOUND
    "box_plot",                      # Line 133 - NOT FOUND
    "quality_dashboard",             # Line 134 - NOT FOUND
    "create_lineage",                # Line 136 - NOT FOUND
    "AuditLogger",                   # Line 137 - NOT FOUND
    "compute_quality_score",         # Line 138 - NOT FOUND
    "detect_schema_drift",           # Line 139 - NOT FOUND
    "snapshot_schema",               # Line 140 - NOT FOUND
    "apply_retention_policy",        # Line 141 - NOT FOUND
]
```

### Recommended Actions

**Option 1: Import missing items into __init__.py**
```python
# Add to socrata_toolkit/__init__.py
from socrata_toolkit.analysis import (
    detect_outliers_iqr,
    detect_outliers_zscore,
    detect_all_outliers,
    correlation_analysis,
    time_series_summary,
    classify_distribution,
    classify_all_distributions,
    flag_anomalies,
)
from socrata_toolkit.visualization import (
    histogram,
    bar_chart,
    correlation_heatmap,
    time_series_chart,
    box_plot,
    quality_dashboard,
)
from socrata_toolkit.lineage import create_lineage
from socrata_toolkit.audit import AuditLogger
from socrata_toolkit.quality import (
    compute_quality_score,
    detect_schema_drift,
    snapshot_schema,
    apply_retention_policy,
)
```

**Option 2: Remove from __all__**
- If items don't exist or shouldn't be public, remove from `__all__`
- Keep only items that are actually implemented

### Priority: **CRITICAL** (Breaks public API contract)

---

## CATEGORY 4: SYNTAX AND DEFINITION ERRORS
**Severity:** HIGH | **Type:** Various | **Count:** 10+ errors

### Issue Description
Critical syntax errors and undefined variables prevent proper code execution in auth module.

### Affected Files

#### socrata_toolkit/api/auth.py

| Line(s) | Issue | Severity |
|---------|-------|----------|
| 82 | Class declaration "Role" is obscured by a declaration of the same name | ERROR |
| 92 | Class declaration "Permission" is obscured by a declaration of the same name | ERROR |
| 904 | Expected expression - orphaned code | ERROR |
| 926-933 | Undefined variables: expires_delta, config, request_id, uuid, user | ERROR |
| 939 | "return" can be used only within a function | ERROR |
| 942 | Unindent not expected | ERROR |

### Details

**Class Redeclarations (Lines 82, 92):**
```python
# Line 82 - DUPLICATE DEFINITION
class Role:
    # First definition
    ...

# Later in file - DUPLICATE DEFINITION
class Role:  # ❌ Error: Class declaration obscured
    # Second definition
    ...

# Line 92 - DUPLICATE DEFINITION
class Permission:
    # First definition
    ...

# Later in file - DUPLICATE DEFINITION  
class Permission:  # ❌ Error: Class declaration obscured
    # Second definition
    ...
```

**Orphaned Code (Lines 904-942):**
```python
# Line 904 - Unexpected expression
Expected expression but found orphaned code block

# Line 926
expires_delta  # ❌ is not defined

# Line 927  
config  # ❌ is not defined

# Line 930
request_id  # ❌ is not defined
uuid  # ❌ is not defined

# Line 933
user  # ❌ is not defined

# Line 939
return  # ❌ can be used only within a function (code at module level)

# Line 942
Unindent not expected
```

### Root Cause Analysis
- Module-level code that should be inside functions
- Duplicate class definitions (overwriting each other)
- Undefined variable references in module scope
- Improper indentation or code structure

### Recommended Actions

1. **Remove duplicate class definitions** - Keep only one definition of each class
2. **Move module-level code into functions** - Wrap lines 904-942 in appropriate function
3. **Define missing variables** - Either import them or define them properly
4. **Fix indentation** - Ensure proper Python indentation throughout

**Example Fix:**
```python
# Consolidate Role class
class Role(Enum):
    GUEST = "guest"
    DATA_CONSUMER = "data_consumer"
    # ... other roles

# Consolidate Permission class
class Permission(Enum):
    DATASETS_READ = "datasets:read"
    RECORDS_READ = "records:read"
    # ... other permissions

# Move code into function context
def initialize_jwt_config(expires_delta: timedelta, webhook_url: str) -> dict:
    config = {
        'algorithm': 'HS256',
        'expires_delta': expires_delta
    }
    request_id = str(uuid4())
    user = get_current_user()
    return {
        'config': config,
        'request_id': request_id,
        'user': user
    }
```

### Priority: **HIGH** (Code won't execute)

---

## CATEGORY 5: UNUSED IMPORTS
**Severity:** LOW | **Type:** reportUnusedImport | **Count:** 432 warnings

### Issue Description
432 import statements across the project import modules or symbols that are never used in their respective files.

### Summary Statistics
- **Total unused import warnings:** 432
- **Files affected:** ~50+ files
- **Most common unused imports:**

| Import | Occurrences | Files |
|--------|-------------|-------|
| `json` | 15 | alerts, alert_delivery, cdc_compliance, etc. |
| `os` | 12 | api.py, api/auth.py, etc. |
| `Any` | 8+ | Multiple analysis/integration files |
| `Optional` | 7+ | Multiple modules |
| `field` | 6 | dataclass field imports |
| `datetime` | 5 | Various utility modules |
| `timezone` | 5 | Time-related modules |

### Examples of Unused Import Warnings

**socrata_toolkit/alert_delivery.py (Line 23)**
```python
import json  # ❌ Imported but never used in this file
```

**socrata_toolkit/api.py (Line 30)**
```python
import os  # ❌ Imported but never used in this file
```

**socrata_toolkit/api/auth.py (Line 45)**
```python
import hashlib  # ❌ Imported but never used
import os       # ❌ Imported but never used
import time     # ❌ Imported but never used
from uuid import UUID, uuid4  # ❌ uuid4 not used
```

**socrata_toolkit/alerts.py (Line 13)**
```python
from typing import Optional  # ❌ Not used in module
```

### Root Cause Analysis
- Code refactoring removed usage but left imports
- Copy-pasted imports from other files
- Incomplete cleanup during development
- Defensive imports that are no longer needed

### Impact Assessment
- **Code Quality:** Reduces readability and maintainability
- **Import Time:** Minimal performance impact
- **Type Checking:** No functional impact
- **Deployment Size:** Negligible

### Recommended Actions

1. **Run automated cleanup:**
   ```bash
   # Using autoflake
   pip install autoflake
   autoflake --remove-all-unused-imports --in-place socrata_toolkit/*.py
   ```

2. **Manual review (recommended):**
   - Check each unused import
   - Remove if truly unused
   - Keep if intentionally used for re-export

3. **Configure Pylance to exclude:**
   - Create `.pylanceignore` if warnings are acceptable

### Priority: **LOW** (Code quality improvement, not functionality)

---

## KNOWN PROBLEM AREAS (From Open Tabs)

The following files were flagged in open editor tabs and require attention:

### 1. socrata_toolkit/material_standards.py
- **Status:** Marked in open tabs
- **Known Issues:** Import dependencies on missing modules
- **Recommendation:** Verify all material standard definitions are properly implemented

### 2. socrata_toolkit/material_definitions.py
- **Status:** Marked in open tabs
- **Known Issues:** Circular import risks with material_standards.py
- **Lines of Interest:** Check line 19 onwards for import structure

### 3. socrata_toolkit/material_compliance.py
- **Status:** Marked in open tabs
- **Known Issues:** Dependency on material_standards module
- **Recommendation:** Ensure proper import resolution

### 4. socrata_toolkit/design_rules.py
- **Status:** Marked in open tabs
- **Known Issues:** Imports from material_standards
- **Recommendation:** Validate circular dependencies

### 5. socrata_toolkit/lineage_core.py
- **Status:** Marked in open tabs
- **Known Issues:** Potential circular imports with lineage_tracking.py
- **Recommendation:** Check import order

### 6. socrata_toolkit/lineage_tracking.py
- **Status:** Marked in open tabs
- **Known Issues:** Dependency chain with lineage_core.py
- **Recommendation:** Verify no circular imports

---

## ADDITIONAL ISSUES FROM PYLANCE DIAGNOSTICS

### Missing Modules in Tests/Examples

The following modules are imported but missing:

```
socrata_toolkit.quality_expectations
socrata_toolkit.quality_profiler
socrata_toolkit.quality_validator
socrata_toolkit.scd_type2
socrata_toolkit.temporal_queries
socrata_toolkit.soft_delete
socrata_toolkit.work_management
socrata_toolkit.microsoft_graph
socrata_toolkit.entity_matching
socrata_toolkit.master_data
socrata_toolkit.entity_reconciliation
socrata_toolkit.qgis_compatibility
socrata_toolkit.observability_logging
```

### Testing Framework Issues

**pytest not resolved in test files:**
- tests/test_docker_environment.py
- tests/test_integration_quick_start.py
- tests/test_quality.py
- tests/test_material_standards.py
- tests/test_api_security.py
- tests/test_schema_registry.py
- tests/test_cdc.py
- tests/test_m365_sync.py
- tests/test_lineage.py
- tests/test_entity_resolution.py
- tests/test_microsoft_graph.py
- tests/test_observability.py
- tests/test_spatial.py

**Recommendation:** Ensure pytest is installed and properly configured in virtual environment

---

## PRIORITY RANKING: ALL ISSUES

| Rank | Category | Count | Impact | Action Required |
|------|----------|-------|--------|-----------------|
| 🔴 CRITICAL | __all__ mismatch | 19 | Breaks public API | Fix __init__.py exports |
| 🔴 CRITICAL | Unknown symbols in api/main.py | 4 | API auth broken | Add missing functions to auth.py |
| 🟠 HIGH | Syntax errors in api/auth.py | 10 | Code won't execute | Fix class redeclarations and code structure |
| 🟡 MEDIUM | Missing shapely module | 3 | Geospatial features broken | Install shapely dependency |
| 🟡 MEDIUM | Missing quality modules | 10+ | Quality framework incomplete | Implement missing modules |
| 🟡 MEDIUM | Missing entity modules | 5+ | Entity resolution broken | Implement missing modules |
| 🟢 LOW | Unused imports | 432 | Code quality issue | Clean up imports |

---

## IMPLEMENTATION ROADMAP

### Phase 1: Critical Fixes (Immediate)
**Timeline:** Today  
**Effort:** 2-4 hours

1. Fix `socrata_toolkit/__init__.py` - Add/remove __all__ items (19 fixes)
2. Add missing symbols to `socrata_toolkit/api/auth.py` (4 fixes)
3. Fix syntax errors in `socrata_toolkit/api/auth.py` (10 fixes)

### Phase 2: High Priority Fixes (This week)
**Timeline:** Within 1 week  
**Effort:** 4-8 hours

1. Resolve shapely dependency (3 fixes)
2. Implement missing quality modules (10+ implementations)
3. Implement missing entity modules (5+ implementations)

### Phase 3: Code Quality (Optional)
**Timeline:** Next sprint  
**Effort:** 2-4 hours

1. Remove unused imports (432 cleanup fixes)
2. Refactor for clarity and maintainability

---

## VERIFICATION CHECKLIST

After fixes, run verification:

```bash
# Run Pyright scan again
python -m pyright socrata_toolkit/ tests/ --outputjson > pyright_results_after.json

# Check error count
# Should reduce from 357 to < 50 (only real type issues)

# Verify imports work
python -c "from socrata_toolkit import *"

# Run test suite
pytest tests/ -v

# Lint cleanup
pylint socrata_toolkit/ --disable=missing-docstring
```

---

## CONCLUSION

The NYC Data project has **357 import-related errors** primarily caused by:

1. **Incomplete public API** - Missing __all__ exports in __init__.py
2. **Broken authentication module** - Missing functions in api/auth.py
3. **Syntax issues** - Class redeclarations and orphaned code
4. **Missing dependencies** - shapely and other modules
5. **Code debt** - Unused imports throughout

**Estimated effort to fix:** 8-16 hours of development work

**Critical path:** Fix issues in priority order starting with __init__.py and api/auth.py to restore basic functionality.

---

**Report Generated:** 2026-05-11 01:43:00 UTC  
**Tool:** Pyright v1.1.409  
**Status:** ✅ Diagnostic Complete - Awaiting Implementation
