# NYC DOT Sidewalk Toolkit -- Common Tasks
# Run any target with: make <target>

.PHONY: install test lint doctor report clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install the toolkit with all extras
	pip install -e ".[all]"

install-minimal: ## Install core only (no optional deps)
	pip install -e .

setup: ## Run the interactive setup wizard
	python -m socrata_toolkit.install_wizard

test: ## Run the full test suite
	python -m pytest tests/ -v

test-quick: ## Run tests without verbose output
	python -m pytest tests/ -q

test-cov: ## Run tests with coverage report
	python -m pytest tests/ --cov=socrata_toolkit --cov-report=term-missing

lint: ## Run linting checks
	python -m ruff check socrata_toolkit/ tests/

format: ## Auto-format code
	python -m black socrata_toolkit/ tests/
	python -m isort socrata_toolkit/ tests/

doctor: ## Check installation health
	python -c "from socrata_toolkit.cli import main; main(['doctor'])" 2>/dev/null || socrata doctor

report: ## Generate a sample contract report (uses default config)
	@mkdir -p outputs/reports
	@echo "Generate reports via: socrata pipeline <domain> <4x4> --json-out outputs/data.json"

clean: ## Remove build artifacts and caches
	rm -rf __pycache__ .pytest_cache .ruff_cache dist build *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
