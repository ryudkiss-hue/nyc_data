import sys
sys.path.insert(0, 'src')
from socrata_toolkit.core.duckdb_pipeline import SOCRATA_DATASETS

print(f"Actual SOCRATA_DATASETS count: {len(SOCRATA_DATASETS)}")
print("\nDatasets grouped by category:")
print(f"Core SMD (inspection, violations, etc): {[k for k in SOCRATA_DATASETS.keys() if k in ['inspection', 'violations', 'built', 'lot_info', 'reinspection', 'tree_damage', 'dismissals', 'correspondences', 'curb_metal_protruding']]}")
print(f"\nAccessibility (ramps): {[k for k in SOCRATA_DATASETS.keys() if 'ramp' in k.lower() or 'signal' in k.lower()]}")
print(f"\nConstruction/Permits: {[k for k in SOCRATA_DATASETS.keys() if 'permit' in k.lower() or 'construction' in k.lower() or 'capital' in k.lower() or 'resurfacing' in k.lower()]}")
print(f"\nTotal: {len(SOCRATA_DATASETS)} datasets")
