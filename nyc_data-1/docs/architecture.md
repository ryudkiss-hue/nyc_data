# Architecture

## Layers
1. **Ingestion**: `client.py`
2. **Transformation/Analysis**: `analysis.py`, `text_analytics.py`, `nlp_advanced.py`, `spatial.py`, `dot_sidewalk.py`, `llm_duck_bridge.py`
3. **Persistence**: `exporters.py` + CLI pipeline
4. **UX**: `cli.py` and `app.py`
5. **Ops**: `validation.py`, `state.py`, `logging_utils.py`, CI
