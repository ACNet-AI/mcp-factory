"""
Authorization data models and types
"""

from dataclasses import dataclass, field
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


# Core Three-Tier Role System with Configurable Permissions
DEFAULT_ROLES = {
    "visitor": {
        "description": "Free/trial user - basic access for product evaluation",
        "base_permissions": [
            # Only truly universal permissions that apply to ALL MCP servers
            MCPPermission("mcp", "read", "info", "View basic server information"),
            MCPPermission("mcp", "read", "capabilities", "View server capabilities"),
        ],
        "default_limitations": {
            "daily_requests": 50,
            "max_tokens_per_request": 500,
            "rate_limit_per_minute": 5,
            "trial_duration_days": 7,
        },
        "extensible": True,  # Changed: visitor can now be extended with app-specific permissions
    },
    "user": {
        "description": "Paid user - full access with extensible tiers",
        "base_permissions": [
            # Only truly universal permissions that apply to ALL MCP servers
            MCPPermission("mcp", "read", "info", "View basic server information"),
            MCPPermission("mcp", "read", "capabilities", "View server capabilities"),
            MCPPermission("mcp", "read", "status", "View server status"),
        ],
        "default_limitations": {"daily_requests": 1000, "max_tokens_per_request": 4000, "rate_limit_per_minute": 60},
        "extensible": True,  # Key: this role can be extended with tiers and app-specific permissions
    },
    "admin": {
        "description": "System administrator - full system access",
        "base_permissions": [
            # Universal admin permissions
            MCPPermission("mcp", "read", "*", "View all server information"),
            MCPPermission("mcp", "write", "config", "Modify server configuration"),
            MCPPermission("mcp", "admin", "system", "System administration"),
            MCPPermission("user", "read", "*", "View user information"),
            MCPPermission("user", "write", "*", "Modify user information"),
            MCPPermission("user", "admin", "*", "User administration"),
            MCPPermission("system", "read", "*", "View system information"),
            MCPPermission("system", "write", "*", "Modify system configuration"),
            MCPPermission("system", "admin", "*", "System administration"),
        ],
        "default_limitations": {},
        "extensible": True,  # Changed: admin can also be extended for app-specific admin features
    },
}

# Global role permission overrides
_role_permission_overrides: dict[str, list[MCPPermission]] = {}


def configure_role_permissions(role_name: str, additional_permissions: list[MCPPermission]) -> None:
    """
    Configure additional permissions for a role.

    This allows developers to add application-specific permissions to core roles.

    Args:
        role_name: The role name to configure
        additional_permissions: Additional permissions to add
    """
    if role_name not in DEFAULT_ROLES:
        raise ValueError(f"Unknown role: {role_name}")

    if not DEFAULT_ROLES[role_name]["extensible"]:
        raise ValueError(f"Role {role_name} is not extensible")

    _role_permission_overrides[role_name] = additional_permissions.copy()


def get_role_permissions(role_name: str) -> list[MCPPermission]:
    """
    Get effective permissions for a role (base + configured).

    Args:
        role_name: The role name to get permissions for

    Returns:
        List of effective permissions for the role
    """
    if role_name not in DEFAULT_ROLES:
        return []

    # Start with base permissions
    permissions = DEFAULT_ROLES[role_name]["base_permissions"].copy()  # type: ignore[attr-defined]

    # Add any configured additional permissions
    if role_name in _role_permission_overrides:
        permissions.extend(_role_permission_overrides[role_name])

    return permissions  # type: ignore[no-any-return]


# Global role configuration overrides
_role_config_overrides: dict[str, dict[str, Any]] = {}


def configure_role_limitations(role_name: str, limitations: dict[str, Any]) -> None:
    """
    Configure custom limitations for a role.

    This allows developers to override default limitations for their specific application.

    Args:
        role_name: The role name to configure
        limitations: Custom limitations to apply
    """
    if role_name not in DEFAULT_ROLES:
        raise ValueError(f"Unknown role: {role_name}")

    _role_config_overrides[role_name] = limitations.copy()


def get_role_limitations(role_name: str) -> dict[str, Any]:
    """
    Get effective limitations for a role (default + overrides).

    Args:
        role_name: The role name to get limitations for

    Returns:
        Dictionary of effective limitations for the role
    """
    if role_name not in DEFAULT_ROLES:
        return {}

    # Start with default limitations
    limitations = DEFAULT_ROLES[role_name].get("default_limitations", {}).copy()  # type: ignore[attr-defined]

    # Apply any configured overrides
    if role_name in _role_config_overrides:
        limitations.update(_role_config_overrides[role_name])

    return limitations  # type: ignore[no-any-return]


def reset_role_configuration() -> None:
    """Reset all role configuration overrides to defaults."""
    _role_config_overrides.clear()


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
# Core Three-Tier Role System (New Simplified Design)
# =============================================================================


