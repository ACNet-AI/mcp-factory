"""
Authorization data models and types
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class PermissionAction(Enum):
    """Permission action type"""

    GRANT = "grant"
    REVOKE = "revoke"


class PermissionType(Enum):
    """Permission type"""

    ROLE = "role"
    POLICY = "policy"
    TEMPORARY = "temporary"


@dataclass
class MCPPermission:
    """MCP permission definition"""

    resource: str  # mcp, tool, system
    action: str  # read, write, admin, external, execute
    scope: str  # *, specific_tool_name, etc.
    description: str = ""

    def to_string(self) -> str:
        """Convert to string representation"""
        return f"{self.resource}:{self.action}:{self.scope}"

    @classmethod
    def from_string(cls, permission_str: str) -> "MCPPermission":
        """Create permission object from string"""
        parts = permission_str.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid permission string: {permission_str}")
        return cls(resource=parts[0], action=parts[1], scope=parts[2])


@dataclass
class PermissionHistory:
    """Permission change history record"""

    id: int | None
    user_id: str
    action: PermissionAction
    permission_type: PermissionType
    permission_value: str
    granted_by: str
    reason: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


@dataclass
class UserMetadata:
    """User metadata"""

    user_id: str
    display_name: str | None = None
    email: str | None = None
    created_at: datetime | None = None
    last_login: datetime | None = None
    status: str = "active"
    metadata: dict[str, Any] | None = None


@dataclass
class TemporaryPermission:
    """temporary permission"""

    id: int | None
    user_id: str
    resource: str
    action: str
    scope: str
    granted_by: str
    expires_at: datetime
    is_active: bool = True
    created_at: datetime | None = None


# Predefined roles and permissions
DEFAULT_ROLES = {
    "free_user": {
        "description": "Free user - basic functionality access",
        "permissions": [
            MCPPermission("mcp", "read", "*", "View server information"),
            MCPPermission("tool", "read", "*", "View tool list"),
            MCPPermission("tool", "execute", "basic", "Execute basic tools"),
            MCPPermission("prompt", "read", "free", "View free prompts"),
            MCPPermission("resource", "read", "public", "Access public resources"),
        ],
        "limitations": {"daily_requests": 100, "max_tokens_per_request": 1000, "rate_limit_per_minute": 10},
    },
    "premium_user": {
        "description": "Premium user - advanced functionality access",
        "permissions": [
            MCPPermission("mcp", "read", "*", "View server information"),
            MCPPermission("tool", "read", "*", "View tool list"),
            MCPPermission("tool", "execute", "basic", "Execute basic tools"),
            MCPPermission("tool", "execute", "ai", "Execute AI tools"),
            MCPPermission("tool", "execute", "premium", "Execute premium tools"),
            MCPPermission("prompt", "read", "*", "View all prompts"),
            MCPPermission("prompt", "execute", "premium", "Execute premium prompts"),
            MCPPermission("resource", "read", "*", "Access all resources"),
            MCPPermission("resource", "write", "private", "Write to private resources"),
        ],
        "limitations": {"daily_requests": 1000, "max_tokens_per_request": 4000, "rate_limit_per_minute": 50},
    },
    "enterprise_user": {
        "description": "Enterprise user - enterprise-level functionality (read-only admin permissions)",
        "permissions": [
            MCPPermission("mcp", "read", "*", "View server information"),
            # MCPPermission("mcp", "write", "*", "Modify server configuration"),  # removed: prevent affecting other users
            MCPPermission("tool", "read", "*", "View tool list"),
            MCPPermission("tool", "execute", "*", "Execute all tools"),
            MCPPermission("tool", "execute", "external", "Access external systems"),
            MCPPermission("prompt", "read", "*", "View all prompts"),
            MCPPermission("prompt", "execute", "*", "Execute all prompts"),
            MCPPermission("prompt", "create", "*", "Create prompts"),
            MCPPermission("resource", "read", "*", "Access all resources"),
            MCPPermission("resource", "write", "*", "Write to all resources"),
            MCPPermission("resource", "create", "*", "Create resources"),
        ],
        "limitations": {
            "daily_requests": "unlimited",
            "max_tokens_per_request": "unlimited",
            "rate_limit_per_minute": 200,
        },
    },
    "admin": {
        "description": "System administrator - full permissions",
        "permissions": [
            MCPPermission("mcp", "read", "*", "View server information"),
            MCPPermission("mcp", "write", "*", "Modify server configuration"),
            MCPPermission("mcp", "admin", "*", "Administrator operations"),
            MCPPermission("tool", "read", "*", "View tool list"),
            MCPPermission("tool", "execute", "*", "Execute all tools"),
            MCPPermission("tool", "create", "*", "Create tools"),
            MCPPermission("tool", "delete", "*", "Delete tools"),
            MCPPermission("prompt", "read", "*", "View all prompts"),
            MCPPermission("prompt", "execute", "*", "Execute all prompts"),
            MCPPermission("prompt", "create", "*", "Create prompts"),
            MCPPermission("prompt", "delete", "*", "Delete prompts"),
            MCPPermission("resource", "read", "*", "Access all resources"),
            MCPPermission("resource", "write", "*", "Write to all resources"),
            MCPPermission("resource", "create", "*", "Create resources"),
            MCPPermission("resource", "delete", "*", "Delete resources"),
            MCPPermission("system", "read", "*", "View system information"),
            MCPPermission("system", "write", "*", "Modify system configuration"),
            MCPPermission("system", "admin", "*", "System administration permissions"),
        ],
        "limitations": {},
    },
}

# Mapping from MCP annotation types to permissions
ANNOTATION_TO_PERMISSION = {
    # Basic permissions
    "readonly": MCPPermission("mcp", "read", "*"),
    "modify": MCPPermission("mcp", "write", "*"),
    "destructive": MCPPermission("mcp", "admin", "*"),
    # Tool permissions
    "basic_tool": MCPPermission("tool", "execute", "basic"),
    "ai_tool": MCPPermission("tool", "execute", "ai"),
    "external_tool": MCPPermission("tool", "execute", "external"),
    "premium_tool": MCPPermission("tool", "execute", "premium"),
    # Prompt permissions
    "free_prompt": MCPPermission("prompt", "read", "free"),
    "premium_prompt": MCPPermission("prompt", "execute", "premium"),
    "create_prompt": MCPPermission("prompt", "create", "*"),
    # Resource permissions
    "public_resource": MCPPermission("resource", "read", "public"),
    "private_resource": MCPPermission("resource", "read", "private"),
    "sensitive_resource": MCPPermission("resource", "read", "sensitive"),
    # System permissions
    "system_admin": MCPPermission("system", "admin", "*"),
    "user_management": MCPPermission("system", "write", "users"),
    # Backward compatibility
    "external": MCPPermission("tool", "execute", "external"),
}

# =============================================================================
# TODO: Permission model extensions
# =============================================================================

# TODO: Add more predefined roles (priority: medium)
# - guest: guest role, minimal permissions
# - moderator: moderator role, medium admin permissions
# - developer: developer role, development-related permissions
# - auditor: auditor role, read-only audit permissions

# TODO: Add permission template system (priority: low)
# - PERMISSION_TEMPLATES: predefined permission combination templates
# - ROLE_INHERITANCE: role inheritance relationship definitions
# - CONDITIONAL_PERMISSIONS: conditional permissions (based on time, IP, etc.)

# TODO: Add permission constraints and validation (priority: medium)
# - PERMISSION_CONSTRAINTS: permission constraint rules
# - ROLE_VALIDATION_RULES: role validation rules
# - SECURITY_POLICIES: security policy definitions
