# FastAPI service for NYC DOT operational intelligence
# Phase 4 REST API layer

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    sqlalchemy==2.0.23 \
    psycopg[binary]==3.1.12 \
    redis==5.0.1 \
    pydantic==2.5.0 \
    python-dotenv==1.0.0 \
    PyJWT==2.8.1

# Copy application code
COPY socrata_toolkit /app/socrata_toolkit

# Create non-root user for security
RUN useradd -m -u 1000 apiuser && chown -R apiuser:apiuser /app
USER apiuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Expose API port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "socrata_toolkit.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
