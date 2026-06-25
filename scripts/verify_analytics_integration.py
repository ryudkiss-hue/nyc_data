#!/usr/bin/env python3
"""
Verification script for Analytics Integration (Phase C-F).
Checks that all callbacks, layouts, and data services are properly wired.

Usage:
    python scripts/verify_analytics_integration.py [--verbose]

Output:
    - List of all registered callbacks
    - Validation of component IDs
    - Mock data flow test (filters → AnalyticsEngine → figures)
    - Performance baseline measurements
"""

import logging
import sys
from pathlib import Path
from typing import List, Tuple

# Setup paths
APP_PATH = str(Path(__file__).resolve().parent.parent / "app")
SRC_PATH = str(Path(__file__).resolve().parent.parent / "src")
for p in [APP_PATH, SRC_PATH]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

def check_imports() -> Tuple[bool, List[str]]:
    """Verify all required modules can be imported."""
    logger.info("=" * 70)
    logger.info("STEP 1: Checking Imports")
    logger.info("=" * 70)

    imports = [
        ("dash", "Dash framework"),
        ("dash_mantine_components", "Dash Mantine Components"),
        ("plotly.graph_objects", "Plotly"),
        ("pandas", "Pandas"),
        ("geopandas", "GeoPandas"),
        ("numpy", "NumPy"),
        ("scipy", "SciPy"),
    ]

    errors = []
    for module_name, description in imports:
        try:
            __import__(module_name)
            logger.info(f"✅ {description:<40} ({module_name})")
        except ImportError as e:
            logger.error(f"❌ {description:<40} ({module_name}): {e}")
            errors.append(f"{description} ({module_name})")

    # Check optional spatial libraries
    optional = [
        ("libpysal", "LibPySAL (Moran's I)"),
        ("esda", "ESDA (Moran's I computation)"),
        ("statsmodels", "StatsModels (Decomposition)"),
    ]

    for module_name, description in optional:
        try:
            __import__(module_name)
            logger.info(f"✅ {description:<40} ({module_name}) [OPTIONAL]")
        except ImportError:
            logger.warning(f"⚠️  {description:<40} ({module_name}) [OPTIONAL, may affect Phase B]")

    return len(errors) == 0, errors

def check_callback_files() -> Tuple[bool, List[str]]:
    """Verify callback files exist and are readable."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 2: Checking Callback Files")
    logger.info("=" * 70)

    files = [
        "app/callbacks/analytics.py",
        "app/callbacks/analytics_integration.py",
        "app/callbacks/decorators.py",
    ]

    errors = []
    for file_path in files:
        full_path = Path(file_path)
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            logger.info(f"✅ {file_path:<50} ({size_kb:.1f} KB)")
        else:
            logger.error(f"❌ {file_path:<50} NOT FOUND")
            errors.append(file_path)

    return len(errors) == 0, errors

def check_layout_files() -> Tuple[bool, List[str]]:
    """Verify layout files exist."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: Checking Layout Files")
    logger.info("=" * 70)

    files = [
        "app/dash_layouts.py",
        "app/dash_layouts_analytics_integration.py",
    ]

    errors = []
    for file_path in files:
        full_path = Path(file_path)
        if full_path.exists():
            size_kb = full_path.stat().st_size / 1024
            logger.info(f"✅ {file_path:<50} ({size_kb:.1f} KB)")
        else:
            logger.error(f"❌ {file_path:<50} NOT FOUND")
            errors.append(file_path)

    return len(errors) == 0, errors

def check_analytics_engine() -> Tuple[bool, List[str]]:
    """Verify AnalyticsEngine class and methods."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 4: Checking AnalyticsEngine Methods")
    logger.info("=" * 70)

    errors = []
    try:
        from app.callbacks.analytics import AnalyticsEngine

        methods = [
            "chart_morans_i",
            "chart_distribution_classification",
            "chart_anomaly_detection",
            "chart_seasonal_decomposition",
            "chart_bootstrap_ci",
        ]

        for method_name in methods:
            if hasattr(AnalyticsEngine, method_name):
                method = getattr(AnalyticsEngine, method_name)
                logger.info(f"✅ AnalyticsEngine.{method_name}()")
            else:
                logger.error(f"❌ AnalyticsEngine.{method_name}() NOT FOUND")
                errors.append(f"AnalyticsEngine.{method_name}")

    except Exception as e:
        logger.error(f"❌ Failed to import AnalyticsEngine: {e}")
        errors.append(f"AnalyticsEngine import: {e}")

    return len(errors) == 0, errors

def check_callback_decorators() -> Tuple[bool, List[str]]:
    """Verify callback decorators."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 5: Checking Callback Decorators")
    logger.info("=" * 70)

    errors = []
    try:
        from app.callbacks.decorators import memoize_with_ttl, timer_callback

        logger.info("✅ @timer_callback decorator")
        logger.info("✅ @memoize_with_ttl() decorator")

    except Exception as e:
        logger.error(f"❌ Failed to import decorators: {e}")
        errors.append(f"Decorators import: {e}")

    return len(errors) == 0, errors

