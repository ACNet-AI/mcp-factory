"""Tool configuration definitions for ManagedServer.

This module contains the configuration data for all tools that can be
registered by ManagedServer, including management tools and user permission tools.
"""

from typing import Any

# Custom management methods (defined in ManagedServer class, guaranteed to exist)
SELF_IMPLEMENTED_METHODS: dict[str, dict[str, Any]] = {
    # Meta management tools - Manage management tools themselves
    "get_management_tools_info": {
        "description": "Get information and status of currently registered management tools",
        "async": False,
        "title": "View management tool information",
        "annotation_type": "readonly",
        "no_params": True,
        "tags": {"readonly", "safe", "meta", "introspection"},
        "enabled": True,
    },
    "clear_management_tools": {
        "description": "Clear all registered management tools (excluding meta management tools)",
        "async": False,
        "title": "Clear management tools",
        "annotation_type": "destructive",
        "no_params": True,
        "tags": {"admin", "destructive", "dangerous", "meta"},
        "enabled": True,
    },
    "recreate_management_tools": {
        "description": "Recreate all management tools (smart deduplication, won't affect meta tools)",
        "async": False,
        "title": "Recreate management tools",
        "annotation_type": "destructive",
        "no_params": True,
        "tags": {"admin", "modify", "meta", "recovery"},
        "enabled": True,
    },
    "reset_management_tools": {
        "description": "Completely reset management tool system (clear then rebuild, dangerous operation)",
        "async": False,
        "title": "Reset management tool system",
        "annotation_type": "destructive",
        "no_params": True,
        "tags": {"admin", "destructive", "dangerous", "meta", "emergency"},
        "enabled": True,
    },
    "toggle_management_tool": {
        "description": "Dynamically enable/disable specified management tool",
        "async": False,
        "title": "Toggle tool status",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "meta", "dynamic"},
        "enabled": True,
    },
    "get_tools_by_tags": {
        "description": "Filter and display management tools by tags",
        "async": False,
        "title": "Query tools by tags",
        "annotation_type": "readonly",
        "tags": {"readonly", "safe", "meta", "query"},
        "enabled": True,
    },
    # Permission Management - ManagedServer extensions
    "debug_permission": {
        "description": "Debug permission check process with detailed diagnostics",
        "async": False,
        "title": "Debug permission",
        "annotation_type": "readonly",
        "tags": {"admin", "debug", "permission", "diagnostic"},
        "enabled": True,
    },
    "review_permission_requests": {
        "description": "Review and approve/reject permission requests",
        "async": False,
        "title": "Review permission requests",
        "annotation_type": "destructive",
        "tags": {"admin", "permission", "review", "saas"},
        "enabled": True,
    },
    "assign_role": {
        "description": "Assign role to user (admin operation)",
        "async": False,
        "title": "Assign user role",
        "annotation_type": "destructive",
        "tags": {"admin", "permission", "assign", "saas"},
        "enabled": True,
    },
    "revoke_role": {
        "description": "Revoke role from user (admin operation)",
        "async": False,
        "title": "Revoke user role",
        "annotation_type": "destructive",
        "tags": {"admin", "permission", "revoke", "saas"},
        "enabled": True,
    },
}

# FastMCP native methods (inherited from FastMCP, need existence check)
FASTMCP_NATIVE_METHODS: dict[str, dict[str, Any]] = {
    # Query methods - Safe, read-only operations
    "get_tools": {
        "description": "Get all registered tools on the server",
        "async": True,
        "title": "View tool list",
        "annotation_type": "readonly",
        "no_params": True,
        "tags": {"readonly", "safe", "query"},
        "enabled": True,
    },
    "get_resources": {
        "description": "Get all registered resources on the server",
        "async": True,
        "title": "View resource list",
        "annotation_type": "readonly",
        "no_params": True,
        "tags": {"readonly", "safe", "query"},
        "enabled": True,
    },
    "get_resource_templates": {
        "description": "Get all registered resource templates on the server",
        "async": True,
        "title": "View resource templates",
        "annotation_type": "readonly",
        "no_params": True,
        "tags": {"readonly", "safe", "query"},
        "enabled": True,
    },
    "get_prompts": {
        "description": "Get all registered prompts on the server",
        "async": True,
        "title": "View prompt templates",
        "annotation_type": "readonly",
        "no_params": True,
        "tags": {"readonly", "safe", "query"},
        "enabled": True,
    },
    # Server composition management - High-risk operations
    "mount": {
        "description": "Mount another FastMCP server to the current server",
        "async": False,
        "title": "Mount server",
        "annotation_type": "external",
        "tags": {"admin", "external", "dangerous", "composition"},
        "enabled": True,
    },
    "import_server": {
        "description": "Import all tools and resources from another FastMCP server",
        "async": True,
        "title": "Import server",
        "annotation_type": "external",
        "tags": {"admin", "external", "dangerous", "composition"},
        "enabled": True,
    },
    # Dynamic management - Medium risk operations
    "add_tool": {
        "description": "Dynamically add tool to server",
        "async": False,
        "title": "Add tool",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "dynamic"},
        "enabled": True,
    },
    "remove_tool": {
        "description": "Remove specified tool from server",
        "async": False,
        "title": "Remove tool",
        "annotation_type": "destructive",
        "tags": {"admin", "destructive", "dangerous", "dynamic"},
        "enabled": True,
    },
    "add_resource": {
        "description": "Dynamically add resource to server",
        "async": False,
        "title": "Add resource",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "dynamic"},
        "enabled": True,
    },
    "add_prompt": {
        "description": "Dynamically add prompt to server",
        "async": False,
        "title": "Add prompt template",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "dynamic"},
        "enabled": True,
    },
    "add_template": {
        "description": "Add a resource template to the server",
        "async": False,
        "title": "Add resource template",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "dynamic"},
        "enabled": True,
    },
    "add_resource_fn": {
        "description": "Add a resource or template to the server from a function",
        "async": False,
        "title": "Add resource from function",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "dynamic", "advanced"},
        "enabled": True,
    },
    "add_middleware": {
        "description": "Add middleware to the server",
        "async": False,
        "title": "Add middleware",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "middleware", "advanced"},
        "enabled": True,
    },
    # Tool Transformation - FastMCP 2.8.0+ feature
    "transform_tool": {
        "description": "Transform existing tools using Tool Transformation API. Use manage_get_tools.",
        "async": False,
        "title": "Transform tool",
        "annotation_type": "destructive",
        "tags": {"admin", "modify", "transform", "advanced"},
        "enabled": True,
    },
}

