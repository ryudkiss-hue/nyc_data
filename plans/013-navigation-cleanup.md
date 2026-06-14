# Plan 013 — Navigation Cleanup and Platform Guard

**Slug:** navigation-cleanup
**Commit:** 1e84782
**Priority:** P2
**Effort:** S
**Risk:** LOW — label text changes and a platform guard; routing logic unchanged
**Category:** UX / DX
**Status:** TODO

---

## Problem

Three separate issues degrade navigation UX and cross-platform correctness:

### A — Jargon-heavy sidebar labels (`app/dash_layouts.py:188–200`)

Current sidebar navigation uses internal engineering jargon that means nothing to an NYC DOT analyst:

| Current label | What it actually is |
|---|---|
| "Telemetrics Dashboard" | Main dashboard / KPI overview |
| "Empirical Statistics" | Statistical analysis |
| "Geospatial Intel" | GIS / map analysis |
| "Structural Mandate" | Engineering / compliance reports |
| "NLP Analytics" | Natural-language query interface |
| "Center of Excellence" | Documentation / tutorials |
| "Engine Configuration" | App settings |
| "Analyst AI" | AI assistant / copilot |
| "MISSION COMMAND" | Navigation header |

The "JID SCRAPER" and "SODA INGEST" worker-queue panel and "Forensic Audit" terminal are internal debug artifacts surfaced to analysts.

### B — Windows PATH hardcoded unconditionally (`app/dash_app.py:21–23`)

```python
MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
os.environ["PYTENSOR_FLAGS"] = f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"
```

On Linux/macOS (the production environment), this prepends a non-existent Windows path to `PATH` and sets `PYTENSOR_FLAGS` to a `.exe` path. It's harmless on Linux but introduces noise in logs and environment introspection. It should only run on Windows.

### C — Dead heartbeat callback in `navigation.py` (`app/callbacks/navigation.py:59–67`)

```python
@app.callback(
    Output("audit-log-terminal", "children", allow_duplicate=True),
    Input("url", "pathname"),
    State("audit-log-terminal", "children"),
    prevent_initial_call="initial_duplicate"
)
def heartbeat_callback(path, current_log):
    # Industrial heartbeat for session tracking
    return no_update
```

This callback always returns `no_update`, fires on every navigation, and uses `allow_duplicate=True` which suppresses an error that would have caught the duplicate output. It can be safely removed.

---

## Implementation

### Step 1 — Rename sidebar nav labels (`app/dash_layouts.py`)

Change `render_sidebar()` (starting at `app/dash_layouts.py:174`). Replace the `dmc.NavLink` labels and the `dmc.Text("MISSION COMMAND")` header:

**Before:**
```python
                            dmc.Group([
                                DashIconify(icon="mdi:city-variant-outline", width=30, color="black"),
                                dmc.Text("MISSION COMMAND", size="lg", fw=800, c="black"),
                            ]),
                            dmc.Divider(),
                            dmc.NavLink(id="nav-dash", label="Telemetrics Dashboard", leftSection=DashIconify(icon="mdi:view-dashboard"), href="/"),
                            dmc.NavLink(id="nav-const", label="Construction Planner", leftSection=DashIconify(icon="mdi:crane"), href="/const"),
                            dmc.NavLink(id="nav-labor", label="Labor & Lifecycle", leftSection=DashIconify(icon="mdi:account-hard-hat"), href="/labor"),
                            dmc.NavLink(id="nav-reports", label="Reporting Engine", leftSection=DashIconify(icon="mdi:file-chart"), href="/reports"),
                            dmc.NavLink(id="nav-stats", label="Empirical Statistics", leftSection=DashIconify(icon="mdi:math-log"), href="/stats"),
                            dmc.NavLink(id="nav-geo", label="Geospatial Intel", leftSection=DashIconify(icon="mdi:map-marker-radius"), href="/geo"),
                            dmc.NavLink(id="nav-eng", label="Structural Mandate", leftSection=DashIconify(icon="mdi:hard-hat"), href="/eng"),
                            dmc.NavLink(id="nav-sql", label="SQL Studio", leftSection=DashIconify(icon="mdi:database-search"), href="/sql"),
                            dmc.NavLink(id="nav-nlp", label="NLP Analytics", leftSection=DashIconify(icon="mdi:robot-confused"), href="/nlp"),
                            dmc.NavLink(id="nav-tutorials", label="Center of Excellence", leftSection=DashIconify(icon="mdi:book-open-page-variant"), href="/tutorials"),
                            dmc.NavLink(id="nav-settings", label="Engine Configuration", leftSection=DashIconify(icon="mdi:cog"), href="/settings"),
                            dmc.NavLink(id="nav-toolbox", label="Analytical Toolbox", leftSection=DashIconify(icon="mdi:toolbox-outline"), href="/toolbox"),
                            dmc.NavLink(id="nav-copilot", label="Analyst AI", leftSection=DashIconify(icon="mdi:robot-happy"), href="/copilot"),
```

