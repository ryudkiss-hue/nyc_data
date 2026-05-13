# Use the modern, slim version of Debian Bookworm for smaller size
FROM python:3.11-slim-bookworm

# Set environment variables to optimize Python for Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install ONLY the bare minimum OS libraries required for spatial libraries (Shapely/GeoPandas)
# We immediately clean up the apt caches in the same RUN layer to prevent image bloat.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libspatialindex-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt .

# Remove heavy/unnecessary dependencies from requirements before installing
# (Removes kaleido for PDF exports, and any heavy quantum/3D rendering libs)
RUN sed -i '/kaleido/d' requirements.txt && \
    sed -i '/qiskit/d' requirements.txt && \
    sed -i '/vtk/d' requirements.txt && \
    pip install -r requirements.txt

# Copy the rest of the application code
# Make sure you have a .dockerignore file that excludes .venv, __pycache__, and local .db files!
COPY . .

# Expose the port NiceGUI/FastAPI uses
EXPOSE 8000

# Run the application
# Using uvicorn directly is generally leaner and recommended for production
CMD ["uvicorn", "socrata_toolkit.api:app", "--host", "0.0.0.0", "--port", "8000"]