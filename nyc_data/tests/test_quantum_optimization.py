"""Tests for quantum optimization module (classical fallback path)."""

import pandas as pd
import pytest

from socrata_toolkit.quantum_optimization import (
    CrewAssignment,
    QuantumConfig,
    RouteResult,
    optimize_crew_assignment,
    optimize_repair_route,
)


def _sample_locations():
    return pd.DataFrame({
        "location_id": ["L1", "L2", "L3", "L4", "L5", "L6"],
        "latitude": [40.71, 40.72, 40.73, 40.74, 40.75, 40.76],
        "longitude": [-74.00, -73.99, -73.98, -73.97, -73.96, -73.95],
        "_priority_score": [0.9, 0.7, 0.5, 0.3, 0.8, 0.6],
        "borough": ["MANHATTAN"] * 3 + ["BROOKLYN"] * 3,
    })


def test_crew_assignment_classical():
    df = _sample_locations()
    result = optimize_crew_assignment(df, n_crews=3)
    assert isinstance(result, CrewAssignment)
    assert result.method == "classical"
    assert len(result.assignments) == 3
    # All locations should be assigned
    all_assigned = sum(len(v) for v in result.assignments.values())
    assert all_assigned == 6
    assert 0 <= result.balance_score <= 1


def test_crew_assignment_fallback_qiskit():
    df = _sample_locations()
    # Qiskit not installed, should fall back to classical
    result = optimize_crew_assignment(df, n_crews=2, config=QuantumConfig(backend="qiskit"))
    assert result.method == "classical"


def test_crew_assignment_fallback_cirq():
    df = _sample_locations()
    result = optimize_crew_assignment(df, n_crews=2, config=QuantumConfig(backend="cirq"))
    assert result.method == "classical"


def test_crew_assignment_single_crew():
    df = _sample_locations()
    result = optimize_crew_assignment(df, n_crews=1)
    assert len(result.assignments[0]) == 6


def test_route_optimization():
    df = _sample_locations()
    result = optimize_repair_route(df)
    assert isinstance(result, RouteResult)
    assert len(result.route) == 6
    assert result.total_distance > 0
    assert result.estimated_time_hours > 0
    assert result.method == "classical_2opt"


def test_route_optimization_single_location():
    df = pd.DataFrame({"location_id": ["L1"], "latitude": [40.71], "longitude": [-74.00]})
    result = optimize_repair_route(df)
    assert len(result.route) == 1
    assert result.total_distance == 0


def test_route_optimization_two_locations():
    df = pd.DataFrame({
        "location_id": ["L1", "L2"],
        "latitude": [40.71, 40.85],
        "longitude": [-74.00, -73.87],
    })
    result = optimize_repair_route(df)
    assert len(result.route) == 2
    assert result.total_distance > 0


def test_quantum_config_defaults():
    cfg = QuantumConfig()
    assert cfg.backend == "classical"
    assert cfg.shots == 1024
    assert cfg.simulator is True
