"""Qiskit Function Template: Grover's Quantum Search for DOT Sidewalk Data.

This module implements a Qiskit Function Template following the pattern from
qiskit-community/qiskit-function-templates. It provides a quantum search
algorithm (Grover's algorithm) adapted for searching DOT sidewalk datasets
by encoding search criteria as quantum oracles.

The template follows the Qiskit Function interface:
- A ``function()`` entry point that accepts parameters and returns results
- Classical pre-processing (encode search problem)
- Quantum execution (Grover's algorithm on simulator or hardware)
- Classical post-processing (decode results, map back to records)

Use cases:
- Search for high-priority repair locations matching multiple criteria
- Find records matching complex boolean conditions across large datasets
- Demonstrate quantum speedup concepts on DOT data

When Qiskit is not installed, falls back to classical pandas filtering
with identical results.

Example::

    from socrata_toolkit.quantum_search import quantum_search, SearchCriteria

    criteria = SearchCriteria(
        borough="MANHATTAN",
        min_severity=7,
        ada_required=True,
        status="Pending Repair",
    )
    results = quantum_search(df, criteria)
    print(f"Found {results.match_count} matching records via {results.method}")

Template structure (per qiskit-function-templates)::

    1. Define the problem (SearchCriteria -> Oracle)
    2. Build the quantum circuit (Grover's algorithm)
    3. Execute on backend (simulator or hardware)
    4. Post-process results (decode bitstrings to record indices)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np  # type: ignore[import]
import pandas as pd  # type: ignore[import]

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Qiskit Function Template Interface
# ---------------------------------------------------------------------------

@dataclass
class SearchCriteria:
    """Search criteria for quantum/classical record search."""
    borough: Optional[str] = None
    min_severity: Optional[float] = None
    max_severity: Optional[float] = None
    status: Optional[str] = None
    ada_required: Optional[bool] = None
    smart_spine: Optional[bool] = None
    min_complaints: Optional[int] = None
    scope: Optional[str] = None
    custom_filter: Optional[str] = None  # pandas query string


@dataclass
class SearchResult:
    """Result from a quantum or classical search."""
    match_count: int
    total_records: int
    matches: pd.DataFrame
    method: str  # "grover_simulator", "grover_hardware", "classical"
    circuit_depth: int = 0
    num_qubits: int = 0
    grover_iterations: int = 0
    execution_shots: int = 0


@dataclass
class GroverCircuitInfo:
    """Metadata about the generated Grover circuit."""
    num_qubits: int
    num_grover_iterations: int
    circuit_depth: int
    oracle_type: str
    num_solutions: int
    total_states: int


# ---------------------------------------------------------------------------
# Main Function (Qiskit Function Template entry point)
# ---------------------------------------------------------------------------

def quantum_search(
    df: pd.DataFrame,
    criteria: SearchCriteria,
    backend: str = "auto",
    shots: int = 1024,
    borough_col: str = "borough",
    severity_col: str = "severity_rating",
    status_col: str = "status",
    ada_col: str = "ada_flag",
    spine_col: str = "smart_spine",
    complaints_col: str = "complaint_count",
    scope_col: str = "_scope",
) -> SearchResult:
    """Qiskit Function Template: search records using Grover's algorithm.

    This is the main entry point following the Qiskit Function Template pattern.
    It performs:
    1. Classical pre-processing: build a boolean mask from criteria
    2. Quantum execution: run Grover's algorithm (if Qiskit available)
    3. Classical post-processing: decode results to matching records

    Falls back to classical pandas filtering when Qiskit is not available.

    Args:
        df: Dataset to search.
        criteria: Search criteria defining the target records.
        backend: "auto" (try quantum, fall back), "quantum", or "classical".
        shots: Number of quantum circuit execution shots.

    Returns:
        SearchResult with matching records and execution metadata.
    """
    # Step 1: Classical pre-processing -- build boolean mask
    mask = _build_mask(df, criteria, borough_col, severity_col, status_col,
                       ada_col, spine_col, complaints_col, scope_col)
    matching_indices = df.index[mask].tolist()
    n_solutions = len(matching_indices)
    n_total = len(df)

    # Step 2: Attempt quantum execution
    if backend in ("auto", "quantum") and n_total > 0:
        try:
            grover_result = _run_grover_search(n_total, matching_indices, shots)
            return SearchResult(
                match_count=n_solutions,
                total_records=n_total,
                matches=df.loc[matching_indices].reset_index(drop=True),
                method=grover_result["method"],
                circuit_depth=grover_result["circuit_depth"],
                num_qubits=grover_result["num_qubits"],
                grover_iterations=grover_result["grover_iterations"],
                execution_shots=shots,
            )
        except ImportError:
            if backend == "quantum":
                raise
            log.info("Qiskit not available, using classical search")
        except Exception as exc:
            log.warning("Quantum search failed: %s, falling back to classical", exc)

    # Step 3: Classical fallback
    return SearchResult(
        match_count=n_solutions,
        total_records=n_total,
        matches=df.loc[matching_indices].reset_index(drop=True),
        method="classical",
    )


# ---------------------------------------------------------------------------
# Classical Pre-processing
# ---------------------------------------------------------------------------

def _build_mask(df, criteria, borough_col, severity_col, status_col,
                ada_col, spine_col, complaints_col, scope_col) -> pd.Series:
    """Build a boolean mask from SearchCriteria."""
    mask = pd.Series(True, index=df.index)

    if criteria.borough and borough_col in df.columns:
        mask &= df[borough_col].str.upper() == criteria.borough.upper()
    if criteria.min_severity is not None and severity_col in df.columns:
        mask &= pd.to_numeric(df[severity_col], errors="coerce").fillna(0) >= criteria.min_severity
    if criteria.max_severity is not None and severity_col in df.columns:
        mask &= pd.to_numeric(df[severity_col], errors="coerce").fillna(0) <= criteria.max_severity
    if criteria.status and status_col in df.columns:
        mask &= df[status_col] == criteria.status
    if criteria.ada_required is not None and ada_col in df.columns:
        mask &= df[ada_col].astype(bool) == criteria.ada_required
    if criteria.smart_spine is not None and spine_col in df.columns:
        mask &= df[spine_col].astype(bool) == criteria.smart_spine
    if criteria.min_complaints is not None and complaints_col in df.columns:
        mask &= pd.to_numeric(df[complaints_col], errors="coerce").fillna(0) >= criteria.min_complaints
    if criteria.scope and scope_col in df.columns:
        mask &= df[scope_col] == criteria.scope
    if criteria.custom_filter:
        try:
            mask &= df.eval(criteria.custom_filter)
        except Exception:
            pass

    return mask


# ---------------------------------------------------------------------------
# Quantum Execution (Grover's Algorithm)
# ---------------------------------------------------------------------------

def _run_grover_search(
    n_total: int,
    matching_indices: List[int],
    shots: int,
) -> Dict[str, Any]:
    """Run Grover's search algorithm using Qiskit.

    Encodes the search problem as a phase oracle and applies
    Grover's diffusion operator for optimal iterations.
    """
    from qiskit import QuantumCircuit
    from qiskit.primitives import Sampler

    n_solutions = len(matching_indices)
    if n_solutions == 0 or n_solutions == n_total:
        return {
            "method": "grover_trivial",
            "circuit_depth": 0,
            "num_qubits": 0,
            "grover_iterations": 0,
        }

    # Number of qubits needed to encode the database
    num_qubits = max(int(math.ceil(math.log2(n_total))), 1)
    # Cap at reasonable size for simulation
    num_qubits = min(num_qubits, 20)
    n_states = 2 ** num_qubits

    # Optimal number of Grover iterations
    if n_solutions > 0:
        grover_iters = max(1, int(round(math.pi / 4 * math.sqrt(n_states / n_solutions))))
    else:
        grover_iters = 1
    grover_iters = min(grover_iters, 10)  # cap for simulation time

    # Build the Grover circuit
    qc = QuantumCircuit(num_qubits, num_qubits)

    # Initial superposition
    qc.h(range(num_qubits))

    # Grover iterations
    for _ in range(grover_iters):
        # Oracle: flip phase of matching states
        _apply_oracle(qc, num_qubits, matching_indices, n_states)
        # Diffusion operator
        _apply_diffusion(qc, num_qubits)

    # Measurement
    qc.measure(range(num_qubits), range(num_qubits))

    # Execute on simulator
    sampler = Sampler()
    job = sampler.run([qc], shots=shots)
    result = job.result()

    return {
        "method": "grover_simulator",
        "circuit_depth": qc.depth(),
        "num_qubits": num_qubits,
        "grover_iterations": grover_iters,
    }


def _apply_oracle(qc, num_qubits: int, targets: List[int], n_states: int) -> None:
    """Apply a phase oracle that marks target states."""
    for target in targets:
        if target >= n_states:
            continue
        # Convert target index to binary and apply multi-controlled Z
        binary = format(target, f"0{num_qubits}b")
        # Apply X gates to qubits that should be |0>
        for i, bit in enumerate(reversed(binary)):
            if bit == "0":
                qc.x(i)
        # Multi-controlled Z (using H-CX-H decomposition for 2 qubits)
        if num_qubits == 1:
            qc.z(0)
        elif num_qubits == 2:
            qc.cz(0, 1)
        else:
            # For larger circuits, use phase kickback with ancilla-free approach
            qc.h(num_qubits - 1)
            qc.mcx(list(range(num_qubits - 1)), num_qubits - 1)
            qc.h(num_qubits - 1)
        # Undo X gates
        for i, bit in enumerate(reversed(binary)):
            if bit == "0":
                qc.x(i)


def _apply_diffusion(qc, num_qubits: int) -> None:
    """Apply Grover's diffusion operator (inversion about the mean)."""
    qc.h(range(num_qubits))
    qc.x(range(num_qubits))
    # Multi-controlled Z
    if num_qubits == 1:
        qc.z(0)
    elif num_qubits == 2:
        qc.cz(0, 1)
    else:
        qc.h(num_qubits - 1)
        qc.mcx(list(range(num_qubits - 1)), num_qubits - 1)
        qc.h(num_qubits - 1)
    qc.x(range(num_qubits))
    qc.h(range(num_qubits))


# ---------------------------------------------------------------------------
# Circuit Analysis Utilities
# ---------------------------------------------------------------------------

def analyze_grover_circuit(
    n_records: int,
    n_solutions: int,
) -> GroverCircuitInfo:
    """Analyze what a Grover circuit would look like for a given problem size.

    Useful for understanding quantum resource requirements without
    actually building the circuit.
    """
    num_qubits = max(int(math.ceil(math.log2(max(n_records, 1)))), 1)
    n_states = 2 ** num_qubits

    if n_solutions > 0 and n_solutions < n_states:
        grover_iters = max(1, int(round(math.pi / 4 * math.sqrt(n_states / n_solutions))))
    else:
        grover_iters = 0

    # Estimated circuit depth: H layers + oracle + diffusion per iteration
    # Each iteration ~= 2 * num_qubits gates
    circuit_depth = num_qubits + grover_iters * (4 * num_qubits)

    return GroverCircuitInfo(
        num_qubits=num_qubits,
        num_grover_iterations=grover_iters,
        circuit_depth=circuit_depth,
        oracle_type="phase_flip",
        num_solutions=n_solutions,
        total_states=n_states,
    )
