FROM python:3.11-slim

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Set working directory to parent for package imports
WORKDIR /app/src

# Install base FastAPI/uvicorn first
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic python-dotenv structlog

# Copy and install layer-specific requirements if they exist
COPY requirements.txt* ./L05_planning/
RUN if [ -f L05_planning/requirements.txt ]; then pip install --no-cache-dir -r L05_planning/requirements.txt; fi

# Copy application
COPY . ./L05_planning/

# Expose port
EXPOSE 8005

# Set Python path so package imports work
ENV PYTHONPATH=/app/src

# Run as a package module
CMD ["uvicorn", "L05_planning.main:app", "--host", "0.0.0.0", "--port", "8005"]
