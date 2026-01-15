"""Configuration settings for L12 Natural Language Interface.

This module defines the L12Settings class using Pydantic BaseSettings for
environment variable support and validation.

Environment Variables:
    L12_SERVICE_CATALOG_PATH: Path to service catalog JSON
    L12_LAZY_INITIALIZATION: Enable lazy initialization (default: true)
    L12_SESSION_TTL_SECONDS: Session TTL in seconds (default: 3600)
    L12_CLEANUP_INTERVAL_SECONDS: Cleanup interval in seconds (default: 300)
    L12_FUZZY_THRESHOLD: Fuzzy match threshold 0-1 (default: 0.7)
    L12_USE_SEMANTIC_MATCHING: Enable semantic matching (default: true)
    L12_HTTP_HOST: HTTP API host (default: 0.0.0.0)
    L12_HTTP_PORT: HTTP API port (default: 8005)
    L12_MCP_SOCKET_PATH: MCP socket path (default: /tmp/l12_mcp.sock)
    L12_ENABLE_MEMORY_MONITOR: Enable memory monitoring (default: true)
    L12_MEMORY_LIMIT_MB: Per-session memory limit in MB (default: 500)
    L12_MEMORY_SNAPSHOT_INTERVAL: Memory snapshot interval in seconds (default: 60)
    L12_L01_BASE_URL: L01 Data Layer base URL (default: http://localhost:8002)
    L12_L04_BASE_URL: L04 Model Gateway base URL (default: http://localhost:8004)
    L12_ENABLE_L01_BRIDGE: Enable L01 usage tracking (default: true)
    L12_LOG_LEVEL: Logging level (default: INFO)

Example:
    >>> from L12_nl_interface.config.settings import get_settings
    >>> settings = get_settings()
    >>> print(f"Session TTL: {settings.session_ttl_seconds}s")
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class L12Settings(BaseSettings):
    """Configuration settings for L12 Natural Language Interface.

    Uses Pydantic BaseSettings to load configuration from environment
    variables with the prefix L12_. All settings have sensible defaults.

    Attributes:
        service_catalog_path: Path to service_catalog.json
        lazy_initialization: Enable lazy service initialization
        session_ttl_seconds: Session time-to-live in seconds
        cleanup_interval_seconds: Session cleanup interval in seconds
        fuzzy_threshold: Fuzzy matching threshold (0.0-1.0)
        use_semantic_matching: Enable semantic matching via L04
        http_host: HTTP API host
        http_port: HTTP API port
        mcp_socket_path: MCP server socket path
        enable_memory_monitor: Enable memory monitoring
        memory_limit_mb: Per-session memory limit in MB
        memory_snapshot_interval: Memory snapshot interval in seconds
        l01_base_url: L01 Data Layer base URL
        l04_base_url: L04 Model Gateway base URL
        enable_l01_bridge: Enable L01 usage tracking
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    model_config = SettingsConfigDict(
        env_prefix="L12_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service Factory Configuration
    service_catalog_path: str = Field(
        default="data/service_catalog.json",
        description="Path to service catalog JSON file (relative to L12 root)",
    )
    lazy_initialization: bool = Field(
        default=True,
        description="Enable lazy initialization of services on first use",
    )

    # Session Management Configuration
    session_ttl_seconds: int = Field(
        default=3600,
        description="Session time-to-live in seconds (default: 1 hour)",
        gt=0,
        le=86400,  # Max 24 hours
    )
    cleanup_interval_seconds: int = Field(
        default=300,
        description="Interval for cleanup task in seconds (default: 5 minutes)",
        gt=0,
        le=3600,  # Max 1 hour
    )

    # Matching Configuration
    fuzzy_threshold: float = Field(
        default=0.7,
        description="Fuzzy matching threshold (0.0-1.0, higher = stricter)",
        ge=0.0,
        le=1.0,
    )
    use_semantic_matching: bool = Field(
        default=True,
        description="Enable semantic matching using L04 embeddings",
    )

    # HTTP API Configuration
    http_host: str = Field(
        default="0.0.0.0",
        description="HTTP API host address",
    )
    http_port: int = Field(
        default=8005,
        description="HTTP API port number",
        gt=0,
        lt=65536,
    )

    # MCP Server Configuration
    mcp_socket_path: str = Field(
        default="/tmp/l12_mcp.sock",
        description="MCP server Unix socket path",
    )

    # Memory Monitor Configuration
    enable_memory_monitor: bool = Field(
        default=True,
        description="Enable memory monitoring and leak detection",
    )
    memory_limit_mb: float = Field(
        default=500.0,
        description="Per-session memory limit in megabytes",
        gt=0.0,
        le=4096.0,  # Max 4GB
    )
    memory_snapshot_interval: int = Field(
        default=60,
        description="Memory snapshot interval in seconds",
        gt=0,
        le=3600,  # Max 1 hour
    )

    # External Service URLs
    l01_base_url: str = Field(
        default="http://localhost:8002",
        description="L01 Data Layer base URL for usage tracking",
    )
    l04_base_url: str = Field(
        default="http://localhost:8004",
        description="L04 Model Gateway base URL for semantic matching",
    )

    # L01 Bridge Configuration
    enable_l01_bridge: bool = Field(
        default=True,
        description="Enable L01 usage tracking bridge",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    @field_validator("service_catalog_path")
    @classmethod
    def validate_catalog_path(cls, v: str) -> str:
        """Validate service catalog path format.

        Args:
            v: Path string to validate

        Returns:
            Validated path string

        Raises:
            ValueError: If path is invalid
        """
        if not v:
            raise ValueError("service_catalog_path cannot be empty")

        # Convert to Path for validation
        path = Path(v)

        # If absolute path, check it exists
        if path.is_absolute() and not path.exists():
            logger.warning(f"Absolute catalog path does not exist: {v}")

        return v

    @field_validator("http_host")
    @classmethod
    def validate_http_host(cls, v: str) -> str:
        """Validate HTTP host format.

        Args:
            v: Host string to validate

        Returns:
            Validated host string

        Raises:
            ValueError: If host is invalid
        """
        if not v:
            raise ValueError("http_host cannot be empty")

        # Basic validation - allow localhost, 0.0.0.0, IP addresses, hostnames
        valid_hosts = ["localhost", "0.0.0.0", "127.0.0.1"]
        if v not in valid_hosts and not v.replace(".", "").replace(":", "").isalnum():
            raise ValueError(f"Invalid http_host format: {v}")

        return v

    @field_validator("mcp_socket_path")
    @classmethod
    def validate_socket_path(cls, v: str) -> str:
        """Validate MCP socket path format.

        Args:
            v: Socket path to validate

        Returns:
            Validated socket path

        Raises:
            ValueError: If path is invalid
        """
        if not v:
            raise ValueError("mcp_socket_path cannot be empty")

        # Ensure it ends with .sock
        if not v.endswith(".sock"):
            logger.warning(f"MCP socket path should end with .sock: {v}")

        return v

    @field_validator("l01_base_url", "l04_base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate external service base URLs.

        Args:
            v: URL to validate

        Returns:
            Validated URL

        Raises:
            ValueError: If URL is invalid
        """
        if not v:
            raise ValueError("Base URL cannot be empty")

        # Must start with http:// or https://
        if not v.startswith(("http://", "https://")):
            raise ValueError(f"Base URL must start with http:// or https://: {v}")

        # Remove trailing slash for consistency
        if v.endswith("/"):
            v = v.rstrip("/")

        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level.

        Args:
            v: Log level to validate

        Returns:
            Validated log level (uppercase)

        Raises:
            ValueError: If log level is invalid
        """
        v_upper = v.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        if v_upper not in valid_levels:
            raise ValueError(
                f"Invalid log_level '{v}'. Must be one of: {', '.join(valid_levels)}"
            )

        return v_upper

    def get_catalog_path_absolute(self) -> Path:
        """Get absolute path to service catalog.

        If service_catalog_path is relative, it's resolved relative to
        the L12_nl_interface module directory.

        Returns:
            Absolute Path to service catalog

        Example:
            >>> settings = get_settings()
            >>> catalog_path = settings.get_catalog_path_absolute()
            >>> print(catalog_path)
        """
        path = Path(self.service_catalog_path)

        if path.is_absolute():
            return path

        # Resolve relative to L12 module directory
        # Assuming this file is in src/L12_nl_interface/config/settings.py
        l12_root = Path(__file__).parent.parent
        return l12_root / path

    def configure_logging(self) -> None:
        """Configure Python logging based on log_level setting.

        Example:
            >>> settings = get_settings()
            >>> settings.configure_logging()
        """
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logger.info(f"Logging configured with level: {self.log_level}")

    def validate_external_dependencies(self) -> dict[str, bool]:
        """Check availability of external dependencies.

        This performs basic connectivity checks to L01 and L04 services.

        Returns:
            Dict with availability status for each dependency

        Example:
            >>> settings = get_settings()
            >>> status = settings.validate_external_dependencies()
            >>> if not status['l01_available']:
            ...     print("Warning: L01 unavailable")
        """
        import httpx

        results = {
            "l01_available": False,
            "l04_available": False,
        }

        # Check L01 (if bridge enabled)
        if self.enable_l01_bridge:
            try:
                response = httpx.get(f"{self.l01_base_url}/health", timeout=2.0)
                results["l01_available"] = response.status_code == 200
            except Exception as e:
                logger.warning(f"L01 health check failed: {e}")

        # Check L04 (if semantic matching enabled)
        if self.use_semantic_matching:
            try:
                response = httpx.get(f"{self.l04_base_url}/health", timeout=2.0)
                results["l04_available"] = response.status_code == 200
            except Exception as e:
                logger.warning(f"L04 health check failed: {e}")

        return results

    def summary(self) -> dict[str, any]:
        """Get summary of all settings.

        Returns:
            Dict with all settings values

        Example:
            >>> settings = get_settings()
            >>> print(settings.summary())
        """
        return {
            "service_catalog_path": self.service_catalog_path,
            "lazy_initialization": self.lazy_initialization,
            "session_ttl_seconds": self.session_ttl_seconds,
            "cleanup_interval_seconds": self.cleanup_interval_seconds,
            "fuzzy_threshold": self.fuzzy_threshold,
            "use_semantic_matching": self.use_semantic_matching,
            "http_host": self.http_host,
            "http_port": self.http_port,
            "mcp_socket_path": self.mcp_socket_path,
            "enable_memory_monitor": self.enable_memory_monitor,
            "memory_limit_mb": self.memory_limit_mb,
            "memory_snapshot_interval": self.memory_snapshot_interval,
            "l01_base_url": self.l01_base_url,
            "l04_base_url": self.l04_base_url,
            "enable_l01_bridge": self.enable_l01_bridge,
            "log_level": self.log_level,
        }


# Global singleton instance (lazy-loaded)
_settings_instance: Optional[L12Settings] = None


def get_settings() -> L12Settings:
    """Get global L12Settings singleton instance.

    Returns:
        L12Settings instance

    Example:
        >>> from L12_nl_interface.config.settings import get_settings
        >>> settings = get_settings()
        >>> print(f"HTTP port: {settings.http_port}")
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = L12Settings()
        logger.info("L12Settings initialized from environment")
    return _settings_instance


def reset_settings() -> None:
    """Reset global settings instance (primarily for testing).

    Example:
        >>> reset_settings()  # Force reload from environment
        >>> settings = get_settings()  # Gets fresh instance
    """
    global _settings_instance
    _settings_instance = None
    logger.debug("L12Settings instance reset")
