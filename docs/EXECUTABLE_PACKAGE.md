# NYC DOT Toolkit - Complete Executable Package

Guide to the complete executable deployment package for the NYC DOT Sidewalk Data Governance Toolkit.

## What's Included

The toolkit is packaged with multiple entry points for different use cases and platforms:

### 1. **Universal Python Launcher** (`launcher.py`)

Single entry point for all operations across all platforms.

```bash
python launcher.py --help
```

**Features**:
- CLI command execution
- Web dashboard launch
- Docker orchestration
- System setup and initialization
- Health diagnostics

**Advantages**:
- ✅ Works on Windows, Linux, MacOS
- ✅ No platform-specific syntax
- ✅ Integrated help system
- ✅ Consistent interface

---

### 2. **Platform-Specific Deployment Scripts**

#### Windows: `deploy.ps1`

PowerShell script for Windows 10/11 with full feature support.

```powershell
.\deploy.ps1 setup
.\deploy.ps1 start
.\deploy.ps1 logs
.\deploy.ps1 stop
```

**Features**:
- Color-coded output
- Full error handling
- Docker detection and auto-selection
- PowerShell-native operations

#### Linux/MacOS: `deploy.sh`

Bash script for Unix-like systems.

```bash
./deploy.sh setup
./deploy.sh start
./deploy.sh logs
./deploy.sh stop
```

**Features**:
- ANSI color output
- Service management
- Log streaming
- Volume cleanup options

---

### 3. **Make-Based Build Automation** (`Makefile`)

GNU Make commands for development and deployment.

```bash
make help        # Show all available commands
make setup-all   # Complete setup
make deploy      # Full deployment
make dev         # Development environment
make test        # Run tests
make clean       # Cleanup
```

**Features**:
- 30+ commands for all operations
- Automatic platform detection
- Colored output
- Documentation inline

---

### 4. **Docker Compose Configuration** (`docker-compose.yml`)

Complete microservices stack pre-configured.

```bash
docker-compose up -d
docker-compose ps
docker-compose logs -f
docker-compose down
```

**Includes**:
- PostgreSQL 16 + PostGIS
- Redis cache
- Prometheus metrics
- Grafana dashboards
- Jaeger tracing
- Application containers

---

## Usage Comparison

Choose the method that fits your workflow:

| Method | Platform | Best For | Command |
|--------|----------|----------|---------|
| **Launcher** | All | Unified interface, automation | `python launcher.py ...` |
| **PowerShell** | Windows | Native Windows integration | `.\deploy.ps1 ...` |
| **Bash** | Linux/MacOS | Unix-native operations | `./deploy.sh ...` |
| **Make** | All | Development workflow | `make ...` |
| **Docker Compose** | All | Container management | `docker-compose ...` |

---

## Quick Start Paths

### Path 1: Fastest (5 minutes)

```bash
# Windows
.\deploy.ps1 setup
.\deploy.ps1 start
start http://localhost:8501

# Linux/MacOS
./deploy.sh setup
./deploy.sh start
open http://localhost:8501

# All platforms
python launcher.py setup all
python launcher.py docker up
python launcher.py web
```

### Path 2: Developer (10 minutes)

```bash
# Install with full dependencies
make install

# Start dev environment with everything
make dev

# Run tests during development
make test

# Format code
make format

# Deploy when ready
make deploy
```

### Path 3: Production (15 minutes)

```bash
# Production-grade build
make prod-build

# Verify tests pass
make test

# Deploy to production
docker-compose -f docker-compose.yml up -d

# Monitor
docker-compose logs -f
```

---

## File Structure

```
nyc_data/
├── launcher.py              # Universal Python launcher (all platforms)
├── deploy.ps1               # Windows PowerShell script
├── deploy.sh                # Linux/MacOS Bash script
├── Makefile                 # Make build automation
├── docker-compose.yml       # Complete microservices stack
├── Dockerfile               # Application container
├── Dockerfile.api           # API server container
├── QUICKSTART.md            # 5-minute setup guide
├── README.md                # Main documentation
├── pyproject.toml           # Python project config
├── requirements.txt         # Python dependencies
├── .env.docker.example      # Environment template
├── .env.socrata             # Environment config (create from template)
├── socrata_toolkit/         # Main application code
│   ├── __init__.py
│   ├── cli.py              # CLI commands
│   ├── app.py              # Streamlit dashboard
│   ├── api.py              # FastAPI REST API
│   ├── governance_processor.py
│   ├── schema_registry.py
│   ├── cdc_engine.py
│   ├── lineage_core.py
│   └── ... (100+ modules)
├── docker/                  # Docker configuration
│   ├── postgres/
│   └── prometheus/
├── sql/                     # Database initialization scripts
│   ├── 001_init.sql
│   ├── 003_schema_registry.sql
│   └── ... (more schemas)
├── tests/                   # Test suite
│   ├── test_*.py
│   └── conftest.py
├── docs/                    # Documentation
│   ├── DEPLOYMENT_GUIDE.md
│   ├── architecture.md
│   ├── api_guide.md
│   ├── PHASE3_COMPLETION_SUMMARY.md
│   └── ... (20+ guides)
└── scripts/                 # Utility scripts
    ├── init_db.sh
    └── ... (setup scripts)
```

