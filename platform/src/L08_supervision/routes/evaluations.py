"""
L08 Supervision Layer - Policy Evaluation Routes

REST API for evaluating requests against policies.
"""

import logging
import time
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..models.domain import PolicyVerdict
from ..models.error_codes import ErrorCodes

logger = logging.getLogger(__name__)

router = APIRouter()


class EvaluationRequest(BaseModel):
    """Request for policy evaluation"""
    request_id: Optional[str] = Field(None, description="Optional request tracking ID")
    agent_id: str = Field(..., description="Agent making the request")
    operation: str = Field(..., description="Operation being performed")
    resource: Dict[str, Any] = Field(..., description="Resource being accessed")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")


class EvaluationResponse(BaseModel):
    """Response from policy evaluation"""
    request_id: Optional[str]
    decision_id: str
    verdict: str
    confidence: float
    explanation: str
    matched_rules: list
    evaluation_latency_ms: float
    escalation: Optional[Dict[str, Any]] = None
    audit_event_id: Optional[str] = None


class ConstraintCheckRequest(BaseModel):
    """Request for constraint check"""
    agent_id: str
    constraint_id: str
    requested: int = Field(default=1, ge=1)


class ConstraintCheckResponse(BaseModel):
    """Response from constraint check"""
    allowed: bool
    remaining: Optional[int] = None
    error: Optional[str] = None


class AnomalyReportRequest(BaseModel):
    """Request to record a metric observation"""
    agent_id: str
    metric_name: str
    value: float
    detect: bool = Field(default=True, description="Whether to run anomaly detection")


class AnomalyReportResponse(BaseModel):
    """Response from anomaly reporting"""
    recorded: bool
    anomalies_detected: int
    anomalies: list
    error: Optional[str] = None


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_request(
    request: Request,
    evaluation: EvaluationRequest
):
    """
    Evaluate an agent request against policies and constraints.

    This is the main entry point for supervision checks. It:
    1. Evaluates policies (deny-wins rule)
    2. Checks applicable constraints
    3. Creates escalation if needed
    4. Records to audit trail

    Returns:
        Policy decision with verdict (ALLOW, DENY, or ESCALATE)
    """
    service = request.app.state.supervision_service
    start_time = time.perf_counter()

    try:
        decision, error = await service.evaluate_request(
            agent_id=evaluation.agent_id,
            operation=evaluation.operation,
            resource=evaluation.resource,
            context=evaluation.context,
        )

        if error:
            logger.error(f"Evaluation failed: {error}")
            raise HTTPException(status_code=400, detail=error)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Build response
        response = EvaluationResponse(
            request_id=evaluation.request_id,
            decision_id=decision.decision_id,
            verdict=decision.verdict.value,
            confidence=decision.confidence,
            explanation=decision.explanation,
            matched_rules=decision.matched_rules,
            evaluation_latency_ms=latency_ms,
        )

        # Include escalation info if present
        if "escalation" in decision.request_context:
            response.escalation = decision.request_context["escalation"]

        logger.info(
            f"Evaluated request: agent={evaluation.agent_id}, "
            f"operation={evaluation.operation}, verdict={decision.verdict.value}, "
            f"latency={latency_ms:.2f}ms"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Evaluation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.POLICY_EVALUATION_FAILED.value}: {str(e)}"
        )


@router.post("/constraints/check", response_model=ConstraintCheckResponse)
async def check_constraint(
    request: Request,
    check: ConstraintCheckRequest
):
    """
    Check a rate limit or quota constraint.

    Returns whether the request is allowed and remaining capacity.
    """
    service = request.app.state.supervision_service

    try:
        allowed, error = await service.check_rate_limit(
            agent_id=check.agent_id,
            constraint_id=check.constraint_id,
            requested=check.requested,
        )

        return ConstraintCheckResponse(
            allowed=allowed,
            error=error,
        )

    except Exception as e:
        logger.exception(f"Constraint check error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.CONSTRAINT_VIOLATION.value}: {str(e)}"
        )


@router.post("/metrics/report", response_model=AnomalyReportResponse)
async def report_metric(
    request: Request,
    report: AnomalyReportRequest
):
    """
    Record a metric observation and optionally detect anomalies.

    Use this endpoint to report agent metrics for baseline building
    and anomaly detection.
    """
    service = request.app.state.supervision_service

    try:
        anomalies, error = await service.record_metric(
            agent_id=report.agent_id,
            metric_name=report.metric_name,
            value=report.value,
            detect=report.detect,
        )

        anomaly_dicts = []
        for anomaly in anomalies:
            anomaly_dicts.append({
                "anomaly_id": anomaly.anomaly_id,
                "metric_name": anomaly.metric_name,
                "severity": anomaly.severity.value,
                "baseline_value": anomaly.baseline_value,
                "observed_value": anomaly.observed_value,
                "z_score": anomaly.z_score,
                "description": anomaly.description,
            })

        return AnomalyReportResponse(
            recorded=True,
            anomalies_detected=len(anomalies),
            anomalies=anomaly_dicts,
            error=error,
        )

    except Exception as e:
        logger.exception(f"Metric report error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.ANOMALY_DETECTION_FAILED.value}: {str(e)}"
        )


@router.post("/baselines/{agent_id}/{metric_name}")
async def set_baseline(
    request: Request,
    agent_id: str,
    metric_name: str,
    values: list[float]
):
    """
    Set baseline statistics from historical values.

    Provide a list of historical observations to establish the baseline
    for anomaly detection.
    """
    service = request.app.state.supervision_service

    if len(values) < 10:
        raise HTTPException(
            status_code=400,
            detail=f"{ErrorCodes.INSUFFICIENT_BASELINE_DATA.value}: Need at least 10 values for baseline"
        )

    success, error = await service.set_baseline(
        agent_id=agent_id,
        metric_name=metric_name,
        values=values,
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    return {
        "status": "baseline_set",
        "agent_id": agent_id,
        "metric_name": metric_name,
        "sample_count": len(values),
    }


@router.get("/compliance/{agent_id}")
async def get_compliance_status(
    request: Request,
    agent_id: str
):
    """
    Get compliance status for an agent.

    Returns compliance score, risk level, and recommendations.
    """
    service = request.app.state.supervision_service

    try:
        status = await service.get_compliance_status(agent_id)
        return status

    except Exception as e:
        logger.exception(f"Compliance status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.INTERNAL_ERROR.value}: {str(e)}"
        )


@router.get("/compliance/report")
async def get_compliance_report(
    request: Request,
    entity_id: Optional[str] = None,
    period_hours: int = 24
):
    """
    Generate a compliance report.

    If entity_id is provided, generates report for that entity.
    Otherwise, generates system-wide report.
    """
    service = request.app.state.supervision_service

    try:
        report = await service.get_compliance_report(
            entity_id=entity_id,
            period_hours=period_hours,
        )
        return report

    except Exception as e:
        logger.exception(f"Compliance report error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"{ErrorCodes.INTERNAL_ERROR.value}: {str(e)}"
        )