# User permission tools (registered as regular tools, not management tools)
USER_PERMISSION_TOOLS: dict[str, dict[str, Any]] = {
    "request_permission_upgrade": {
        "description": "Request permission upgrade - users can request role upgrades",
        "method": "_request_permission_impl",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "permission", "self-service"},
        "enabled": True,
    },
    "view_my_permissions": {
        "description": "View my permissions - view current roles, permissions and usage limits",
        "method": "_view_my_permissions_impl",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "permission", "readonly", "self-service"},
        "enabled": True,
    },
    "view_my_permission_requests": {
        "description": "View my request history - view permission request status and history records",
        "method": "_view_my_requests_impl",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "permission", "readonly", "self-service"},
        "enabled": True,
    },
}

# User billing self-service tools (non-management tools)
USER_BILLING_TOOLS: dict[str, dict[str, Any]] = {
    "purchase_plan": {
        "description": "Purchase subscription plan - buy or upgrade your subscription",
        "method": "_purchase_plan_impl",
        "annotations": {
            "readOnlyHint": False,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "billing", "self-service"},
        "enabled": True,
    },
    "view_my_subscription": {
        "description": "View my subscription - check current plan and usage status",
        "method": "_view_my_subscription_impl",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "billing", "readonly", "self-service"},
        "enabled": True,
    },
    "view_available_plans": {
        "description": "View available plans - browse subscription options and pricing",
        "method": "_view_available_plans_impl",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "billing", "readonly", "self-service"},
        "enabled": True,
    },
    "view_my_usage": {
        "description": "View my usage - check current usage statistics and limits",
        "method": "_view_my_usage_impl",
        "annotations": {
            "readOnlyHint": True,
            "destructiveHint": False,
            "openWorldHint": False,
        },
        "tags": {"user", "billing", "readonly", "self-service"},
        "enabled": True,
    },
}


def get_management_method_configs() -> dict[str, dict[str, Any]]:
    """Get all management method configurations.

    Returns:
        Dictionary containing all management tool configurations.
        Keys are method names, values are configuration dictionaries.
    """
    return {**SELF_IMPLEMENTED_METHODS, **FASTMCP_NATIVE_METHODS}


def get_self_implemented_methods() -> dict[str, dict[str, Any]]:
    """Get self-implemented management method configurations.

    Returns:
        Dictionary containing only self-implemented management tool configurations.
    """
    return SELF_IMPLEMENTED_METHODS.copy()


def get_fastmcp_native_methods() -> dict[str, dict[str, Any]]:
    """Get FastMCP native method configurations.

    Returns:
        Dictionary containing only FastMCP native method configurations.
    """
    return FASTMCP_NATIVE_METHODS.copy()


def get_user_permission_tools() -> dict[str, dict[str, Any]]:
    """Get user permission tool configurations.

    Returns:
        Dictionary containing user permission tool configurations.
    """
    return USER_PERMISSION_TOOLS.copy()


def get_user_billing_tools() -> dict[str, dict[str, Any]]:
    """Get user billing tool configurations.

    Returns:
        Dictionary containing user billing tool configurations.
    """
    return USER_BILLING_TOOLS.copy()


def get_methods_by_annotation_type(annotation_type: str) -> dict[str, dict[str, Any]]:
    """Get management methods filtered by annotation type.

    Args:
        annotation_type: The annotation type to filter by (readonly, destructive, etc.)

    Returns:
        Dictionary containing methods matching the annotation type.
    """
    all_methods = get_management_method_configs()
    return {name: config for name, config in all_methods.items() if config.get("annotation_type") == annotation_type}


def get_methods_by_tags(include_tags: set[str], exclude_tags: set[str] | None = None) -> dict[str, dict[str, Any]]:
    """Get management methods filtered by tags.

    Args:
        include_tags: Tags that must be present
        exclude_tags: Tags that must not be present

    Returns:
        Dictionary containing methods matching the tag criteria.
    """
    exclude_tags = exclude_tags or set()
    all_methods = get_management_method_configs()

    result = {}
    for name, config in all_methods.items():
        method_tags = config.get("tags", set())

        # Check if all include_tags are present
        if not include_tags.issubset(method_tags):
            continue

        # Check if any exclude_tags are present
        if exclude_tags.intersection(method_tags):
            continue

        result[name] = config

    return result
