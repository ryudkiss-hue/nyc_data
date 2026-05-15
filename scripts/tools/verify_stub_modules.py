"""Verification script to test that all stub modules can be imported."""

import sys
from pathlib import Path

# Add the current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# List of modules to verify
MODULES_TO_VERIFY = [
    "socrata_toolkit.quality_expectations",
    "socrata_toolkit.quality_profiler",
    "socrata_toolkit.quality_validator",
    "socrata_toolkit.scd_type2",
    "socrata_toolkit.temporal_queries",
    "socrata_toolkit.soft_delete",
    "socrata_toolkit.work_management",
    "socrata_toolkit.microsoft_graph",
    "socrata_toolkit.entity_matching",
    "socrata_toolkit.master_data",
    "socrata_toolkit.entity_reconciliation",
    "socrata_toolkit.qgis_compatibility",
    "socrata_toolkit.observability_logging",
]


def verify_imports():
    """Verify all modules can be imported."""
    failed = []
    successful = []

    for module_name in MODULES_TO_VERIFY:
        try:
            __import__(module_name)
            successful.append(module_name)
            print(f"[OK] {module_name}")
        except Exception as e:
            failed.append((module_name, str(e)))
            print(f"[FAILED] {module_name}: {e}")

    print("\n" + "=" * 60)
    print(f"Verification Results: {len(successful)} successful, {len(failed)} failed")
    print("=" * 60)

    if failed:
        print("\nFailed modules:")
        for module_name, error in failed:
            print(f"  - {module_name}: {error}")
        return False

    print("\nAll 13 modules verified successfully!")
    return True


if __name__ == "__main__":
    success = verify_imports()
    sys.exit(0 if success else 1)
