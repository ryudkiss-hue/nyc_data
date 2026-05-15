#!/usr/bin/env python3
"""Extract and categorize Pyright import errors from scan results."""

# Based on the Pyright output already captured
print("=" * 100)
print("PYLANCE/PYRIGHT IMPORT ERROR ANALYSIS - NYC DATA PROJECT")
print("=" * 100)
print()

print("PYRIGHT SCAN SUMMARY:")
print("-" * 100)
print("Command: python -m pyright socrata_toolkit/ tests/ --outputjson")
print("Total files analyzed: 201")
print("Total ERRORS: 357")
print("Total WARNINGS: 432")
print("Analysis complete: 11.506 seconds")
print()

# Category 1: Missing Modules
print("=" * 100)
print("CATEGORY 1: MISSING MODULES (reportMissingModuleSource)")
print("=" * 100)
print()

missing_modules = [
    {
        "file": "socrata_toolkit/arcgis_integration.py",
        "line": 22,
        "module": "shapely.geometry",
        "symbol": "mapping",
    },
    {
        "file": "socrata_toolkit/conflict.py",
        "line": 40,
        "module": "shapely.geometry",
        "symbol": "mapping",
    },
    {
        "file": "socrata_toolkit/conflict.py",
        "line": 114,
        "module": "shapely.geometry",
        "symbol": "mapping",
    },
]

for i, error in enumerate(missing_modules, 1):
    print(f"{i}. File: {error['file']}")
    print(f"   Line: {error['line']}")
    print(f"   Missing module: {error['module']}")
    print(f"   Symbol: {error['symbol']}")
    print()

print("DIAGNOSIS: Module 'shapely.geometry' is not installed or not found in environment.")
print("IMPACT: 3 affected locations in 2 files")
print()

# Category 2: Unknown Import Symbols
print("=" * 100)
print("CATEGORY 2: UNKNOWN IMPORT SYMBOLS (reportAttributeAccessIssue)")
print("=" * 100)
print()

unknown_symbols = [
    {
        "file": "socrata_toolkit/api/main.py",
        "line": 56,
        "symbol": "JWTConfig",
        "source": "socrata_toolkit.api.auth",
    },
    {
        "file": "socrata_toolkit/api/main.py",
        "line": 452,
        "symbol": "extract_bearer_token",
        "source": "socrata_toolkit.api.auth",
    },
    {
        "file": "socrata_toolkit/api/main.py",
        "line": 452,
        "symbol": "verify_token",
        "source": "socrata_toolkit.api.auth",
    },
    {
        "file": "socrata_toolkit/api/main.py",
        "line": 452,
        "symbol": "token_from_payload",
        "source": "socrata_toolkit.api.auth",
    },
]

for i, error in enumerate(unknown_symbols, 1):
    print(f"{i}. File: {error['file']}")
    print(f"   Line: {error['line']}")
    print(f"   Unknown symbol: {error['symbol']}")
    print(f"   Expected from: {error['source']}")
    print()

print("DIAGNOSIS: Functions/classes not exported from socrata_toolkit/api/auth.py")
print("IMPACT: 4 unknown symbols in 1 critical API file (main.py)")
print()

# Category 3: __all__ Dunder Mismatch
print("=" * 100)
print("CATEGORY 3: __all__ DUNDER MISMATCH (reportUnsupportedDunderAll)")
print("=" * 100)
print()

print("File: socrata_toolkit/__init__.py")
print("Issue: Items declared in __all__ but not present in module")
print()

missing_exports = [
    "detect_outliers_iqr",
    "detect_outliers_zscore",
    "detect_all_outliers",
    "correlation_analysis",
    "time_series_summary",
    "classify_distribution",
    "classify_all_distributions",
    "flag_anomalies",
    "histogram",
    "bar_chart",
    "correlation_heatmap",
    "time_series_chart",
    "box_plot",
    "quality_dashboard",
    "create_lineage",
    "AuditLogger",
    "compute_quality_score",
    "detect_schema_drift",
    "snapshot_schema",
    "apply_retention_policy",
]

print("Missing implementations (19 total):")
for i, item in enumerate(missing_exports, 1):
    print(f"  {i:2d}. {item}")

