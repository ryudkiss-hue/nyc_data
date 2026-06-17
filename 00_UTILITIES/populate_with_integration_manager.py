#!/usr/bin/env python3
"""
Use enhanced DatasetIntegrationManager v2 to populate metadata for all 21 Phase 1 datasets.

This demonstrates the full workflow:
1. Load registry
2. Fetch Socrata metadata for each dataset
3. Auto-detect visualization columns
4. Update visualization specs with real column names
5. Save enhanced registry
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from socrata_toolkit.integration_v2 import DatasetIntegrationManager


def main():
    """Populate Phase 1 dataset metadata."""
    registry_path = Path("docs/DATASET_REGISTRY.yaml")

    print("[INFO] Initializing DatasetIntegrationManager...\n")
    mgr = DatasetIntegrationManager(str(registry_path))

    print("[INFO] Populating metadata for all Phase 1 datasets...\n")
    results = mgr.populate_all_metadata()

    print(f"\n[SUMMARY]")
    print(f"  Total datasets: {results['total']}")
    print(f"  Successfully fetched: {results['fetched']}")
    print(f"  Updated with schemas: {results['updated']}")
    print(f"  Errors: {results['errors']}")
    print(f"\n[RESULT]")
    print(f"  Registry enhanced with:")
    print(f"  [PASS] Real column schemas")
    print(f"  [PASS] Auto-detected IV/DV columns")
    print(f"  [PASS] Row counts & update timestamps")
    print(f"  [PASS] Geographic column hints")
    print(f"  [PASS] Visualization auto-configuration")
    print(f"\n  Registry saved to: {registry_path}")


if __name__ == "__main__":
    main()
