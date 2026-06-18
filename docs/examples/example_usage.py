#!/usr/bin/env python
"""Example usage of config-driven dataset integration system.

Demonstrates:
1. Loading and generating artifacts from DATASET_REGISTRY.yaml
2. Creating charts with ChartFactory
3. Computing KPIs with KPIEngine
4. Loading and validating data with DatasetLoader
5. Adding a new dataset with full regeneration

Run with:
    python example_usage.py
"""

import pandas as pd
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from socrata_toolkit.integration import DatasetIntegrationManager
from socrata_toolkit.abstraction_layers import (
    ChartFactory,
    ChartSpec,
    KPIEngine,
    DatasetLoader,
    SchemaRegistry,
)


def example_1_load_and_generate():
    """Example 1: Load registry and generate all artifacts."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Load Registry and Generate Artifacts")
    print("="*70)

    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    print(f"\nLoaded registry with {mgr.registry['registry_metadata']['total_datasets']} datasets")
    print(f"Active: {mgr.registry['registry_metadata']['active_datasets']}")

    # List all datasets
    all_datasets = mgr.list_datasets()
    print(f"\nFirst 10 datasets: {all_datasets[:10]}")

    # Generate artifacts
    print("\nGenerating all artifacts...")
    artifacts = mgr.generate_all()

    for artifact_type, path in artifacts.items():
        print(f"  ✓ {artifact_type}: {path}")


def example_2_create_charts():
    """Example 2: Create charts with ChartFactory."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Create Charts with ChartFactory")
    print("="*70)

    # Create sample data
    df = pd.DataFrame({
        "borough": ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN_ISLAND"],
        "violation_count": [150, 120, 95, 110, 75],
    })

    print("\nSample data:")
    print(df)

    # Create chart
    factory = ChartFactory()
    spec = ChartSpec(
        chart_type="vertical_bar",
        data=df,
        iv_column="borough",
        dv_column="violation_count",
        title="Violations by Borough",
    )

    fig = factory.create(spec)
    print("\n✓ Created vertical bar chart")
    print(f"  Chart type: {spec.chart_type}")
    print(f"  Title: {spec.title}")
    print(f"  IV: {spec.iv_column}, DV: {spec.dv_column}")

    # Create horizontal bar chart
    spec2 = ChartSpec(
        chart_type="horizontal_bar",
        data=df,
        iv_column="borough",
        dv_column="violation_count",
        title="Violations by Borough (Horizontal)",
    )

    fig2 = factory.create(spec2)
    print("\n✓ Created horizontal bar chart")


def example_3_compute_kpis():
    """Example 3: Compute KPIs with KPIEngine."""
    print("\n" + "="*70)
    print("EXAMPLE 3: Compute KPIs with KPIEngine")
    print("="*70)

    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    # Create sample inspection data
    df = pd.DataFrame({
        "objectid": range(1, 501),
        "borough": ["MANHATTAN"] * 250 + ["BROOKLYN"] * 250,
        "status": ["COMPLETED"] * 475 + ["PENDING"] * 25,
        "violation_count": [2, 3, 1, 4, 2] * 100,
    })

    print("\nSample inspection data:")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {df.columns.tolist()}")

    # Compute KPI
    result = mgr.kpi_engine.compute(
        dataset_key="inspection",
        kpi_name="inspections_scheduled_week",
        data=df,
    )

    print(f"\n✓ Computed KPI: {result.kpi_name}")
    print(f"  Value: {result.value} {result.unit}")
    print(f"  Sample size: {result.sample_size}")
    print(f"  Timestamp: {result.timestamp}")

    # Compute another KPI
    result2 = mgr.kpi_engine.compute(
        dataset_key="inspection",
        kpi_name="inspection_completion_rate",
        data=df,
    )

    print(f"\n✓ Computed KPI: {result2.kpi_name}")
    print(f"  Value: {result2.value} {result2.unit}")
    print(f"  Target: {result2.metadata.get('target')}")


