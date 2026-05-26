# 🔑 API Keys Setup

This guide explains how to get and configure the API tokens used by Manhattan Mission Control.

---

## Socrata App Token

### What it is

The Socrata App Token is a **free** credential that identifies your application to the NYC Open Data API. Without it, requests are rate-limited to ~1 req/second. With a token, limits are much higher (thousands of requests/day).

### When you need it

| Scenario | Token needed? |
|----------|--------------|
| Using the HTML browser app for casual searching | ❌ No (anonymous access is fine) |
| Running the browser app with heavy SOQL queries | ✅ Recommended |
| Running the Streamlit dashboard | ✅ Recommended |
| Deploying to Render/Heroku for team use | ✅ Yes |
| Automated data pipelines (GitHub Actions) | ✅ Yes |

### How to get one

1. **Go to:** [https://data.cityofnewyork.us/](https://data.cityofnewyork.us/)
2. Click **Sign In** (or **Register** if you don't have an account — it's free)
3. After logging in, click your username → **Developer Settings**
4. Click **Create New App Token**
5. Fill in:
   - **Application Name:** Manhattan Mission Control (or anything)
   - **Description:** NYC open data explorer
   - **Website:** `https://ryudkiss-hue.github.io/nyc_data/` (optional)
6. Click **Save** — copy the **App Token** that appears

> ⚠️ **Secret key:** The full token includes an **App Token** (public-ish) and a **Secret Token** (private). For read-only access you only need the App Token. Never commit either to git.

---

## Configuring the Token

### Local development (.env file)

```bash
# 1. Copy the example file
cp .env.example .env

# 2. Edit .env and add your token
SOCRATA_APP_TOKEN=your_app_token_here
```

The `.env` file is gitignored — it will never be accidentally committed.

### Render.com

1. Go to your Render service dashboard
2. Click **Environment** in the left menu
3. Click **Add Environment Variable**
4. Key: `SOCRATA_APP_TOKEN`
5. Value: your token
6. Click **Save** — the service restarts automatically

### Heroku

```bash
heroku config:set SOCRATA_APP_TOKEN=your_token_here
```

Or via the Heroku dashboard: **Settings → Config Vars → Reveal Config Vars → Add**.

### GitHub Actions

1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `SOCRATA_APP_TOKEN`
4. Value: your token
5. Click **Add secret**

Use it in your workflow:
```yaml
env:
  SOCRATA_APP_TOKEN: ${{ secrets.SOCRATA_APP_TOKEN }}
```

### Docker

```bash
# Pass at runtime
docker run -e SOCRATA_APP_TOKEN=your_token nyc-mission-control

# Or in docker-compose.yml
environment:
  - SOCRATA_APP_TOKEN=${SOCRATA_APP_TOKEN}

# And set in your shell:
export SOCRATA_APP_TOKEN=your_token
docker compose up
```

### Browser app (HTML)

In the HTML app, click **⚙️ Settings** in the top menu and enter your token in the **API Token** field. It's saved to `localStorage` (stays in your browser, never sent anywhere except to Socrata).

---

## Other Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOCRATA_APP_TOKEN` | *(empty)* | Socrata API token |
| `MISSION_DEMO` | `0` | Set to `1` to force demo mode (loads sample data, no API calls) |
| `PYTHONPATH` | *(empty)* | Must be `.` when running `python -m streamlit run app/app.py` |
| `STREAMLIT_SERVER_PORT` | `8501` | Port for the Streamlit server |

### Example .env file

```bash
# NYC DOT Mission Control — Environment Configuration
# Copy to .env and fill in values. Never commit .env to git.

# Socrata API token (free at data.cityofnewyork.us)
SOCRATA_APP_TOKEN=

# Force demo mode: 1=demo, 0=live (default 0)
MISSION_DEMO=0

# Python path fix (required for some launch methods)
PYTHONPATH=.
```

---

## Verifying Your Token

### In the browser app

1. Open [https://ryudkiss-hue.github.io/nyc_data/](https://ryudkiss-hue.github.io/nyc_data/)
2. Click **⚙️ Settings**
3. Enter your token
4. Run any search — if results load quickly without rate limit messages, the token is working

### In the Streamlit dashboard

1. Go to **Settings → Health**
2. Check the **API Connectivity** row — it should show ✅ green
3. Or watch the top header: **Live Data** badge = token is active, **Demo Mode** badge = token not found

### Via command line

```bash
curl "https://data.cityofnewyork.us/resource/nc67-uf89.json?$limit=1" \
  -H "X-App-Token: YOUR_TOKEN"
# Should return a JSON array with one row
```

---

## Rate Limits

| Scenario | Limit |
|----------|-------|
| No token (anonymous) | ~1 request/second, ~1,000 rows max |
| With free app token | Higher limits, ~50,000 rows per request |
| With registered account | Contact Socrata for enterprise limits |

When rate-limited, you'll see a `429 Too Many Requests` error. The app handles this gracefully and shows a helpful message.

---

## Security Best Practices

1. **Never commit tokens to git** — use `.env` (gitignored) or secrets manager
2. **Use environment variables** — not hardcoded strings in source code
3. **Rotate tokens if exposed** — go to Developer Settings → revoke and recreate
4. **Read-only is fine** — Socrata tokens for public data are read-only anyway
5. **Separate tokens per environment** — use different tokens for dev vs. production

---

*[[Home]] · [[Getting-Started]] · [[Deployment-Guide]] · [[Troubleshooting]]*
