"""
Authorization Engine - RBAC, OAuth Scopes, ABAC
"""

from typing import List, Optional
from ..models import ConsumerProfile, RouteDefinition, RequestContext
from ..errors import ErrorCode, AuthorizationError


class AuthorizationEngine:
    """
    Enforces access control policies:
    - Role-Based Access Control (RBAC)
    - OAuth 2.0 Scopes
    - Attribute-Based Access Control (ABAC)
    """

    def __init__(self, supervision_client=None):
        """
        Args:
            supervision_client: L08 Supervision client for ABAC policies
        """
        self.supervision_client = supervision_client

    async def authorize(
        self,
        context: RequestContext,
        consumer: ConsumerProfile,
        route: RouteDefinition,
    ) -> bool:
        """
        Authorize request

        Args:
            context: Request context
            consumer: Consumer profile
            route: Route definition

        Returns:
            True if authorized

        Raises:
            AuthorizationError: If not authorized
        """
        # Check consumer status
        if consumer.status.value != "active":
            raise AuthorizationError(
                ErrorCode.E9202,
                f"Consumer suspended: {consumer.status}",
                details={"consumer_id": consumer.consumer_id},
            )

        # Check tenant context
        if context.tenant_id and context.tenant_id != consumer.tenant_id:
            raise AuthorizationError(
                ErrorCode.E9205,
                "Cross-tenant access attempt",
                details={
                    "consumer_tenant": consumer.tenant_id,
                    "request_tenant": context.tenant_id,
                },
            )

        # Check OAuth scopes
        if route.required_scopes:
            if not self._check_scopes(consumer.oauth_scopes, route.required_scopes):
                raise AuthorizationError(
                    ErrorCode.E9207,
                    "Insufficient OAuth scopes",
                    details={
                        "required": route.required_scopes,
                        "provided": consumer.oauth_scopes,
                    },
                )

        # Check RBAC roles
        if route.required_roles:
            if not self._check_roles(consumer.roles, route.required_roles):
                raise AuthorizationError(
                    ErrorCode.E9206,
                    "Insufficient role for operation",
                    details={
                        "required": route.required_roles,
                        "provided": consumer.roles,
                    },
                )

        # Check ABAC policies (via L08 Supervision)
        if self.supervision_client:
            policy_result = await self._evaluate_abac_policies(
                context, consumer, route
            )
            if not policy_result:
                raise AuthorizationError(
                    ErrorCode.E9201,
                    "Authorization policy denied access",
                    details={"route_id": route.route_id},
                )

        return True

    def _check_scopes(
        self, consumer_scopes: List[str], required_scopes: List[str]
    ) -> bool:
        """Check if consumer has all required OAuth scopes"""
        consumer_scope_set = set(consumer_scopes)
        required_scope_set = set(required_scopes)
        return required_scope_set.issubset(consumer_scope_set)

    def _check_roles(
        self, consumer_roles: List[str], required_roles: List[str]
    ) -> bool:
        """Check if consumer has any of the required roles"""
        # Role hierarchy: ADMIN > DEVELOPER > GUEST
        role_hierarchy = {"admin": 3, "developer": 2, "guest": 1}

        consumer_role_levels = [
            role_hierarchy.get(r.lower(), 0) for r in consumer_roles
        ]
        required_role_levels = [
            role_hierarchy.get(r.lower(), 0) for r in required_roles
        ]

        if not consumer_role_levels:
            return False

        max_consumer_level = max(consumer_role_levels)
        min_required_level = min(required_role_levels) if required_role_levels else 0

        return max_consumer_level >= min_required_level

    async def _evaluate_abac_policies(
        self,
        context: RequestContext,
        consumer: ConsumerProfile,
        route: RouteDefinition,
    ) -> bool:
        """
        Evaluate ABAC policies via L08 Supervision

        Returns:
            True if allowed, False if denied
        """
        if not self.supervision_client:
            return True  # No ABAC policies configured

        try:
            # Call L08 Supervision for policy evaluation
            policy_request = {
                "consumer_id": consumer.consumer_id,
                "tenant_id": consumer.tenant_id,
                "route_id": route.route_id,
                "method": context.metadata.method,
                "path": context.metadata.path,
                "rate_limit_tier": consumer.rate_limit_tier.value,
                "client_ip": context.metadata.client_ip,
            }

            result = await self.supervision_client.evaluate_policy(policy_request)
            return result.get("allowed", False)

        except Exception as e:
            # Fail-secure: deny on policy evaluation error
            raise AuthorizationError(
                ErrorCode.E9201,
                f"Policy evaluation failed: {str(e)}",
            )