@dataclass
class UserTier:
    """
    User tier definition for extending the base 'user' role.

    The core system has only 3 roles: visitor, user, admin
    The 'user' role can be extended with multiple tiers for flexible pricing.

    Billing Modes:
    - subscription: Traditional subscription-based (monthly/yearly)
    - pay_per_use: Pay-per-use billing (charged per request/usage)
    - prepaid: Prepaid billing (users prepay, then consume)
    - free: No billing (rate-limited free tier)

    Note: "proxy" tier_id indicates users accessing via an intermediary
    (e.g., platform, reseller, aggregator). The payment method (credits,
    cash, tokens) is determined by the intermediary, not the tier.
    """

    tier_id: str
    name: str
    description: str

    # Billing mode configuration
    billing_mode: str = "subscription"  # "subscription", "pay_per_use", "prepaid", "free"

    # Subscription-based billing (traditional)
    price: float = 0.0
    currency: str = "USD"
    billing_cycle: str = "monthly"

    # Pay-per-use / Prepaid billing
    balance_check_required: bool = False  # Whether to check balance before access
    minimum_balance: float = 0.0  # Minimum balance required for access
    rate_limit_per_hour: int = 1000  # Operations per hour (applies to all tiers)

    # Extensions to base user role
    additional_permissions: list[MCPPermission] = field(default_factory=list)
    limitation_overrides: dict[str, Any] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_pay_per_use(self) -> bool:
        """Check if this is a pay-per-use tier."""
        return self.billing_mode in ("pay_per_use", "prepaid")

    def requires_balance_check(self) -> bool:
        """Check if this tier requires balance validation."""
        return self.is_pay_per_use() and self.balance_check_required

    def is_subscription_tier(self) -> bool:
        """Check if this is a subscription-based tier."""
        return self.billing_mode == "subscription"

    def is_free_tier(self) -> bool:
        """Check if this is a free tier."""
        return self.billing_mode == "free"


# =============================================================================
# Proxy Access Configuration
# =============================================================================


@dataclass
class ProxyConfig:
    """
    Configuration for a single proxy (platform/reseller/aggregator).

    Proxies are intermediaries that can access the service on behalf of their users.
    Each proxy has its own API key and access configuration.

    Note: Pricing and revenue sharing are handled by the proxy platform,
    not by the developer's server.
    """

    name: str  # Unique identifier (e.g., "mcp-factory", "awesome-platform")
    api_key: str  # API key for authentication
    enabled: bool = True  # Whether this proxy is currently active
    rate_limit_per_hour: int | None = None  # Override tier rate limit if needed
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional info (e.g., contract_id, contact_email)


@dataclass
class AuthorizedProxies:
    """
    Authorized proxies configuration.

    Manages which proxies (platforms/resellers/aggregators) are authorized to access
    the service on behalf of their users. This represents commercial partnerships,
    not free access.

    Each proxy must be explicitly authorized by the developer and has specific terms:
    - API key for authentication
    - Revenue sharing agreement
    - Rate limits and other constraints
    """

    proxies: dict[str, ProxyConfig] = field(default_factory=dict)
    assigns_tier: str = "proxy_tier"  # Which tier proxies are assigned to

    def add_proxy(self, proxy: ProxyConfig) -> None:
        """Add an authorized proxy."""
        self.proxies[proxy.name] = proxy

    def remove_proxy(self, name: str) -> None:
        """Remove a proxy authorization."""
        if name in self.proxies:
            del self.proxies[name]

    def disable_proxy(self, name: str) -> None:
        """Temporarily disable a proxy without removing it."""
        if name in self.proxies:
            self.proxies[name].enabled = False

    def enable_proxy(self, name: str) -> None:
        """Re-enable a previously disabled proxy."""
        if name in self.proxies:
            self.proxies[name].enabled = True

    def is_authorized(self, api_key: str) -> bool:
        """Check if an API key belongs to an authorized and enabled proxy."""
        for proxy in self.proxies.values():
            if proxy.api_key == api_key and proxy.enabled:
                return True
        return False

    def get_proxy_by_key(self, api_key: str) -> ProxyConfig | None:
        """Get proxy configuration by API key."""
        for proxy in self.proxies.values():
            if proxy.api_key == api_key:
                return proxy
        return None

    def get_proxy_by_name(self, name: str) -> ProxyConfig | None:
        """Get proxy configuration by name."""
        return self.proxies.get(name)

    def get_enabled_proxies(self) -> list[ProxyConfig]:
        """Get all enabled proxies."""
        return [p for p in self.proxies.values() if p.enabled]


# =============================================================================
# TODO: Future Extensions (Low Priority)
# =============================================================================

# TODO: Add conditional permissions (priority: low)
# - Time-based permissions (business hours only)
# - IP-based permissions (geographic restrictions)
# - Usage-based permissions (after X operations)
