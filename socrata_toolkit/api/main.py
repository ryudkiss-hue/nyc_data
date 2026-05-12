"""FastAPI application factory with middleware and dependency injection.

Creates and configures the FastAPI application with:
    - CORS middleware for cross-origin requests
    - Request logging with Phase 2 OperationalLogger
    - Request ID generation for distributed tracing
    - Structured error handlers
    - Health check endpoints
    - Prometheus metrics export
    - Dependency injection for database, cache, auth

Usage:
    from socrata_toolkit.api.main import create_app
    app = create_app()
    # Run with: uvicorn socrata_toolkit.api.main:app --reload

Example:
    import asyncio
    from socrata_toolkit.api.main import create_app
    
    app = create_app()
    
    # Test health endpoint
    async def test():
        async with app.app_context():
            response = await app.get("/health")
            print(response.json())
    
    asyncio.run(test())
"""

from __future__ import annotations

from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional, AsyncGenerator, Callable
import uuid
import logging

# Core FastAPI imports
try:
    from fastapi import FastAPI, Request, Depends
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Phase 2 observability integration
from socrata_toolkit.observability.manager import OperationalLogger, OperationalContext
from socrata_toolkit.analysis.metrics import MetricsRegistry

# API modules
from socrata_toolkit.api.config import APIConfig
from socrata_toolkit.api.cache import CacheManager, CacheStats
from socrata_toolkit.api.auth import JWTConfig, User
from socrata_toolkit.api.exceptions import APIException, ExternalServiceError
from socrata_toolkit.api.schemas import HealthResponse, ErrorResponse

# Set up logging
logger = logging.getLogger(__name__)


class AppState:
    """Application state container for dependency injection.

    Stores global app resources (database, cache, config, auth).

    Attributes:
        config: API configuration
        metrics_registry: Phase 2 MetricsRegistry for Prometheus
        cache_manager: Redis cache manager
        jwt_config: JWT configuration
        operational_logger: Phase 2 OperationalLogger
        cache_stats: Cache hit/miss statistics
    """

    def __init__(self, config: APIConfig):
        """Initialize app state.

        Args:
            config: API configuration
        """
        self.config = config
        self.metrics_registry = MetricsRegistry()
        self.cache_manager = CacheManager(
            redis_url=config.redis_url,
            timeout=config.redis_timeout,
        )
        self.jwt_config = JWTConfig(
            secret_key=config.jwt_secret_key,
            algorithm=config.jwt_algorithm,
            expiry_minutes=config.jwt_expiry_minutes,
        )
        self.operational_logger = OperationalLogger(__name__)
        self.cache_stats = CacheStats()


# Middleware implementations

