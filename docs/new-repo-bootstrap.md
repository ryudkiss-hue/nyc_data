# New Repository Bootstrap Guide

If you want this project in a brand-new repository:

## 1. Create the remote repo
Using GitHub CLI:
```bash
gh repo create <org-or-user>/socrata-toolkit --private --source . --remote origin --push
```

Or manually create a repo in GitHub UI and then:
```bash
git remote add origin <new-repo-url>
git push -u origin <branch>
```

## 2. Protect default branch
- Require PR review
- Require status checks (`ci` workflow)
- Disallow force-push to default branch

## 3. Configure repository secrets
- `SOCRATA_APP_TOKEN`
- `PG_DSN` (if integration tests use managed Postgres)
- `MONGO_URI`

## 4. Enable Actions
Ensure GitHub Actions are enabled so `.github/workflows/ci.yml` executes.

## 5. Publish docs
- Keep `/docs` as the source of truth.
- Optionally publish with GitHub Pages.

## 6. First-run validation
```bash
./scripts/bootstrap.sh
source .venv/bin/activate
socrata doctor --check-db
pytest -q
```
