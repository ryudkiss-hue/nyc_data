# Plan 001: Committed .env credentials rotated, scrubbed from git history, and CI secret-scanning added

> **Executor instructions**: Follow this plan step by step. Run every
> verification command and confirm the expected result before moving to the
> next step. If anything in the "STOP conditions" section occurs, stop and
> report — do not improvise. When done, update the status row for this plan
> in `plans/README.md`.
>
> **Drift check (run first)**: `git diff --stat 4343044..HEAD -- .env .gitignore .env.example .github/workflows/`
> If any in-scope file changed since this plan was written, compare the
> "Current state" excerpts against the live code before proceeding; on a
> mismatch, treat it as a STOP condition.

## Status

- **Priority**: P1
- **Effort**: S
- **Risk**: LOW
- **Depends on**: none
- **Category**: security
- **Planned at**: commit `4343044`, 2026-06-12

## Why this matters

The file `.env` was committed to the repository in commit `deea3ea` and contains
live API credentials (Socrata app token at line 3, Gemini API key at line 9).
Although `.env` appears in `.gitignore`, the gitignore rule was added after the
commit, so the file is currently tracked. Any person who clones or has cloned this
repo — including CI runners — can read those credentials. Committed secrets must be
treated as burned regardless of whether they are later removed: they live in git
history. This plan rotates the credentials, scrubs the file from git history, and
adds a CI gate to prevent future commits of secret values.

## Current state

- `.env` is tracked by git (`git ls-files .env` returns `.env`).
- The file was committed in `deea3ea` ("docs(phase2): Phase 2 implementation kickoff and planning").
- `.gitignore` line 6 has `.env`, but the commit predates this rule.
- `.env.example` at repo root is a safe template with placeholder values — it must stay.
- The credential types that need rotation are:
  - **Socrata app token** at `.env:3` (key name: `SOCRATA_APP_TOKEN`)
  - **Gemini API key** at `.env:9` (key name: `GEMINI_API_KEY`)
- Do NOT reproduce or log the actual values anywhere.

## Commands you will need

| Purpose | Command | Expected on success |
|---------|---------|---------------------|
| Confirm .env is tracked | `git ls-files .env` | outputs `.env` |
| Verify .gitignore | `grep "^\.env$" .gitignore` | outputs `.env` |
| Remove from tracking | `git rm --cached .env` | staged deletion |
| Verify untracked | `git ls-files .env` | empty output |
| Install git-filter-repo | `pip install git-filter-repo` | exit 0 |
| Scrub from history | `git filter-repo --path .env --invert-paths --force` | exit 0 |
| Lint | `ruff check src/ tests/ app/` | `All checks passed!` |
| Tests (smoke) | `pytest tests/test_config.py tests/test_client.py -q` | all pass |

## Scope

**In scope** (the only files you should modify):

- `.env` — replace all real values with placeholders (matching `.env.example` format)
- `.gitignore` — verify `.env` rule is present (no change needed if already there)
- `.env.example` — add any missing env vars found during step 3
- `.github/workflows/ci.yml` — add `git-secrets` or `truffleHog` scanning step

**Out of scope** (do NOT touch):

- Any source `.py` files — credential rotation does not require code changes
- `pyproject.toml`, `requirements*.txt`
- Any other workflow files besides `ci.yml`

## Git workflow

- Branch from the current branch: `git checkout -b fix/001-scrub-env-credentials`
- Commit style matches repo: `fix: <description>` (conventional commits — see `git log --oneline -5`)
- Do NOT push or open a PR until Step 5 is complete and verified

## Steps

### Step 1: Rotate both credentials before any git operations

**Before touching any files**, rotate the burned credentials externally:

1. **Socrata app token** (`SOCRATA_APP_TOKEN`): Log in at
   `https://data.cityofnewyork.us/profile/edit/developer_settings`, revoke the
   current token, and generate a new one.
2. **Gemini API key** (`GEMINI_API_KEY`): Go to Google Cloud Console →
   APIs & Services → Credentials, delete the current key, create a new one.

Store the new values in your local `.env` file (not committed) or in a password
manager. Do NOT write the new values into any file that will be committed.

**Verify**: Confirm you have new values for both keys ready before proceeding.

