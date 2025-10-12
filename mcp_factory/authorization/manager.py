"""
MCP Authorization Manager - Refactored

Core implementation of Casbin-based permission management
Now acts as a coordinator for specialized services.
"""

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

import casbin

from .audit import get_audit_logger
from .cache import get_permission_cache
from .config import get_default_authz_db_path, get_default_authz_policy_path
from .debug_service import DebugService
from .models import (
    DEFAULT_ROLES,
    MCPPermission,
)
from .permission_engine import PermissionCheckResult, PermissionEngine
from .role_service import RoleService
from .saas_service import SaaSService


# Core types for authorization system
class AccessToken(Protocol):
    """Access token protocol"""

    client_id: str
    scopes: list[str]


def get_access_token() -> "AccessToken | None":
    """Get access token from context"""
    # This is a placeholder implementation
    # In a real application, this would extract token from request context
    return None


def get_current_user_info() -> tuple[str | None, list[str]]:
    """Get current user information from context"""
    # Get access token from context
    token = get_access_token()
    if token:
        return token.client_id, token.scopes
    return None, []


def format_permission_error(result: PermissionCheckResult) -> str:
    """Format permission error message"""
    lines = [
        f"❌ Permission check failed for user '{result.user_id}'",
        f"📋 Required: {result.required_permission}",
        f"👤 User roles: {', '.join(result.user_roles) if result.user_roles else 'None'}",
        f"🔍 Reason: {result.reason}",
    ]

    if result.suggestions:
        lines.append("💡 Suggestions:")
        for suggestion in result.suggestions:
            lines.append(f"   • {suggestion}")

    return "\n".join(lines)


logger = logging.getLogger(__name__)


