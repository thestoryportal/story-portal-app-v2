"""
API Documentation Aggregator

Unified Swagger UI that combines OpenAPI specifications from all 12 service layers.
"""

import logging
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, List
import asyncio

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Platform API Documentation",
    version="1.0.0",
    description="Unified API documentation for all 12 service layers",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service registry
SERVICES = [
    {"name": "L01 Data Layer", "url": "http://l01-data-layer:8001", "port": 8001},
    {"name": "L02 Runtime", "url": "http://l02-runtime:8002", "port": 8002},
    {"name": "L03 Tool Execution", "url": "http://l03-tool-execution:8003", "port": 8003},
    {"name": "L04 Model Gateway", "url": "http://l04-model-gateway:8004", "port": 8004},
    {"name": "L05 Planning", "url": "http://l05-planning:8005", "port": 8005},
    {"name": "L06 Evaluation", "url": "http://l06-evaluation:8006", "port": 8006},
    {"name": "L07 Learning", "url": "http://l07-learning:8007", "port": 8007},
    {"name": "L09 API Gateway", "url": "http://l09-api-gateway:8009", "port": 8009},
    {"name": "L10 Human Interface", "url": "http://l10-human-interface:8010", "port": 8010},
    {"name": "L11 Integration", "url": "http://l11-integration:8011", "port": 8011},
    {"name": "L12 Service Hub", "url": "http://l12-nl-interface:8012", "port": 8012},
]


async def fetch_service_openapi(service: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch OpenAPI spec from a service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{service['url']}/openapi.json")
            response.raise_for_status()
            return {
                "name": service["name"],
                "url": service["url"],
                "port": service["port"],
                "spec": response.json(),
                "available": True,
            }
    except Exception as e:
        logger.warning(f"Failed to fetch OpenAPI spec from {service['name']}: {e}")
        return {
            "name": service["name"],
            "url": service["url"],
            "port": service["port"],
            "spec": None,
            "available": False,
            "error": str(e),
        }


@app.get("/")
async def root():
    """Root endpoint - redirect to docs."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Agentic Platform API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .container {
                max-width: 1200px;
                padding: 2rem;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 3rem;
            }
            .header h1 {
                font-size: 3rem;
                margin-bottom: 1rem;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
            }
            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
            }
            .services-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }
            .service-card {
                background: white;
                border-radius: 1rem;
                padding: 1.5rem;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .service-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(0,0,0,0.3);
            }
            .service-card h3 {
                color: #667eea;
                margin-bottom: 0.5rem;
                font-size: 1.2rem;
            }
            .service-card p {
                color: #6b7280;
                margin-bottom: 1rem;
                font-size: 0.9rem;
            }
            .service-links a {
                display: inline-block;
                margin-right: 0.5rem;
                margin-bottom: 0.5rem;
                padding: 0.5rem 1rem;
                background: #667eea;
                color: white;
                text-decoration: none;
                border-radius: 0.5rem;
                font-size: 0.9rem;
                transition: background 0.3s ease;
            }
            .service-links a:hover {
                background: #5a67d8;
            }
            .global-links {
                text-align: center;
                margin-top: 2rem;
            }
            .global-link {
                display: inline-block;
                margin: 0.5rem;
                padding: 1rem 2rem;
                background: white;
                color: #667eea;
                text-decoration: none;
                border-radius: 0.5rem;
                font-weight: 600;
                font-size: 1.1rem;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
                transition: all 0.3s ease;
            }
            .global-link:hover {
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.3);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Agentic Platform</h1>
                <p>Comprehensive API Documentation</p>
            </div>

            <div class="services-grid">
                <div class="service-card">
                    <h3>L01 Data Layer</h3>
                    <p>Persistent storage and data access</p>
                    <div class="service-links">
                        <a href="http://localhost:8001/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8001/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8001/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L02 Runtime</h3>
                    <p>Task execution engine</p>
                    <div class="service-links">
                        <a href="http://localhost:8002/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8002/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8002/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L03 Tool Execution</h3>
                    <p>Tool integration and execution</p>
                    <div class="service-links">
                        <a href="http://localhost:8003/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8003/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8003/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L04 Model Gateway</h3>
                    <p>LLM provider abstraction</p>
                    <div class="service-links">
                        <a href="http://localhost:8004/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8004/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8004/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L05 Planning</h3>
                    <p>Task planning and orchestration</p>
                    <div class="service-links">
                        <a href="http://localhost:8005/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8005/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8005/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L06 Evaluation</h3>
                    <p>Task evaluation and metrics</p>
                    <div class="service-links">
                        <a href="http://localhost:8006/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8006/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8006/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L07 Learning</h3>
                    <p>Model improvement and learning</p>
                    <div class="service-links">
                        <a href="http://localhost:8007/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8007/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8007/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L09 API Gateway</h3>
                    <p>External API gateway</p>
                    <div class="service-links">
                        <a href="http://localhost:8009/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8009/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8009/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L10 Human Interface</h3>
                    <p>Web UI backend</p>
                    <div class="service-links">
                        <a href="http://localhost:8010/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8010/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8010/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L11 Integration</h3>
                    <p>External service integration</p>
                    <div class="service-links">
                        <a href="http://localhost:8011/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8011/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8011/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>

                <div class="service-card">
                    <h3>L12 Service Hub</h3>
                    <p>Natural language interface</p>
                    <div class="service-links">
                        <a href="http://localhost:8012/docs" target="_blank">Swagger UI</a>
                        <a href="http://localhost:8012/redoc" target="_blank">ReDoc</a>
                        <a href="http://localhost:8012/openapi.json" target="_blank">OpenAPI</a>
                    </div>
                </div>
            </div>

            <div class="global-links">
                <a href="/services" class="global-link">View All Services Status</a>
                <a href="/specs" class="global-link">Download All OpenAPI Specs</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/services")
async def list_services():
    """List all services with their status."""
    # Fetch all service specs in parallel
    tasks = [fetch_service_openapi(service) for service in SERVICES]
    results = await asyncio.gather(*tasks)

    return JSONResponse({
        "total": len(SERVICES),
        "available": sum(1 for r in results if r["available"]),
        "unavailable": sum(1 for r in results if not r["available"]),
        "services": results,
    })


@app.get("/specs")
async def get_all_specs():
    """Get OpenAPI specs from all services."""
    tasks = [fetch_service_openapi(service) for service in SERVICES]
    results = await asyncio.gather(*tasks)

    # Filter only available services
    available_specs = [
        {
            "name": r["name"],
            "url": r["url"],
            "spec": r["spec"],
        }
        for r in results
        if r["available"]
    ]

    return JSONResponse({
        "specs": available_specs,
        "total": len(available_specs),
    })


@app.get("/spec/{service_name}")
async def get_service_spec(service_name: str):
    """Get OpenAPI spec for a specific service."""
    # Find service
    service = next((s for s in SERVICES if service_name in s["url"]), None)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    result = await fetch_service_openapi(service)

    if not result["available"]:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {result.get('error', 'Unknown error')}"
        )

    return JSONResponse(result["spec"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "api-docs-aggregator"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8099)