### Step 2: Replace .env contents with placeholders

Open `.env` and replace every real value with a placeholder matching the format
in `.env.example`. The result must look like:

```
SOCRATA_APP_TOKEN=your-socrata-app-token-here
SOCRATA_DOMAIN=data.cityofnewyork.us
ANTHROPIC_API_KEY=your-anthropic-api-key-here
GEMINI_API_KEY=your-gemini-api-key-here
OLLAMA_HOST=http://localhost:11434
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PG_DSN=postgresql://user:password@host:5432/database
DUCKDB_PATH=data/local_db/nyc_mission_control.duckdb
SOCRATA_CACHE_DIR=data/cache
PYTHONPATH=src:.
PYTHON_VERSION=3.11.9
```

**Verify**: `grep -c "your-\|\.\.\.here\|localhost" .env` → should return ≥ 5
(confirms placeholders, not real values).

### Step 3: Untrack .env and add missing vars to .env.example

```bash
git rm --cached .env
```

Check `.env.example` against the full list of env vars in `CLAUDE.md` (lines
313–335 of `CLAUDE.md`) and add any missing ones as commented-out optional
entries. Minimally add:

```
# Optional: MotherDuck cloud DuckDB
MOTHERDUCK_TOKEN=your-motherduck-token-here
```

**Verify**: `git ls-files .env` → empty output (file is no longer tracked).

### Step 4: Scrub .env from git history

Install `git-filter-repo` if not already present:

```bash
pip install git-filter-repo
```

Scrub the file from all commits:

```bash
git filter-repo --path .env --invert-paths --force
```

This rewrites history. The remote will need a force-push (coordinate with any
teammates before doing so).

**Verify**:
```bash
git log --all --full-history -- .env
```
→ should return no output (no commits reference `.env` anymore).

**Verify**:
```bash
git ls-files .env
```
→ empty output.

### Step 5: Add secret-scanning CI gate

In `.github/workflows/ci.yml`, add a new job **before** the `test` job:

```yaml
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - name: Scan for committed secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          head: HEAD
          extra_args: --only-verified
```

**Verify**: YAML is valid — `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → no error.

### Step 6: Commit and push

```bash
git add .gitignore .env.example .github/workflows/ci.yml
git commit -m "fix: scrub committed .env credentials and add secret-scanning CI gate"
git push --force-with-lease origin fix/001-scrub-env-credentials
```

Note: `--force-with-lease` is required because history was rewritten in Step 4.

## Test plan

No new pytest tests are required — this is a credential hygiene and git history
fix. The CI secret-scan job added in Step 5 is itself the regression test.

After merge, verify the CI pipeline runs the `secret-scan` job on the next PR
and exits 0.

## Done criteria

All must hold:

- [ ] `git ls-files .env` → empty output
- [ ] `git log --all --full-history -- .env` → no output
- [ ] `grep -c "your-\|\.\.\.here" .env` ≥ 5 (placeholders only)
- [ ] `.github/workflows/ci.yml` contains `trufflehog` or equivalent secret-scan step
- [ ] Both rotated credentials (Socrata token, Gemini key) tested and working in local `.env`
- [ ] `ruff check src/ tests/ app/` → `All checks passed!`
- [ ] `plans/README.md` status row updated to DONE

## STOP conditions

Stop and report back (do not improvise) if:

- `git filter-repo` fails — do not attempt manual rebase; report the error.
- The `.env` file contains credential types beyond `SOCRATA_APP_TOKEN` and
  `GEMINI_API_KEY` (there may be additional burned tokens the plan doesn't name).
- A teammate has unpushed commits based on the current history — force-push
  would lose their work; coordinate first.
- The `truffleHog` scan step triggers on any existing file in the repo — investigate
  before merging.

## Maintenance notes

- Every new env var added to the codebase must also appear in `.env.example` with
  a placeholder value and a comment explaining its purpose.
- The `truffleHog` scan runs `--only-verified` to reduce false positives; if it
  starts flagging legitimate config values, adjust the `--exclude-paths` arg rather
  than disabling the step.
- `MOTHERDUCK_TOKEN` is not yet in `.env.example` — Plan 002 (motherduck-token-security)
  adds it and fixes the code-level exposure.
