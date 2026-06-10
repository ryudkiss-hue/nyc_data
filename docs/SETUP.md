# 🛠️ Setup & Environment Guide

## 1. Prerequisites
- **Python**: 3.9 – 3.12
- **Git**: For source control
- **Docker Desktop**: Recommended for full-stack services (Postgres, Redis, Grafana)
- **Socrata App Token**: Required for live NYC Open Data access. [Register here](https://data.cityofnewyork.us/profile/app_tokens).

---

## 2. Quick Start (Analyst Install)

### Step 1: Clone and Install
```bash
git clone https://github.com/ryudkiss-hue/nyc_data.git
cd nyc_data
pip install -e ".[all]"
```

### Step 2: Configuration Wizard
Run the interactive wizard to generate your `.env` and analyst profiles:
```bash
socrata wizard
```
**Required Variables**:
- `SOCRATA_APP_TOKEN`
- `PG_DSN` (Optional, if using external Postgres)

### Step 3: Health Check
Verify your local environment is correctly configured:
```bash
python launcher.py doctor
```

---

## 3. Docker Deployment

The toolkit uses Docker Compose profiles to manage services.

### Analyst-Only Stack
Starts Postgres and the analyst runner:
```bash
docker compose --profile analyst up -d
```

### Full Platform Stack
Starts the complete observability and API suite (Postgres, Redis, Prometheus, Grafana, Jaeger, API):
```bash
docker compose up -d
```

### Service URLs
| Service | URL |
|---------|-----|
| **Mission Control (Streamlit)** | http://localhost:8501 |
| **FastAPI Docs** | http://localhost:8000/docs |
| **Grafana Dashboards** | http://localhost:3000 |

---

## 4. Development Workflow

### Coding Standards
- **Formatting**: Uses `black` and `isort`.
- **Linting**: Uses `ruff`.
- **Typing**: Mandatory type hints on all public function signatures.

### Testing & CI
Run the test suite locally before pushing:
```bash
pytest tests/
```
The CI pipeline (GitHub Actions) enforces a **45% coverage gate** for `core/` and `analyst/` pillars and runs automated linting and security scans.

---

## 5. Troubleshooting
- **Port Conflicts**: Ensure ports 8000, 8501, and 3000 are available.
- **Database Connection**: Use `socrata doctor --check-db` to verify DuckDB/Postgres writability.
- **Out of Memory**: Increase Docker memory allocation to 6-8GB for heavy workloads.
