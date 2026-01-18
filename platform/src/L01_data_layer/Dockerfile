FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory to parent for package imports
WORKDIR /app/src

# Install base FastAPI/uvicorn first
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic python-dotenv structlog

# Copy shared library first
COPY shared /app/shared

# Copy and install layer-specific requirements if they exist
COPY src/L01_data_layer/requirements.txt* ./L01_data_layer/
RUN if [ -f L01_data_layer/requirements.txt ]; then pip install --no-cache-dir -r L01_data_layer/requirements.txt; fi

# Copy application
COPY src/L01_data_layer ./L01_data_layer/

# Expose port
EXPOSE 8001

# Set Python path so package imports work
ENV PYTHONPATH=/app/src

# Run as a package module
CMD ["uvicorn", "L01_data_layer.main:app", "--host", "0.0.0.0", "--port", "8001"]
