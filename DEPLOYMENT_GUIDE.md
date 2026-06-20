# Dual-Tier Fuzzy Router Deployment Guide

## Overview

The NYC DOT SIM Dual-Tier Fuzzy Router is a production-ready question-answering system that routes analyst natural language questions to pre-built KPI answers and optional Claude-powered synthesis.

## Installation

### Prerequisites
- Python 3.11+
- pip or conda

### Setup

1. **Install the package:**
```bash
pip install -e ".[dev,mission]"
```

2. **Initialize configuration:**
```bash
# Configuration is loaded from:
# - config/kpi_registry.json (pre-built KPI metadata)
# - config/research_questions.json (research question templates)
# - cache/kpi_embeddings.json (pre-computed Claude embeddings)
# - data/local_db/router_observability.duckdb (observability store)

# All directories are created automatically on first run
```

3. **Set environment variables (optional):**
```bash
export ROUTER_REGISTRY_PATH="config/kpi_registry.json"
export ROUTER_QUESTIONS_PATH="config/research_questions.json"
export ROUTER_EMBEDDINGS_CACHE_PATH="cache/kpi_embeddings.json"
export ROUTER_OBSERVABILITY_DB="data/local_db/router_observability.duckdb"
export ROUTER_DEBUG="false"
```

## Usage

### Command Line

**Basic query:**
```bash
socrata-nlquery "How many violations were fixed by borough?"
```

**With Tier 2 expansion:**
```bash
socrata-nlquery "Why are violations spiking in Manhattan?" --expand
```

**Record feedback as helpful:**
```bash
socrata-nlquery "violations fixed by borough" --helpful
```

**Correct a wrong match:**
```bash
socrata-nlquery "violations fixed" --wrong --corrected-kpi KPI-045
```

**Output as JSON:**
```bash
socrata-nlquery "question" --json
```

### Python API

```python
from socrata_toolkit.core.cli_nlquery import run_nl_query
from socrata_toolkit.core.config import get_config

config = get_config()
kpi_registry = config.load_kpi_registry()
research_questions = config.load_research_questions()
embeddings_cache = config.load_embeddings_cache()

result = run_nl_query(
    question="How many violations fixed?",
    kpi_registry=kpi_registry,
    research_questions=research_questions,
    embeddings_cache=embeddings_cache,
    expand=False
)

print(result)
```

## Architecture

### Tier 1: Pre-Built Answers (Instant)
- **Router:** Hybrid ensemble of programmatic (BM25/FastText/Jaccard) + Claude embeddings
- **Latency:** <200ms
- **Output:** KPI metadata, datasets, SQL pattern, visualizations

### Tier 2: Claude Expansion (On-Demand)
- **Triggered by:** `--expand` flag
- **Latency:** ~5 seconds
- **Output:** Claude synthesis + NLP-suggested next questions

### Observability
- **Storage:** DuckDB (persists routing decisions, feedback, weight history)
- **Metrics:** Routing accuracy, ensemble agreement, feedback collection
- **Queries:** Track system performance over time

## Configuration Files

### KPI Registry (`config/kpi_registry.json`)
```json
{
  "KPI-089": {
    "kpi_id": "KPI-089",
    "kpi_name": "Violations Fixed by Borough & Month",
    "summary": "...",
    "datasets": [...],
    "sql_pattern": "SELECT ...",
    "related_kpis": [...]
  }
}
```

### Research Questions (`config/research_questions.json`)
```json
[
  {
    "question_id": "Q1",
    "text": "Why are violations spiking?",
    "related_kpi": "KPI-089",
    "category": "Root Cause Analysis"
  }
]
```

## Performance Tuning

### Caching
- Embeddings are pre-computed and cached in `cache/kpi_embeddings.json`
- KPI registry is loaded once at startup
- DuckDB uses memory-mapped I/O for fast access

### Scaling
- For >1000 KPIs: Consider sharding the registry by category
- For high QPS: Deploy multiple CLI instances behind a load balancer
- For Tier 2: Use Claude API caching for repeated questions

## Monitoring

### Check routing accuracy (last 24h):
```python
from socrata_toolkit.core.observability.duckdb_store import DuckDBObservabilityStore

store = DuckDBObservabilityStore()
accuracy = store.get_routing_accuracy(window_hours=24)
print(f"Routing accuracy: {accuracy:.2%}")
```

### Get recent feedback:
```python
recent = store.get_recent_feedback(limit=100)
for f in recent:
    print(f"{f['question']} -> {f['original_kpi_id']} (helpful: {f['helpful']})")
```

## Deployment Checklist

- [ ] Python 3.11+ installed
- [ ] Package installed: `pip install -e ".[mission]"`
- [ ] Config files present: `config/kpi_registry.json`, `config/research_questions.json`
- [ ] Embeddings cache ready: `cache/kpi_embeddings.json`
- [ ] DuckDB initialized: `data/local_db/router_observability.duckdb`
- [ ] CLI callable: `socrata-nlquery --help`
- [ ] Tests passing: `pytest tests/ -q`

## Troubleshooting

**No KPIs found:**
- Check `config/kpi_registry.json` exists and is valid JSON
- Verify `ROUTER_REGISTRY_PATH` environment variable if set

**CLI not found:**
- Run `pip install -e .` to register CLI entry points
- Check `socrata-nlquery --help` works

**Slow responses:**
- Check embeddings cache is loaded (`cache/kpi_embeddings.json` exists)
- Consider disabling `--expand` for faster Tier 1-only responses

## Support

For issues or feature requests, see the project repository or contact the development team.
