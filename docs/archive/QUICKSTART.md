# NYC DOT SIM Toolkit - Quick Start Guide

Get the Dash Mission Control dashboard running in under 5 minutes.

## Installation

### Prerequisites
- Python 3.11+
- pip

### Local Setup

```bash
# Clone the repository
git clone <repo-url>
cd nyc_data

# Install dependencies
pip install -e ".[mission,xlsx]"

# (Optional) Set your Socrata API token
export SOCRATA_APP_TOKEN=your-token-here
export ANTHROPIC_API_KEY=your-api-key-here
```

### Launch the Dashboard

```bash
# Option 1: Direct Dash Mission Control (RECOMMENDED)
python app/dash_app.py
# → Open http://localhost:8011

# Option 2: Via launcher shim
python main.py
# → Launches Dash or falls back to Streamlit

# Option 3: Streamlit (SECONDARY - for data exploration)
streamlit run app/app.py
# → Open http://localhost:8501

# Option 4: Docker (requires Docker)
docker compose up mission-control
# → http://localhost:8011
```

## What You Can Do

Once the dashboard loads, you can:
- **Home** — View project status and Metrics
- **Construction Lists** — Browse construction projects by borough
- **GIS & Conflicts** — Visualize spatial overlaps between permits and inspections
- **Contract Analytics** — Analyze contractor performance and spending
- **Forecasting** — Forecast SLA breaches and project timelines

## Configuration

### API Token (Required)

For full data access (>2,000 rows), you'll need a Socrata API token:

1. Visit https://data.cityofnewyork.us/profile/settings/tokens
2. Create a new token
3. Set it in your environment:
   ```bash
   export SOCRATA_APP_TOKEN=your-token-here
   ```

### Optional Features

- **NL Queries** — `ANTHROPIC_API_KEY` for natural language questions
- **Demo Mode** — `MISSION_DEMO=1` (no API calls, synthetic data)

See `docs/DEPLOYMENT.md` for cloud deployment, Docker, and environment configuration.

## Troubleshooting

**Dashboard won't load:**
```bash
# Check if Dash is running (primary)
curl http://localhost:8011/

# Check FastAPI logs
python app/dash_app.py  # Check terminal output for errors

# Alternative: Check if Streamlit is running (secondary)
curl http://localhost:8501/_stcore/health
streamlit run app/app.py --logger.level=debug
```

**Missing data:**
```bash
# Verify API token
echo $SOCRATA_APP_TOKEN

# Check DuckDB cache
ls -la data/local_db/
```

**CLI Tools
python launcher.py cli meta --domain data.cityofnewyork.us --fourfour a2nx-4u46

# Docker management
python launcher.py docker up
python launcher.py docker down
python launcher.py docker status

# System health
python launcher.py doctor
python launcher.py info
```

### Using Make

```bash
# Install
make install

# Start development
make dev

# Run tests
make test

# View help
make help
```

### Using Platform Scripts

**Windows PowerShell**:
```powershell
.\deploy.ps1 setup
.\deploy.ps1 start
.\deploy.ps1 logs
.\deploy.ps1 stop
```

**Linux/MacOS Bash**:
```bash
./deploy.sh setup
./deploy.sh start
./deploy.sh logs
./deploy.sh stop
```

## Troubleshooting

### Docker won't start
- **Windows**: Open Docker Desktop application
- **Linux**: Run `sudo systemctl start docker`
- **MacOS**: Open `/Applications/Docker.app`

### Python packages error
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/MacOS
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e ".[all]"
```

### Port already in use
```bash
# Change port
python launcher.py web --port 8502

# Or check what's using the port
# Windows: netstat -ano | findstr :8501
# Linux: lsof -i :8501
```

### Database connection error
```bash
# Restart PostgreSQL
python launcher.py docker restart --service postgres

# Or full restart
python launcher.py docker down
python launcher.py docker up
```

## Next Steps

1. **Complete Setup**: See [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)
2. **Learn Architecture**: See [Architecture Documentation](docs/architecture.md)
3. **API Usage**: See [API Guide](docs/api_guide.md)
4. **Data Governance**: See [Data Governance Guide](docs/PHASE3_COMPLETION_SUMMARY.md)
5. **Microsoft 365**: See [M365 Integration](docs/MICROSOFT_365_INTEGRATION.md)
6. **GIS/Mapping**: See [Geospatial Guide](docs/geospatial.md)

## Three Ways to Use This Toolkit

### 1. **Command-Line Interface (CLI)**
```bash
python launcher.py cli search --query repairs
python launcher.py cli profile <dataset>
python launcher.py cli lineage <dataset>
```
*Best for*: Automated scripts, batch processing, integration with other tools

### 2. **Web Dashboard (Streamlit)**
```bash
python launcher.py web
# Opens interactive dashboard at http://localhost:8501
```
*Best for*: Visual exploration, reports, stakeholder presentations

### 3. **Docker Services**
```bash
python launcher.py docker up
# Access PostgreSQL, APIs, monitoring, tracing
```
*Best for*: Production deployment, scaling, integration architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    NYC DOT Toolkit Stack                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │   Streamlit │  │   FastAPI    │  │   CLI Tools     │   │
│  │  Dashboard  │  │   REST API   │  │   (socrata cli) │   │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘   │
│         │                │                    │             │
│         └────────────┬───┴────────────────────┘             │
│                      │                                       │
│        ┌─────────────▼──────────────────────┐              │
│        │  Governance & Compliance Engine    │              │
│        │  • Schema Registry                 │              │
│        │  • CDC Processor                   │              │
│        │  • Lineage Tracking                │              │
│        │  • Compliance Checker              │              │
│        └──────────┬─────────────────────────┘              │
│                   │                                         │
│        ┌──────────▼──────────┬──────────────┐             │
│        │   PostgreSQL +      │    Redis     │             │
│        │   PostGIS          │    Cache     │             │
│        │   (Data Storage)    │              │             │
│        └─────────────────────┴──────────────┘             │
│                   │                                         │
│        ┌──────────▼──────────────────────┐               │
│        │  Monitoring & Observability      │               │
│        │  • Prometheus                    │               │
│        │  • Grafana                       │               │
│        │  • Jaeger                        │               │
│        └───────────────────────────────────┘              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Support Resources

| Need | Resource |
|------|----------|
| Setup help | [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) |
| How it works | [Architecture](docs/architecture.md) |
| CLI commands | [CLI Reference](docs/cli.md) |
| REST API | [API Guide](docs/api_guide.md) |
| Data governance | [Governance Guide](docs/PHASE3_COMPLETION_SUMMARY.md) |
| Troubleshooting | [FAQ](docs/sop_faq.md) |
| Microsoft 365 | [M365 Integration](docs/MICROSOFT_365_INTEGRATION.md) |
| GIS/Mapping | [Geospatial Guide](docs/geospatial.md) |
| Database access | [Database Guide](docs/INTEGRATION_QUICK_START.md) |

---

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Maintainer**: NYC DOT Development Team
