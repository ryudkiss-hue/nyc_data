"""Tests for quantum search function template (classical path)."""
import pandas as pd
import pytest

from socrata_toolkit.quantum.search import (
    GroverCircuitInfo,
    SearchCriteria,
    SearchResult,
    analyze_grover_circuit,
    quantum_search,
)


def _sample_data():
    return pd.DataFrame({
        "borough": ["MANHATTAN", "MANHATTAN", "BROOKLYN", "QUEENS", "BRONX"],
        "severity_rating": [8, 3, 9, 2, 7],
        "status": ["Pending Repair", "Complete", "Pending Repair", "Complete", "Pending Repair"],
        "ada_flag": [True, False, False, False, True],
        "smart_spine": [True, False, True, False, True],
        "complaint_count": [5, 0, 8, 1, 3],
    })


def test_quantum_search_basic():
    df = _sample_data()
    criteria = SearchCriteria(borough="MANHATTAN")
    result = quantum_search(df, criteria)
    assert isinstance(result, SearchResult)
    assert result.match_count == 2
    assert result.method == "classical"  # Qiskit not installed
    assert len(result.matches) == 2


def test_quantum_search_severity():
    df = _sample_data()
    criteria = SearchCriteria(min_severity=7)
    result = quantum_search(df, criteria)
    assert result.match_count == 3  # severity 8, 9, 7


def test_quantum_search_combined_criteria():
    df = _sample_data()
    criteria = SearchCriteria(borough="MANHATTAN", min_severity=5, status="Pending Repair")
    result = quantum_search(df, criteria)
    assert result.match_count == 1  # only Manhattan, severity 8, Pending


def test_quantum_search_ada():
    df = _sample_data()
    criteria = SearchCriteria(ada_required=True)
    result = quantum_search(df, criteria)
    assert result.match_count == 2


def test_quantum_search_no_matches():
    df = _sample_data()
    criteria = SearchCriteria(borough="STATEN ISLAND")
    result = quantum_search(df, criteria)
    assert result.match_count == 0
    assert len(result.matches) == 0


def test_quantum_search_all_match():
    df = _sample_data()
    criteria = SearchCriteria()  # no filters
    result = quantum_search(df, criteria)
    assert result.match_count == 5


def test_quantum_search_min_complaints():
    df = _sample_data()
    criteria = SearchCriteria(min_complaints=5)
    result = quantum_search(df, criteria)
    assert result.match_count == 2  # 5 and 8


def test_quantum_search_custom_filter():
    df = _sample_data()
    criteria = SearchCriteria(custom_filter="severity_rating > 5")
    result = quantum_search(df, criteria)
    assert result.match_count == 3


def test_analyze_grover_circuit():
    info = analyze_grover_circuit(n_records=1000, n_solutions=10)
    assert isinstance(info, GroverCircuitInfo)
    assert info.num_qubits == 10  # ceil(log2(1000))
    assert info.total_states == 1024
    assert info.num_grover_iterations > 0
    assert info.circuit_depth > 0


def test_analyze_grover_circuit_small():
    info = analyze_grover_circuit(n_records=4, n_solutions=1)
    assert info.num_qubits == 2
    assert info.num_grover_iterations >= 1


def test_analyze_grover_circuit_all_solutions():
    info = analyze_grover_circuit(n_records=8, n_solutions=8)
    assert info.num_grover_iterations == 0  # no search needed