---

## Launcher Command Reference

### Setup & Initialization

```bash
# Complete setup
python launcher.py setup all

# Individual components
python launcher.py setup database
python launcher.py setup schema
python launcher.py setup config
```

### CLI Operations

```bash
# Search datasets
python launcher.py cli search --query "repairs"

# Get metadata
python launcher.py cli meta --domain data.cityofnewyork.us --fourfour a2nx-4u46

# Profile data
python launcher.py cli profile <domain> <fourfour>

# Generate reports
python launcher.py cli report <domain> <fourfour>
```

### Web Interface

```bash
# Launch dashboard
python launcher.py web

# Development mode
python launcher.py web --dev

# Custom host/port
python launcher.py web --host 0.0.0.0 --port 8080
```

### Docker Management

```bash
# Start all services
python launcher.py docker up

# Start specific service
python launcher.py docker up --service postgres

# View service status
python launcher.py docker status

# Stream logs
python launcher.py docker logs
python launcher.py docker logs --service postgres

# Stop services
python launcher.py docker down

# Stop and clean volumes
python launcher.py docker down --remove-volumes
```

### System Diagnostics

```bash
# Full health check
python launcher.py doctor

# System information
python launcher.py info
```

---

## Make Command Reference

### Development

```bash
make install          # Install with all dependencies
make install-minimal  # Install core only
make setup           # Run setup wizard
make dev             # Start dev environment
make test            # Run full test suite
make test-quick      # Run tests quickly
make test-cov        # Tests with coverage
make lint            # Check code quality
make format          # Auto-format code
```

### Docker

```bash
make docker-build      # Build images
make docker-up         # Start services
make docker-down       # Stop services
make docker-logs       # View logs
make docker-status     # Show status
make docker-restart    # Restart services
make docker-clean      # Stop and remove volumes
```

### Database

```bash
make db-init         # Initialize schema
make db-backup       # Backup database
make db-shell        # Open database CLI
```

### Complete Workflows

```bash
make setup-all       # Install + config + build
make deploy          # Full deployment
make prod-build      # Production-grade build
make clean           # Remove all artifacts
make clean-all       # Complete cleanup
```

---

## PowerShell Script Reference (`deploy.ps1`)

### Setup

```powershell
.\deploy.ps1 setup
```

Creates `.env.socrata` configuration file and validates environment.

### Service Management

```powershell
.\deploy.ps1 start              # Start all services
.\deploy.ps1 start -Service postgres    # Start specific service
.\deploy.ps1 stop               # Stop all services
.\deploy.ps1 stop -RemoveVolumes        # Stop and clean volumes
.\deploy.ps1 status             # Show service status
.\deploy.ps1 logs               # Stream logs
.\deploy.ps1 logs -Service postgres    # Specific service logs
```

### Advanced Options

```powershell
.\deploy.ps1 help               # Show help
```

---

## Bash Script Reference (`deploy.sh`)

### Setup

```bash
./deploy.sh setup
```

Creates `.env.socrata` and initializes directories.

### Service Management

```bash
./deploy.sh start                    # Start all services
./deploy.sh start --service postgres # Start specific service
./deploy.sh stop                     # Stop all services
./deploy.sh stop --volumes           # Stop and remove volumes
./deploy.sh status                   # Show status
./deploy.sh logs                     # Stream logs
./deploy.sh logs --service postgres  # Specific service logs
./deploy.sh restart                  # Restart services
```

### Advanced

```bash
./deploy.sh build                    # Build images
./deploy.sh clean                    # Full cleanup
./deploy.sh help                     # Show help
```

---

## Docker Compose Commands

For those preferring direct Docker Compose:

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View status
docker-compose ps

# Stream logs
docker-compose logs -f

# Access services
docker-compose exec postgres psql -U dot_user -d sidewalk_db
docker-compose exec redis redis-cli

# Stop services
docker-compose down

# Remove volumes
docker-compose down -v
```

---

## Configuration Files

### `.env.socrata` (Environment Variables)

```bash
SOCRATA_DOMAIN=data.cityofnewyork.us
SOCRATA_APP_TOKEN=your_token_here
POSTGRES_USER=dot_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=sidewalk_db
GRAFANA_ADMIN_PASSWORD=your_password
LOG_LEVEL=INFO
```

### `socrata_toolkit.config.json` (Application Config)

```json
{
  "socrata": {
    "domain": "data.cityofnewyork.us",
    "default_datasets": {
      "complaints_311": "a2nx-4u46"
    }
  },
  "postgres": {
    "host": "localhost",
    "port": 5432,
    "database": "sidewalk_db"
  }
}
```

### `.streamlit/config.toml` (Dashboard Config)

```toml
[theme]
primaryColor = "#1f77b4"