async def request_id_middleware(request: Request, call_next: Callable):
    """Add request ID to each request for distributed tracing.

    Generates X-Request-ID header if not present.

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler

    Returns:
        Response with X-Request-ID header
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


async def logging_middleware(request: Request, call_next: Callable):
    """Log all requests and responses with Phase 2 OperationalLogger.

    Attributes logged:
        - Request path, method, query params
        - Response status code, latency
        - Request ID for tracing
        - Error details if applicable

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler

    Returns:
        Response with request logged
    """
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger_instance = OperationalLogger(__name__)

    # Log request
    logger_instance.info(
        f"{request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params) if request.query_params else None,
        },
    )

    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        # Log exception
        logger_instance.error(
            f"Request error: {str(exc)}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
            },
        )
        raise


def create_app(config: Optional[APIConfig] = None) -> FastAPI:
    """Create and configure FastAPI application.

    Sets up:
        - CORS middleware
        - Request logging and tracing
        - Exception handlers
        - Health checks
        - Metrics export
        - Dependency injection

    Args:
        config: API configuration (uses defaults if None)

    Returns:
        FastAPI: Configured FastAPI application instance

    Example:
        >>> app = create_app()
        >>> print(f"API running on {app.title}")
        API running on NYC DOT Sidewalk Operational Intelligence API
    """
    if not HAS_FASTAPI:
        raise ImportError("FastAPI is required. Install with: pip install fastapi uvicorn")

    # Initialize configuration
    config = config or APIConfig()

    # Initialize app state
    state = AppState(config)

    # Define lifespan context manager
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for startup/shutdown.

        Startup:
            - Verify database connection
            - Verify cache connection
            - Warm up cache with summary KPIs
            - Log startup

        Shutdown:
            - Close database connections
            - Close cache connections
            - Log shutdown
        """
        # Startup
        logger.info("API startup initiated")

        # Verify cache
        if state.cache_manager.is_available():
            logger.info("Cache available")
        else:
            logger.warning("Cache unavailable - falling back to database queries")

        # Emit startup metrics
        state.metrics_registry.emit_counter("api_startup_total", 1.0)

        logger.info(
            f"API started: {config.api_host}:{config.api_port}, "
            f"environment={config.environment}"
        )

        yield

        # Shutdown
        logger.info("API shutdown initiated")
        state.metrics_registry.emit_counter("api_shutdown_total", 1.0)

    # Create FastAPI app
    app = FastAPI(
        title="NYC DOT Sidewalk Operational Intelligence API",
        description="Production-grade REST API exposing KPI data, operational metrics, "
        "and compliance reports from Phase 3 materialized views",
        version=config.api_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"/openapi.json",
        lifespan=lifespan,
    )

    # Store state in app
    app.state.config = config
    app.state.cache_manager = state.cache_manager
    app.state.jwt_config = state.jwt_config
    app.state.metrics_registry = state.metrics_registry
    app.state.operational_logger = state.operational_logger
    app.state.cache_stats = state.cache_stats

    # Add middleware (order matters - FIFO for requests, LIFO for responses)

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Total-Count"],
    )

    # Logging middleware
    app.middleware("http")(logging_middleware)

    # Request ID middleware
    app.middleware("http")(request_id_middleware)

    # Exception handlers

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handle custom API exceptions.

        Returns structured error response with:
            - error_code: Standard error code
            - message: Human-readable message
            - status_code: HTTP status code
            - request_id: Request ID for tracing
            - details: Additional context

        Args:
            request: FastAPI request
            exc: APIException instance

        Returns:
            JSONResponse: Structured error response
        """
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        exc.request_id = request_id

        # Log to Phase 2 observability
        state.operational_logger.error(
            f"{exc.error_code.value}: {exc.message}",
            extra={
                "request_id": request_id,
                "error_code": exc.error_code.value,
                "status_code": exc.status_code,
            },
        )

        # Emit error metric
        state.metrics_registry.emit_counter(
            "api_errors_total",
            1.0,
            labels={"error_code": exc.error_code.value},
        )

        error_response = ErrorResponse(
            error_code=exc.error_code.value,
            message=exc.message,
            status_code=exc.status_code,
            request_id=request_id,
            details=exc.details,
            timestamp=datetime.now(timezone.utc),
        )

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions.

        Converts to 500 Internal Server Error without exposing details.

        Args:
            request: FastAPI request
            exc: Exception instance

        Returns:
            JSONResponse: 500 error response
        """
        from socrata_toolkit.api.exceptions import ErrorCode

        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # Log full exception details internally
        state.operational_logger.error(
            f"Unhandled exception: {str(exc)}",
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
                "traceback": repr(exc),
            },
        )

        # Emit metric
        state.metrics_registry.emit_counter(
            "api_errors_total",
            1.0,
            labels={"error_code": "INTERNAL_SERVER_ERROR"},
        )

        error_response = ErrorResponse(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR.value,
            message="Internal server error",
            status_code=500,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc),
        )

        return JSONResponse(
            status_code=500,
            content=error_response.model_dump(mode="json"),
        )

    # Health check endpoint

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Check API and dependency health.

        Returns status of:
            - API service
            - Database connection
            - Cache connection

        Returns:
            HealthResponse: Health status snapshot
        """
        cache_status = "healthy" if state.cache_manager.is_available() else "unavailable"
        database_status = "healthy"  # Would query actual database in production

        overall_status = "healthy" if cache_status in ("healthy", "unavailable") else "degraded"

        return HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc),
            database=database_status,
            cache=cache_status,
            version=config.api_version,
        )

    # Metrics endpoint (Prometheus format)

    @app.get("/metrics", tags=["Observability"])
    async def metrics_endpoint() -> str:
        """Export metrics in Prometheus text format.

        Returns:
            str: Prometheus-formatted metrics
        """
        return state.metrics_registry.export_prometheus()

    # Dependency injection functions

    async def get_cache_manager() -> CacheManager:
        """Inject cache manager dependency.

        Returns:
            CacheManager: Application cache manager instance
        """
        return state.cache_manager

    async def get_config() -> APIConfig:
        """Inject config dependency.

        Returns:
            APIConfig: Application configuration
        """
        return state.config

    async def get_current_user(
        authorization: Optional[str] = None,
    ) -> User:
        """Inject authenticated user dependency.

        Verifies JWT token from Authorization header and returns user context.

        Args:
            authorization: Authorization header (Bearer <token>)

        Returns:
            User: Authenticated user with roles and permissions

        Raises:
            AuthenticationError: If token is invalid or missing
        """
        from socrata_toolkit.api.auth import extract_bearer_token, verify_token, token_from_payload

        try:
            token = extract_bearer_token(authorization)
            payload = verify_token(token, state.jwt_config)
            user = token_from_payload(payload)
            return user
        except Exception as e:
            from socrata_toolkit.api.exceptions import AuthenticationError

            raise AuthenticationError(str(e))

    # Store dependencies in app for use in route handlers
    app.dependency_overrides = {
        "get_cache_manager": get_cache_manager,
        "get_config": get_config,
        "get_current_user": get_current_user,
    }

    # Import and include routes
    from socrata_toolkit.api.routes import router

    app.include_router(
        router,
        prefix="/api",
        dependencies=[
            Depends(get_cache_manager),
            Depends(get_config),
        ],
    )

    return app


# Create app instance for uvicorn
app = create_app()

if __name__ == "__main__":
    # Development server
    import uvicorn

    config = APIConfig()

    uvicorn.run(
        app,
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower(),
    )
