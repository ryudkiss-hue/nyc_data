# `socrata_toolkit.ai` — AI, NL→SQL & Optimization

**File:** `socrata_toolkit/ai.py` | **Pillar:** AI  
**Dependencies:** `pandas`, `openai`/`langchain` (optional), `scikit-learn` (optional)

---

## NLP & Sentiment

### `sentiment_score(text) → float`
Heuristic sentiment scoring. Returns a value in `[-1.0, 1.0]`.

Positive keywords: `good, safe, improve, success` (+0.2 each)  
Negative keywords: `bad, danger, delay, fail` (-0.2 each)

```python
from socrata_toolkit import sentiment_score

score = sentiment_score("The repair was successful and safe")
# → 0.4
score = sentiment_score("Dangerous delay on this project")
# → -0.4
```

### `enrich_construction_list(df, text_col="description") → pd.DataFrame`
Adds `_ai_sentiment` (float) and `_ai_summary` (str) columns to a construction DataFrame.

```python
from socrata_toolkit import enrich_construction_list

enriched = enrich_construction_list(df, text_col="description")
print(enriched[["description", "_ai_sentiment", "_ai_summary"]].head())
```

---

## LLM Chatbot

### `SocrataLLMChatbot`
Conversational AI interface for Socrata datasets.

```python
from socrata_toolkit import SocrataLLMChatbot

bot = SocrataLLMChatbot(model="gpt-4o")
response = bot.chat("How many 311 complaints were filed in Brooklyn last month?")
print(response)
```

| Attribute | Description |
|-----------|-------------|
| `model` | LLM model name (default: `gpt-3.5-turbo`) |
| `conversation_history` | List of past exchanges |
| `max_history` | Max exchanges to retain (default: 10) |
| `dataset_context` | Optional dataset context for grounding |

---

## NL→SQL

### `SQLQueryEngine`
Natural language to SQL translation engine.

```python
from socrata_toolkit.ai import SQLQueryEngine

engine = SQLQueryEngine()
sql = engine.translate("Show me all complaints in Queens from 2024")
print(sql)  # → "SELECT * FROM datasets WHERE description LIKE '%...%'"
```

> Extend this class with a real LangChain `SQLDatabaseChain` or OpenAI function-calling backend for production use.

---

## Quantum-Inspired Search

### `quantum_search(items, criteria) → SimpleNamespace`
Simulates a Grover-algorithm-inspired search over a collection.

```python
from socrata_toolkit import quantum_search

result = quantum_search(items=df.to_dict("records"), criteria={"borough": "BROOKLYN"})
print(result.method)            # "Grover search"
print(result.num_qubits)        # e.g. 13
print(result.grover_iterations) # e.g. 12
print(result.match_count)       # 1
```

Returns: `{match_count, method, num_qubits, grover_iterations, circuit_depth, matches}`

### `analyze_grover_circuit(n_records, n_solutions=1) → SimpleNamespace`
Compute theoretical Grover circuit parameters for a given dataset size.

```python
from socrata_toolkit.ai import analyze_grover_circuit

circuit = analyze_grover_circuit(n_records=50000, n_solutions=1)
print(circuit.num_qubits)           # 16
print(circuit.num_grover_iterations) # ~176
print(circuit.circuit_depth)        # 160
print(circuit.total_states)         # 65536
```

Formula:
- `n_qubits = ceil(log2(n_records))`
- `grover_iterations = floor(π/4 × sqrt(N/k))` where `k = n_solutions`

---

## Route Optimization

### `optimize_repair_route(df, lat_col, lon_col) → SimpleNamespace`
Simulated TSP route optimization using simulated annealing.

```python
from socrata_toolkit.ai import optimize_repair_route

route = optimize_repair_route(df, lat_col="latitude", lon_col="longitude")
print(route.total_distance)        # 42.5 km
print(route.estimated_time_hours)  # 3.5 hours
print(route.method)                # "Simulated Annealing"
print(route.route)                 # [0, 3, 1, 7, 2, ...] — index order
```

---

## Crew Assignment

### `optimize_crew_assignment(df, n_crews=5, config=None) → SimpleNamespace`
Distribute work items across N crews using a round-robin assignment strategy.

```python
from socrata_toolkit.ai import optimize_crew_assignment, QuantumConfig

config = QuantumConfig(backend="quantum", max_iterations=200)
assignment = optimize_crew_assignment(df, n_crews=4, config=config)

print(assignment.method)       # "quantum solver"
print(assignment.total_cost)   # float
print(assignment.balance_score)# 0.92 (0–1, higher is more balanced)
print(assignment.assignments)  # {"crew_1": ["0","3",...], "crew_2": [...]}
```

### `QuantumConfig` (dataclass)
```python
@dataclass
class QuantumConfig:
    backend: str = "classical"  # "classical" | "quantum" | "hybrid"
    max_iterations: int = 100
```

---

## 311 Triage

### `triage_complaints(df) → pd.DataFrame`
Classify 311 complaints by priority using basic NLP. Adds `_priority` column.

```python
from socrata_toolkit.ai import triage_complaints

triaged = triage_complaints(df)
# → adds "_priority" column: "critical" | "high" | "medium" | "low"
```

---

## Search Criteria

### `SearchCriteria` (dataclass)
Structured search parameters for quantum search.

```python
@dataclass
class SearchCriteria:
    column: str|None = None
    target_value: Any = None
    tolerance: float = 0.0
    borough: str|None = None
    min_severity: float|None = None
    status: str|None = None
```
