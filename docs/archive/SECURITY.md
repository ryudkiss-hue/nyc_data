# Security Guidelines

## Protecting Sensitive Information

### Never Commit Credentials
**DO NOT** commit the following to version control:
- API keys (Gemini, OpenAI, etc.)
- Tokens (Socrata, GitHub, etc.)
- Database passwords
- Private encryption keys
- AWS/GCP credentials

### Environment Variables Setup

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Update with your actual values:**
   Edit `.env` with your real API keys and tokens

3. **Verify `.env` is ignored:**
   ```bash
   git check-ignore .env  # Should output: .env
   ```

### For GitHub Actions / CI/CD

Store secrets in **GitHub Secrets** instead:
1. Go to: **Settings → Secrets and variables → Actions**
2. Add your secrets there
3. Reference in workflows as: `${{ secrets.YOUR_SECRET_NAME }}`

Example:
```yaml
env:
  GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
  SOCRATA_APP_TOKEN: ${{ secrets.SOCRATA_APP_TOKEN }}
```

### If You Accidentally Commit Secrets

**IMMEDIATELY:**
1. Revoke/regenerate the exposed credentials
2. Clean Git history using `git-filter-repo` or `BFG Repo-Cleaner`
3. Force push: `git push --force-with-lease`

```bash
# Example using BFG (recommended for beginners)
bfg --delete-files .env
git reflog expire --expire=now --all && git gc --prune=now
git push --force-with-lease
```

---

**Last updated:** 2026-06-02
