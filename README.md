# NYC DOT SIM Dual-Tier Fuzzy Router

A production-ready natural language question-answering system for NYC Department of Transportation analysts. Routes analyst questions to pre-built KPI answers (Tier 1) with optional Claude-powered synthesis (Tier 2).

## Quick Start

### 1. Install

```bash
git clone <repo-url>
cd nyc_data
./scripts/setup.sh
```

### 2. Ask a Question

```bash
socrata-nlquery "How many violations were fixed by borough?"
```

### 3. With Analysis

```bash
socrata-nlquery "Why are violations spiking?" --expand
```

## Features

- **Tier 1 (Instant):** Pre-built answers via hybrid ensemble router (BM25 + Claude embeddings)
- **Tier 2 (Expansion):** Claude synthesis + NLP-suggested follow-up questions
- **Feedback Loop:** Record helpful/wrong markings for continuous improvement
- **Observability:** DuckDB-based tracking of routing decisions and accuracy
- **CLI:** Full-featured command-line interface with JSON output
- **Training:** Built-in accuracy evaluation and weight optimization

## System Architecture

```
Question → [Hybrid Router] → Tier 1 Answer
                          ↓
                    Optional: Claude Expansion → Tier 2 Synthesis
                          ↓
                      Feedback Collection
                          ↓
                    Weight Optimization
```

## Available Commands

```bash
# Basic query (Tier 1 only)
socrata-nlquery "violations fixed by borough"

# With Claude expansion (Tier 2)
socrata-nlquery "Why violations spiking?" --expand

# Mark feedback
socrata-nlquery "violations" --helpful
socrata-nlquery "violations" --wrong --corrected-kpi KPI-045

# JSON output (for scripting)
socrata-nlquery "question" --json

# Evaluation & training
socrata-nlquery evaluate --registry config/kpi_registry_full.json
socrata-nlquery train --feedback-source data/local_db/router_observability.duckdb

# Run demo
socrata-nlquery demo
```

## Configuration

See `DEPLOYMENT_GUIDE.md` for:
- Environment variables
- Configuration files
- Performance tuning
- Troubleshooting

## Testing

```bash
pytest tests/ -q
```

## Development

```bash
make test      # Run all tests
make lint      # Check code style
make demo      # Run end-to-end demo
make evaluate  # Evaluate router accuracy
make train     # Optimize router weights
```

## Documentation

- `DEPLOYMENT_GUIDE.md` — Production deployment
- `docs/superpowers/specs/` — System design specifications
- `docs/superpowers/plans/` — Implementation plans

## Support

For issues or questions, contact the development team.
