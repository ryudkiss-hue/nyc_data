#!/usr/bin/env python
"""Verify that all 6 critical modules are importable with proper exports."""

import sys

modules_to_test = {
    "socrata_toolkit.material_standards": [
        "MaterialCategory",
        "SurfaceCondition",
        "SurfaceAssessment",
        "MaterialStandard",
        "MaterialInspector",
        "assess_surface",
        "validate_against_standard",
        "generate_compliance_report",
    ],
    "socrata_toolkit.quality_integration": [
        "QualityIntegration",
        "QualityFramework",
        "QualityPipeline",
        "create_quality_pipeline",
        "run_all_quality_checks",
    ],
    "socrata_toolkit.spatial_database": [
        "SpatialIndex",
        "GeometryHandler",
        "SpatialQuery",
        "create_spatial_index",
        "query_geographic_area",
    ],
    "socrata_toolkit.observability_integration": [
        "ObservabilityManager",
        "ObservabilityFramework",
        "MetricsPipeline",
        "setup_observability",
        "record_operation_metrics",
    ],
    "socrata_toolkit.microsoft_graph": [
        "GraphClient",
        "GraphAPIClient",
        "M365Integration",
        "initialize_graph_api",
        "sync_with_graph",
    ],
    "socrata_toolkit.qgis_compatibility": [
        "QGISProject",
        "LayerConverter",
        "QGISExporter",
        "validate_qgis_compatibility",
        "convert_all_layers",
    ],
}

print("=" * 70)
print("CRITICAL MODULE IMPORT VERIFICATION")
print("=" * 70)

all_passed = True
total_classes = 0
total_functions = 0

for module_name, expected_exports in modules_to_test.items():
    try:
        mod = __import__(module_name, fromlist=expected_exports)
        print(f"\nOK {module_name}")

        missing = []
        for export_name in expected_exports:
            if hasattr(mod, export_name):
                obj = getattr(mod, export_name)
                if isinstance(obj, type):
                    total_classes += 1
                    print(f"  OK {export_name} (class)")
                else:
                    total_functions += 1
                    print(f"  OK {export_name} (function)")
            else:
                missing.append(export_name)

        if missing:
            print(f"  MISSING: {', '.join(missing)}")
            all_passed = False

    except Exception as e:
        print(f"\nFAIL {module_name}")
        print(f"  ERROR: {e}")
        all_passed = False

print("\n" + "=" * 70)
print(f"SUMMARY: {total_classes} classes, {total_functions} functions")
print("=" * 70)

if all_passed:
    print("SUCCESS: ALL MODULES AND EXPORTS VERIFIED")
    sys.exit(0)
else:
    print("FAILURE: SOME MODULES OR EXPORTS MISSING")
    sys.exit(1)
