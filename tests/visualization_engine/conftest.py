"""Pytest configuration and fixtures for visualization engine tests.

Provides mock MotherDuck connections and test data for all phases.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pandas as pd
import pytest

from socrata_toolkit.motherduck.connector import MotherDuckConnection


@pytest.fixture
def mock_connection():
    """Create a mock MotherDuckConnection for testing.

    Returns:
        MagicMock of MotherDuckConnection
    """
    conn = MagicMock()
    return conn


@pytest.fixture
def phase_b_test_data():
    """Create test data for Phase B (spatial clustering).

    Returns:
        DataFrame with Phase B test data
    """
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "morans_i_value": [0.65, 0.42, -0.15, 0.28, -0.08],
            "classification": [
                "STRONG_CLUSTERING",
                "MODERATE_CLUSTERING",
                "RANDOM_DISTRIBUTION",
                "MODERATE_CLUSTERING",
                "SPATIAL_DISPERSION",
            ],
            "location_count": [250, 180, 150, 200, 95],
            "p_value": [0.001, 0.045, 0.85, 0.12, 0.92],
            "significance": [
                "Significant",
                "Significant",
                "Not Significant",
                "Not Significant",
                "Not Significant",
            ],
            "analytics_timestamp": [datetime.now() - timedelta(days=i) for i in range(5)],
        }
    )


@pytest.fixture
def phase_c_test_data():
    """Create test data for Phase C (distributions).

    Returns:
        DataFrame with Phase C test data
    """
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "record_count": [1000, 850, 720, 950, 580],
            "mean_val": [15.5, 12.3, 18.7, 10.2, 22.1],
            "median_val": [14.0, 11.5, 17.5, 9.0, 20.0],
            "std_val": [8.5, 7.2, 9.1, 6.3, 11.5],
            "skewness": [0.85, 0.42, -0.25, 1.15, -0.55],
            "distribution_type": [
                "RIGHT_SKEWED",
                "NORMAL",
                "LEFT_SKEWED",
                "RIGHT_SKEWED",
                "LEFT_SKEWED",
            ],
            "concentration_percent": [42.5, 38.1, 45.3, 35.7, 52.1],
            "min_val": [0, 0, 1, 0, 2],
            "max_val": [95, 82, 78, 88, 105],
            "analytics_timestamp": [datetime.now() - timedelta(days=i) for i in range(5)],
        }
    )


@pytest.fixture
def phase_d_test_data():
    """Create test data for Phase D (geographic anomalies).

    Returns:
        DataFrame with Phase D test data
    """
    import random

    random.seed(42)

    locations = []
    for borough in ["MN", "BK", "BX", "QN", "SI"]:
        for i in range(5):
            locations.append(
                {
                    "location_id": f"{borough}-{i:03d}",
                    "borough": borough,
                    "latitude": 40.7 + random.uniform(-0.1, 0.1),
                    "longitude": -74.0 + random.uniform(-0.1, 0.1),
                    "inspection_count": random.randint(10, 100),
                    "z_score_violations": random.uniform(-3, 3),
                    "outlier_class": random.choice(["HIGH_OUTLIER", "NORMAL", "LOW_OUTLIER"]),
                    "priority_rank": i + 1,
                    "analytics_timestamp": datetime.now(),
                }
            )

    return pd.DataFrame(locations)


@pytest.fixture
def phase_e_test_data():
    """Create test data for Phase E (time series decomposition).

    Returns:
        DataFrame with Phase E test data
    """
    dates = pd.date_range(start="2026-04-01", end="2026-06-10", freq="D")
    data_rows = []

    for date in dates:
        for borough in ["MN", "BK", "BX", "QN", "SI"]:
            data_rows.append(
                {
                    "date": date,
                    "borough": borough,
                    "violation_count": 50 + (20 * (date.day % 7) / 7),
                    "trend_value": 45.0 + (date.day / 30),
                    "seasonal_value": 15.0 * (date.day % 7 - 3.5) / 7,
                    "residual_value": (hash(str(date) + borough) % 10 - 5) / 10,
                    "forecast_next_period": 50.0 + (20 * ((date.day + 1) % 7) / 7),
                    "analytics_timestamp": datetime.now(),
                }
            )

    return pd.DataFrame(data_rows)


@pytest.fixture
def phase_f_test_data():
    """Create test data for Phase F (bootstrap CI & SLA).

    Returns:
        DataFrame with Phase F test data
    """
    return pd.DataFrame(
        {
            "borough": ["MN", "BK", "BX", "QN", "SI"],
            "point_estimate": [0.82, 0.75, 0.88, 0.71, 0.79],
            "ci_lower_95": [0.78, 0.70, 0.85, 0.66, 0.74],
            "ci_upper_95": [0.86, 0.80, 0.91, 0.76, 0.84],
            "interval_width": [0.08, 0.10, 0.06, 0.10, 0.10],
            "prob_meets_sla": [0.85, 0.72, 0.92, 0.68, 0.78],
            "risk_level": ["HIGH", "MEDIUM", "HIGH", "LOW", "MEDIUM"],
            "analytics_timestamp": [datetime.now() - timedelta(days=i) for i in range(5)],
        }
    )


@pytest.fixture
def kpi_test_data():
    """Create test data for KPI cards.

    Returns:
        DataFrame with KPI test data
    """
    kpi_names = [
        "phase_b_clustering_strength",
        "phase_b_confidence",
        "phase_b_resource_gap",
        "phase_c_concentration_index",
        "phase_c_segmentation_potential",
        "phase_c_type_certainty",
        "phase_c_distribution_balance",
        "phase_d_outlier_concentration",
        "phase_d_adoption_rate",
        "phase_d_priority_score",
        "phase_e_trend_direction",
        "phase_e_seasonality_strength",
        "phase_e_resource_gap",
        "phase_e_forecast_confidence",
        "phase_f_sla_probability",
        "phase_f_risk_score",
        "phase_f_ci_coverage",
        "phase_f_investment_justification",
    ]

    data_rows = []
    for borough in ["MN", "BK", "BX", "QN", "SI"]:
        for i, kpi_name in enumerate(kpi_names):
            data_rows.append(
                {
                    "kpi_name": kpi_name,
                    "borough": borough,
                    "kpi_value": 50 + (i * 2) % 40,
                    "metric_category": kpi_name.replace("_", " ").title(),
                    "analytics_timestamp": datetime.now(),
                }
            )

    return pd.DataFrame(data_rows)