def example_4_validate_data():
    """Example 4: Load and validate data with DatasetLoader."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Load and Validate Data")
    print("="*70)

    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    # Create sample data with missing column (invalid)
    df_invalid = pd.DataFrame({
        "violation_id": range(1, 11),
        # Missing 'status' column (required)
    })

    print("\nAttempting to validate dataset with missing required column...")
    result = mgr.schema_registry.validate("violations", df_invalid)

    print(f"\n✓ Validation result: {result.validation_status}")
    if result.errors:
        print(f"  Errors: {result.errors}")

    # Create valid data
    df_valid = pd.DataFrame({
        "violation_id": range(1, 11),
        "borough": ["MANHATTAN"] * 10,
        "created_date": pd.date_range("2026-01-01", periods=10),
        "status": ["OPEN"] * 5 + ["CLOSED"] * 5,
    })

    print("\nValidating dataset with all required columns...")
    result2 = mgr.schema_registry.validate("violations", df_valid)

    print(f"\n✓ Validation result: {result2.validation_status}")
    print(f"  Columns present: {result2.columns_present}")


def example_5_add_dataset():
    """Example 5: Add a new dataset and regenerate artifacts."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Add New Dataset (Would Regenerate All Artifacts)")
    print("="*70)

    print("\nDemonstration of add_dataset() workflow:")
    print("""
    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    mgr.add_dataset(
        fourfour="h933-akrx",
        name="Street Pavement Ratings",
        kpis=["pavement_avg_rating", "rating_by_borough"],
        status="active",
        frequency="monthly",
        quality_score=0.88,
        columns=[
            {"name": "block_id", "type": "string", "required": true},
            {"name": "rating", "type": "float", "required": true},
            {"name": "last_inspected", "type": "datetime", "required": false},
        ],
        visualization={
            "default_chart": "horizontal_bar",
            "iv_column": "block_id",
            "dv_column": "rating",
            "title_template": "Pavement Ratings by Block",
        },
        tags=["construction", "quality_assurance"],
    )
    # This would:
    # 1. Add dataset to DATASET_REGISTRY.yaml
    # 2. Regenerate plotly_charts.py
    # 3. Regenerate visualization_callbacks.py
    # 4. Regenerate dash_layouts_sections.py
    # 5. Regenerate kpi_stubs.py
    # 6. Regenerate documentation
    """)

    print("✓ Single method call replaces 7-file manual process")


def example_6_registry_structure():
    """Example 6: Explore registry structure."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Explore Registry Structure")
    print("="*70)

    mgr = DatasetIntegrationManager("docs/DATASET_REGISTRY.yaml")

    # Get inspection dataset config
    inspection_config = mgr.get_dataset("inspection")

    print("\nInspection Dataset Configuration:")
    print(f"  Name: {inspection_config['name']}")
    print(f"  Fourfour: {inspection_config['fourfour']}")
    print(f"  Status: {inspection_config['status']}")
    print(f"  Frequency: {inspection_config['frequency']}")
    print(f"  Quality Score: {inspection_config['quality_score']}")
    print(f"  Estimated Rows: {inspection_config['estimated_rows']}")

    print(f"\nColumns ({len(inspection_config['columns'])}):")
    for col in inspection_config['columns'][:3]:
        required = "✓" if col.get("required") else "✗"
        print(f"  {required} {col['name']}: {col['type']}")

    print(f"\nVisualization:")
    viz = inspection_config['visualization']
    print(f"  Chart Type: {viz['default_chart']}")
    print(f"  IV: {viz['iv_column']}, DV: {viz['dv_column']}")
    print(f"  Title: {viz['title_template']}")

    print(f"\nKPIs ({len(inspection_config['kpis'])}):")
    for kpi in inspection_config['kpis']:
        print(f"  - {kpi}")


def main():
    """Run all examples."""
    print("\n" + "#"*70)
    print("# Config-Driven Dataset Integration System — Examples")
    print("#"*70)

    try:
        example_1_load_and_generate()
    except Exception as e:
        print(f"✗ Example 1 failed: {e}")

    try:
        example_2_create_charts()
    except Exception as e:
        print(f"✗ Example 2 failed: {e}")

    try:
        example_3_compute_kpis()
    except Exception as e:
        print(f"✗ Example 3 failed: {e}")

    try:
        example_4_validate_data()
    except Exception as e:
        print(f"✗ Example 4 failed: {e}")

    try:
        example_5_add_dataset()
    except Exception as e:
        print(f"✗ Example 5 failed: {e}")

    try:
        example_6_registry_structure()
    except Exception as e:
        print(f"✗ Example 6 failed: {e}")

    print("\n" + "#"*70)
    print("# Examples Complete")
    print("#"*70 + "\n")


if __name__ == "__main__":
    main()