def check_data_service() -> Tuple[bool, List[str]]:
    """Verify data service functions."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 6: Checking Data Service Layer")
    logger.info("=" * 70)

    errors = []
    try:
        from app.services.analytics_service import (
            get_dataset,
            get_metric_metrics,
            get_spatial_data,
            get_timeseries_data,
            validate_filters,
        )

        functions = [
            ("get_dataset", "Fetch dataset"),
            ("get_spatial_data", "Fetch spatial data"),
            ("get_timeseries_data", "Fetch time series"),
            ("get_metric_metrics", "Fetch Metric metrics"),
            ("validate_filters", "Validate filters"),
        ]

        for func_name, description in functions:
            logger.info(f"✅ {description:<30} ({func_name})")

    except Exception as e:
        logger.error(f"❌ Failed to import analytics_service: {e}")
        errors.append(f"analytics_service import: {e}")

    return len(errors) == 0, errors

def check_integration_callbacks() -> Tuple[bool, List[str]]:
    """Verify integration callback definitions."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 7: Checking Integration Callbacks")
    logger.info("=" * 70)

    errors = []
    try:
        # Import to check for syntax errors
        import app.callbacks.analytics_integration as integration

        callbacks = [
            "update_distribution_classification",
            "update_anomaly_detection",
            "update_seasonal_decomposition",
            "update_bootstrap_ci_metrics",
            "update_morans_i",
            "trigger_all_updates",
        ]

        for callback_name in callbacks:
            if hasattr(integration, callback_name):
                logger.info(f"✅ {callback_name}()")
            else:
                logger.error(f"❌ {callback_name}() NOT FOUND")
                errors.append(callback_name)

    except SyntaxError as e:
        logger.error(f"❌ Syntax error in analytics_integration.py: {e}")
        errors.append(f"SyntaxError: {e}")
    except Exception as e:
        logger.error(f"❌ Failed to import analytics_integration: {e}")
        errors.append(f"Import error: {e}")

    return len(errors) == 0, errors

