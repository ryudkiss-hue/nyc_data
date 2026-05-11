# NYC DOT Sidewalk Toolkit - Quick Start Guide

Get up and running in 5 minutes.

## One Command Setup

### Windows (PowerShell)

```powershell
git clone <repo-url>
cd nyc_data
.\deploy.ps1 setup
.\deploy.ps1 start
Start http://localhost:8501
```

### Linux / MacOS

```bash
git clone <repo-url>
cd nyc_data
chmod +x deploy.sh
./deploy.sh setup
./deploy.sh start
open http://localhost:8501
```

### All Platforms

```bash
git clone <repo-url>
cd nyc_data
python launcher.py setup all
python launcher.py docker up
python launcher.py web
# Open browser to http://localhost:8501
```

## What You Get

After setup completes, you have:

| Service | URL | Username | Password |
|---------|-----|----------|----------|
| **Streamlit Dashboard** | http://localhost:8501 | - | - |
| **PostgreSQL Database** | localhost:5432 | dot_user | (see .env.socrata) |
| **Grafana Monitoring** | http://localhost:3000 | admin | (see .env.socrata) |
| **Prometheus Metrics** | http://localhost:9090 | - | - |
| **Jaeger Tracing** | http://localhost:16686 | - | - |

## First Steps

### 1. Edit Configuration

```bash
# Edit .env.socrata with your Socrata API token
nano .env.socrata        # Linux/MacOS
# or
notepad .env.socrata     # Windows
```

### 2. Run CLI Command

```bash
# Search for datasets
python launcher.py cli search --query "sidewalk repairs"

# Or via launcher on Windows
py launcher.py cli search --query "sidewalk repairs"
```

### 3. Check Health

```bash
# Run system diagnostics
python launcher.py doctor
```

### 4. View Dashboard

Open browser to **http://localhost:8501**

## Common Commands

### Using Python Launcher

```bash
# Web dashboard
python launcher.py web

# CLI tools
python launcher.py cli search --query repairs
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