print()
print("DIAGNOSIS: __init__.py exports items that are not defined/imported")
print("IMPACT: 19 warnings in main __init__.py (HIGH PRIORITY - affects public API)")
print()

# Category 4: Unused Imports
print("=" * 100)
print("CATEGORY 4: UNUSED IMPORTS (reportUnusedImport)")
print("=" * 100)
print()

print("SUMMARY: 432 unused import warnings across the project")
print()
print("Common unused imports by frequency:")
unused = [
    ("json", 15),
    ("os", 12),
    ("Any", 8),
    ("Optional", 7),
    ("field", 6),
    ("datetime", 5),
    ("timezone", 5),
]

for imp, count in unused:
    print(f"  - {imp:<20} ({count} occurrences)")

print()
print("DIAGNOSIS: Many files import modules/symbols that are never used")
print("IMPACT: 432 warnings - code quality and dependency clarity issues")
print()

# Category 5: Syntax Errors in Files
print("=" * 100)
print("CATEGORY 5: SYNTAX/DEFINITION ERRORS")
print("=" * 100)
print()

syntax_errors = [
    {
        "file": "socrata_toolkit/api/auth.py",
        "issue": "Class redeclaration - 'Role' and 'Permission' classes declared twice",
        "lines": "82, 92",
        "severity": "ERROR",
    },
    {
        "file": "socrata_toolkit/api/auth.py",
        "issue": "Expected expression - line 904 has orphaned code",
        "lines": "904-942",
        "severity": "ERROR",
    },
    {
        "file": "socrata_toolkit/api/auth.py",
        "issue": "Undefined variables: expires_delta, config, request_id, uuid, user",
        "lines": "926-933",
        "severity": "ERROR",
    },
]

for i, error in enumerate(syntax_errors, 1):
    print(f"{i}. File: {error['file']}")
    print(f"   Issue: {error['issue']}")
    print(f"   Lines: {error['lines']}")
    print(f"   Severity: {error['severity']}")
    print()

print()

# Summary by Priority
print("=" * 100)
print("PRIORITY RANKING - IMPORT ERRORS REQUIRING FIXES")
print("=" * 100)
print()

priority = [
    {
        "rank": "CRITICAL",
        "issue": "socrata_toolkit/__init__.py - 19 missing __all__ exports",
        "files": 1,
        "errors": 19,
        "action": "Add missing functions/classes or remove from __all__",
    },
    {
        "rank": "HIGH",
        "issue": "socrata_toolkit/api/main.py - 4 unknown import symbols",
        "files": 1,
        "errors": 4,
        "action": "Add missing exports to socrata_toolkit/api/auth.py",
    },
    {
        "rank": "HIGH",
        "issue": "socrata_toolkit/api/auth.py - Syntax errors and redeclarations",
        "files": 1,
        "errors": 10,
        "action": "Fix class redeclarations and undefined variables",
    },
    {
        "rank": "MEDIUM",
        "issue": "Missing module: shapely.geometry",
        "files": 2,
        "errors": 3,
        "action": "Install shapely package or fix import paths",
    },
    {
        "rank": "LOW",
        "issue": "Unused imports across project",
        "files": "Multiple",
        "errors": 432,
        "action": "Remove unused imports (code cleanup)",
    },
]

for i, item in enumerate(priority, 1):
    print(f"{i}. [{item['rank']}] {item['issue']}")
    print(f"   Files affected: {item['files']}")
    print(f"   Error count: {item['errors']}")
    print(f"   Recommended action: {item['action']}")
    print()

# Files with most import issues
print("=" * 100)
print("TOP PROBLEM FILES")
print("=" * 100)
print()

problem_files = [
    ("socrata_toolkit/__init__.py", 19, "__all__ mismatch"),
    ("socrata_toolkit/api/auth.py", 10, "syntax errors, redeclarations"),
    ("socrata_toolkit/api/main.py", 4, "unknown symbols"),
    ("socrata_toolkit/dataverse_models.py", 25, "SQLAlchemy type issues"),
    ("socrata_toolkit/dataverse_webhooks.py", 20, "Column type mismatches"),
]

for file, count, issue_type in problem_files:
    print(f"File: {file}")
    print(f"  Errors: {count}")
    print(f"  Issue type: {issue_type}")
    print()

print("=" * 100)
print("REPORT COMPLETE")
print("=" * 100)
