"""
L10 Human Interface - Main Entrypoint with Socket.IO

Runs the FastAPI application with Socket.IO support using uvicorn.
"""

import logging
import uvicorn
from .app_socketio import socket_app
from .config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """
    Run the L10 Human Interface server with Socket.IO support.
    """
    settings = get_settings()

    logger.info(f"Starting L10 Human Interface on {settings.host}:{settings.port}")
    logger.info(f"Socket.IO endpoint: ws://{settings.host}:{settings.port}/socket.io/")

    uvicorn.run(
        "src.L10_human_interface.app_socketio:socket_app",
        host=settings.host,
        port=settings.port,
        log_level="info",
        reload=False,  # Disable reload in production
        access_log=True
    )


if __name__ == "__main__":
    main()
