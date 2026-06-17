"""
Cloud Run deployment entry point.

Unified application that serves:
- Dash Mission Control (http://localhost:8080/)
- FastAPI backend (http://localhost:8080/api/)

Uses MotherDuck as primary cloud platform with DuckDB fallback.
Automatically detects and uses available platform.

To run locally:
    python -m uvicorn app.cloud_run:app --reload --port 8080

To run via Docker:
    docker build -t nyc-toolkit -f Dockerfile.cloudbuild .
    docker run -p 8080:8080 \
      -e MOTHERDUCK_TOKEN=your_token \
      -e ANTHROPIC_API_KEY=your_key \
      nyc-toolkit
"""

import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Dash app
from app.dash_app import app as dash_app

# Import platform utilities
from socrata_toolkit.platform import (
    get_connection,
    get_platform_name,
    is_motherduck,
)

# Create FastAPI app
app = FastAPI(
    title="NYC DOT Sidewalk Toolkit",
    description="Multi-platform analytics for 26 NYC Open Data datasets",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API Routes
# ============================================================================


@app.get("/")
async def root():
    """Redirect to Dash dashboard."""
    return JSONResponse({"message": "NYC Sidewalk Toolkit", "visit": "/dash/"})


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    try:
        conn = get_connection()
        platform = get_platform_name()

        # Test connection with a simple query
        result = conn.execute("SELECT 1 AS test").fetchall()

        return {
            "status": "healthy",
            "platform": platform,
            "connection": "OK",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }, 503


@app.get("/api/platform")
async def get_platform():
    """Get active platform (MotherDuck or DuckDB)."""
    try:
        platform = get_platform_name()
        is_md = is_motherduck()

        return {
            "platform": platform,
            "is_motherduck": is_md,
            "motherduck_token_set": bool(os.getenv("MOTHERDUCK_TOKEN")),
            "duckdb_path": os.getenv("DUCKDB_PATH", "./data/local_db/nyc_mission_control.duckdb"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/datasets")
async def list_datasets():
    """List all 57 datasets with row counts."""
    try:
        conn = get_connection()

        # Get all tables
        query = """
            SELECT table_name, row_count
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY row_count DESC
        """

        results = conn.execute(query).fetchall()

        datasets = [
            {"name": row[0], "rows": row[1]}
            for row in results
        ]

        return {
            "count": len(datasets),
            "datasets": datasets,
            "platform": get_platform_name(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def execute_query(query_obj: dict):
    """Execute SQL query and return results."""
    try:
        sql = query_obj.get("query")
        platform = query_obj.get("platform")

        if not sql:
            raise ValueError("Query parameter required")

        conn = get_connection(platform=platform)
        df = conn.execute(sql).df()

        return {
            "rows": len(df),
            "platform": get_platform_name(),
            "data": df.head(100).to_dict(orient="records"),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/dataset/{dataset_name}/stats")
async def dataset_stats(dataset_name: str):
    """Get statistics for a specific dataset."""
    try:
        conn = get_connection()

        # Validate table name (prevent SQL injection)
        valid_tables = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        valid_names = [t[0] for t in valid_tables]

        if dataset_name not in valid_names:
            raise ValueError(f"Dataset '{dataset_name}' not found")

        # Get stats
        stats = conn.execute(f"""
            SELECT
                COUNT(*) as row_count,
                COUNT(DISTINCT 1) as distinct_count
            FROM "{dataset_name}"
        """).fetchone()

        return {
            "dataset": dataset_name,
            "rows": stats[0] if stats else 0,
            "platform": get_platform_name(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Dash Integration
# ============================================================================

# Mount Dash app at /dash/
app.mount("/dash", dash_app.server)

# ============================================================================
# Startup/Shutdown Events
# ============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    logger.info("Starting NYC Sidewalk Toolkit")
    try:
        conn = get_connection()
        platform = get_platform_name()
        logger.info(f"✓ Connected to {platform}")

        # Log available datasets
        tables = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='main'"
        ).fetchone()
        logger.info(f"✓ {tables[0]} datasets available")
    except Exception as e:
        logger.error(f"Startup error: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down NYC Sidewalk Toolkit")


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))

    logger.info(f"Starting server on port {port}")
    logger.info("Dash at: http://localhost:{port}/dash/")
    logger.info("API at: http://localhost:{port}/api/")

    uvicorn.run(
        "app.cloud_run:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )


