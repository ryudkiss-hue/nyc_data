from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import pandas as pd

from .core import (
    MODEL_DEFAULT,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
)

logger = logging.getLogger(__name__)

# ── NLP & Text Analytics ──────────────────────────────────────────────────────

@dataclass
class NLPResult:
    sentiment: float
    summary: str
    entities: list[dict[str, str]] = field(default_factory=list)

def sentiment_score(text: str) -> float:
    """Heuristic-based sentiment scoring (falls back to 0.0)."""
    low = text.lower()
    score = 0.0
    for w in ["good", "safe", "improve", "success"]:
        if w in low:
            score += 0.2
    for w in ["bad", "danger", "delay", "fail"]:
        if w in low:
            score -= 0.2
    return max(-1.0, min(1.0, score))

def summarize_text(text: str, max_sentences: int = 2) -> str:
    sents = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    return ". ".join(sents[:max_sentences]) + ("." if sents else "")

# ── LLM & NLP ─────────────────────────────────────────────────────────────────

class SocrataLLMChatbot:
    """Conversational AI for Socrata datasets."""

    def __init__(self, model: str | None = None, model_name: str | None = None, **kwargs):
        self.model = model or model_name or MODEL_DEFAULT
        self.model_name = self.model
        self.llm: Any = None
        self.conversation_history = []
        self.max_history = 10
        self.dataset_context = None

    def chat(self, message: str) -> str:
        return f"Simulated response to: {message}"

class SQLQueryEngine:
    """Natural language to SQL engine."""

    def translate(self, question: str) -> str:
        return f"SELECT * FROM datasets WHERE description LIKE '%{question}%'"

class LegalPolicyEngine:
    """RAG-Powered Legal Policy Engine for NYC Street Design Manual, ADA CFR 36, and Local Law 60."""

    def __init__(self):
        self.knowledge_base = {
            "slope": "ADA CFR 36 § 405.2: Running slope of walking surfaces shall not be steeper than 1:20 (5.0%). Cross slope shall not be steeper than 1:48 (2.0%).",
            "width": "NYC Street Design Manual: Minimum clear path width is 5 feet. In constrained scenarios, 4 feet is permitted with 5x5 passing spaces every 200 feet.",
            "trip": "Local Law 60 (Sidewalk Maintenance): Property owners are responsible for repairing defects including trip hazards greater than 0.5 inches.",
            "owner_responsibility": "NYC Administrative Code § 19-152 (Local Law 60): The owner of any real property, at their own cost and expense, shall install, construct, repave, reconstruct and repair the sidewalk flags in front of or abutting such property.",
            "city_responsibility": "NYC Administrative Code § 19-152 (Exceptions): The city is responsible for sidewalk repairs if the damage is caused by city-owned trees, or for abutting one-, two-, or three-family residential properties strictly occupied for residential purposes.",
        }

    def generate_compliance_memo(self, defect_description: str) -> str:
        """Generates an official compliance memo citing specific legal code based on the defect description."""
        desc_lower = defect_description.lower()
        citations = []

        if any(w in desc_lower for w in {"slope", "steep", "grade"}):
            citations.append(self.knowledge_base["slope"])
        if any(w in desc_lower for w in {"width", "narrow", "clearance", "block"}):
            citations.append(self.knowledge_base["width"])
        if any(w in desc_lower for w in {"trip", "pothole", "crack", "uneven", "lip"}):
            citations.append(self.knowledge_base["trip"])
        if any(w in desc_lower for w in {"owner", "property", "commercial", "responsible"}):
            citations.append(self.knowledge_base["owner_responsibility"])
        if any(
            w in desc_lower
            for w in {"tree", "root", "city", "residential", "1-family", "2-family", "3-family"}
        ):
            citations.append(self.knowledge_base["city_responsibility"])

        if not citations:
            citations.append(
                "General Maintenance Requirement: Sidewalks must be maintained free from defects and pedestrian hazards."
            )

        memo = f"OFFICIAL COMPLIANCE MEMO\n{'=' * 30}\nSubject: Evaluation of Defect - '{defect_description}'\n\nBased on the provided description, the following statutory requirements apply:\n\n"
        for i, citation in enumerate(citations, 1):
            memo += f"{i}. {citation}\n"
        memo += "\nACTION REQUIRED: Field inspection required to verify compliance with the cited regulations."
        return memo

# ── Optimization & Quantum ────────────────────────────────────────────────────

@dataclass
class QuantumSearchResult:
    match_count: int
    method: str
    num_qubits: int
    grover_iterations: int
    circuit_depth: int
    matches: list[Any]

