"""
OpenAPI Utilities

Provides utilities for generating, customizing, and serving OpenAPI specifications
for all service layers.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, HTMLResponse

logger = logging.getLogger(__name__)


def customize_openapi(
    app: FastAPI,
    title: str,
    version: str,
    description: Optional[str] = None,
    contact: Optional[Dict[str, str]] = None,
    license_info: Optional[Dict[str, str]] = None,
    servers: Optional[List[Dict[str, str]]] = None,
    tags_metadata: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Generate customized OpenAPI schema for FastAPI application.

    Args:
        app: FastAPI application instance
        title: API title
        version: API version
        description: API description
        contact: Contact information
        license_info: License information
        servers: List of servers
        tags_metadata: Tag descriptions

    Returns:
        OpenAPI schema dictionary

    Example:
        from shared import customize_openapi

        app = FastAPI()

        def custom_openapi():
            if app.openapi_schema:
                return app.openapi_schema

            schema = customize_openapi(
                app=app,
                title="L01 Data Layer API",
                version="1.0.0",
                description="Persistent storage and data access layer",
                contact={
                    "name": "Platform Team",
                    "email": "platform@example.com",
                },
                servers=[
                    {"url": "http://localhost:8001", "description": "Development"},
                    {"url": "https://api.example.com", "description": "Production"},
                ],
            )

            app.openapi_schema = schema
            return app.openapi_schema

        app.openapi = custom_openapi
    """
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=title,
        version=version,
        description=description or "",
        routes=app.routes,
    )

    # Add contact information
    if contact:
        openapi_schema["info"]["contact"] = contact

    # Add license information
    if license_info:
        openapi_schema["info"]["license"] = license_info

    # Add servers
    if servers:
        openapi_schema["servers"] = servers

    # Add tags metadata
    if tags_metadata:
        openapi_schema["tags"] = tags_metadata

    # Add security schemes
    openapi_schema["components"] = openapi_schema.get("components", {})
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token in the format: Bearer <token>",
        },
        "apiKey": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication",
        },
    }

    # Add common response schemas
    openapi_schema["components"]["schemas"] = openapi_schema["components"].get("schemas", {})
    openapi_schema["components"]["schemas"].update({
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "error": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "example": "VAL_001"},
                        "message": {"type": "string", "example": "Validation error"},
                        "details": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string"},
                                    "message": {"type": "string"},
                                },
                            },
                        },
                        "request_id": {"type": "string", "format": "uuid"},
                    },
                },
            },
        },
        "HealthResponse": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["healthy", "degraded", "unhealthy"],
                },
                "timestamp": {"type": "string", "format": "date-time"},
                "service": {"type": "string"},
                "version": {"type": "string"},
                "components": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "status": {"type": "string"},
                            "message": {"type": "string"},
                        },
                    },
                },
            },
        },
    })

    logger.info(
        f"Generated OpenAPI schema for {title}",
        extra={
            'event': 'openapi_generated',
            'title': title,
            'version': version,
        }
    )

    return openapi_schema


def setup_swagger_ui(
    app: FastAPI,
    openapi_url: str = "/openapi.json",
    docs_url: str = "/docs",
    redoc_url: str = "/redoc",
    swagger_ui_parameters: Optional[Dict[str, Any]] = None,
):
    """
    Configure Swagger UI and ReDoc for FastAPI application.

    Args:
        app: FastAPI application
        openapi_url: OpenAPI schema endpoint
        docs_url: Swagger UI endpoint
        redoc_url: ReDoc endpoint
        swagger_ui_parameters: Custom Swagger UI parameters

    Example:
        from shared import setup_swagger_ui

        app = FastAPI()

        setup_swagger_ui(
            app,
            swagger_ui_parameters={
                "defaultModelsExpandDepth": -1,
                "displayRequestDuration": True,
                "filter": True,
            }
        )
    """
    app.openapi_url = openapi_url
    app.docs_url = docs_url
    app.redoc_url = redoc_url

    if swagger_ui_parameters:
        app.swagger_ui_parameters = swagger_ui_parameters

    logger.info(
        "Swagger UI configured",
        extra={
            'event': 'swagger_ui_configured',
            'docs_url': docs_url,
            'redoc_url': redoc_url,
        }
    )


