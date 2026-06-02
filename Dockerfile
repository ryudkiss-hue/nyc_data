FROM python:3.11-slim

LABEL maintainer="NYC DOT Sidewalk Toolkit"
LABEL description="Full-stack NYC DOT Sidewalk Inspection & Management Toolkit"

# System dependencies for geospatial, PDF, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (for layer caching)
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir poetry-core && \
    pip install --no-cache-dir requests pandas numpy click pyyaml && \
    pip install --no-cache-dir matplotlib openpyxl shapely plotly flask gunicorn streamlit folium

# Copy project files
COPY src/socrata_toolkit/ src/socrata_toolkit/
COPY app/ app/
COPY scripts/ scripts/
COPY tests/ tests/
COPY docs/ docs/
COPY data/ data/
COPY Makefile .
COPY .streamlit/ .streamlit/

# Install the toolkit itself
RUN pip install --no-cache-dir -e .

# Create output directories
RUN mkdir -p outputs/reports outputs/charts outputs/workflows

# Default ports: 8501 (Streamlit), 5000 (Flask API)
EXPOSE 8501 5000

RUN useradd -m appuser
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8501/healthz || exit 1

# Default: launch Streamlit dashboard
CMD ["streamlit", "run", "app/app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true", "--browser.gatherUsageStats=false"]