def quantum_search(items: Any, criteria: Any) -> QuantumSearchResult:
    """Simulated quantum search algorithm."""
    count = 1 if items is not None else 0
    return QuantumSearchResult(
        match_count=count,
        method="Grover search",
        num_qubits=8,
        grover_iterations=12,
        circuit_depth=120,
        matches=items[:1] if items is not None and hasattr(items, "__getitem__") else [],
    )

class LLMBridge:
    """Stub for LLM connectivity."""

    def ask(self, prompt: str) -> str:
        return f"Simulated response to: {prompt}"

class TriageEngine:
    """Stub for triage logic."""

    def triage(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        return df

# ── AI Enrichment ─────────────────────────────────────────────────────────────

def enrich_construction_list(
    df: pd.DataFrame, text_col: str | None = "description"
) -> pd.DataFrame:
    """Enrich a construction list with AI-derived features."""
    if text_col not in df.columns:
        return df
    out = df.copy()
    sentiments = []
    summaries = []
    for _, row in df.iterrows():
        text = str(row.get(text_col, ""))
        sentiments.append(sentiment_score(text))
        summaries.append(summarize_text(text))
    out["_ai_sentiment"] = sentiments
    out["_ai_summary"] = summaries
    return out

# ── Optimization (Quantum-Inspired) ───────────────────────────────────────────

@dataclass
class QuantumConfig:
    backend: str = "classical"
    max_iterations: int = 100

@dataclass
class SearchCriteria:
    column: str | None = None
    target_value: Any = None
    tolerance: float = 0.0
    borough: str | None = None
    min_severity: float | None = None
    status: str | None = None

def analyze_grover_circuit(n_records: int, n_solutions: int = 1) -> Any:
    """Return metrics for a Grover quantum search circuit.

    Quantum Advantage: In a dataset of N records, a classical search takes O(N)
    time. Grover's algorithm takes O(sqrt(N)) time, providing a quadratic speedup
    for searching unstructured NYC DOT records.
    """
    n_qubits = max(1, math.ceil(math.log2(max(n_records, 2))))
    # Optimal iterations: pi/4 * sqrt(N/M)
    grover_iters = max(1, int(math.pi / 4 * math.sqrt(n_records / max(n_solutions, 1))))

    return SimpleNamespace(
        num_qubits=n_qubits,
        num_grover_iterations=grover_iters,
        circuit_depth=n_qubits * 12,  # Estimated gates per qubit
        total_states=2**n_qubits,
        theoretical_speedup=f"{round(n_records / grover_iters, 2)}x",
        method="Grover Unstructured Search",
    )

def analyze_quantum_efficiency(n_records: int) -> Any:
    """Compare classical vs quantum complexity for infrastructure audits."""
    classical_ops = n_records
    quantum_ops = math.sqrt(n_records)
    efficiency_gain = (classical_ops - quantum_ops) / classical_ops * 100

    return {
        "classical_complexity": "O(N)",
        "quantum_complexity": "O(√N)",
        "estimated_efficiency_gain_pct": round(efficiency_gain, 4),
        "status": "Quantum Ready",
    }

def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance in miles between two points on the earth."""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 3956  # Radius of earth in miles
    return c * r

@dataclass
class RouteOptResult:
    total_distance_miles: float
    estimated_time_hours: float
    method: str
    route: list[Any]
    ordered_df: pd.DataFrame

def optimize_repair_route(
    df: pd.DataFrame, lat_col: str = "latitude", lon_col: str = "longitude"
) -> Any:
    """Return an optimized route using a Nearest Neighbor TSP heuristic.
    Orders a dataframe of locations to minimize travel time for in-house crews.
    """
    if df.empty or lat_col not in df.columns or lon_col not in df.columns:
        return RouteOptResult(
            total_distance_miles=0.0,
            estimated_time_hours=0.0,
            method="Nearest Neighbor TSP",
            route=[],
            ordered_df=df,
        )

    # Drop rows with missing coordinates for routing
    valid_df = df.dropna(subset=[lat_col, lon_col]).copy()
    if valid_df.empty:
        return RouteOptResult(
            total_distance_miles=0.0,
            estimated_time_hours=0.0,
            method="Nearest Neighbor TSP",
            route=[],
            ordered_df=df,
        )

    unvisited = valid_df.index.tolist()
    current_node = unvisited.pop(0)  # Start at the first location in the list
    route = [current_node]
    total_distance = 0.0

    while unvisited:
        current_lat, current_lon = (
            float(valid_df.loc[current_node, lat_col]),
            float(valid_df.loc[current_node, lon_col]),
        )
        # Find the nearest neighbor
        distances = [
            (
                node,
                _haversine_distance(
                    current_lat,
                    current_lon,
                    float(valid_df.loc[node, lat_col]),
                    float(valid_df.loc[node, lon_col]),
                ),
            )
            for node in unvisited
        ]
        nearest_node, min_dist = min(distances, key=lambda x: x[1])

        route.append(nearest_node)
        total_distance += min_dist
        unvisited.remove(nearest_node)
        current_node = nearest_node

    return RouteOptResult(
        total_distance_miles=round(total_distance, 2),
        estimated_time_hours=round(
            total_distance / 10.0 + (len(route) * 0.5), 1
        ),  # Assume 10mph in NYC + 30 mins per stop
        method="Nearest Neighbor TSP",
        route=route,
        ordered_df=valid_df.loc[route].reset_index(drop=True),
    )

@dataclass
class CrewAssignResult:
    method: str
    total_cost: float
    balance_score: float
    assignments: dict[str, list[str]]

def optimize_crew_assignment(
    df: pd.DataFrame, n_crews: int = 5, config: Any = None
) -> CrewAssignResult:
    """Simulate crew assignment optimization."""
    assignments = {f"crew_{i + 1}": [] for i in range(n_crews)}
    for idx in df.index:
        crew = f"crew_{(idx % n_crews) + 1}"
        assignments[crew].append(str(idx))
    return CrewAssignResult(
        method=(config.backend if config and hasattr(config, "backend") else "classical")
        + " solver",
        total_cost=float(len(df) * 12.5),
        balance_score=0.92,
        assignments=assignments,
    )

def triage_complaints(
    df: pd.DataFrame,
    text_col: str = "description",
    api_url: str = "http://localhost:8000/v1/chat/completions",
) -> pd.DataFrame:
    """
    Classify 311 complaints by sending them to your local LLM API.
    Requires the local model to be running and exposing a standard REST endpoint.
    """
    import requests

    out = df.copy()
    priorities = []

    for _, row in out.iterrows():
        text = str(row.get(text_col, ""))
        if not text.strip():
            priorities.append(PRIORITY_MEDIUM)
            continue

        try:
            # Prompt your local model to act as a triage agent
            payload = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an NYC DOT triage agent. Read the complaint and output ONLY: CRITICAL, HIGH, MEDIUM, or LOW.",
                    },
                    {"role": "user", "content": text},
                ],
                "temperature": 0.1,
            }
            res = requests.post(api_url, json=payload, timeout=5).json()
            reply = (
                res.get("choices", [{}])[0].get("message", {}).get("content", "").strip().upper()
            )
            priorities.append(
                reply
                if reply in {PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW}
                else PRIORITY_MEDIUM
            )
        except Exception as e:
            logger.warning(f"Local LLM parsing failed: {e}")
            priorities.append(PRIORITY_MEDIUM)

    out["_priority"] = priorities
    return out

def export_training_data_for_local_llm(
    df: pd.DataFrame, output_path: str, text_col: str = "description", label_col: str = "severity"
):
    """
    Exports historical Socrata datasets into a standard JSONL format to fine-tune
    your local models so they learn how to parse NYC DOT terminology.
    """
    import json

    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in df.dropna(subset=[text_col, label_col]).iterrows():
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an NYC DOT triage agent. Categorize the severity of the following 311 complaint.",
                    },
                    {"role": "user", "content": str(row[text_col])},
                    {"role": "assistant", "content": str(row[label_col])},
                ]
            }
            f.write(json.dumps(example) + "\n")

def triage_complaints_gemini(
    df: pd.DataFrame, text_col: str, model_name: str, api_key: str
) -> pd.DataFrame:
    """
    Classify 311 complaints by sending them to the Google Gemini API.
    """
    import requests

    out = df.copy()
    priorities = []

    for _, row in out.iterrows():
        text = str(row.get(text_col, ""))
        if not text.strip() or not api_key:
            priorities.append(PRIORITY_MEDIUM)
            continue

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Categorize severity as CRITICAL, HIGH, MEDIUM, or LOW: {text}"
                            }
                        ]
                    }
                ]
            }
            res = requests.post(url, json=payload, timeout=5).json()
            reply = (
                res.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
                .upper()
            )
            priorities.append(
                reply
                if reply in {PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW}
                else PRIORITY_MEDIUM
            )
        except Exception as e:
            logger.warning(f"Gemini API parsing failed: {e}")
            priorities.append(PRIORITY_MEDIUM)

    out["_priority"] = priorities
    return out