def create_openapi_endpoint(
    app: FastAPI,
    include_examples: bool = True,
) -> None:
    """
    Create custom OpenAPI endpoint with additional metadata.

    Args:
        app: FastAPI application
        include_examples: Include example requests/responses

    Example:
        from shared import create_openapi_endpoint

        app = FastAPI()
        create_openapi_endpoint(app, include_examples=True)
    """

    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_schema():
        """Get OpenAPI schema."""
        return JSONResponse(app.openapi())

    @app.get("/api-docs", include_in_schema=False)
    async def get_api_docs():
        """Get API documentation as HTML."""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - API Documentation</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
                }}
                .header {{
                    background: #1f2937;
                    color: white;
                    padding: 2rem;
                    text-align: center;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 2rem;
                }}
                .docs-link {{
                    display: inline-block;
                    margin: 1rem;
                    padding: 1rem 2rem;
                    background: #3b82f6;
                    color: white;
                    text-decoration: none;
                    border-radius: 0.5rem;
                    font-weight: 600;
                }}
                .docs-link:hover {{
                    background: #2563eb;
                }}
                .section {{
                    margin: 2rem 0;
                    padding: 1.5rem;
                    background: #f9fafb;
                    border-radius: 0.5rem;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{app.title}</h1>
                <p>{app.description or "API Documentation"}</p>
            </div>
            <div class="container">
                <div class="section">
                    <h2>Documentation Options</h2>
                    <a href="/docs" class="docs-link">Swagger UI</a>
                    <a href="/redoc" class="docs-link">ReDoc</a>
                    <a href="/openapi.json" class="docs-link">OpenAPI JSON</a>
                </div>
                <div class="section">
                    <h2>Quick Links</h2>
                    <ul>
                        <li><a href="/health/live">Health Check (Live)</a></li>
                        <li><a href="/health/ready">Health Check (Ready)</a></li>
                        <li><a href="/health/startup">Health Check (Startup)</a></li>
                    </ul>
                </div>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


def add_common_responses(
    app: FastAPI,
) -> None:
    """
    Add common response schemas to all endpoints.

    Args:
        app: FastAPI application

    Example:
        from shared import add_common_responses

        app = FastAPI()
        add_common_responses(app)
    """
    # Common responses for all endpoints
    common_responses = {
        400: {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
        401: {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
        403: {
            "description": "Forbidden",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
        500: {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
        503: {
            "description": "Service Unavailable",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                }
            },
        },
    }

    # Add to app
    app.responses = common_responses


def generate_service_openapi(
    service_name: str,
    service_port: int,
    service_description: str,
    version: str = "1.0.0",
) -> Dict[str, Any]:
    """
    Generate standardized OpenAPI configuration for a service.

    Args:
        service_name: Service name (e.g., "l01-data-layer")
        service_port: Service port
        service_description: Service description
        version: API version

    Returns:
        OpenAPI configuration dictionary

    Example:
        config = generate_service_openapi(
            service_name="l01-data-layer",
            service_port=8001,
            service_description="Persistent storage and data access",
        )

        app = FastAPI(**config)
    """
    return {
        "title": f"{service_name.upper()} API",
        "version": version,
        "description": service_description,
        "contact": {
            "name": "Agentic Platform Team",
            "email": "platform@example.com",
            "url": "https://github.com/example/agentic-platform",
        },
        "license_info": {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        "servers": [
            {
                "url": f"http://localhost:{service_port}",
                "description": "Development server",
            },
            {
                "url": f"http://{service_name}:{service_port}",
                "description": "Docker container",
            },
        ],
        "openapi_tags": [
            {
                "name": "health",
                "description": "Health check endpoints",
            },
            {
                "name": "api",
                "description": "Core API endpoints",
            },
        ],
    }


def setup_complete_api_docs(
    app: FastAPI,
    service_name: str,
    service_port: int,
    service_description: str,
    version: str = "1.0.0",
) -> None:
    """
    Complete setup of API documentation for a service.

    This is a convenience function that:
    - Customizes OpenAPI schema
    - Configures Swagger UI
    - Adds common responses
    - Creates custom endpoints

    Args:
        app: FastAPI application
        service_name: Service name
        service_port: Service port
        service_description: Service description
        version: API version

    Example:
        from fastapi import FastAPI
        from shared import setup_complete_api_docs

        app = FastAPI()

        setup_complete_api_docs(
            app=app,
            service_name="l01-data-layer",
            service_port=8001,
            service_description="Persistent storage and data access layer",
        )
    """
    # Generate configuration
    config = generate_service_openapi(
        service_name=service_name,
        service_port=service_port,
        service_description=service_description,
        version=version,
    )

    # Customize OpenAPI
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        schema = customize_openapi(
            app=app,
            title=config["title"],
            version=config["version"],
            description=config["description"],
            contact=config["contact"],
            license_info=config["license_info"],
            servers=config["servers"],
            tags_metadata=config.get("openapi_tags"),
        )

        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # Setup Swagger UI
    setup_swagger_ui(
        app,
        swagger_ui_parameters={
            "defaultModelsExpandDepth": -1,
            "displayRequestDuration": True,
            "filter": True,
            "tryItOutEnabled": True,
        },
    )

    # Add common responses
    add_common_responses(app)

    # Create custom endpoints
    create_openapi_endpoint(app, include_examples=True)

    logger.info(
        f"Complete API documentation setup for {service_name}",
        extra={
            'event': 'api_docs_setup_complete',
            'service': service_name,
            'version': version,
        }
    )