class MCPAuthorizationManager:
    """MCP Authorization Manager - Refactored as service coordinator"""

    def __init__(
        self,
        model_path: str | None = None,
        policy_path: str | None = None,
        db_path: str | None = None,
        enable_cache: bool = True,
        enable_audit: bool = True,
    ):
        """
        Initialize authorization manager

        Args:
            model_path: Casbin model file path
            policy_path: Casbin policy file path
            db_path: Extended database path
            enable_cache: Whether to enable permission caching
            enable_audit: Whether to enable audit logging
        """
        self.model_path = model_path or self._get_default_model_path()
        self.policy_path = policy_path or get_default_authz_policy_path()
        self.db_path = db_path or get_default_authz_db_path()
        self.enable_cache = enable_cache
        self.enable_audit = enable_audit

        # Initialize permission cache
        self.cache = get_permission_cache() if enable_cache else None

        # Initialize audit logging
        self.audit_logger = get_audit_logger() if enable_audit else None

        # Initialize Casbin
        self._init_casbin()

        # Initialize extended database
        self._init_extended_database()

        # Initialize specialized services
        self._init_services()

        # Set default permissions
        self._setup_default_permissions()

    def _get_default_model_path(self) -> str:
        """Get default model file path"""
        current_dir = Path(__file__).parent
        model_path = current_dir / "rbac_model.conf"
        return str(model_path)

    def _init_casbin(self) -> None:
        """Initialize Casbin enforcer"""
        try:
            # Ensure policy file exists
            if not Path(self.policy_path).exists():
                # Create empty policy file
                Path(self.policy_path).touch()
                logger.info(f"Created empty policy file: {self.policy_path}")

            self.enforcer = casbin.Enforcer(self.model_path, self.policy_path)
            logger.info(f"Casbin enforcer initialized with model: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Casbin enforcer: {e}")
            raise

    def _init_extended_database(self) -> None:
        """Initialize extended database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # User metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_metadata (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                status TEXT DEFAULT 'active',
                metadata TEXT
            )
        """)

        # Permission change history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permission_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                permission_type TEXT NOT NULL,
                permission_value TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        """)

        # Temporary permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS temporary_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                resource TEXT NOT NULL,
                action TEXT NOT NULL,
                scope TEXT NOT NULL,
                granted_by TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Extended database initialized: {self.db_path}")

    def _init_services(self) -> None:
        """Initialize specialized services"""
        # Initialize permission engine
        self.permission_engine = PermissionEngine(
            enforcer=self.enforcer,
            db_path=self.db_path,
            enable_cache=self.enable_cache,
            enable_audit=self.enable_audit,
        )

        # Initialize role service
        self.role_service = RoleService(
            enforcer=self.enforcer,
            db_path=self.db_path,
            enable_cache=self.enable_cache,
            enable_audit=self.enable_audit,
        )

        # Initialize debug service
        self.debug_service = DebugService(
            enforcer=self.enforcer,
            db_path=self.db_path,
            role_service=self.role_service,
            permission_engine=self.permission_engine,
        )

        # Initialize SaaS service
        self.saas_service = SaaSService(
            enforcer=self.enforcer,
            db_path=self.db_path,
            role_service=self.role_service,
            enable_audit=self.enable_audit,
        )

        logger.info("All authorization services initialized")

    def _setup_default_permissions(self) -> None:
        """Set up default permissions and roles"""
        try:
            # Clear existing policies (only on first setup)
            if not self._has_existing_policies():
                # Set role hierarchy
                self.enforcer.add_grouping_policy("admin", "editor")
                self.enforcer.add_grouping_policy("editor", "viewer")

                # Add permissions for each default role
                for role_name, role_config in DEFAULT_ROLES.items():
                    for permission in role_config["permissions"]:  # type: ignore[attr-defined]
                        # Type hint for MyPy - cast to MCPPermission
                        perm: MCPPermission = permission
                        self.enforcer.add_policy(
                            role_name,
                            perm.resource,
                            perm.action,
                            perm.scope,
                            "allow",
                        )

                # Save policies
                self.enforcer.save_policy()
                logger.info("Default permissions and roles set up successfully")
            else:
                logger.info("Existing policies found, skipping default setup")
        except Exception as e:
            logger.error(f"Error setting up default permissions: {e}")

    def _has_existing_policies(self) -> bool:
        """Check if there are existing policies"""
        return len(self.enforcer.get_policy()) > 0

    # =============================================================================
    # Core Permission Operations - Delegated to PermissionEngine
    # =============================================================================

    def check_permission(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str = "*",
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> bool:
        """Check user permissions"""
        return self.permission_engine.check_permission(user_id, resource, action, scope, ip_address, session_id)

    def check_annotation_permission(self, user_id: str, annotation_type: str) -> bool:
        """Check annotation type permissions"""
        return self.permission_engine.check_annotation_permission(user_id, annotation_type)

    def check_permission_detailed(
        self,
        user_id: str,
        resource: str,
        action: str,
        scope: str = "*",
        ip_address: str | None = None,
        session_id: str | None = None,
    ) -> PermissionCheckResult:
        """Check user permissions (returns detailed results)"""
        return self.permission_engine.check_permission_detailed(
            user_id, resource, action, scope, ip_address, session_id
        )

    # =============================================================================
    # Role Management Operations - Delegated to RoleService
    # =============================================================================

    def assign_role(self, user_id: str, role: str, assigned_by: str, reason: str = "") -> bool:
        """Assign role to user"""
        return self.role_service.assign_role(user_id, role, assigned_by, reason)

    def remove_role(self, user_id: str, role: str, removed_by: str, reason: str = "") -> bool:
        """Remove user role"""
        return self.role_service.remove_role(user_id, role, removed_by, reason)

    # For backward compatibility
    def revoke_role(self, user_id: str, role: str, revoked_by: str, reason: str = "") -> bool:
        """Revoke user role (alias for remove_role)"""
        return self.remove_role(user_id, role, revoked_by, reason)

    def grant_direct_permission(
        self, user_id: str, resource: str, action: str, scope: str = "*", granted_by: str = "", reason: str = ""
    ) -> bool:
        """Grant permission directly to user"""
        return self.role_service.grant_direct_permission(user_id, resource, action, scope, granted_by, reason)

    def revoke_direct_permission(
        self, user_id: str, resource: str, action: str, scope: str = "*", revoked_by: str = "", reason: str = ""
    ) -> bool:
        """Revoke direct permission from user"""
        return self.role_service.revoke_direct_permission(user_id, resource, action, scope, revoked_by, reason)

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
        """Grant temporary permission to user"""
        return self.role_service.grant_temporary_permission(
            user_id, resource, action, scope, expires_in_hours, granted_by, reason
        )

    def get_user_roles(self, user_id: str) -> list[str]:
        """Get all roles assigned to a user"""
        return self.role_service.get_user_roles(user_id)

    def get_user_permissions(self, user_id: str) -> list[list[str]]:
        """Get all permissions for a user"""
        return self.role_service.get_user_permissions(user_id)

    def get_effective_permissions(self, user_id: str) -> dict[str, Any]:
        """Get effective permissions for a user"""
        return self.role_service.get_effective_permissions(user_id)

    def get_users_for_role(self, role: str) -> list[str]:
        """Get all users with a specific role"""
        return self.role_service.get_users_for_role(role)

    def get_permission_history(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get permission change history for a user"""
        return self.role_service.get_permission_history(user_id, limit)

    def get_available_roles(self) -> dict[str, dict]:
        """Get all available roles"""
        return self.role_service.get_available_roles()

    def cleanup_expired_permissions(self) -> None:
        """Clean up expired temporary permissions"""
        return self.role_service.cleanup_expired_permissions()

    # =============================================================================
    # Debug Operations - Delegated to DebugService
    # =============================================================================

    def debug_permission(self, user_id: str, resource: str, action: str, scope: str = "*") -> dict:
        """Debug permission check process"""
        return self.debug_service.debug_permission(user_id, resource, action, scope)

    def print_debug_info(self, debug_info: dict) -> None:
        """Print formatted debug information"""
        return self.debug_service.print_debug_info(debug_info)

    def get_system_health(self) -> dict[str, Any]:
        """Get authorization system health status"""
        return self.debug_service.get_system_health()

    def validate_configuration(self) -> dict[str, Any]:
        """Validate authorization system configuration"""
        return self.debug_service.validate_configuration()

    # =============================================================================
    # SaaS Operations - Delegated to SaaSService
    # =============================================================================

    def submit_permission_request(self, user_id: str, requested_role: str, reason: str = "") -> str:
        """User submits permission request"""
        return self.saas_service.submit_permission_request(user_id, requested_role, reason)

    def get_permission_requests(self, user_id: str | None = None, status: str | None = None) -> list[dict]:
        """Get permission request list"""
        return self.saas_service.get_permission_requests(user_id, status)

    def review_permission_request(self, request_id: str, reviewer_id: str, action: str, comment: str = "") -> bool:
        """Review permission request"""
        return self.saas_service.review_permission_request(request_id, reviewer_id, action, comment)

    def get_user_permission_summary(self, user_id: str) -> dict:
        """Get user permission summary"""
        return self.saas_service.get_user_permission_summary(user_id)

    def get_request_statistics(self, days: int = 30) -> dict[str, Any]:
        """Get permission request statistics"""
        return self.saas_service.get_request_statistics(days)

    def cleanup_old_requests(self, days_to_keep: int = 365) -> int:
        """Clean up old permission requests"""
        return self.saas_service.cleanup_old_requests(days_to_keep)

    def get_pending_requests_summary(self) -> dict[str, Any]:
        """Get summary of pending requests"""
        return self.saas_service.get_pending_requests_summary()

    def auto_approve_requests(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """Auto-approve requests based on criteria"""
        return self.saas_service.auto_approve_requests(criteria)

    # =============================================================================
    # Cache Management Methods
    # =============================================================================

    def get_cache_stats(self) -> dict[str, Any] | None:
        """Get permission cache statistics"""
        if not self.cache:
            return None
        return self.cache.get_stats()

    def clear_cache(self) -> None:
        """Clear all permission cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Permission cache cleared")

    def invalidate_user_cache(self, user_id: str) -> None:
        """Clear specific user's permission cache"""
        if self.cache:
            self.cache.invalidate_user(user_id)
            logger.info(f"Cache invalidated for user: {user_id}")

    def invalidate_permission_cache(self, permission: str) -> None:
        """Clear specific permission cache"""
        if self.cache:
            self.cache.invalidate_permission(permission)
            logger.info(f"Cache invalidated for permission: {permission}")

    def configure_cache(self, ttl: int = 300, max_size: int = 10000) -> None:
        """Reconfigure permission cache"""
        if self.enable_cache:
            from .cache import configure_permission_cache

            configure_permission_cache(ttl=ttl, max_size=max_size)
            self.cache = get_permission_cache()
            logger.info(f"Permission cache reconfigured: TTL={ttl}s, max_size={max_size}")

    # =============================================================================
    # Audit Log Management Methods
    # =============================================================================

    def get_audit_stats(self, days: int = 7) -> dict[str, Any] | None:
        """Get audit statistics"""
        if not self.audit_logger:
            return None
        return self.audit_logger.get_audit_stats(days=days)

    def query_audit_events(
        self,
        user_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Query audit events"""
        if not self.audit_logger:
            return []

        from .audit import AuditEventType

        event_type_enum = None
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type)
            except ValueError:
                logger.warning(f"Invalid event type: {event_type}")
                return []

        events = self.audit_logger.query_events(
            user_id=user_id,
            event_type=event_type_enum,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        # Convert to dictionary format
        return [
            {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "timestamp": event.timestamp.isoformat(),
                "user_id": event.user_id,
                "result": event.result.value,
                "resource": event.resource,
                "action": event.action,
                "scope": event.scope,
                "details": event.details,
                "ip_address": event.ip_address,
                "session_id": event.session_id,
                "duration_ms": event.duration_ms,
                "error_message": event.error_message,
            }
            for event in events
        ]

    def cleanup_audit_logs(self, days_to_keep: int = 90) -> int:
        """Clean up old audit logs"""
        if not self.audit_logger:
            return 0
        return self.audit_logger.cleanup_old_events(days_to_keep=days_to_keep)
