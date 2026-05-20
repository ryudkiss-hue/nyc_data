# NYC DOT Sidewalk Toolkit -- Complete Build & Deployment Automation
# Run any target with: make <target>

.PHONY: help install setup test lint format docker run dev deploy clean

# Detect OS
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
    LAUNCH_CMD = python3 launcher.py
endif
ifeq ($(UNAME_S),Darwin)
    LAUNCH_CMD = python3 launcher.py
endif
ifeq ($(OS),Windows_NT)
    LAUNCH_CMD = python launcher.py
endif
LAUNCH_CMD ?= python launcher.py

# ============================================================================
# CORE DEVELOPMENT
# ============================================================================

help: ## 📖 Show this help
	@echo ""
	@echo "NYC DOT Sidewalk Toolkit - Build & Deployment Automation"
	@echo "=========================================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

install: ## 📦 Install toolkit with all dependencies
	pip install -e ".[all]"
	@echo "✓ Toolkit installed successfully"

install-minimal: ## 📦 Install toolkit with core only
	pip install -e .
	@echo "✓ Core toolkit installed"

setup: ## 🔧 Run interactive setup wizard
	python -m socrata_toolkit.install_wizard

build-exe: ## 📦 Build Windows standalone executable (PyInstaller)
	python scripts/build_exe.py

test: ## 🧪 Run full test suite with verbose output
	python -m pytest tests/ -v

test-quick: ## 🧪 Run tests with minimal output
	python -m pytest tests/ -q

test-cov: ## 📊 Run tests with coverage report
	python -m pytest tests/ --cov=socrata_toolkit --cov-report=term-missing

lint: ## 🔍 Check code quality with ruff
	python -m ruff check socrata_toolkit/ tests/

format: ## 🎨 Auto-format code with black and isort
	python -m black socrata_toolkit/ tests/
	python -m isort socrata_toolkit/ tests/
	@echo "✓ Code formatted"

doctor: ## 🏥 Check installation health and dependencies
	$(LAUNCH_CMD) doctor

# ============================================================================
# DASH & CLI INTERFACES
# ============================================================================

cli: ## ⚙️ Run CLI tool (pass args with ARGS=...)
	$(LAUNCH_CMD) cli $(ARGS)

web: ## 🌐 Launch Streamlit web dashboard
	$(LAUNCH_CMD) python dash_app/app.py

web-dev: ## 🌐 Launch Streamlit in development mode
	$(LAUNCH_CMD) web --dev

info: ## ℹ️ Show system information
	$(LAUNCH_CMD) info

# ============================================================================
# DOCKER ORCHESTRATION
# ============================================================================

docker-build: ## 🐳 Build all Docker images
	docker-compose build

docker-up: ## 🐳 Start all Docker services
	$(LAUNCH_CMD) docker up

docker-down: ## 🐳 Stop all Docker services
	$(LAUNCH_CMD) docker down

docker-clean: ## 🐳 Stop services and remove volumes (destructive)
	$(LAUNCH_CMD) docker down --remove-volumes

docker-logs: ## 📋 Show Docker service logs
	docker-compose logs -f

docker-logs-postgres: ## 📋 Show PostgreSQL logs
	docker-compose logs -f postgres

docker-logs-api: ## 📋 Show API logs
	docker-compose logs -f api

docker-status: ## 📊 Show Docker service status
	docker-compose ps

docker-restart: ## 🔄 Restart all Docker services
	docker-compose restart

# ============================================================================
# DEPLOYMENT & SETUP
# ============================================================================

setup-all: install setup docker-build ## 🚀 Complete setup (install, config, build)
	@echo ""
	@echo "✓ Setup complete! Next steps:"
	@echo "  1. Edit .env.socrata with your credentials"
	@echo "  2. Run: make docker-up"
	@echo "  3. Run: make web"
	@echo ""

deploy: setup-all docker-up ## 🚀 Full deployment (setup + start)
	@echo ""
	@echo "✓ Deployment complete!"
	@echo "  Services available at:"
	@echo "    PostgreSQL:  localhost:5432"
	@echo "    Grafana:     http://localhost:3000"
	@echo "    Prometheus:  http://localhost:9090"
	@echo ""

dev: install docker-up web ## 👨‍💻 Development environment (install, docker, web)

prod-build: format test lint docker-build ## 🏭 Production build (format, test, lint, docker)
	@echo "✓ Production build complete"

# ============================================================================
# DATABASE & SCHEMA
# ============================================================================

db-init: ## 🗄️ Initialize database schema
	$(LAUNCH_CMD) setup database

db-migrate: ## 🔄 Run database migrations
	docker-compose exec postgres psql -U dot_user -d sidewalk_db -f /docker-entrypoint-initdb.d/init.sql

db-backup: ## 💾 Backup PostgreSQL database
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U dot_user sidewalk_db > backups/sidewalk_db_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Database backed up to backups/"

db-shell: ## 🐚 Open PostgreSQL shell
	docker-compose exec postgres psql -U dot_user -d sidewalk_db

# ============================================================================
# REPORTING & ANALYSIS
# ============================================================================

report: ## 📄 Generate sample reports
	@mkdir -p outputs/reports
	@echo "Generate reports via: socrata pipeline <domain> <4x4> --json-out outputs/data.json"

profile: ## 📊 Run data profiling analysis
	python -c "from socrata_toolkit.analysis import profile_dataframe; print('Profiling tools ready')"

# ============================================================================
# MAINTENANCE & CLEANUP
# ============================================================================

clean: ## 🧹 Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "✓ Build artifacts cleaned"

clean-docker: ## 🧹 Remove Docker containers and images
	docker-compose down -v
	docker system prune -f
	@echo "✓ Docker cleaned"

clean-all: clean clean-docker ## 🧹 Complete cleanup (artifacts, docker, cache)
	@echo "✓ Complete cleanup finished"

# ============================================================================
# DOCUMENTATION & HELP
# ============================================================================

docs: ## 📚 Show documentation
	@echo "Documentation available in ./docs/"
	@ls -la docs/*.md | head -10

quickstart: ## 🚀 Show quick start guide
	@echo ""
	@echo "Quick Start Guide"
	@echo "================="
	@echo ""
	@echo "1. Initial Setup:"
	@echo "   make setup-all"
	@echo ""
	@echo "2. Start Services:"
	@echo "   make docker-up"
	@echo ""
	@echo "3. Launch Dashboard:"
	@echo "   make web"
	@echo ""
	@echo "4. CLI Usage:"
	@echo "   make cli ARGS='search --query repairs'"
	@echo ""
	@echo "5. Check Status:"
	@echo "   make docker-status"
	@echo ""

# ============================================================================
# DEFAULT TARGET
# ============================================================================

.DEFAULT_GOAL := help

# Display help on empty make command
all: help
