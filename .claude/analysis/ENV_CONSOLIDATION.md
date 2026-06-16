# Environment Variable Consolidation

**Date:** 2026-06-16  
**Status:** Complete

---

## What Changed

All environment configuration has been consolidated into a single authoritative `.env` file in the project root.

### Before (Fragmented)
```
./.env                    ← Main config
./config/.env            ← GitHub Actions template
./config/.env.example    ← Example config
./.env.example           ← Example config (duplicate)
./.env.socrata           ← PostgreSQL config
```

### After (Consolidated)
```
./.env                    ← SINGLE SOURCE OF TRUTH (all vars)
./.env.example            ← Template for new users (no credentials)
./config/.env            ← DEPRECATED (note added, no longer used)
./config/.env.example    ← DEPRECATED (consolidated to root)
./.env.socrata           ← DEPRECATED (PG_DSN moved to .env)
```

---

## Variables Now Consolidated

### Socrata / NYC Data
- `SOCRATA_APP_TOKEN` ← [from .env]
- `SOCRATA_DOMAIN` ← [from .env.example]
- `SOCRATA_CACHE_DIR` ← [from config/.env.example]

### API Keys
- `ANTHROPIC_API_KEY` ← [from .env, .env.example]
- `MOTHERDUCK_TOKEN` ← [new, for cloud analytics]
- `GEMINI_API_KEY` ← [from .env]

### Google Cloud
- `GCP_PROJECT` ← [new]
- `GCS_BUCKET` ← [new]

### Database
- `DUCKDB_PATH` ← [from config/.env.example]
- `PG_DSN` ← [from .env.socrata, config/.env.example]

### Python
- `PYTHONPATH` ← [from .env, config/.env.example]
- `PYTHON_VERSION` ← [from .env, config/.env.example]

### Optional Services
- `SLACK_WEBHOOK_URL` ← [from .env, .env.example]
- `OLLAMA_HOST` ← [from .env, config/.env]

### Paths & Storage
- `DATA_DIR` ← [from config/.env.example]
- `OUTPUT_DIR` ← [from config/.env.example]

### Analyst Features
- `ANALYST_PROFILE` ← [from config/.env.example]
- `ANALYST_CRON` ← [from config/.env.example]

### Docker Compose
- `POSTGRES_USER` ← [from config/.env.example]
- `POSTGRES_PASSWORD` ← [from config/.env.example]
- `POSTGRES_DB` ← [from config/.env.example]
- `POSTGRES_HOST` ← [new]
- `POSTGRES_PORT` ← [new]

### Wizard / Setup
- `WIZARD_NONINTERACTIVE` ← [from config/.env.example]
- `WIZARD_ALLOW_EMPTY_TOKEN` ← [from config/.env.example]

---

## How to Update Your Setup

### For Local Development

1. **Copy template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your credentials:**
   ```bash
   # Required
   SOCRATA_APP_TOKEN=your-token-from-https://data.cityofnewyork.us/...
   ANTHROPIC_API_KEY=your-key-from-https://console.anthropic.com/
   
   # Optional (only if using)
   MOTHERDUCK_TOKEN=your-token-from-https://console.motherduck.com/
   GCP_PROJECT=your-gcp-project-id
   GCS_BUCKET=your-gcs-bucket-name
   ```

3. **Verify it works:**
   ```bash
   source .env
   echo $SOCRATA_APP_TOKEN  # Should show your token (hidden in .gitignore)
   ```

### For Docker / CI-CD

**GitHub Actions Secrets:**
Instead of config/.env, use Settings → Secrets and variables → Actions:
- `SOCRATA_APP_TOKEN`
- `ANTHROPIC_API_KEY`
- `MOTHERDUCK_TOKEN` (if using)
- etc.

Then reference in workflow:
```yaml
env:
  SOCRATA_APP_TOKEN: ${{ secrets.SOCRATA_APP_TOKEN }}
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Docker Compose:**
Reference the root `.env`:
```yaml
services:
  app:
    env_file:
      - .env
```

---

## Deprecated Files (Can Be Deleted)

These files have been replaced and can be safely deleted:

- `config/.env` — Now just a deprecation notice
- `.env.socrata` — Now just a deprecation notice

**Do NOT delete:**
- `.env` — Your local credentials (in .gitignore)
- `.env.example` — Template for new users (in git, not in .gitignore)

---

## Why This Consolidation?

**Before:** 5 separate .env files with overlapping, conflicting, or duplicate variables  
**After:** 1 authoritative source + 1 template

**Benefits:**
- ✅ Single source of truth
- ✅ Easier to maintain (update in one place)
- ✅ Clearer documentation (all vars in one place with comments)
- ✅ Better for onboarding (new users copy .env.example)
- ✅ Reduced confusion (no conflicting files)

---

## Migration Checklist

- [x] Consolidated all variables into root `.env`
- [x] Updated `.env.example` template with all variables
- [x] Added deprecation notices to old files
- [x] Documented consolidation in this file
- [ ] Delete `config/.env` (after merging, once everyone migrated)
- [ ] Delete `.env.socrata` (after merging, once everyone migrated)
- [ ] Update `config/.env.example` to point to root .env.example (optional, can delete)

---

## Questions?

If you see references to `config/.env` or `.env.socrata` in CI/CD or docs:
1. Update them to use root `.env`
2. Remove the old file reference
3. Check `.env.example` for required variables

All environment variables are now documented in `.env.example`.
