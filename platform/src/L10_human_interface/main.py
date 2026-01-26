"""
human interface - Placeholder Implementation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import httpx
import asyncio
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="human interface",
    description="Placeholder implementation for human interface",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "l10-human-interface",
        "version": "2.0.0"
    }

@app.get("/health/live")
async def health_live():
    """Liveness probe"""
    return {"status": "alive"}

@app.get("/health/ready")
async def health_ready():
    """Readiness probe"""
    return {"status": "ready"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "human interface",
        "status": "placeholder",
        "message": "Service placeholder - implementation pending"
    }

@app.get("/api/services/health")
async def get_services_health():
    """
    Aggregate real health data from all services
    Returns actual status and latency for each service
    """
    services = [
        {"name": "L01 Data Layer", "url": "http://l01-data-layer:8001", "port": 8001},
        {"name": "L02 Runtime", "url": "http://l02-runtime:8002", "port": 8002},
        {"name": "L03 Tool Execution", "url": "http://l03-tool-execution:8003", "port": 8003},
        {"name": "L04 Model Gateway", "url": "http://l04-model-gateway:8004", "port": 8004},
        {"name": "L05 Planning", "url": "http://l05-planning:8005", "port": 8005},
        {"name": "L09 API Gateway", "url": "http://l09-api-gateway:8009", "port": 8009},
        {"name": "L10 Human Interface", "url": "http://localhost:8010", "port": 8010},
        {"name": "L12 Service Hub", "url": "http://l12-service-hub:8012", "port": 8012},
    ]

    async def check_service_health(service):
        """Check health of a single service"""
        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{service['url']}/health/live")
                latency = int((time.time() - start_time) * 1000)  # Convert to ms

                if response.status_code == 200:
                    return {
                        "name": service["name"],
                        "status": "healthy",
                        "latency": latency
                    }
                else:
                    return {
                        "name": service["name"],
                        "status": "unhealthy",
                        "latency": latency
                    }
        except Exception as e:
            logger.warning(f"Failed to check health for {service['name']}: {e}")
            return {
                "name": service["name"],
                "status": "unhealthy",
                "latency": 0
            }

    # Check all services concurrently
    results = await asyncio.gather(*[check_service_health(service) for service in services])

    return results

@app.on_event("startup")
async def startup():
    logger.info("human interface starting...")
    logger.info("human interface started (placeholder)")

@app.on_event("shutdown")
async def shutdown():
    logger.info("human interface shutting down...")
