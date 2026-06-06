"""Shared pytest fixtures and test utilities for NYC DOT SIM Toolkit tests."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

# Ensure the project root is on sys.path so tests can import the package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "src")
for p in (ROOT, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)

# Try to import faker; if not available, skip volume tests
try:
    from faker import Faker
    HAS_FAKER = True
except ImportError:
    HAS_FAKER = False


# ============================================================================
# Seeded Faker for reproducible synthetic data
# ============================================================================

@pytest.fixture(scope="session")
def faker_instance():
    """Session-scoped Faker instance with fixed seed for reproducibility."""
    if not HAS_FAKER:
        pytest.skip("faker not installed")
    fake = Faker()
    Faker.seed(42)
    return fake


# ============================================================================
# Common DataFrames
# ============================================================================

@pytest.fixture
def sample_df():
    """Sample DataFrame for SIM complaint parsing tests."""
    data = {
        "id": [1, 2, 3, 4, 5, 6, 7],
        "description": [
            "There is a large crack and a trip hazard near the curb cut. A wheelchair cannot pass.",
            "Tree root damage has caused significant uplift on the sidewalk.",
            "A large pothole is pooling water after rain.",
            "Just a simple crack, nothing major.",
            "",
            "Multiple issues: root damage AND a trip hazard.",
            "Water pooling and ADA accessibility problem.",
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def empty_dataframe():
    """Empty DataFrame for edge case testing."""
    return pd.DataFrame()


@pytest.fixture
def single_row_dataframe():
    """Single-row DataFrame for boundary tests."""
    return pd.DataFrame({"id": [1], "value": [10], "status": ["active"]})


@pytest.fixture
def sample_coordinates() -> list[tuple[float, float]]:
    """NYC-area (lon, lat) coordinates for spatial testing."""
    return [
        (-74.01, 40.70),
        (-74.012, 40.702),
        (-74.014, 40.704),
        (-74.016, 40.706),
        (-74.018, 40.708),
        (-74.02, 40.71),
        (-74.022, 40.712),
        (-74.024, 40.714),
        (-74.026, 40.716),
        (-74.028, 40.718),
    ]


@pytest.fixture
def sample_values() -> list[float]:
    """Condition scores (0-100) aligned with sample_coordinates."""
    return [80.0, 60.0, 45.0, 30.0, 75.0, 55.0, 40.0, 88.0, 20.0, 65.0]


@pytest.fixture
def sample_segment_ids() -> list[str]:
    """Segment IDs aligned with sample_coordinates."""
    return [f"seg_{i}" for i in range(10)]


@pytest.fixture
def borough_dataframe():
    """Sample DataFrame with borough-level data."""
    return pd.DataFrame({
        "borough": ["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"],
        "total_complaints": [500, 300, 400, 350, 200],
        "resolved_complaints": [450, 270, 360, 315, 180],
    })


@pytest.fixture
def inspection_dataframe():
    """Sample inspection data with multiple columns."""
    return pd.DataFrame({
        "_score": np.array([75, 80, 50, 90, 60, 85, 40, 95, 55, 70]),
        "_lat": np.array([40.70, 40.71, 40.72, 40.73, 40.74, 40.75, 40.76, 40.77, 40.78, 40.79]),
        "_lon": np.array([-74.01, -74.02, -74.03, -74.04, -74.05, -74.06, -74.07, -74.08, -74.09, -74.10]),
        "status": ["open", "closed", "open", "closed", "open", "closed", "open", "closed", "open", "closed"],
    })


@pytest.fixture
def quality_test_dataframe():
    """DataFrame for quality scoring tests."""
    return pd.DataFrame({
        "id": range(100),
        "name": [f"item_{i}" for i in range(100)],
        "value": np.random.randint(0, 100, 100),
        "created_date": pd.date_range("2024-01-01", periods=100),
        "category": np.random.choice(["A", "B", "C"], 100),
    })


# ============================================================================
# Common Mocks
# ============================================================================

@pytest.fixture
def mock_sklearn_vectorizer():
    """Mock TfidfVectorizer for NLP tests without sklearn."""
    with patch("socrata_toolkit.analysis.TfidfVectorizer") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        mock_tfidf_matrix = MagicMock()
        mock_instance.fit_transform.return_value = mock_tfidf_matrix
        yield mock_instance


@pytest.fixture
def mock_socrata_client():
    """Mock SocrataClient for API tests."""
    with patch("socrata_toolkit.core.client.SocrataClient") as mock_class:
        mock_instance = MagicMock()
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_streamlit():
    """Mock streamlit module for app tests."""
    with patch("streamlit") as mock_st:
        mock_st.session_state = {}
        yield mock_st


@pytest.fixture
def mock_geopandas():
    """Mock geopandas for spatial tests without heavy geospatial deps."""
    with patch("geopandas") as mock_gpd:
        yield mock_gpd


@pytest.fixture
def mock_shapely():
    """Mock shapely for geometry tests."""
    with patch("shapely") as mock_shapely:
        yield mock_shapely


# ============================================================================
# Faker Factories (for volume/pipeline tests)
# ============================================================================

@pytest.fixture
def fake_inspection_records(faker_instance):
    """Generate 100 realistic inspection records using Faker."""
    if not HAS_FAKER:
        pytest.skip("faker not installed")

    records = []
    for i in range(100):
        records.append({
            "id": f"insp_{i:06d}",
            "address": faker_instance.street_address(),
            "borough": faker_instance.random_element(["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]),
            "complaint_date": faker_instance.date_object(),
            "completion_date": faker_instance.date_object(),
            "status": faker_instance.random_element(["open", "closed", "pending"]),
            "severity": faker_instance.random_int(min=0, max=10),
            "inspector": faker_instance.name(),
        })
    return records


@pytest.fixture
def fake_violation_records(faker_instance):
    """Generate 500 realistic violation records using Faker."""
    if not HAS_FAKER:
        pytest.skip("faker not installed")

    records = []
    violations = ["crack", "pothole", "root damage", "water pooling", "ADA hazard"]
    for i in range(500):
        records.append({
            "violation_id": f"vio_{i:06d}",
            "address": faker_instance.street_address(),
            "violation_type": faker_instance.random_element(violations),
            "severity": faker_instance.random_int(min=1, max=5),
            "date_reported": faker_instance.date_time(),
            "date_resolved": faker_instance.date_time() if faker_instance.boolean() else None,
            "inspector_notes": faker_instance.sentence(nb_words=10),
        })
    return records


@pytest.fixture
def fake_large_dataframe(faker_instance):
    """Generate a large (10K row) realistic DataFrame for performance tests."""
    if not HAS_FAKER:
        pytest.skip("faker not installed")

    records = []
    for i in range(10000):
        records.append({
            "id": f"row_{i:06d}",
            "timestamp": faker_instance.date_time(),
            "borough": faker_instance.random_element(["MANHATTAN", "BRONX", "BROOKLYN", "QUEENS", "STATEN ISLAND"]),
            "value": faker_instance.random_int(min=0, max=100),
            "category": faker_instance.random_element(["A", "B", "C", "D"]),
            "description": faker_instance.sentence(),
        })
    return pd.DataFrame(records)


@pytest.fixture
def fake_geospatial_dataframe(faker_instance):
    """Generate fake geospatial data with coordinates and properties."""
    if not HAS_FAKER:
        pytest.skip("faker not installed")

    records = []
    for i in range(100):
        records.append({
            "id": f"geo_{i:06d}",
            "latitude": float(faker_instance.latitude()),
            "longitude": float(faker_instance.longitude()),
            "address": faker_instance.street_address(),
            "value": faker_instance.random_int(min=0, max=100),
        })
    return pd.DataFrame(records)


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Temporary directory for test data files."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def sample_csv_file(temp_data_dir, sample_df):
    """Create a temporary CSV file with sample data."""
    csv_path = temp_data_dir / "sample.csv"
    sample_df.to_csv(csv_path, index=False)
    return csv_path


@pytest.fixture
def sample_json_file(temp_data_dir, borough_dataframe):
    """Create a temporary JSON file with sample data."""
    json_path = temp_data_dir / "sample.json"
    borough_dataframe.to_json(json_path)
    return json_path


@pytest.fixture
def sample_parquet_file(temp_data_dir, inspection_dataframe):
    """Create a temporary Parquet file with sample data."""
    parquet_path = temp_data_dir / "sample.parquet"
    inspection_dataframe.to_parquet(parquet_path)
    return parquet_path


@pytest.fixture
def random_seed():
    """Set random seed for reproducibility."""
    np.random.seed(42)
    return 42


# ============================================================================
# Markers for test classification
# ============================================================================

def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "requires_faker: marks tests that require the faker library"
    )
    config.addinivalue_line(
        "markers", "requires_flask: marks tests that require Flask"
    )
    config.addinivalue_line(
        "markers", "requires_postgres: marks tests that require PostgreSQL"
    )
