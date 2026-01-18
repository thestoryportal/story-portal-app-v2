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
COPY src/L10_human_interface/requirements.txt* ./L10_human_interface/
RUN if [ -f L10_human_interface/requirements.txt ]; then pip install --no-cache-dir -r L10_human_interface/requirements.txt; fi

# Copy application
COPY src/L10_human_interface ./L10_human_interface/

# Expose port
EXPOSE 8010

# Set Python path so package imports work (include both /app and /app/src)
ENV PYTHONPATH=/app:/app/src

# Run as a package module
CMD ["uvicorn", "L10_human_interface.main:app", "--host", "0.0.0.0", "--port", "8010"]