[server]
port = 8501
headless = true
```

---

## Entry Points

### For Command-Line Usage

```bash
# Direct module execution
python -m socrata_toolkit.cli search --query repairs

# Or via launcher
python launcher.py cli search --query repairs
```

### For Web Dashboard

```bash
# Direct Streamlit
streamlit run socrata_toolkit/app.py

# Or via launcher
python launcher.py web
```

### For REST API

```bash
# Direct uvicorn
uvicorn socrata_toolkit.api:app --host 0.0.0.0 --port 8000

# Via Docker
docker-compose up -d api
# API available at http://localhost:8000/docs
```

### For Batch Processing

```bash
# Direct Python
python scripts/batch_process.py

# Or via CLI
python launcher.py cli pipeline <domain> <fourfour>
```

---

## Execution Flow

```
┌──────────────────────────────────────────────────────┐
│  User Invokes: python launcher.py <command>          │
└──────────────┬───────────────────────────────────────┘
               │
    ┌──────────┴──────────┬──────────────┬──────────────┐
    │                     │              │              │
    ▼                     ▼              ▼              ▼
┌──────────┐  ┌──────────────┐  ┌────────────┐  ┌──────────┐
│   CLI    │  │   Docker     │  │    Web     │  │   Setup  │
│ Command  │  │ Management   │  │ Dashboard  │  │          │
│ Routing  │  │ (compose)    │  │(Streamlit) │  │          │
└────┬─────┘  └──────┬───────┘  └─────┬──────┘  └────┬─────┘
     │               │               │              │
     ▼               ▼               ▼              ▼
 ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐
 │ Execute │  │  Start   │  │  Render    │  │ Create   │
 │ Command │  │ Services │  │ Interface  │  │ Config   │
 └────┬────┘  └────┬─────┘  └─────┬──────┘  └────┬─────┘
      │            │              │              │
      └────────────┴──────────────┴──────────────┘
              │
              ▼
      ┌──────────────────┐
      │ Governance Stack │
      │ • Schema Reg     │
      │ • CDC Engine     │
      │ • Lineage        │
      │ • Compliance     │
      └────────┬─────────┘
               │
      ┌────────▼──────────┐
      │  Data Layer       │
      │ PostgreSQL + GIS  │
      │ Redis Cache       │
      └───────────────────┘
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Git cloned and dependencies installed
- [ ] `.env.socrata` configured with credentials
- [ ] Docker and Docker Compose installed
- [ ] Ports 5432, 6379, 3000, 8000, 8501, 9090 available
- [ ] Internet connection for initial setup

### Deployment

- [ ] Run `python launcher.py setup all`
- [ ] Run `python launcher.py docker up`
- [ ] Run `python launcher.py doctor` to verify
- [ ] Run `python launcher.py web` to launch dashboard
- [ ] Access http://localhost:8501

### Post-Deployment

- [ ] Dashboard accessible and responsive
- [ ] CLI commands functioning
- [ ] Database connected (check logs)
- [ ] Monitoring accessible (Grafana, Prometheus)
- [ ] Tests passing: `make test`

---

## Troubleshooting Quick Links

| Issue | Solution |
|-------|----------|
| Python not found | Install Python 3.9+ |
| Docker not running | Start Docker Desktop or daemon |
| Ports in use | Change ports in docker-compose.yml |
| Import errors | Run `pip install -e ".[all]"` |
| Database won't connect | Run `python launcher.py docker restart --service postgres` |
| Streamlit crashes | Check logs: `docker-compose logs app` |
| Permission denied on scripts | Run `chmod +x deploy.sh` on Linux/MacOS |

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

---

## Documentation Map

- **Quick Start**: [QUICKSTART.md](../QUICKSTART.md) - 5-minute setup
- **Full Deployment**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete guide
- **This Document**: [EXECUTABLE_PACKAGE.md](EXECUTABLE_PACKAGE.md) - Package overview
- **Architecture**: [architecture.md](architecture.md) - System design
- **API Docs**: [api_guide.md](api_guide.md) - REST endpoints
- **CLI Reference**: [cli.md](cli.md) - Command-line tool
- **Data Governance**: [PHASE3_COMPLETION_SUMMARY.md](PHASE3_COMPLETION_SUMMARY.md)
- **FAQ**: [sop_faq.md](sop_faq.md) - Common questions

---

## Summary

The NYC DOT Toolkit is packaged with **multiple execution paths** for maximum flexibility:

1. **Universal**: Python launcher works everywhere
2. **Native**: PowerShell on Windows, Bash on Unix
3. **Declarative**: Make commands for development
4. **Direct**: Docker Compose for container orchestration

Choose the method that best fits your workflow and platform. All paths lead to the same robust, feature-complete data governance solution.

---

**Version**: 0.3.0  
**Last Updated**: 2026-05-11  
**Status**: Production Ready
