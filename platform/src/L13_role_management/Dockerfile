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
COPY src/L13_role_management/requirements.txt* ./L13_role_management/
RUN if [ -f L13_role_management/requirements.txt ]; then pip install --no-cache-dir -r L13_role_management/requirements.txt; fi

# Copy application
COPY src/L13_role_management ./L13_role_management/

# Expose port
EXPOSE 8013

# Set Python path so package imports work (include both /app and /app/src)
ENV PYTHONPATH=/app:/app/src

# Run as a package module
CMD ["uvicorn", "L13_role_management.main:app", "--host", "0.0.0.0", "--port", "8013"]
