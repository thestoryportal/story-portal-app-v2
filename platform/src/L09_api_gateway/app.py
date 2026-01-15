"""
FastAPI application entrypoint for L09 API Gateway
"""

import uvicorn
from .gateway import APIGateway
from .config import get_settings


# Create gateway instance
gateway = APIGateway()
app = gateway.app


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    await gateway.startup()
    print("API Gateway started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler"""
    await gateway.shutdown()
    print("API Gateway shutdown complete")


def main():
    """Run gateway with uvicorn"""
    settings = get_settings()

    uvicorn.run(
        "src.L09_api_gateway.app:app",
        host=settings.host,
        port=settings.port,
        workers=1,  # Use 1 worker for development
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
