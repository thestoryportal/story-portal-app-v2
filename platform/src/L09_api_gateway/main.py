"""
L09 API Gateway - Main Entry Point

This module provides the FastAPI application instance for the L09 API Gateway.
The gateway implements:
- Authentication (JWT, API Keys)
- Authorization (RBAC)
- Rate Limiting (Redis-based)
- Request Routing (to backend services)
- CORS Configuration
- Health Checks

For development usage:
    uvicorn L09_api_gateway.main:app --host 0.0.0.0 --port 8009 --reload

For production usage (in Docker):
    uvicorn L09_api_gateway.main:app --host 0.0.0.0 --port 8009
"""

from .gateway import APIGateway

# Create gateway instance
gateway = APIGateway()
app = gateway.app


@app.on_event("startup")
async def startup_event():
    """Initialize gateway services on startup"""
    await gateway.startup()
    print("✅ L09 API Gateway started successfully on port 8009")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up gateway resources on shutdown"""
    await gateway.shutdown()
    print("🛑 L09 API Gateway shutdown complete")


# Export app for uvicorn
__all__ = ["app"]
