"""
L08 Supervision Layer - Health Routes

Health check endpoints for monitoring and orchestration.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/metrics")
async def get_metrics(request: Request):
    """
    Get Prometheus-compatible metrics.

    Returns metrics in Prometheus text format.
    """
    service = getattr(request.app.state, "supervision_service", None)

    if not service:
        return JSONResponse(
            status_code=503,
            content={"error": "Service not initialized"}
        )

    # Gather metrics from all components
    stats = service.get_health_status()

    # Build Prometheus format
    lines = []

    # Policy engine metrics
    policy_stats = stats.get("policy_engine", {})
    lines.append(f"l08_active_policies {policy_stats.get('total_policies', 0)}")
    lines.append(f"l08_policy_evaluations_total {policy_stats.get('total_evaluations', 0)}")
    lines.append(f"l08_policy_cache_hit_ratio {policy_stats.get('cache_hit_ratio', 0)}")

    # Constraint enforcer metrics
    constraint_stats = stats.get("constraint_enforcer", {})
    lines.append(f"l08_active_constraints {constraint_stats.get('total_constraints', 0)}")
    lines.append(f"l08_constraint_checks_total {constraint_stats.get('total_checks', 0)}")
    lines.append(f"l08_constraint_violations_total {constraint_stats.get('total_violations', 0)}")

    # Anomaly detector metrics
    anomaly_stats = stats.get("anomaly_detector", {})
    lines.append(f"l08_metrics_tracked {anomaly_stats.get('metrics_tracked', 0)}")
    lines.append(f"l08_anomalies_detected_total {anomaly_stats.get('total_anomalies', 0)}")

    # Escalation metrics
    escalation_stats = stats.get("escalation_orchestrator", {})
    lines.append(f"l08_pending_escalations {escalation_stats.get('pending_escalations', 0)}")
    lines.append(f"l08_escalations_total {escalation_stats.get('total_escalations', 0)}")
    lines.append(f"l08_escalation_timeouts_total {escalation_stats.get('total_timeouts', 0)}")

    # Audit metrics
    audit_stats = stats.get("audit_manager", {})
    lines.append(f"l08_audit_entries_total {audit_stats.get('total_entries', 0)}")
    lines.append(f"l08_audit_signed_entries {audit_stats.get('signed_entries', 0)}")

    # Compliance metrics
    compliance_stats = stats.get("compliance_monitor", {})
    lines.append(f"l08_entities_tracked {compliance_stats.get('entities_tracked', 0)}")

    return "\n".join(lines)


@router.get("/health/detailed")
async def health_detailed(request: Request) -> Dict[str, Any]:
    """
    Detailed health check with component status.

    Returns health status for each component.
    """
    service = getattr(request.app.state, "supervision_service", None)

    if not service:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "SupervisionService not initialized"
            }
        )

    return await service.health_check()


@router.get("/health/components")
async def health_components(request: Request) -> Dict[str, Any]:
    """
    Get health status of individual components.
    """
    service = getattr(request.app.state, "supervision_service", None)

    if not service:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "components": {}
            }
        )

    health = await service.health_check()
    return {
        "status": health.get("status", "unknown"),
        "components": health.get("components", {}),
    }


@router.get("/stats")
async def get_stats(request: Request) -> Dict[str, Any]:
    """
    Get operational statistics.
    """
    service = getattr(request.app.state, "supervision_service", None)

    if not service:
        return {
            "initialized": False,
            "stats": {}
        }

    return {
        "initialized": service._initialized,
        "stats": service.get_health_status(),
    }


@router.get("/config")
async def get_config(request: Request) -> Dict[str, Any]:
    """
    Get current configuration (non-sensitive values only).
    """
    config = getattr(request.app.state, "config", None)

    if not config:
        return {"configured": False}

    # Return non-sensitive configuration
    return {
        "configured": True,
        "dev_mode": getattr(config, 'dev_mode', config.vault_url is None),  # Dev mode if no vault
        "policy_cache_ttl_seconds": config.policy_cache_ttl_seconds,
        "enable_policy_caching": config.enable_policy_caching,
        "escalation_timeout_seconds": config.escalation_timeout_seconds,
        "max_escalation_level": config.max_escalation_level,
        "z_score_threshold": config.z_score_threshold,
        "iqr_multiplier": config.iqr_multiplier,
        "require_mfa_for_admin": config.require_mfa_for_admin,
    }
