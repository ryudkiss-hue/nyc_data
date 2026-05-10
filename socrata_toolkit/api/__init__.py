"""FastAPI REST service for NYC DOT operational intelligence.

This module provides a production-grade REST API exposing KPI data, operational metrics,
and compliance reports from Phase 3 materialized views. It integrates with Phase 2
observability infrastructure and Phase 1 domain models.

Key Components:
    - FastAPI application factory (main.py)
    - SQLAlchemy ORM models for materialized views (models.py)
    - Pydantic request/response schemas (schemas.py)
    - JWT authentication and RBAC (auth.py)
    - Redis caching with TTL management (cache.py)
    - REST endpoints for incidents, repairs, KPIs (routes.py)
    - Custom exception handling with structured logging (exceptions.py)
    - Configuration management (config.py)

Usage:
    from socrata_toolkit.api.main import create_app
    app = create_app()
    # Run with: uvicorn socrata_toolkit.api.main:app --reload
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    "create_app",
    "APIConfig",
]

from socrata_toolkit.api.config import APIConfig
from socrata_toolkit.api.main import create_app

__version__ = "0.1.0"
