FROM python:3.11-slim

# Install curl for health checks and libpq for PostgreSQL client
RUN apt-get update && apt-get install -y curl libpq5 && rm -rf /var/lib/apt/lists/*

# Set working directory to parent for package imports
WORKDIR /app/src

# Install base FastAPI/uvicorn first
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic python-dotenv structlog

# Copy shared clients for inter-layer communication (from platform root)
COPY shared /app/shared

# Copy and install layer-specific requirements if they exist
COPY src/L03_tool_execution/requirements.txt* ./L03_tool_execution/
RUN if [ -f L03_tool_execution/requirements.txt ]; then pip install --no-cache-dir -r L03_tool_execution/requirements.txt; fi

# Copy application
COPY src/L03_tool_execution ./L03_tool_execution/

# Expose port
EXPOSE 8003

# Set Python path so package imports work (include both /app and /app/src)
ENV PYTHONPATH=/app:/app/src

# Run as a package module
CMD ["uvicorn", "L03_tool_execution.main:app", "--host", "0.0.0.0", "--port", "8003"]