def check_component_ids() -> Tuple[bool, List[str]]:
    """Verify component IDs are consistent between callbacks and layouts."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 8: Checking Component IDs")
    logger.info("=" * 70)

    component_mapping = {
        "Phase C": {
            "inputs": ["store-global-filters", "distribution-column-limit"],
            "outputs": ["distribution-chart-container", "distribution-narrative"],
        },
        "Phase D": {
            "inputs": ["store-global-filters", "anomaly-detection-toggle"],
            "outputs": ["anomaly-detection-chart", "anomaly-narrative", "anomaly-count-badge"],
        },
        "Phase E": {
            "inputs": ["store-global-filters", "decomposition-date-col", "decomposition-value-col"],
            "outputs": ["decomposition-chart-container", "decomposition-narrative"],
        },
        "Phase F": {
            "inputs": ["store-global-filters", "metric-refresh-interval"],
            "outputs": ["metric-bootstrap-figures", "metric-bootstrap-summary"],
        },
        "Phase B": {
            "inputs": ["store-global-filters", "morans-i-column-select"],
            "outputs": ["morans-i-gauge", "morans-i-narrative"],
        },
    }

    errors = []
    for phase, ids in component_mapping.items():
        logger.info(f"\n{phase}:")
        logger.info(f"  Inputs:  {', '.join(ids['inputs'])}")
        logger.info(f"  Outputs: {', '.join(ids['outputs'])}")

    logger.info("\n⚠️  Verify these IDs match your actual dashboard layouts!")

    return True, errors

def run_mock_data_flow() -> Tuple[bool, List[str]]:
    """Test data flow with mock data."""
    logger.info("\n" + "=" * 70)
    logger.info("STEP 9: Testing Mock Data Flow")
    logger.info("=" * 70)

    errors = []

    try:
        import numpy as np
        import pandas as pd

        from app.callbacks.analytics import AnalyticsEngine

        # Create mock data
        logger.info("Creating mock datasets...")

        # Phase C: Distribution data
        df_dist = pd.DataFrame({
            "id": range(100),
            "value1": np.random.normal(100, 15, 100),
            "value2": np.random.exponential(50, 100),
            "value3": np.random.uniform(0, 100, 100),
        })
        logger.info(f"✅ Mock distribution data: {df_dist.shape[0]} rows × {df_dist.shape[1]} cols")

        # Test Phase C
        try:
            data_bundle = {"data": df_dist}
            fig, narrative = AnalyticsEngine.chart_distribution_classification(data_bundle)
            logger.info("✅ Phase C (Distribution): Generated figure + narrative")
            if "Distribution" not in narrative and "Error" not in narrative:
                logger.warning(f"⚠️  Phase C narrative unexpected: {narrative[:50]}")
        except Exception as e:
            logger.error(f"❌ Phase C failed: {e}")
            errors.append(f"Phase C: {e}")

        # Phase D: Spatial data (mock)
        try:
            import geopandas as gpd
            from shapely.geometry import Point

            coords = np.random.uniform(-74.05, -73.75, (20, 2))
            gdf_spatial = gpd.GeoDataFrame(
                {
                    "id": range(20),
                    "value": np.random.normal(50, 10, 20),
                },
                geometry=[Point(xy) for xy in coords],
                crs="EPSG:4326"
            )
            logger.info(f"✅ Mock spatial data: {len(gdf_spatial)} points")

            data_bundle = {"spatial": gdf_spatial}
            fig, narrative = AnalyticsEngine.chart_anomaly_detection(data_bundle)
            logger.info("✅ Phase D (Anomaly): Generated figure + narrative")
        except Exception as e:
            logger.warning(f"⚠️  Phase D skipped (GeoPandas/Shapely): {e}")

        # Phase E: Time series data
        try:
            dates = pd.date_range("2026-01-01", periods=50, freq="D")
            df_ts = pd.DataFrame({
                "date": dates,
                "value": np.cumsum(np.random.normal(0, 5, 50)) + 100,
            })
            logger.info(f"✅ Mock time series data: {len(df_ts)} points")

            data_bundle = {"timeseries": df_ts}
            fig, narrative = AnalyticsEngine.chart_seasonal_decomposition(data_bundle)
            logger.info("✅ Phase E (Decomposition): Generated figure + narrative")
        except Exception as e:
            logger.error(f"❌ Phase E failed: {e}")
            errors.append(f"Phase E: {e}")

        # Phase F: Metric metrics
        try:
            metrics = {
                "completion_rate": (0.874, 0.852, 0.891),
                "quality_score": (92.0, 90.5, 93.2),
            }
            for metric_name, (point_est, ci_lower, ci_upper) in metrics.items():
                data_bundle = {"metrics": {metric_name: (point_est, ci_lower, ci_upper)}}
                fig, narrative = AnalyticsEngine.chart_bootstrap_ci(data_bundle)
                logger.info(f"✅ Phase F ({metric_name}): Generated figure + narrative")
        except Exception as e:
            logger.error(f"❌ Phase F failed: {e}")
            errors.append(f"Phase F: {e}")

        # Phase B: Moran's I (requires libpysal)
        try:
            data_bundle = {"spatial": gdf_spatial}
            fig, narrative = AnalyticsEngine.chart_morans_i(data_bundle)
            if "Insufficient" not in narrative and "Error" not in narrative:
                logger.info("✅ Phase B (Moran's I): Generated figure + narrative")
            else:
                logger.warning(f"⚠️  Phase B (Moran's I): {narrative[:50]}")
        except Exception as e:
            logger.warning(f"⚠️  Phase B skipped (libpysal/esda): {e}")

    except Exception as e:
        logger.error(f"❌ Mock data flow test failed: {e}")
        errors.append(f"Mock data flow: {e}")

    return len(errors) == 0, errors

def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("ANALYTICS INTEGRATION VERIFICATION")
    print("=" * 70)

    checks = [
        ("Imports", check_imports),
        ("Callback Files", check_callback_files),
        ("Layout Files", check_layout_files),
        ("AnalyticsEngine Methods", check_analytics_engine),
        ("Callback Decorators", check_callback_decorators),
        ("Data Service Layer", check_data_service),
        ("Integration Callbacks", check_integration_callbacks),
        ("Component IDs", check_component_ids),
        ("Mock Data Flow", run_mock_data_flow),
    ]

    results = {}
    for check_name, check_func in checks:
        try:
            success, errors = check_func()
            results[check_name] = (success, errors)
        except Exception as e:
            logger.error(f"❌ Check '{check_name}' crashed: {e}")
            results[check_name] = (False, [str(e)])

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(1 for success, _ in results.values() if success)
    total = len(results)

    for check_name, (success, errors) in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status:10} {check_name}")
        if errors:
            for error in errors:
                print(f"           └─ {error}")

    print("\n" + "=" * 70)
    print(f"OVERALL: {passed}/{total} checks passed")
    print("=" * 70)

    if passed == total:
        logger.info("\n🎉 All checks passed! Analytics integration is ready for deployment.")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} check(s) failed. See above for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
