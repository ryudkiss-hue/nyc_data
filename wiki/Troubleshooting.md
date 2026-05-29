# 🛠️ Troubleshooting

Common errors and how to fix them.

---

## 🔴 Installation & Startup Errors

### `ModuleNotFoundError: No module named 'app'`

**Full error:**
```
ModuleNotFoundError: No module named 'app.analytics'; 'app' is not a package
```

**Cause:** Python's `sys.path` doesn't include the repo root, so `from app.analytics import ...` fails.

**Fix:**
```bash
# Always launch with PYTHONPATH=. 
PYTHONPATH=. streamlit run app/app.py

# Or set it in your shell
export PYTHONPATH=.
streamlit run app/app.py
```

For Render.com: Make sure `PYTHONPATH=.` is in your environment variables (it's already in `render.yaml`).

---

### `ModuleNotFoundError: No module named 'streamlit'`

**Cause:** The `streamlit` package isn't installed.

**Fix:**
```bash
pip install -e ".[mission]"
# or explicitly:
pip install streamlit
```

---

### `ModuleNotFoundError: No module named 'sodapy'`

**Fix:**
```bash
pip install -e ".[mission]"
# or:
pip install sodapy
```

---

### `ImportError: cannot import name 'Callable' from 'typing'`

**Cause:** Python 3.9 compatibility issue with `from typing import Callable`.

**Fix:** Update the import in the affected file:
```python
# Change:
from typing import Callable
# To:
from collections.abc import Callable
```

Or upgrade to Python 3.10+.

---

### Streamlit won't start — port already in use

```
OSError: [Errno 98] Address already in use
```

**Fix:**
```bash
# Find and kill the process on port 8501
lsof -ti:8501 | xargs kill -9

# Or use a different port
streamlit run app/app.py --server.port=8502
```

---

## 🟡 Data Loading Errors

### "Ingestion failed" / No data loads

**Symptoms:** The dashboard shows an error banner instead of data.

**Possible causes and fixes:**

| Cause | Fix |
|-------|-----|
| No Socrata token | Set `SOCRATA_APP_TOKEN` in `.env` or use demo mode |
| Rate limited (429 error) | Add a token or wait a few minutes |
| Network issue | Check internet connectivity |
| Socrata API down | Check [status.socrata.com](http://status.socrata.com) |

**Enable demo mode (no internet required):**
```bash
MISSION_DEMO=1 PYTHONPATH=. streamlit run app/app.py
```

---

### "No module found for dataset key: ..."

**Cause:** The `config/datasets.yaml` file is missing a dataset entry, or the key doesn't match.

**Fix:** Check `config/datasets.yaml` and ensure all keys match what's referenced in `app/data_loader.py`.

---

### Parquet cache errors

**Symptoms:** `ArrowInvalid`, `pyarrow.lib.ArrowIOError`, or corrupted data.

**Fix:**
```bash
# Clear the parquet cache
rm -rf data/local_db/socrata_cache/*.parquet

# Or use the Settings → Cache tab in the dashboard
```

---

## 🔵 GitHub Pages Issues

### Pages shows README instead of the app

**Cause:** GitHub Pages source is set to "Deploy from branch (main / root)" instead of "GitHub Actions".

**Fix:**
1. Go to repo → **Settings → Pages**
2. Set **Source** to **GitHub Actions**
3. Re-trigger the workflow: push any commit to `main`

---

### Pages workflow fails with "pages not enabled"

**Fix:** Enable GitHub Pages in the repo settings (see above), then re-run the workflow.

---

### App deployed but shows blank page

**Cause:** Usually a JavaScript error.

**Fix:**
1. Open browser developer tools (F12)
2. Check the Console tab for errors
3. Try a hard refresh: `Ctrl+Shift+R`

---

## 🟠 Render.com Deployment Issues

### Build fails with dependency errors

**Typical error:**
```
error: subprocess-exited-with-error
× pip subprocess to install build dependencies did not run successfully
```

**Fix:** Ensure the `buildCommand` in `render.yaml` is:
```
pip install -e ".[mission,postgres,xlsx]"
```

---

### App starts but crashes immediately

**Check the Render logs** (Logs tab in service dashboard):

| Log message | Fix |
|-------------|-----|
| `ModuleNotFoundError` | Add `PYTHONPATH=.` to environment variables |
| `port already in use` | Render assigns a port via `$PORT` — ensure your start command uses `--server.port=$PORT` |
| `Broken pipe` | Normal for health check — not an error |

---

### Health check fails (app never goes "live")

**Cause:** The app takes too long to start, or the health check path doesn't respond.

**Fix:** In `render.yaml`, ensure:
```yaml
healthCheckPath: /
```

The Streamlit app responds on `/` after startup.

---

## 🔍 Browser App Issues

### Search returns no results

**Possible causes:**
- Network error reaching Socrata API
- Rate limiting (too many searches in quick succession)
- Browser blocking the API request (CORS / security policy)

**Fix:**
1. Open browser developer tools → Network tab
2. Look for failed requests to `api.us.socrata.com`
3. If you see CORS errors — these should not happen as Socrata allows cross-origin requests. Try refreshing.
4. If rate limited: add your Socrata token in **Settings**

---

### Map doesn't load

**Cause:** Leaflet.js CDN not loading (network issue), or dataset has no coordinate data.

**Fix:**
1. Check your internet connection
2. Verify the dataset has a `location`, `the_geom`, `latitude`/`longitude` column
3. Try refreshing the page

---

### localStorage errors / settings not saving

**Cause:** Browser is in private/incognito mode (localStorage disabled), or storage quota exceeded.

**Fix:**
- Use a regular (non-incognito) browser window
- Or clear site data: DevTools → Application → Storage → Clear site data

---

## 🔎 Linting / CI Errors

### Ruff reports errors

```bash
# Auto-fix what's fixable
ruff check app/ src/ --fix

# Check remaining issues
ruff check app/ src/
```

**Common issues:**

| Error code | Meaning | Fix |
|------------|---------|-----|
| `F401` | Unused import | Remove the import |
| `E402` | Import not at top | Add `# noqa: E402` comment |
| `UP035` | Deprecated typing import | Use `collections.abc` instead |
| `I001` | Imports not sorted | Run `ruff check --fix` |
| `B007` | Loop variable unused | Rename to `_variable` |
| `F841` | Local variable unused | Remove the assignment |

---

### pytest failures

```bash
# Run with verbose output
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_analytics.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=term-missing
```

---

## 📋 Checking System Health

The Settings → Health tab in the Streamlit dashboard runs automated checks. You can also run readiness checks from the CLI:

```bash
socrata readiness
```

A readiness score ≥ 80 means the system is production-ready.

---

## 🆘 Getting More Help

1. **In-app Help:** Press `?` or click **❓ Help** in the browser app
2. **GitHub Issues:** [github.com/ryudkiss-hue/nyc_data/issues](https://github.com/ryudkiss-hue/nyc_data/issues)
3. **Docs:** [docs/TROUBLESHOOTING.md](../docs/TROUBLESHOOTING.md) — extended troubleshooting
4. **Logs:** Check `outputs/logs/ingest.jsonl` for ingestion event history

---

*[[Home]] · [[Getting-Started]] · [[Deployment-Guide]] · [[API-Keys-Setup]]*
