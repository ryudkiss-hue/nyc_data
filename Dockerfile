# Stage 1: Base - System dependencies and common environment
FROM python:3.11-slim AS base

LABEL maintainer="NYC DOT Socrata Toolkit"
LABEL description="Unified NYC DOT Socrata Toolkit — Municipal Data Ingestion & Analytics"

# System dependencies for geospatial, PDF, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgdal-dev libgeos-dev libproj-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (for layer caching)
COPY pyproject.toml README.md ./
COPY requirements.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi

# Pre-install core dependencies to speed up builds
RUN pip install --no-cache-dir poetry-core requests pandas numpy click pyyaml matplotlib openpyxl shapely plotly flask gunicorn streamlit folium

# Copy project files
COPY . .

# Install the toolkit in editable mode for path resolution
RUN pip install -e .

# Create common directories
RUN mkdir -p data/local_db outputs/reports outputs/charts outputs/workflows .cache/socrata_data .cache/serverside_data

ENV PYTHONUNBUFFERED=1
RUN useradd -m appuser
USER appuser

# Stage 2: Analyst - Autopilot runner
FROM base AS analyst
LABEL description="Analyst autopilot runner and setup wizard"
ENV ANALYST_PROFILE=config/analyst_profile.yaml
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
CMD ["python", "-m", "socrata_toolkit.core.cli", "analyst", "run"]

# Stage 3: Mission - Manhattan Mission Control (Streamlit)
FROM base AS mission
LABEL description="Manhattan Mission Control (Streamlit)"
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8501/healthz || exit 1
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

# Stage 4: Turbo - Dash platform
FROM base AS turbo
LABEL description="Turbo-Stream Dash Platform — NYC DOT Socrata Toolkit"
USER root
# Dash specific deps from Dockerfile.turbo
RUN pip install --no-cache-dir \
    dash==4.2.0 \
    dash-extensions==2.0.5 \
    dash-iconify==0.1.2 \
    dash-mantine-components==2.7.0 \
    dash-ag-grid==35.2.0
USER appuser
EXPOSE 8012
ENV PORT=8012
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8012/api/v1/health || exit 1
CMD ["uvicorn", "app.dash_app:server", "--host", "0.0.0.0", "--port", "8012", "--workers", "4"]
