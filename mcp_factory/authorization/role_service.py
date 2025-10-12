"""
Role Service - Role and permission management

This module handles role assignment, permission granting,
and user permission queries.
"""

import logging
import sqlite3
from typing import Any

from .audit import get_audit_logger
from .cache import get_permission_cache
from .models import DEFAULT_ROLES, PermissionAction, PermissionType

logger = logging.getLogger(__name__)


class RoleService:
    """Role and permission management service"""

    def __init__(self, enforcer: Any, db_path: str, enable_cache: bool = True, enable_audit: bool = True) -> None:
        """
        Initialize role service

        Args:
            enforcer: Casbin enforcer instance
            db_path: Database path
            enable_cache: Whether to enable permission caching
            enable_audit: Whether to enable audit logging
        """
        self.enforcer = enforcer
        self.db_path = db_path
        self.enable_cache = enable_cache
        self.enable_audit = enable_audit

        # Initialize permission cache
        self.cache = get_permission_cache() if enable_cache else None

        # Initialize audit logging
        self.audit_logger = get_audit_logger() if enable_audit else None

    def assign_role(self, user_id: str, role: str, assigned_by: str, reason: str = "") -> bool:
        """
        Assign role to user

        Args:
            user_id: User ID
            role: Role name
            assigned_by: Assigner ID
            reason: Assignment reason

        Returns:
            bool: Whether successful
        """
        try:
            # Check if role exists
            if not self._role_exists(role):
                logger.error(f"Role does not exist: {role}")
                return False

            # Add role assignment
            success = self.enforcer.add_grouping_policy(user_id, role)
            success = bool(success)  # Convert Any to bool

            if success:
                # Record history
                self._record_permission_history(
                    user_id, PermissionAction.GRANT, PermissionType.ROLE, role, assigned_by, reason
                )

                # Record audit log
                if self.audit_logger:
                    self.audit_logger.log_role_change(
                        user_id=user_id,
                        role=role,
                        action="assigned",
                        operator_id=assigned_by,
                        reason=reason,
                    )

                # Clear user permission cache
                if self.cache:
                    self.cache.invalidate_user(user_id)

                # Save policies
                self.enforcer.save_policy()

                logger.info(f"Role '{role}' assigned to user '{user_id}' by '{assigned_by}'")

            return success
        except Exception as e:
            logger.error(f"Error assigning role: {e}")
            return False

    def remove_role(self, user_id: str, role: str, removed_by: str, reason: str = "") -> bool:
        """
        Remove user role

        Args:
            user_id: User ID
            role: Role name
            removed_by: Remover ID
            reason: Removal reason

        Returns:
            bool: Whether successful
        """
        try:
            success = self.enforcer.remove_grouping_policy(user_id, role)
            success = bool(success)  # Convert Any to bool

            if success:
                # Record history
                self._record_permission_history(
                    user_id, PermissionAction.REVOKE, PermissionType.ROLE, role, removed_by, reason
                )

                # Record audit log
                if self.audit_logger:
                    self.audit_logger.log_role_change(
                        user_id=user_id,
                        role=role,
                        action="removed",
                        operator_id=removed_by,
                        reason=reason,
                    )

                # Clear user permission cache
                if self.cache:
                    self.cache.invalidate_user(user_id)

                # Save policies
                self.enforcer.save_policy()

                logger.info(f"Role '{role}' removed from user '{user_id}' by '{removed_by}'")

            return success
        except Exception as e:
            logger.error(f"Error removing role: {e}")
            return False

    def grant_direct_permission(
        self, user_id: str, resource: str, action: str, scope: str = "*", granted_by: str = "", reason: str = ""
    ) -> bool:
        """
        Grant permission directly to user

        Args:
            user_id: User ID
            resource: Resource type
            action: Action type
            scope: Permission scope
            granted_by: Granter ID
            reason: Grant reason

        Returns:
            bool: Whether successful
        """
        try:
            success = self.enforcer.add_policy(user_id, resource, action, scope, "allow")
            success = bool(success)  # Convert Any to bool

            if success:
                # Record history
                permission_value = f"{resource}:{action}:{scope}"
                self._record_permission_history(
                    user_id, PermissionAction.GRANT, PermissionType.POLICY, permission_value, granted_by, reason
                )

                # Clear user permission cache
                if self.cache:
                    self.cache.invalidate_user(user_id)

                # Save policies
                self.enforcer.save_policy()

                logger.info(f"Direct permission '{permission_value}' granted to user '{user_id}' by '{granted_by}'")

            return success
        except Exception as e:
            logger.error(f"Error granting direct permission: {e}")
            return False

    def revoke_direct_permission(
        self, user_id: str, resource: str, action: str, scope: str = "*", revoked_by: str = "", reason: str = ""
    ) -> bool:
        """
        Revoke direct permission from user

        Args:
            user_id: User ID
            resource: Resource type
            action: Action type
            scope: Permission scope
            revoked_by: Revoker ID
            reason: Revoke reason

        Returns:
            bool: Whether successful
        """
        try:
            success = self.enforcer.remove_policy(user_id, resource, action, scope, "allow")
            success = bool(success)  # Convert Any to bool

            if success:
                # Record history
                permission_value = f"{resource}:{action}:{scope}"
                self._record_permission_history(
                    user_id, PermissionAction.REVOKE, PermissionType.POLICY, permission_value, revoked_by, reason
                )

                # Clear user permission cache
                if self.cache:
                    self.cache.invalidate_user(user_id)

                # Save policies
                self.enforcer.save_policy()

                logger.info(f"Direct permission '{permission_value}' revoked from user '{user_id}' by '{revoked_by}'")

            return success
        except Exception as e:
            logger.error(f"Error revoking direct permission: {e}")
            return False

    def grant_temporary_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str = "*",
        expires_in_hours: int = 24,
        granted_by: str = "",
        reason: str = "",
    ) -> bool:
        """
        Grant temporary permission to user

        Args:
            user_id: User ID
            resource: Resource type
            action: Action type
            scope: Permission scope
            expires_in_hours: Expiration time in hours
            granted_by: Granter ID
            reason: Grant reason

        Returns:
            bool: Whether successful
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate expiration time
            expires_at = f"datetime('now', '+{expires_in_hours} hours')"

            cursor.execute(
                f"""
                INSERT INTO temporary_permissions
                (user_id, resource, action, scope, granted_by, expires_at)
                VALUES (?, ?, ?, ?, ?, {expires_at})
                """,
                (user_id, resource, action, scope, granted_by),
            )

            conn.commit()
            conn.close()

            # Record history
            permission_value = f"{resource}:{action}:{scope} (expires in {expires_in_hours}h)"
            self._record_permission_history(
                user_id, PermissionAction.GRANT, PermissionType.TEMPORARY, permission_value, granted_by, reason
            )

            # Clear user permission cache
            if self.cache:
                self.cache.invalidate_user(user_id)

            logger.info(
                f"Temporary permission '{resource}:{action}:{scope}' granted to user '{user_id}' for {expires_in_hours} hours"
            )

            return True
        except Exception as e:
            logger.error(f"Error granting temporary permission: {e}")
            return False

    def get_user_roles(self, user_id: str) -> list[str]:
        """Get all roles assigned to a user"""
        try:
            roles = self.enforcer.get_roles_for_user(user_id)
            return roles if roles else []
        except Exception as e:
            logger.error(f"Error getting user roles: {e}")
            return []

    def get_user_permissions(self, user_id: str) -> list[list[str]]:
        """Get all permissions for a user"""
        try:
            permissions = self.enforcer.get_permissions_for_user(user_id)
            return permissions if permissions else []
        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return []

    def get_effective_permissions(self, user_id: str) -> dict[str, Any]:
        """Get effective permissions for a user (including role-based permissions)"""
        try:
            # Get user roles
            roles = self.get_user_roles(user_id)

            # Get direct permissions
            direct_permissions = self.get_user_permissions(user_id)

            # Get role-based permissions
            permissions = []
            limitations = {}

            for role in roles:
                if role in DEFAULT_ROLES:
                    role_info = DEFAULT_ROLES[role]
                    for perm in role_info["permissions"]:  # type: ignore[attr-defined]
                        # Type hint for MyPy - cast to MCPPermission
                        permission = perm
                        perm_str = f"{permission.resource}:{permission.action}:{permission.scope}"
                        if perm_str not in permissions:
                            permissions.append(perm_str)

                    # Merge limitation information
                    role_limitations = role_info.get("limitations", {})
                    for key, value in role_limitations.items():  # type: ignore[attr-defined]
                        if key not in limitations:
                            limitations[key] = value
                        else:
                            # For numeric limitations, take the maximum
                            if isinstance(value, int | float) and isinstance(limitations[key], int | float):
                                limitations[key] = max(limitations[key], value)

            # Add direct permissions
            for perm in direct_permissions:
                if len(perm) >= 3:
                    perm_str = f"{perm[0]}:{perm[1]}:{perm[2]}"
                    if perm_str not in permissions:
                        permissions.append(perm_str)

            return {
                "user_id": user_id,
                "roles": roles,
                "permissions": permissions,
                "limitations": limitations,
                "direct_permissions": len(direct_permissions),
                "role_permissions": len(permissions) - len(direct_permissions),
            }
        except Exception as e:
            logger.error(f"Error getting effective permissions: {e}")
            return {"user_id": user_id, "roles": [], "permissions": [], "limitations": {}}

    def get_users_for_role(self, role: str) -> list[str]:
        """Get all users with a specific role"""
        try:
            users = self.enforcer.get_users_for_role(role)
            return users if users else []
        except Exception as e:
            logger.error(f"Error getting users for role: {e}")
            return []

    def get_permission_history(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get permission change history for a user"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT action, permission_type, permission_value, granted_by, reason, created_at
                FROM permission_history
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            )

            rows = cursor.fetchall()
            conn.close()

            history = []
            for row in rows:
                history.append(
                    {
                        "action": row[0],
                        "permission_type": row[1],
                        "permission_value": row[2],
                        "granted_by": row[3],
                        "reason": row[4],
                        "created_at": row[5],
                    }
                )

            return history
        except Exception as e:
            logger.error(f"Error getting permission history: {e}")
            return []

    def get_available_roles(self) -> dict[str, dict]:
        """Get all available roles"""
        return {
            role_name: {
                "description": role_config["description"],
                "permissions": [p.to_string() for p in role_config["permissions"]],  # type: ignore[attr-defined]
            }
            for role_name, role_config in DEFAULT_ROLES.items()
        }

    def _role_exists(self, role: str) -> bool:
        """Check if role exists in default roles"""
        return role in DEFAULT_ROLES

    def _record_permission_history(
        self,
        user_id: str,
        action: PermissionAction,
        permission_type: PermissionType,
        permission_value: str,
        granted_by: str,
        reason: str,
    ) -> None:
        """Record permission change history"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO permission_history
                (user_id, action, permission_type, permission_value, granted_by, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, action.value, permission_type.value, permission_value, granted_by, reason),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error recording permission history: {e}")

    def cleanup_expired_permissions(self) -> None:
        """Clean up expired temporary permissions"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Mark expired permissions as inactive
            cursor.execute(
                """
                UPDATE temporary_permissions
                SET is_active = FALSE
                WHERE expires_at <= datetime('now') AND is_active = TRUE
                """
            )

            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()

            if affected_rows > 0:
                logger.info(f"Cleaned up {affected_rows} expired temporary permissions")

                # Clear all cache since we don't know which users were affected
                if self.cache:
                    self.cache.clear()

        except Exception as e:
            logger.error(f"Error cleaning up expired permissions: {e}")
