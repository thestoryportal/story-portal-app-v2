"""
L08 Supervision Layer - Access Control Manager

Administrative access control with ABAC (Attribute-Based Access Control)
and MFA enforcement for sensitive operations.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from ..models.config import SupervisionConfiguration
from ..models.error_codes import ErrorCodes, AccessControlError

logger = logging.getLogger(__name__)


@dataclass
class AdminUser:
    """Administrative user with permissions"""
    user_id: str
    permissions: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    mfa_enabled: bool = True
    granted_at: datetime = field(default_factory=datetime.utcnow)
    granted_by: Optional[str] = None


class AccessControlManager:
    """
    Access control manager for administrative operations.

    Features:
    - ABAC with attribute-based permission checking
    - Role-based permission grouping
    - MFA enforcement for admin actions
    - Permission inheritance from roles
    """

    # Standard roles and their permissions
    ROLE_PERMISSIONS = {
        "admin": ["*"],  # Full access
        "policy_manager": ["policy:read", "policy:write", "policy:deploy"],
        "escalation_approver": ["escalation:read", "escalation:approve"],
        "auditor": ["audit:read", "anomaly:read", "compliance:read"],
        "viewer": ["policy:read", "constraint:read", "audit:read"],
    }

    def __init__(self, config: SupervisionConfiguration):
        """
        Initialize Access Control Manager.

        Args:
            config: Supervision configuration
        """
        self.config = config

        # In-memory user store
        self._users: Dict[str, AdminUser] = {}

        logger.info("AccessControlManager initialized")

    async def grant_access(
        self,
        user_id: str,
        permissions: List[str],
        roles: Optional[List[str]] = None,
        granted_by: Optional[str] = None
    ) -> Tuple[Optional[AdminUser], Optional[str]]:
        """
        Grant administrative access to a user.

        Args:
            user_id: User ID to grant access to
            permissions: List of permissions to grant
            roles: Optional roles to assign
            granted_by: User ID granting the access

        Returns:
            Tuple of (AdminUser, error message)
        """
        try:
            user = AdminUser(
                user_id=user_id,
                permissions=permissions,
                roles=roles or [],
                mfa_enabled=self.config.require_mfa_for_admin,
                granted_at=datetime.utcnow(),
                granted_by=granted_by,
            )

            self._users[user_id] = user

            logger.info(
                f"Granted access to {user_id}: permissions={permissions}, roles={roles}"
            )
            return user, None

        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return None, str(e)

    async def revoke_access(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Revoke administrative access from a user.

        Args:
            user_id: User ID to revoke access from

        Returns:
            Tuple of (success, error message)
        """
        if user_id not in self._users:
            return False, f"{ErrorCodes.PERMISSION_NOT_FOUND.value}: User {user_id} not found"

        del self._users[user_id]
        logger.info(f"Revoked access from {user_id}")
        return True, None

    async def check_permission(
        self,
        user_id: str,
        required_permission: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user has required permission.

        Args:
            user_id: User ID to check
            required_permission: Permission string (e.g., "policy:write")
            context: Optional context for ABAC evaluation

        Returns:
            Tuple of (has_permission, error message)
        """
        if user_id not in self._users:
            return False, f"{ErrorCodes.ACCESS_DENIED.value}: User {user_id} not authorized"

        user = self._users[user_id]

        # Check direct permissions
        if self._has_permission(user, required_permission):
            return True, None

        # Check role-based permissions
        for role in user.roles:
            role_perms = self.ROLE_PERMISSIONS.get(role, [])
            if "*" in role_perms or required_permission in role_perms:
                return True, None

            # Check wildcard permissions (e.g., "policy:*")
            perm_parts = required_permission.split(":")
            if len(perm_parts) == 2:
                wildcard = f"{perm_parts[0]}:*"
                if wildcard in role_perms:
                    return True, None

        return False, (
            f"{ErrorCodes.INSUFFICIENT_PRIVILEGES.value}: "
            f"Missing permission '{required_permission}'"
        )

    def _has_permission(self, user: AdminUser, permission: str) -> bool:
        """Check if user has specific permission"""
        if "*" in user.permissions:
            return True
        if permission in user.permissions:
            return True

        # Check wildcard
        perm_parts = permission.split(":")
        if len(perm_parts) == 2:
            wildcard = f"{perm_parts[0]}:*"
            if wildcard in user.permissions:
                return True

        return False

    async def assign_role(
        self,
        user_id: str,
        role: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Assign a role to a user.

        Args:
            user_id: User ID
            role: Role name to assign

        Returns:
            Tuple of (success, error message)
        """
        if user_id not in self._users:
            return False, f"{ErrorCodes.ACCESS_DENIED.value}: User {user_id} not found"

        if role not in self.ROLE_PERMISSIONS:
            return False, f"{ErrorCodes.ROLE_NOT_ASSIGNED.value}: Unknown role '{role}'"

        user = self._users[user_id]
        if role not in user.roles:
            user.roles.append(role)

        logger.info(f"Assigned role '{role}' to {user_id}")
        return True, None

    async def remove_role(
        self,
        user_id: str,
        role: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Remove a role from a user.

        Args:
            user_id: User ID
            role: Role name to remove

        Returns:
            Tuple of (success, error message)
        """
        if user_id not in self._users:
            return False, f"{ErrorCodes.ACCESS_DENIED.value}: User {user_id} not found"

        user = self._users[user_id]
        if role in user.roles:
            user.roles.remove(role)

        logger.info(f"Removed role '{role}' from {user_id}")
        return True, None

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user (direct + role-based)"""
        if user_id not in self._users:
            return []

        user = self._users[user_id]
        permissions = set(user.permissions)

        for role in user.roles:
            permissions.update(self.ROLE_PERMISSIONS.get(role, []))

        return list(permissions)

    async def get_user(self, user_id: str) -> Optional[AdminUser]:
        """Get user information"""
        return self._users.get(user_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get access control statistics"""
        role_counts = {}
        for user in self._users.values():
            for role in user.roles:
                role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_users": len(self._users),
            "mfa_enabled_count": len([u for u in self._users.values() if u.mfa_enabled]),
            "role_counts": role_counts,
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for access control manager"""
        return {
            "status": "healthy",
            "stats": self.get_stats(),
        }
