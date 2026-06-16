# NYC DOT Sidewalk Data Governance Toolkit - Deployment Guide

Complete guide for deploying the **Dash Mission Control** dashboard and Python toolkit in local, development, and production environments.

## Table of Contents

1. [Quick Start](#quick-start) — 5 minutes to running Dash
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Deployment Options](#deployment-options) — Local, Docker, Cloud (AWS/Render)
5. [Configuration](#configuration)
6. [Running the Dashboard](#running-the-dashboard) — Dash (primary) + Streamlit (secondary)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)

---

## Quick Start

**Goal:** Get Dash Mission Control running in 5 minutes.

### Windows (PowerShell)

```powershell
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Install dependencies
pip install -e ".[mission,xlsx]"

# 3. Edit environment (optional)
notepad .env

# 4. Launch Dash Mission Control (PRIMARY)
python app/dash_app.py

# 5. Open browser
Start-Process "http://localhost:8011"
```

### Linux/MacOS (Bash)

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Install dependencies
pip install -e ".[mission,xlsx]"

# 3. Edit environment (optional)
nano .env

# 4. Launch Dash Mission Control (PRIMARY)
python app/dash_app.py

# 5. Open browser
open http://localhost:8011
```

### All Platforms (Docker)

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Build Dash Mission Control image
docker build -t nyc-mission:dash --target mission .

# 3. Run container
docker run -p 8011:8011 \
  -e SOCRATA_APP_TOKEN=your_token_here \
  nyc-mission:dash

# 4. Open browser
http://localhost:8011
```

### Using Docker Compose

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Edit .env for Socrata token (optional)
cp .env.example .env
nano .env  # Set SOCRATA_APP_TOKEN

# 3. Start Mission Control
docker compose up mission-control

# 4. Open browser
http://localhost:8011
```

---

## Running the Dashboard

### Dash Mission Control (PRIMARY — Recommended)

```bash
# Direct launch
python app/dash_app.py
# → http://localhost:8011

# Or via launcher shim
python main.py
# → Automatically selects Dash primary
```

**Features:**
- FastAPI backend (async, production-grade)
- Plotly interactive visualizations (30+ charts)
- Mantine responsive UI components
- Real-time callbacks for filtering and exports
- PDF/Excel/PPTX report generation
- GIS spatial analysis and mapping
- Advanced analytics (Bayesian, CUSUM, KMeans, survival curves)

**Performance:** ~200ms page loads, callback latency <500ms

### Streamlit (SECONDARY — Alternative)

```bash
# Launch Streamlit UI
streamlit run app/app.py
# → http://localhost:8501
```

**Features:**
- Simplified data exploration interface
- 7-tab layout (Home, Workflows, Quality, Spatial, Governance, AI Copilot, Settings)
- Interactive charts and tables
- Natural language query interface (with Claude API)

**Use when:**
- Dash is unavailable or broken
- Simpler UI is preferred
- Rapid prototyping needed

**Performance:** ~1–2s page loads (Streamlit is slower than Dash/FastAPI)

---

## System Requirements

### Hardware

- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB minimum (8GB+ recommended)
- **Disk**: 10GB available space (20GB+ for data)
- **Network**: Internet access for initial setup

### Software

#### Required
- **Git** (2.0+) - Version control
- **Docker** (20.10+) - Container runtime
- **Docker Compose** (1.29+) - Container orchestration
- **Python** (3.9+) - Runtime and CLI

#### Optional
- **Visual Studio Code** - Code editor
- **PowerShell 7+** - Enhanced Windows shell
- **PostgreSQL Client** - Direct database access
- **DBeaver** - Database GUI client

### Operating System Support

| OS | Status | Notes |
|----|--------|-------|
| Windows 10/11 | ✅ Full | Use PowerShell script or Python launcher |
| Ubuntu 20.04+ | ✅ Full | Use Bash script or Python launcher |
| MacOS 11+ | ✅ Full | Use Bash script or Python launcher |
| WSL 2 | ✅ Full | Linux environment on Windows |

### Network Requirements

| Port | Service | Purpose | Required |
|------|---------|---------|----------|
| **8011** | **Dash FastAPI** | PRIMARY Mission Control dashboard | ✅ Yes |
| **8501** | Streamlit | SECONDARY fallback UI option | Optional |
| 5432 | PostgreSQL | Optional database (if using PG_DSN) | Optional |
| 6379 | Redis | Optional caching layer | Optional |
| 8000 | Legacy FastAPI | Deprecated, not used | No |
| 9090 | Prometheus | Optional monitoring | Optional |
| 3000 | Grafana | Optional dashboards | Optional |
| 16686 | Jaeger | Optional tracing | Optional |

---

## Installation Methods

### Method 1: Python Native (Recommended for Development)

**Best for:** Local development, quick testing  
**Time:** 5–10 minutes  
**Requirements:** Python 3.11+, pip, git

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate        # Linux/MacOS
# or
venv\Scripts\activate           # Windows

# 3. Install with mission extra (Dash + all dependencies)
pip install -e ".[mission,xlsx]"

# 4. Configure (optional)
cp .env.example .env
# Edit .env and set SOCRATA_APP_TOKEN for live data (optional)

# 5. Launch Dash Mission Control
python app/dash_app.py
# → http://localhost:8011

# (Optional) Launch Streamlit alternative
# streamlit run app/app.py
# → http://localhost:8501
```

---

### Method 2: Docker (Recommended for Reproducibility)

**Best for:** Consistent environment, CI/CD, production preview  
**Time:** 10–15 minutes (first run), includes Docker build  
**Requirements:** Docker 20.10+, docker-compose 1.29+

#### Option A: Docker Compose (Easiest)

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Configure environment
cp .env.example .env
# Edit .env: set SOCRATA_APP_TOKEN (optional)

# 3. Start Mission Control
docker compose up mission-control

# 4. Open dashboard
http://localhost:8011

# To stop:
docker compose down
```

#### Option B: Docker Build + Run

```bash
# 1. Clone repository
git clone <repo-url>
cd nyc_data

# 2. Build Dash Mission Control image
docker build -t nyc-mission:dash --target mission .

# 3. Run container
docker run -p 8011:8011 \
  -e SOCRATA_APP_TOKEN=your_token_here \
  nyc-mission:dash

# 4. Open dashboard
http://localhost:8011
```

---

### Method 3: Cloud (AWS, Render, Heroku)

**Best for:** Production deployment, team access  
**Time:** 15–30 minutes  
**Requirements:** Cloud account (AWS, Render, etc.)

See [Production Deployment](#production-deployment) section below.

---

### Method 4: Manual Step-by-Step (Detailed)

#### Prerequisites

**Windows (PowerShell as Admin)**:
```powershell
# Install Docker Desktop from https://www.docker.com
# Verify:
docker --version      # Should be 20.10+
docker-compose --version  # Should be 1.29+

# Install Python 3.11+
python --version
```

**Linux (Ubuntu/Debian)**:
```bash
# Update and install
sudo apt-get update && sudo apt-get upgrade
sudo apt-get install -y git curl

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Python
sudo apt-get install -y python3.11 python3-pip python3-venv
```

**MacOS (Homebrew)**:
```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker + Python
brew install --cask docker
brew install docker-compose python@3.11
```

#### Clone & Setup

```bash
# Clone repository
git clone <repo-url>
cd nyc_data

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install --upgrade pip setuptools
pip install -e ".[mission,xlsx]"
```

#### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env              # Linux/MacOS
# or
notepad .env           # Windows
```

See [Configuration](#configuration) section for required variables.

#### Build & Start Services

```bash
# Build Docker image
docker build -t nyc-mission:dash --target mission .

# Start services
docker-compose up -d mission-control

# Verify services running
docker-compose ps

# View logs
docker-compose logs -f mission-control

# Stop services
docker-compose down
```

#### Step 7: Initialize Database

```bash
# Services auto-initialize on first start
# To manually verify:
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "SELECT version();"
```

#### Step 8: Launch Web Dashboard

```bash
PYTHONPATH=src:. python -m streamlit run app/mission_control.py
# or
python launcher.py web
```

**Time**: ~20 minutes
**Complexity**: Moderate
**Best for**: Understanding the setup process

---

### Method 3: Docker-Only Deployment

Deploy without local Python installation.

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# Access Streamlit via container
docker-compose exec app PYTHONPATH=src:. python -m streamlit run app/mission_control.py

# Access at http://localhost:8501
```

**Time**: ~5 minutes
**Complexity**: Low
**Best for**: Production deployment

---

## Deployment Options

### Local Development

```bash
# Python launcher method
python launcher.py setup all
python launcher.py docker up
python launcher.py web --dev

# Direct with Streamlit
PYTHONPATH=src:. python -m streamlit run app/mission_control.py --logger.level=debug
```

**Ideal for**:
- Development and testing
- Feature implementation
- Bug fixing
- Local experimentation

---

### Staging/Testing

```bash
# Full stack with monitoring
docker-compose -f docker-compose.yml up -d

# Access all services
echo "PostgreSQL:  localhost:5432"
echo "Grafana:     http://localhost:3000"
echo "Prometheus:  http://localhost:9090"
echo "API:         http://localhost:8000/docs"
echo "Dashboard:   http://localhost:8501"
```

**Ideal for**:
- Integration testing
- Performance testing
- Monitoring verification
- Data validation

---

### Production Deployment

See [Production Deployment](#production-deployment) section below.

---

## Configuration

### Environment Variables (.env.socrata)

```bash
# Socrata API Configuration
SOCRATA_DOMAIN=data.cityofnewyork.us
SOCRATA_APP_TOKEN=your_app_token_here

# PostgreSQL Configuration
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=strong_password_here
POSTGRES_DB=sidewalk_db
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Grafana Configuration
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=strong_password_here

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
TIMEZONE=America/New_York

# Optional: Azure Cognitive Services
AZURE_COGNITIVE_KEY=your_key_here
AZURE_COGNITIVE_ENDPOINT=your_endpoint_here

# Optional: API Settings
API_PORT=8000
API_WORKERS=4
API_TIMEOUT=30
```

### Configuration File (socrata_toolkit.config.json)

```json
{
  "socrata": {
    "domain": "data.cityofnewyork.us",
    "default_datasets": {
      "complaints_311": "a2nx-4u46",
      "violations": "wvxf-dwi5",
      "contracts": "n2cp-fakn"
    }
  },
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "sidewalk_db",
    "schema": "public"
  },
  "storage": {
    "output_dir": "outputs",
    "cache_dir": ".cache",
    "temp_dir": "temp"
  },
  "governance": {
    "enforce_schema": true,
    "track_lineage": true,
    "require_audit_log": true
  }
}
```

### Streamlit Configuration (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"

[server]
port = 8501
headless = true
runOnSave = true
maxUploadSize = 200

[client]
gatherUsageStats = false
showErrorDetails = true
```

---

## Usage Examples

### Via Python Launcher

#### CLI Commands

```bash
# Search datasets
python launcher.py cli search --query "sidewalk" --limit 20

# Fetch data
python launcher.py cli meta --domain data.cityofnewyork.us --fourfour a2nx-4u46

# Generate reports
python launcher.py cli profile --domain data.cityofnewyork.us --fourfour a2nx-4u46
```

#### Web Dashboard

```bash
# Launch dashboard
python launcher.py web

# Development mode with debug
python launcher.py web --dev

# Custom host/port
python launcher.py web --host 0.0.0.0 --port 8080
```

#### Docker Management

```bash
# Start all services
python launcher.py docker up

# Start specific service
python launcher.py docker up --service postgres

# View logs
python launcher.py docker logs

# Stop all services
python launcher.py docker down

# Stop and remove volumes
python launcher.py docker down --remove-volumes

# Service status
python launcher.py docker status
```

#### System Health Check

```bash
# Full system diagnostics
python launcher.py doctor

# Shows:
# - Python version
# - Installed packages
# - Docker availability
# - Database connectivity
# - Configuration files
```

### Via Make Commands

```bash
# Install toolkit
make install

# Run tests
make test

# Format code
make format

# Start development environment
make dev

# Deploy to production
make prod-build

# Database operations
make db-init
make db-backup
make db-shell

# Docker management
make docker-up
make docker-down
make docker-logs
```

### Via Direct Scripts

**Windows (PowerShell)**:
```powershell
.\deploy.ps1 setup
.\deploy.ps1 start
.\deploy.ps1 logs
.\deploy.ps1 status
```

**Linux/MacOS (Bash)**:
```bash
./deploy.sh setup
./deploy.sh start
./deploy.sh logs
./deploy.sh status
```

---

## Troubleshooting

### Common Issues and Solutions

#### Docker Issues

**Problem**: `docker: command not found`
```bash
# Solution: Install Docker
# Windows: Download from https://www.docker.com/products/docker-desktop
# Linux: sudo apt-get install docker.io
# MacOS: brew install --cask docker
```

**Problem**: `docker: Cannot connect to Docker daemon`
```bash
# Solution: Start Docker
# Windows: Open Docker Desktop
# Linux: sudo systemctl start docker
# MacOS: open /Applications/Docker.app
```

**Problem**: Permission denied while running docker
```bash
# Linux only:
sudo usermod -aG docker $USER
# Then log out and log back in
```

#### Database Issues

**Problem**: `PostgreSQL connection refused`
```bash
# Solution: Check if PostgreSQL container is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

**Problem**: `Database initialization failed`
```bash
# Solution: Reinitialize database
docker-compose down -v
docker-compose up -d postgres
# Wait ~30 seconds for initialization
docker-compose ps
```

#### Python/Dependencies Issues

**Problem**: `ModuleNotFoundError: No module named 'socrata_toolkit'`
```bash
# Solution: Install toolkit
pip install -e ".[all]"

# Or create virtual environment first
python -m venv venv
source venv/bin/activate
pip install -e ".[all]"
```

**Problem**: `pip: command not found`
```bash
# Solution: Install pip
# Windows: python -m pip install --upgrade pip
# Linux/MacOS: python3 -m pip install --upgrade pip
```

#### Streamlit Issues

**Problem**: Dashboard won't load on localhost:8501
```bash
# Solution: Check if port is in use
# Windows: netstat -ano | findstr :8501
# Linux/MacOS: lsof -i :8501

# Use different port
PYTHONPATH=src:. python -m streamlit run app/mission_control.py --server.port 8502
```

**Problem**: "No such file or directory: socrata_toolkit/app.py"
```bash
# Solution: Run from project root directory
cd /path/to/nyc_data
python launcher.py web
```

### Debugging Tips

#### Enable Verbose Logging

```bash
# Python launcher
python launcher.py --verbose cli <command>

# Streamlit with debug
PYTHONPATH=src:. python -m streamlit run app/mission_control.py --logger.level=debug

# Docker logs
docker-compose logs -f
docker-compose logs -f <service>
```

#### Check System Health

```bash
# Full diagnostic
python launcher.py doctor

# Check Docker
docker-compose ps
docker-compose exec postgres psql -U dot_user -d sidewalk_db -c "SELECT 1"

# Check Python
python -c "import socrata_toolkit; print(socrata_toolkit.__file__)"
```

#### Database Inspection

```bash
# Open PostgreSQL shell
docker-compose exec postgres psql -U dot_user -d sidewalk_db

# List tables
\dt

# Show schema
\d tablename

# Run query
SELECT * FROM schema_registry LIMIT 10;

# Exit
\q
```

---

## Render.com Deployment

Deploy Mission Control to Render.com using the included `render.yaml` blueprint — no server management required.

### One-click deploy

1. Push the repo to GitHub.
2. Go to [render.com](https://render.com) → **New** → **Blueprint** → select your repo.
3. Render reads `render.yaml` and provisions the service automatically.
4. Set environment variables in Render dashboard → **Environment** tab:
   - `SOCRATA_APP_TOKEN` — NYC Open Data token for live data (optional)
   - `GEMINI_API_KEY` / `OPENAI_API_KEY` — for AI Copilot (optional)
5. The default `MISSION_DEMO=1` means the app works without any token.

### Free tier notes

- Bayesian engine uses ADVI (~50 MB RAM) instead of NUTS (~400 MB) — fits Render free tier.
- Free services spin down after inactivity; first load after idle may take ~30 seconds.
- Upgrade to a paid plan for always-on uptime or NUTS sampling.

### Custom domain

Render dashboard → your service → **Settings** → **Custom Domains**. TLS provisioned automatically.

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] All tests passing: `make test`
- [ ] Code formatted: `make format`
- [ ] Linting passes: `make lint`
- [ ] Secure credentials in `.env.socrata` (never commit)
- [ ] Database backups configured
- [ ] SSL/TLS certificates obtained
- [ ] Monitoring and alerting set up
- [ ] Documentation updated

### Production Build

```bash
# Full production build
make prod-build

# Or step by step
make format
make test
make lint
docker-compose -f docker-compose.yml build

# Verify images
docker images | grep nyc_data
```

### Production Deployment on Linux Server

```bash
# 1. SSH to server
ssh user@production-server.com

# 2. Clone repository
git clone <repo-url>
cd nyc_data

# 3. Create .env.socrata with production credentials
nano .env.socrata

# 4. Start services with Docker Compose
docker-compose up -d

# 5. Verify services
docker-compose ps

# 6. Check logs
docker-compose logs -f

# 7. Enable auto-restart
docker-compose exec postgres pg_dump -U dot_user sidewalk_db > backup.sql
```

### Scaling Considerations

For production with high traffic:

```yaml
# docker-compose.yml modifications:
version: '3.9'

services:
  api:
    build: .
    deploy:
      replicas: 3  # Multiple API instances
    environment:
      WORKERS: 4   # Multiple workers per instance

  postgres:
    volumes:
      - pgdata:/var/lib/postgresql/data  # Persistent storage
    environment:
      POSTGRES_MAX_CONNECTIONS: 200      # Increase connections
```

### Monitoring Setup

Grafana dashboard already configured in `docker-compose.yml`. Access at `http://localhost:3000`

Default credentials:
- Username: admin
- Password: (from `.env.socrata` GRAFANA_ADMIN_PASSWORD)

Pre-configured dashboards:
- PostgreSQL performance
- CDC event processing
- API response times
- Data quality metrics

### Backup Strategy

```bash
# Daily backup script
0 2 * * * docker-compose -f /app/nyc_data/docker-compose.yml exec postgres pg_dump -U dot_user sidewalk_db > /backups/sidewalk_db_$(date +\%Y\%m\%d).sql

# Restore from backup
docker-compose exec postgres psql -U dot_user sidewalk_db < backup.sql

# Test restore
docker-compose exec postgres psql -U dot_user sidewalk_db -c "SELECT COUNT(*) FROM sidewalk_inspections;"
```

---

## Additional Resources

- **[Architecture Documentation](./architecture.md)** - System design and components
- **[API Documentation](./api_guide.md)** - REST API endpoints
- **[Data Governance Guide](./PHASE3_COMPLETION_SUMMARY.md)** - Schema, lineage, compliance
- **[Troubleshooting FAQ](./sop_faq.md)** - Common questions
- **[CLI Reference](./cli.md)** - Command-line tool usage
- **[Microsoft 365 Integration](./MICROSOFT_365_INTEGRATION.md)** - Teams, SharePoint, Power BI
- **[GIS Integration](./geospatial.md)** - QGIS, PostGIS, mobile field work

---

## Support

For issues and questions:

1. Check this document's Troubleshooting section
2. Review project documentation in `./docs/`
3. Check Docker logs: `docker-compose logs -f`
4. Run health check: `python launcher.py doctor`
5. Open an issue on GitHub with:
   - Error message
   - Output from `python launcher.py doctor`
   - Platform (Windows/Linux/MacOS)
   - Steps to reproduce

---

**Last Updated**: 2026-05-11
**Version**: 0.3.0
**Maintained by**: NYC DOT Development Team
