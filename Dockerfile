FROM python:3.11-slim

LABEL maintainer="NYC DOT Sidewalk Toolkit"
LABEL description="Full-stack NYC DOT Sidewalk Inspection & Management Toolkit"

# System dependencies for geospatial, PDF, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev libgdal-dev libgeos-dev libproj-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY socrata_toolkit/ socrata_toolkit/
COPY scripts/ scripts/
COPY sql/ sql/
COPY tests/ tests/
COPY docs/ docs/
COPY Makefile .

RUN pip install --no-cache-dir -e ".[all]" && \
    pip install --no-cache-dir flask plotly gunicorn

# Default ports: 8501 (Streamlit), 5000 (Flask API)
EXPOSE 8501 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import socrata_toolkit; print('ok')" || exit 1

# Default: launch Streamlit dashboard
CMD ["streamlit", "run", "socrata_toolkit/dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
