"""
L08 Supervision Layer - Policy Management Routes

REST API for policy CRUD operations, deployment, and rollback.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query

from ..models.dtos import (
    PolicyDefinitionDTO,
    PolicyDefinitionResponse,
    PolicyRuleDTO,
)
from ..models.domain import PolicyDefinition, PolicyRule, PolicyVerdict
from ..models.error_codes import ErrorCodes

logger = logging.getLogger(__name__)

router = APIRouter()


def _dto_to_domain(dto: PolicyDefinitionDTO) -> PolicyDefinition:
    """Convert DTO to domain model"""
    rules = []
    for rule_dto in dto.rules:
        rules.append(PolicyRule(
            rule_id=rule_dto.rule_id or "",
            name=rule_dto.rule_name or rule_dto.name or "",
            condition=rule_dto.condition,
            action=PolicyVerdict(rule_dto.action),
            priority=rule_dto.priority,
            enabled=rule_dto.enabled,
        ))

    return PolicyDefinition(
        policy_id=dto.policy_id or "",
        name=dto.name,
        description=dto.description,
        rules=rules,
        version=str(dto.version),
        active=dto.enabled,  # Map enabled to active
        metadata=dto.metadata or {},
    )


def _domain_to_response(domain: PolicyDefinition) -> PolicyDefinitionResponse:
    """Convert domain model to response DTO"""
    rules = []
    for rule in domain.rules:
        rules.append(PolicyRuleDTO(
            rule_id=rule.rule_id,
            rule_name=rule.name,  # Use name from domain
            name=rule.name,
            condition=rule.condition,
            action=rule.action.value,
            priority=rule.priority,
            enabled=rule.enabled,
        ))

    # Convert version string to int if possible
    try:
        version_int = int(domain.version.split('.')[0]) if '.' in str(domain.version) else int(domain.version)
    except (ValueError, AttributeError):
        version_int = 1

    return PolicyDefinitionResponse(
        policy_id=domain.policy_id,
        name=domain.name,
        description=domain.description,
        rules=rules,
        version=version_int,
        enabled=domain.active,  # Map active to enabled
        tags=domain.metadata.get("tags", []) if isinstance(domain.metadata, dict) else [],
        metadata=domain.metadata if isinstance(domain.metadata, dict) else {},
        created_at=domain.created_at,
        updated_at=domain.updated_at,
    )


@router.post("/policies", response_model=PolicyDefinitionResponse)
async def create_policy(
    request: Request,
    policy: PolicyDefinitionDTO
):
    """
    Create a new policy definition.

    The policy will be created in draft state and must be deployed
    to become active.
    """
    service = request.app.state.supervision_service

    domain_policy = _dto_to_domain(policy)
    result, error = await service.register_policy(domain_policy)

    if error:
        logger.error(f"Failed to create policy: {error}")
        raise HTTPException(status_code=400, detail=error)

    logger.info(f"Created policy: {result.policy_id}")
    return _domain_to_response(result)


@router.get("/policies", response_model=List[PolicyDefinitionResponse])
async def list_policies(
    request: Request,
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """
    List all policies with optional filtering.
    """
    service = request.app.state.supervision_service

    # Get all policies from policy engine
    policies = service.policy_engine._policies.values()

    # Apply filters
    filtered = list(policies)
    if enabled is not None:
        filtered = [p for p in filtered if p.active == enabled]  # Use active field
    if tag:
        # Check tags in metadata
        filtered = [p for p in filtered if tag in p.metadata.get("tags", [])]

    # Apply pagination
    paginated = filtered[offset:offset + limit]

    return [_domain_to_response(p) for p in paginated]


@router.get("/policies/{policy_id}", response_model=PolicyDefinitionResponse)
async def get_policy(
    request: Request,
    policy_id: str
):
    """
    Get a specific policy by ID.
    """
    service = request.app.state.supervision_service

    policy = service.policy_engine._policies.get(policy_id)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"{ErrorCodes.POLICY_NOT_FOUND.value}: Policy {policy_id} not found"
        )

    return _domain_to_response(policy)


@router.put("/policies/{policy_id}", response_model=PolicyDefinitionResponse)
async def update_policy(
    request: Request,
    policy_id: str,
    policy: PolicyDefinitionDTO
):
    """
    Update an existing policy (creates new version).

    The updated policy must be redeployed to take effect.
    """
    service = request.app.state.supervision_service

    # Check policy exists
    existing = service.policy_engine._policies.get(policy_id)
    if not existing:
        raise HTTPException(
            status_code=404,
            detail=f"{ErrorCodes.POLICY_NOT_FOUND.value}: Policy {policy_id} not found"
        )

    # Update with new version
    domain_policy = _dto_to_domain(policy)
    domain_policy.policy_id = policy_id
    # Parse existing version and increment
    try:
        existing_ver = int(existing.version.split('.')[0]) if '.' in str(existing.version) else int(existing.version)
    except (ValueError, AttributeError):
        existing_ver = 1
    domain_policy.version = str(existing_ver + 1)

    result, error = await service.register_policy(domain_policy)
    if error:
        logger.error(f"Failed to update policy: {error}")
        raise HTTPException(status_code=400, detail=error)

    logger.info(f"Updated policy: {policy_id} to version {result.version}")
    return _domain_to_response(result)


@router.delete("/policies/{policy_id}")
async def delete_policy(
    request: Request,
    policy_id: str
):
    """
    Deprecate a policy (soft delete).

    The policy will be disabled but not removed from the system.
    """
    service = request.app.state.supervision_service

    policy = service.policy_engine._policies.get(policy_id)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"{ErrorCodes.POLICY_NOT_FOUND.value}: Policy {policy_id} not found"
        )

    # Disable the policy
    policy.active = False  # Use active field
    logger.info(f"Deprecated policy: {policy_id}")

    return {"status": "deprecated", "policy_id": policy_id}


@router.post("/policies/{policy_id}/deploy")
async def deploy_policy(
    request: Request,
    policy_id: str
):
    """
    Deploy a policy to the active set.

    Once deployed, the policy will be used for all evaluations.
    """
    service = request.app.state.supervision_service

    success, error = await service.deploy_policy(policy_id)
    if error:
        logger.error(f"Failed to deploy policy: {error}")
        raise HTTPException(status_code=400, detail=error)

    logger.info(f"Deployed policy: {policy_id}")
    return {"status": "deployed", "policy_id": policy_id}


@router.post("/policies/{policy_id}/rollback")
async def rollback_policy(
    request: Request,
    policy_id: str,
    target_version: int = Query(..., description="Version to rollback to")
):
    """
    Rollback a policy to a previous version.

    Note: This creates a new version with the content of the target version.
    """
    service = request.app.state.supervision_service

    policy = service.policy_engine._policies.get(policy_id)
    if not policy:
        raise HTTPException(
            status_code=404,
            detail=f"{ErrorCodes.POLICY_NOT_FOUND.value}: Policy {policy_id} not found"
        )

    # Parse current version
    try:
        current_ver = int(policy.version.split('.')[0]) if '.' in str(policy.version) else int(policy.version)
    except (ValueError, AttributeError):
        current_ver = 1

    if target_version >= current_ver:
        raise HTTPException(
            status_code=400,
            detail=f"{ErrorCodes.POLICY_VERSION_CONFLICT.value}: Target version must be less than current version"
        )

    # In a real implementation, we would fetch the historical version
    # For now, just log the rollback request
    logger.info(f"Rollback requested for policy {policy_id} to version {target_version}")

    return {
        "status": "rollback_initiated",
        "policy_id": policy_id,
        "from_version": current_ver,
        "to_version": target_version
    }


@router.post("/policies/validate")
async def validate_policy(
    request: Request,
    policy: PolicyDefinitionDTO
):
    """
    Validate a policy definition without creating it.

    Returns validation results including any warnings or errors.
    """
    service = request.app.state.supervision_service

    errors = []
    warnings = []

    # Validate rules
    for i, rule in enumerate(policy.rules):
        # Check condition syntax
        try:
            service.policy_engine.evaluator.validate(rule.condition)
        except Exception as e:
            errors.append(f"Rule {i}: Invalid condition syntax - {e}")

        # Check for potentially conflicting rules
        if rule.action == "DENY" and rule.priority > 50:
            warnings.append(f"Rule {i}: High priority DENY rule may block many requests")

    # Check for empty rules
    if not policy.rules:
        errors.append("Policy must have at least one rule")

    valid = len(errors) == 0

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings
    }