**After:**
```python
                            dmc.Group([
                                DashIconify(icon="mdi:city-variant-outline", width=30, color="black"),
                                dmc.Text("NYC DOT Analytics", size="lg", fw=800, c="black"),
                            ]),
                            dmc.Divider(),
                            dmc.NavLink(id="nav-dash", label="Dashboard", leftSection=DashIconify(icon="mdi:view-dashboard"), href="/"),
                            dmc.NavLink(id="nav-const", label="Construction Planner", leftSection=DashIconify(icon="mdi:crane"), href="/const"),
                            dmc.NavLink(id="nav-labor", label="Labor & Lifecycle", leftSection=DashIconify(icon="mdi:account-hard-hat"), href="/labor"),
                            dmc.NavLink(id="nav-reports", label="Reports", leftSection=DashIconify(icon="mdi:file-chart"), href="/reports"),
                            dmc.NavLink(id="nav-stats", label="Statistics", leftSection=DashIconify(icon="mdi:math-log"), href="/stats"),
                            dmc.NavLink(id="nav-geo", label="GIS & Maps", leftSection=DashIconify(icon="mdi:map-marker-radius"), href="/geo"),
                            dmc.NavLink(id="nav-eng", label="Engineering", leftSection=DashIconify(icon="mdi:hard-hat"), href="/eng"),
                            dmc.NavLink(id="nav-sql", label="SQL Studio", leftSection=DashIconify(icon="mdi:database-search"), href="/sql"),
                            dmc.NavLink(id="nav-nlp", label="Natural Language Query", leftSection=DashIconify(icon="mdi:robot-happy"), href="/nlp"),
                            dmc.NavLink(id="nav-tutorials", label="Tutorials", leftSection=DashIconify(icon="mdi:book-open-page-variant"), href="/tutorials"),
                            dmc.NavLink(id="nav-settings", label="Settings", leftSection=DashIconify(icon="mdi:cog"), href="/settings"),
                            dmc.NavLink(id="nav-toolbox", label="Toolbox", leftSection=DashIconify(icon="mdi:toolbox-outline"), href="/toolbox"),
                            dmc.NavLink(id="nav-copilot", label="AI Assistant", leftSection=DashIconify(icon="mdi:robot-happy"), href="/copilot"),
```

All `id=` values are **unchanged** — they are used in navigation callbacks in `navigation.py:51–57`. Change only the `label=` strings and the `dmc.Text` content.

### Step 2 — Wrap Windows PATH mutation in a platform guard (`app/dash_app.py`)

**Before (`app/dash_app.py:20–23`):**
```python
# Item 42: Bulletproof environment configuration for High-Performance Bayesian Engine
MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
os.environ["PYTENSOR_FLAGS"] = f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"
```

**After:**
```python
if sys.platform.startswith("win"):
    MINGW_BIN = os.getenv("MINGW_BIN_PATH", r"C:\msys64\mingw64\bin")
    os.environ["PATH"] = f"{MINGW_BIN};" + os.environ.get("PATH", "")
    os.environ["PYTENSOR_FLAGS"] = f"cxx={os.path.join(MINGW_BIN, 'g++.exe')},gcc_version_str=14.1.0"
```

`sys` is already imported at `dash_app.py:3`.

### Step 3 — Remove dead heartbeat callback (`app/callbacks/navigation.py`)

Delete the heartbeat callback block at `navigation.py:59–67`:

```python
    @app.callback(
        Output("audit-log-terminal", "children", allow_duplicate=True),
        Input("url", "pathname"),
        State("audit-log-terminal", "children"),
        prevent_initial_call="initial_duplicate"
    )
    def heartbeat_callback(path, current_log):
        # Industrial heartbeat for session tracking
        return no_update
```

The `audit-log-terminal` element remains in the sidebar (it's part of the Forensic Audit debug section) and doesn't need a callback.

---

## Files in scope

- `app/dash_layouts.py` — rename sidebar nav labels + header text
- `app/dash_app.py` — add `sys.platform` guard around MINGW_BIN block
- `app/callbacks/navigation.py` — remove heartbeat callback

## Files explicitly out of scope

- `app/callbacks/navigation.py` nav-active and toggle-theme callbacks — leave unchanged
- No ID values may change (callbacks depend on them)

---

## Verification

```bash
# Confirm IDs unchanged
grep -o 'id="nav-[^"]*"' app/dash_layouts.py | sort
# Expected: same 13 nav IDs as before

# Confirm new labels present
grep -n '"Dashboard"\|"Statistics"\|"GIS & Maps"\|"AI Assistant"' app/dash_layouts.py
# Expected: lines present

# Confirm platform guard
grep -n "sys.platform" app/dash_app.py
# Expected: 1 match

# Confirm heartbeat removed
grep -n "heartbeat_callback" app/callbacks/navigation.py
# Expected: no matches

# Syntax checks
python -c "import ast; ast.parse(open('app/dash_layouts.py').read()); print('OK')"
python -c "import ast; ast.parse(open('app/dash_app.py').read()); print('OK')"
python -c "import ast; ast.parse(open('app/callbacks/navigation.py').read()); print('OK')"

# Run tests
python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```

---

## Done criteria

- [ ] `grep -c "MISSION COMMAND" app/dash_layouts.py` returns 0
- [ ] `grep -c "Telemetrics Dashboard" app/dash_layouts.py` returns 0
- [ ] `grep -c "Empirical Statistics" app/dash_layouts.py` returns 0
- [ ] `grep -c "sys.platform" app/dash_app.py` returns 1
- [ ] `grep -c "heartbeat_callback" app/callbacks/navigation.py` returns 0
- [ ] `python -m pytest tests/ -q --tb=short` passes at same pre-existing failure count
