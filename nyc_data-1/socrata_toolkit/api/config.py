"""API configuration management with environment-based settings.

Supports development, staging, and production environments with secure
defaults and validation on startup.

Configuration Sources:
    1. Environment variables (highest priority)
    2. .env file for development
    3. Hardcoded defaults

Example:
    from socrata_toolkit.api.config import APIConfig
    config = APIConfig()
    print(config.database_url)
    print(config.redis_url)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import os

from dotenv import load_dotenv


class Environment(Enum):
    """Deployment environments."""

    DEV = "development"
    STAGING = "staging"
    PROD = "production"


@dataclass
class APIConfig:
    """API service configuration.

    Attributes:
        environment: Deployment environment (dev/staging/prod)
        database_url: PostgreSQL connection string
        redis_url: Redis connection URL for caching
        jwt_secret_key: Secret key for JWT signing (generate with: openssl rand -hex 32)
        jwt_algorithm: JWT algorithm (HS256 default)
        jwt_expiry_minutes: Token expiry in minutes (24 hours default)
        api_version: API version string (v1)
        log_level: Logging level (debug/info/warning/error)
        cors_origins: List of allowed CORS origins
        rate_limit_requests: Max requests per minute (None = disabled)
        cache_ttl_summary_kpis: Cache TTL for summary KPIs in seconds (2 hours)
        cache_ttl_segment_details: Cache TTL for segment details (24 hours)
        cache_ttl_contractor_metrics: Cache TTL for contractor metrics (6 hours)
        cache_ttl_incident_lists: Cache TTL for incident lists (1 hour)
        db_pool_size: PostgreSQL connection pool size
        db_pool_overflow: Max overflow connections
        db_pool_timeout: Connection timeout in seconds
    """

    # Environment
    environment: str = "development"
    api_version: str = "v1"
    api_port: int = 8000
    api_host: str = "0.0.0.0"

    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/nyc_sidewalk"
    db_pool_size: int = 10
    db_pool_overflow: int = 20
    db_pool_timeout: float = 30.0

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_timeout: float = 5.0

    # JWT
    jwt_secret_key: str = "change-me-in-production-with-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 24 * 60  # 24 hours

    # Logging
    log_level: str = "info"
    log_format: str = "json"  # json or text

    # CORS
    cors_origins: list[str] = None  # type: ignore

    # Rate limiting
    rate_limit_requests: Optional[int] = 100  # per minute
    rate_limit_window: int = 60  # seconds

    # Cache TTLs (in seconds)
    cache_ttl_summary_kpis: int = 2 * 60 * 60  # 2 hours
    cache_ttl_segment_details: int = 24 * 60 * 60  # 24 hours
    cache_ttl_contractor_metrics: int = 6 * 60 * 60  # 6 hours
    cache_ttl_incident_lists: int = 1 * 60 * 60  # 1 hour

    def __post_init__(self) -> None:
        """Initialize and validate configuration after creation."""
        # Load from environment variables
        self._load_from_env()

        # Validate critical settings
        self._validate()

    def _load_from_env(self) -> None:
        """Load configuration from environment variables and .env file."""
        # Load .env file if present
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            load_dotenv(env_file)

        # Map environment variables to config attributes
        env_mappings = {
            "ENVIRONMENT": "environment",
            "API_VERSION": "api_version",
            "API_PORT": ("api_port", int),
            "API_HOST": "api_host",
            "DATABASE_URL": "database_url",
            "REDIS_URL": "redis_url",
            "JWT_SECRET_KEY": "jwt_secret_key",
            "JWT_ALGORITHM": "jwt_algorithm",
            "JWT_EXPIRY_MINUTES": ("jwt_expiry_minutes", int),
            "LOG_LEVEL": "log_level",
            "LOG_FORMAT": "log_format",
            "RATE_LIMIT_REQUESTS": ("rate_limit_requests", lambda x: int(x) if x else None),
            "CACHE_TTL_SUMMARY_KPIS": ("cache_ttl_summary_kpis", int),
            "CACHE_TTL_SEGMENT_DETAILS": ("cache_ttl_segment_details", int),
            "CACHE_TTL_CONTRACTOR_METRICS": ("cache_ttl_contractor_metrics", int),
            "CACHE_TTL_INCIDENT_LISTS": ("cache_ttl_incident_lists", int),
        }

        for env_var, config_attr in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                if isinstance(config_attr, tuple):
                    attr_name, converter = config_attr
                    setattr(self, attr_name, converter(env_value))
                else:
                    setattr(self, env_var.lower() if "_" not in env_var else config_attr, env_value)

        # Handle CORS origins (space or comma-separated)
        cors_str = os.getenv("CORS_ORIGINS")
        if cors_str:
            self.cors_origins = [origin.strip() for origin in cors_str.replace(",", " ").split()]
        elif not self.cors_origins:
            # Default CORS origins
            if self.environment == "development":
                self.cors_origins = ["http://localhost:3000", "http://localhost:8000"]
            else:
                self.cors_origins = []

    def _validate(self) -> None:
        """Validate critical configuration settings."""
        # In production, validate secret key is not the default
        if self.environment == "production":
            if self.jwt_secret_key == "change-me-in-production-with-openssl-rand-hex-32":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default in production. "
                    "Generate with: openssl rand -hex 32"
                )

            if not self.database_url or self.database_url.startswith("postgresql://postgres:password"):
                raise ValueError("DATABASE_URL must be configured in production")

            if not self.redis_url or self.redis_url.startswith("redis://localhost"):
                raise ValueError("REDIS_URL must be configured in production")

        # Validate JWT settings
        if not self.jwt_secret_key or len(self.jwt_secret_key) < 8:
            raise ValueError("JWT_SECRET_KEY must be at least 8 characters")

        if self.jwt_algorithm not in ("HS256", "HS512", "RS256"):
            raise ValueError(f"Invalid JWT algorithm: {self.jwt_algorithm}")

        if self.jwt_expiry_minutes < 1:
            raise ValueError("JWT expiry must be at least 1 minute")

    @classmethod
    def from_env(cls, env_file: Optional[Path] = None) -> APIConfig:
        """Create APIConfig from environment variables.

        Args:
            env_file: Optional path to .env file to load

        Returns:
            APIConfig instance with environment-based settings

        Example:
            >>> config = APIConfig.from_env(Path(".env.production"))
            >>> print(config.database_url)
        """
        if env_file and env_file.exists():
            load_dotenv(env_file)

        return cls()

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            bool: True if environment is production
        """
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            bool: True if environment is development
        """
        return self.environment == "development"

    def get_cache_ttl(self, cache_type: str) -> int:
        """Get cache TTL for specific data type.

        Args:
            cache_type: Type of cache (summary_kpis, segment_details, contractor_metrics, incident_lists)

        Returns:
            int: Cache TTL in seconds

        Raises:
            ValueError: If cache_type is unknown
        """
        ttl_map = {
            "summary_kpis": self.cache_ttl_summary_kpis,
            "segment_details": self.cache_ttl_segment_details,
            "contractor_metrics": self.cache_ttl_contractor_metrics,
            "incident_lists": self.cache_ttl_incident_lists,
        }

        if cache_type not in ttl_map:
            raise ValueError(f"Unknown cache type: {cache_type}")

        return ttl_map[cache_type]

    def to_dict(self) -> dict:
        """Convert configuration to dictionary (excluding secrets).

        Returns:
            dict: Configuration as dictionary with secrets masked
        """
        config_dict = {
            "environment": self.environment,
            "api_version": self.api_version,
            "api_port": self.api_port,
            "api_host": self.api_host,
            "database_url": "***" if self.database_url else None,
            "redis_url": "***" if self.redis_url else None,
            "jwt_algorithm": self.jwt_algorithm,
            "jwt_expiry_minutes": self.jwt_expiry_minutes,
            "log_level": self.log_level,
            "log_format": self.log_format,
            "cors_origins": self.cors_origins,
            "rate_limit_requests": self.rate_limit_requests,
        }
        return config_dict
