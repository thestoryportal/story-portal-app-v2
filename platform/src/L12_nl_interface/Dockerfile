FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory to parent for package imports
WORKDIR /app/src

# Install base FastAPI/uvicorn first
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic python-dotenv structlog

# Copy shared clients for inter-layer communication (from platform root)
COPY shared /app/shared

# Copy and install layer-specific requirements if they exist
COPY src/L12_nl_interface/requirements.txt* ./L12_nl_interface/
RUN if [ -f L12_nl_interface/requirements.txt ]; then pip install --no-cache-dir -r L12_nl_interface/requirements.txt; fi

# Copy application
COPY src/L12_nl_interface ./L12_nl_interface/

# Expose port 8012 (avoid conflict with L05 on 8005)
EXPOSE 8012

# Set Python path so package imports work (include both /app and /app/src)
ENV PYTHONPATH=/app:/app/src

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
  CMD curl -f http://localhost:8012/health || exit 1

# Run as a package module
CMD ["uvicorn", "L12_nl_interface.interfaces.http_api:app", "--host", "0.0.0.0", "--port", "8012"]
