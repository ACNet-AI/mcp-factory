"""
MCP Factory Authorization System

Casbin-based permission management system supporting:
- Role-Based Access Control (RBAC)
- Fine-grained permission management
- Temporary permission support
- Permission change history tracking
"""

from .audit import AuditEventType, AuditLogger, AuditResult, get_audit_logger
from .config import get_default_data_dir
from .manager import (
    AccessToken,
    MCPAuthorizationManager,
    PermissionCheckResult,
    format_permission_error,
    get_current_user_info,
)
from .models import (
    AuthorizedProxies,
    MCPPermission,
    PermissionHistory,
    ProxyConfig,
    UserMetadata,
    UserTier,
)

__all__ = [
    "MCPAuthorizationManager",
    "MCPPermission",
    "PermissionHistory",
    "UserMetadata",
    "UserTier",
    "ProxyConfig",
    "AuthorizedProxies",
    "AccessToken",
    "PermissionCheckResult",
    "get_current_user_info",
    "format_permission_error",
    "AuditLogger",
    "AuditEventType",
    "AuditResult",
    "get_audit_logger",
    "get_default_data_dir",
]
