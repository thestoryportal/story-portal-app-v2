"""
Gateway configuration settings
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class GatewaySettings(BaseSettings):
    """API Gateway configuration"""

    # Server
    host: str = Field(default="0.0.0.0", env="GATEWAY_HOST")
    port: int = Field(default=8000, env="GATEWAY_PORT")
    workers: int = Field(default=4, env="GATEWAY_WORKERS")

    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")

    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")

    # PostgreSQL (L01)
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="l01_data_layer", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")

    # Authentication
    jwks_url: Optional[str] = Field(default=None, env="JWKS_URL")
    api_key_salt: str = Field(default="default_salt", env="API_KEY_SALT")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_fallback_enabled: bool = Field(
        default=True, env="RATE_LIMIT_FALLBACK_ENABLED"
    )

    # Idempotency
    idempotency_ttl_seconds: int = Field(
        default=86400, env="IDEMPOTENCY_TTL_SECONDS"
    )

    # Request Validation
    max_body_size: int = Field(default=10 * 1024 * 1024, env="MAX_BODY_SIZE")
    max_header_count: int = Field(default=100, env="MAX_HEADER_COUNT")
    max_header_size: int = Field(default=16 * 1024, env="MAX_HEADER_SIZE")
    max_query_length: int = Field(default=4096, env="MAX_QUERY_LENGTH")

    # Circuit Breaker
    circuit_breaker_error_threshold: float = Field(
        default=0.5, env="CIRCUIT_BREAKER_ERROR_THRESHOLD"
    )
    circuit_breaker_window_ms: int = Field(
        default=60000, env="CIRCUIT_BREAKER_WINDOW_MS"
    )
    circuit_breaker_min_requests: int = Field(
        default=10, env="CIRCUIT_BREAKER_MIN_REQUESTS"
    )
    circuit_breaker_open_timeout_ms: int = Field(
        default=60000, env="CIRCUIT_BREAKER_OPEN_TIMEOUT_MS"
    )
    circuit_breaker_ramp_up_duration_ms: int = Field(
        default=300000, env="CIRCUIT_BREAKER_RAMP_UP_DURATION_MS"
    )

    # Timeouts
    default_timeout_ms: int = Field(default=60000, env="DEFAULT_TIMEOUT_MS")
    max_timeout_ms: int = Field(default=120000, env="MAX_TIMEOUT_MS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_sampling_rate: float = Field(default=0.01, env="LOG_SAMPLING_RATE")

    # Metrics
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
_settings: Optional[GatewaySettings] = None


def get_settings() -> GatewaySettings:
    """Get global settings instance"""
    global _settings
    if _settings is None:
        _settings = GatewaySettings()
    return _settings
