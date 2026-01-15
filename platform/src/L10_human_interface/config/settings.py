"""
L10 Human Interface Layer - Configuration Settings

Environment-based configuration using Pydantic BaseSettings.
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class L10Settings(BaseSettings):
    """L10 Human Interface Layer settings."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8010, description="Server port")
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=False, description="Debug mode")

    # Redis configuration
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # PostgreSQL configuration
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="agentic_platform", description="PostgreSQL database")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="postgres", description="PostgreSQL password")

    @property
    def postgres_dsn(self) -> str:
        """Construct PostgreSQL DSN."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Cache TTLs (seconds)
    cache_ttl_agent_list: int = Field(default=60, description="Agent list cache TTL")
    cache_ttl_metrics: int = Field(default=300, description="Metrics cache TTL")
    cache_ttl_agent_detail: int = Field(default=30, description="Agent detail cache TTL")
    cache_ttl_dashboard: int = Field(default=300, description="Dashboard overview cache TTL")

    # Control operation settings
    control_lock_ttl: int = Field(default=30, description="Distributed lock TTL in seconds")
    control_idempotency_ttl: int = Field(default=86400, description="Idempotency TTL (24h)")

    # WebSocket settings
    ws_heartbeat_interval: int = Field(default=30, description="WebSocket heartbeat interval")
    ws_max_connections_per_user: int = Field(default=5, description="Max WebSocket connections per user")
    ws_message_rate_limit: int = Field(default=1000, description="WebSocket message rate limit (msg/sec)")

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = Field(default=5, description="Circuit breaker failure threshold")
    circuit_breaker_timeout_sec: int = Field(default=30, description="Circuit breaker timeout")
    circuit_breaker_success_threshold: int = Field(default=2, description="Circuit breaker success threshold")

    # Authentication
    api_key_header: str = Field(default="X-API-Key", description="API key header name")
    default_tenant_id: str = Field(default="default", description="Default tenant ID")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json or text)")

    class Config:
        env_prefix = "L10_"
        env_file = ".env"
        case_sensitive = False


# Global settings instance (singleton)
_settings: Optional[L10Settings] = None


def get_settings() -> L10Settings:
    """Get or create settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = L10Settings()
    return _settings


def reset_settings():
    """Reset settings (useful for testing)."""
    global _settings
    _settings = None
