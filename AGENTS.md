# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is the **NYC DOT Sidewalk Toolkit** (`socrata_toolkit` v0.3.0) — a Python toolkit for sidewalk inspection and management. The primary interface is a Streamlit dashboard called "Manhattan Mission Control" served on port 8501.

### Running the Application

- **Streamlit (Mission Control):** `MISSION_DEMO=1 python3 -m streamlit run app/app.py --server.port 8501 --server.headless true`
  - `MISSION_DEMO=1` enables synthetic/demo data without needing a Socrata API token.
  - Requires `PYTHONPATH` to include both `/workspace/src` and `/workspace` (the editable install handles this).
- **CLI:** `python3 -m socrata_toolkit.core.cli doctor` (or use the `socrata` entry point if `~/.local/bin` is on PATH).

### Key Development Commands

| Task | Command |
|------|---------|
| Install all deps | `pip install -e ".[all]" -r requirements-dev.txt` |
| Lint | `python3 -m ruff check src/socrata_toolkit/ tests/` |
| Tests | `python3 -m pytest tests/ -v --ignore=tests/test_interactive_explore.py` |
| Run app (demo) | `MISSION_DEMO=1 python3 -m streamlit run app/app.py --server.headless true` |
| Health check | `python3 -c "from socrata_toolkit.core.cli import main; import sys; sys.argv=['socrata','doctor']; main()"` |

### Non-obvious Caveats

1. **PATH:** Installed scripts (pytest, ruff, streamlit, socrata) land in `~/.local/bin` which may not be on PATH by default. Either prefix commands with `python3 -m` or `export PATH="$HOME/.local/bin:$PATH"`.

2. **Test exclusions:** `tests/test_interactive_explore.py` requires the `dash` package (legacy UI, not installed by default). Skip it with `--ignore`. Some tests also require `networkx` and `flask` which are not in the default extras.

3. **Demo mode:** Set `MISSION_DEMO=1` to run Mission Control without a Socrata API token. This uses synthetic data.

4. **psycopg:** The pure-Python psycopg driver needs either `libpq` system library or the `psycopg-binary` pip package. Install `psycopg-binary` in cloud environments to avoid needing the system library.

5. **FastAPI:** The `requirements.txt` lists `fastapi` but the `pyproject.toml` extras don't include it. Install it separately (`pip install fastapi`) to avoid import errors in `tests/test_api_security.py`.
