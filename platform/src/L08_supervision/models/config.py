"""
L08 Supervision Layer - Configuration

Configuration settings for all supervision components.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os


@dataclass
class SupervisionConfiguration:
    """L08 Supervision Layer configuration"""

    # ==========================================================================
    # General Configuration
    # ==========================================================================
    dev_mode: bool = True  # Development mode (uses fallbacks, less strict)

    # ==========================================================================
    # Policy Engine Configuration
    # ==========================================================================
    enable_policy_caching: bool = True
    policy_cache_max_size: int = 1000  # Max cached policies
    policy_cache_ttl_seconds: int = 300
    max_policy_version_history: int = 10
    policy_evaluation_timeout_ms: int = 100  # SLA: <100ms p99
    deny_wins_rule: bool = True  # Deny takes precedence over allow

    # ==========================================================================
    # Constraint Enforcement Configuration
    # ==========================================================================
    enable_constraint_enforcement: bool = True
    rate_limit_window_seconds: int = 60
    allow_on_consensus_fail: bool = False  # Fail-safe vs fail-open
    redis_script_timeout_ms: int = 50

    # ==========================================================================
    # Anomaly Detection Configuration
    # ==========================================================================
    enable_anomaly_detection: bool = True
    anomaly_detection_window_hours: int = 24
    baseline_sample_size: int = 1000
    min_baseline_samples: int = 30
    z_score_threshold: float = 3.0  # 3 sigma
    iqr_multiplier: float = 1.5
    rolling_window_days: int = 30

    # ==========================================================================
    # Escalation Configuration
    # ==========================================================================
    escalation_timeout_seconds: int = 300  # 5 minutes default
    escalation_retry_count: int = 3
    escalation_retry_delay_seconds: int = 2
    enable_escalation_notifications: bool = True
    max_escalation_level: int = 3
    require_mfa_for_approval: bool = True

    # ==========================================================================
    # Audit Trail Configuration
    # ==========================================================================
    enable_immutable_audit: bool = True
    audit_retention_days: int = 365
    audit_signing_enabled: bool = True
    audit_signing_key_id: str = "audit_signer_v1"
    audit_batch_size: int = 100
    audit_flush_interval_seconds: int = 5

    # ==========================================================================
    # Access Control Configuration
    # ==========================================================================
    require_mfa_for_admin: bool = True
    admin_action_logging: bool = True
    session_timeout_minutes: int = 60

    # ==========================================================================
    # Integration Configuration
    # ==========================================================================
    l01_base_url: str = "http://localhost:8001"
    l01_timeout_seconds: int = 30
    l10_base_url: str = "http://localhost:8010"
    l10_timeout_seconds: int = 30
    vault_url: Optional[str] = None  # None = use HMAC fallback
    vault_mount_path: str = "transit"
    redis_url: str = "redis://localhost:6379/0"

    # ==========================================================================
    # Performance Configuration
    # ==========================================================================
    max_concurrent_evaluations: int = 100
    evaluation_queue_size: int = 1000
    metrics_enabled: bool = True
    metrics_prefix: str = "l08_supervision"

    @classmethod
    def from_env(cls) -> "SupervisionConfiguration":
        """Load configuration from environment variables"""
        return cls(
            # General
            dev_mode=os.getenv("L08_DEV_MODE", "true").lower() == "true",

            # Policy engine
            enable_policy_caching=os.getenv("L08_ENABLE_POLICY_CACHING", "true").lower() == "true",
            policy_cache_max_size=int(os.getenv("L08_POLICY_CACHE_MAX_SIZE", "1000")),
            policy_cache_ttl_seconds=int(os.getenv("L08_POLICY_CACHE_TTL_SECONDS", "300")),
            max_policy_version_history=int(os.getenv("L08_MAX_POLICY_VERSION_HISTORY", "10")),
            policy_evaluation_timeout_ms=int(os.getenv("L08_POLICY_EVALUATION_TIMEOUT_MS", "100")),

            # Constraint enforcement
            enable_constraint_enforcement=os.getenv("L08_ENABLE_CONSTRAINT_ENFORCEMENT", "true").lower() == "true",
            rate_limit_window_seconds=int(os.getenv("L08_RATE_LIMIT_WINDOW_SECONDS", "60")),
            allow_on_consensus_fail=os.getenv("L08_ALLOW_ON_CONSENSUS_FAIL", "false").lower() == "true",

            # Anomaly detection
            enable_anomaly_detection=os.getenv("L08_ENABLE_ANOMALY_DETECTION", "true").lower() == "true",
            baseline_sample_size=int(os.getenv("L08_BASELINE_SAMPLE_SIZE", "1000")),
            min_baseline_samples=int(os.getenv("L08_MIN_BASELINE_SAMPLES", "30")),
            z_score_threshold=float(os.getenv("L08_Z_SCORE_THRESHOLD", "3.0")),
            iqr_multiplier=float(os.getenv("L08_IQR_MULTIPLIER", "1.5")),

            # Escalation
            escalation_timeout_seconds=int(os.getenv("L08_ESCALATION_TIMEOUT_SECONDS", "300")),
            escalation_retry_count=int(os.getenv("L08_ESCALATION_RETRY_COUNT", "3")),
            enable_escalation_notifications=os.getenv("L08_ENABLE_ESCALATION_NOTIFICATIONS", "true").lower() == "true",
            max_escalation_level=int(os.getenv("L08_MAX_ESCALATION_LEVEL", "3")),
            require_mfa_for_approval=os.getenv("L08_REQUIRE_MFA_FOR_APPROVAL", "true").lower() == "true",

            # Audit trail
            enable_immutable_audit=os.getenv("L08_ENABLE_IMMUTABLE_AUDIT", "true").lower() == "true",
            audit_retention_days=int(os.getenv("L08_AUDIT_RETENTION_DAYS", "365")),
            audit_signing_enabled=os.getenv("L08_AUDIT_SIGNING_ENABLED", "true").lower() == "true",
            audit_signing_key_id=os.getenv("L08_AUDIT_SIGNING_KEY_ID", "audit_signer_v1"),

            # Access control
            require_mfa_for_admin=os.getenv("L08_REQUIRE_MFA_FOR_ADMIN", "true").lower() == "true",
            admin_action_logging=os.getenv("L08_ADMIN_ACTION_LOGGING", "true").lower() == "true",

            # Integration
            l01_base_url=os.getenv("L01_BASE_URL", "http://localhost:8001"),
            l01_timeout_seconds=int(os.getenv("L01_TIMEOUT_SECONDS", "30")),
            l10_base_url=os.getenv("L10_BASE_URL", "http://localhost:8010"),
            l10_timeout_seconds=int(os.getenv("L10_TIMEOUT_SECONDS", "30")),
            vault_url=os.getenv("VAULT_URL"),
            vault_mount_path=os.getenv("VAULT_MOUNT_PATH", "transit"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),

            # Performance
            max_concurrent_evaluations=int(os.getenv("L08_MAX_CONCURRENT_EVALUATIONS", "100")),
            metrics_enabled=os.getenv("L08_METRICS_ENABLED", "true").lower() == "true",
        )
