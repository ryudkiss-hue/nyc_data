.PHONY: setup test lint demo evaluate train help install clean

help:
	@echo "NYC DOT SIM Fuzzy Router - Available commands:"
	@echo "  make setup     - Install dependencies and validate"
	@echo "  make test      - Run all tests"
	@echo "  make lint      - Check code style with ruff"
	@echo "  make demo      - Run end-to-end demo"
	@echo "  make evaluate  - Evaluate router accuracy on 1,080 variants"
	@echo "  make train     - Optimize router weights from feedback"
	@echo "  make install   - Install package in editable mode"
	@echo "  make clean     - Remove build artifacts"

setup:
	./scripts/setup.sh

install:
	pip install -e ".[dev,mission]"

test:
	pytest tests/socrata_toolkit/core tests/socrata_toolkit/training -q

lint:
	ruff check src/socrata_toolkit tests

demo:
	python3 training/demo_workflow.py

evaluate:
	python3 -c "import sys; sys.path.insert(0, 'src'); from socrata_toolkit.training.evaluate_router import evaluate_router; from socrata_toolkit.core.config import get_config; c=get_config(); import json; print(json.dumps(evaluate_router(c.load_kpi_registry(), []), indent=2))"

train:
	python3 training/train_router_weights.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf build dist *.egg-info
