"""Configuration file JSON Schema definition

Contains JSON Schema specification for FastMCP server configuration files
"""

import textwrap
from typing import Any

# JSON Schema based on FastMCP 2.7.0 configuration files
SERVER_CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["server"],
    "properties": {
        # ===================================================================
        # Group 1: Core Configuration (Required for new users) - Basic and commonly used
        # ===================================================================
        # FastMCP constructor parameters (excluding function objects)
        "server": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Server name, used to identify this MCP server instance",
                },
                "instructions": {
                    "type": "string",
                    "description": ("Server instructions, providing guidance to clients on how to use this server"),
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": ("Server tag list, used to identify and categorize server instances"),
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": ("Server dependency list, used to specify dependencies required by the server"),
                },
                "cache_expiration_seconds": {
                    "type": "number",
                    "description": ("Cache expiration time (seconds), used to control internal cache lifetime"),
                    "default": 0,
                },
                "on_duplicate_tools": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate tools",
                    "default": "warn",
                },
                "on_duplicate_resources": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate resources",
                    "default": "warn",
                },
                "on_duplicate_prompts": {
                    "type": "string",
                    "enum": ["warn", "error", "replace", "ignore"],
                    "description": "Strategy for handling duplicate prompts",
                    "default": "warn",
                },
                "resource_prefix_format": {
                    "type": "string",
                    "enum": ["protocol", "path"],
                    "description": "Resource URI prefix format: 'protocol' (prefix+resource://path) or 'path' (resource://prefix/path)",
                    "default": "path",
                },
                "mask_error_details": {
                    "type": "boolean",
                    "description": "Whether to mask error details in responses, only showing explicitly raised errors",
                    "default": False,
                },
            },
        },
        # Transport and network configuration (set at startup, not runtime dynamic parameters)
        "transport": {
            "type": "object",
            "description": textwrap.dedent("""
                Transport and network configuration for FastMCP server startup.
                Controls how the server communicates (stdio, HTTP) and network settings.
                Note: These are startup parameters, not runtime-modifiable parameters.
                For runtime parameter management, see server-level and settings-level parameters.
            """).strip(),
            "properties": {
                "transport": {
                    "type": "string",
                    "enum": ["stdio", "streamable-http", "sse"],
                    "description": textwrap.dedent("""
                        Server transport protocol:
                        - 'stdio' (default): Standard input/output, best for local tools and Claude Desktop
                        - 'streamable-http': Modern HTTP transport, recommended for web deployments (FastMCP 2.3.0+)
                        - 'sse': Server-Sent Events, deprecated - prefer streamable-http for new projects
                    """).strip(),
                    "default": "stdio",
                },
                # HTTP transport common parameters (shared by streamable-http and sse)
                "host": {
                    "type": "string",
                    "description": "HTTP server listening address, use 0.0.0.0 to listen on all network interfaces",
                    "default": "127.0.0.1",
                },
                "port": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 65535,
                    "description": "HTTP server listening port",
                    "default": 8000,
                },
                "log_level": {
                    "type": "string",
                    "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    "description": "Startup log level for the server (different from runtime log_level setting)",
                    "default": "INFO",
                },
                "path": {
                    "type": "string",
                    "description": textwrap.dedent("""
                        Transport endpoint path:
                        - streamable-http default: '/mcp'
                        - sse default: '/sse'
                        - stdio: ignored (not applicable)
                    """).strip(),
                },
                # Uvicorn server configuration (HTTP transports only)
                "uvicorn_config": {
                    "type": "object",
                    "description": "Additional configuration passed directly to Uvicorn server (HTTP transports only)",
                    "additionalProperties": True,
                    "properties": {
                        "access_log": {"type": "boolean", "description": "Enable/disable access log", "default": True},
                        "reload": {
                            "type": "boolean",
                            "description": "Enable auto-reload on file changes (development only)",
                            "default": False,
                        },
                        "workers": {
                            "type": "integer",
                            "minimum": 1,
                            "description": "Number of worker processes (production only)",
                            "default": 1,
                        },
                    },
                },
                # Starlette middleware configuration (HTTP transports only)
                "middleware": {
                    "type": "array",
                    "description": "Starlette middleware configuration for HTTP transports",
                    "items": {
                        "type": "object",
                        "properties": {
                            "class": {"type": "string", "description": "Middleware class path"},
                            "args": {"type": "array", "description": "Middleware arguments"},
                            "kwargs": {"type": "object", "description": "Middleware keyword arguments"},
                        },
                        "required": ["class"],
                    },
                },
            },
        },
        # ===================================================================
        # Group 2: Feature Configuration (Optional for common use) - Simple and practical
        # ===================================================================
        # ManagedServer extensions
        "management": {
            "type": "object",
            "properties": {
                "expose_management_tools": {
                    "type": "boolean",
                    "description": "Whether to automatically register FastMCP methods as management tools",
                    "default": True,
                },
                "authorization": {
                    "type": ["boolean", "null"],
                    "description": textwrap.dedent("""
                        Whether to enable authorization system for management tools:
                        - null (default): Auto-enable when expose_management_tools=true and auth is configured
                        - true: Force enable authorization system
                        - false: Disable authorization (development only, not recommended for production)
                    """).strip(),
                    "default": None,
                },
            },
        },
        # MCP component declarations - based on actual project directory structure
        "components": {
            "type": "object",
            "description": textwrap.dedent("""
                MCP component declarations based on actual project directory structure.
                Components are automatically discovered and loaded from:
                - tools/ directory (*.py files with register_tool function)
                - resources/ directory (*.py files with register_resource function)
                - prompts/ directory (*.py files with register_prompt function)
            """).strip(),
            "properties": {
                "tools": {
                    "type": "array",
                    "description": "Tool declarations - each tool must exist as a .py file in tools/ directory",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Component name for identification and deduplication",
                            },
                            "module": {
                                "type": "string",
                                "description": "Python module name in tools/ directory (without .py extension)",
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether to load this tool",
                                "default": True,
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorizing and filtering this tool (e.g., ['admin'])",
                                "default": [],
                            },
                            "description": {
                                "type": "string",
                                "description": "Tool description for documentation",
                            },
                            "category": {
                                "type": "string",
                                "description": "Tool category for organization",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional metadata for the tool",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["module"],
                        "additionalProperties": False,
                    },
                },
                "resources": {
                    "type": "array",
                    "description": (
                        "Resource declarations - each resource must exist as a .py file in resources/ directory"
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Component name for identification and deduplication",
                            },
                            "module": {
                                "type": "string",
                                "description": "Python module name in resources/ directory (without .py extension)",
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether to load this resource",
                                "default": True,
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorizing and filtering this resource (e.g., ['public'])",
                                "default": [],
                            },
                            "description": {
                                "type": "string",
                                "description": "Resource description for documentation",
                            },
                            "uri_template": {
                                "type": "string",
                                "description": "Resource URI template (if different from module name)",
                            },
                            "category": {
                                "type": "string",
                                "description": "Resource category for organization",
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional metadata for the resource",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["module"],
                        "additionalProperties": False,
                    },
                },
                "prompts": {
                    "type": "array",
                    "description": "Prompt declarations - each prompt must exist as a .py file in prompts/ directory",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "Component name for identification and deduplication",
                            },
                            "module": {
                                "type": "string",
                                "description": "Python module name in prompts/ directory (without .py extension)",
                            },
                            "enabled": {
                                "type": "boolean",
                                "description": "Whether to load this prompt",
                                "default": True,
                            },
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Tags for categorizing and filtering this prompt (e.g., ['system'])",
                                "default": [],
                            },
                            "description": {
                                "type": "string",
                                "description": "Prompt description for documentation",
                            },
                            "category": {
                                "type": "string",
                                "description": "Prompt category for organization",
                            },
                            "arguments": {
                                "type": "array",
                                "description": "Prompt argument definitions",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "required": {"type": "boolean", "default": False},
                                        "type": {
                                            "type": "string",
                                            "enum": ["string", "number", "boolean", "array", "object"],
                                        },
                                    },
                                    "required": ["name", "description"],
                                },
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional metadata for the prompt",
                                "additionalProperties": True,
                            },
                        },
                        "required": ["module"],
                        "additionalProperties": False,
                    },
                },
                "auto_discovery": {
                    "type": "object",
                    "description": "Automatic component discovery settings",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": (
                                "Whether to enable automatic discovery of components not explicitly declared"
                            ),
                            "default": True,
                        },
                        "scan_directories": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Directories to scan for components",
                            "default": ["tools", "resources", "prompts"],
                        },
                        "ignore_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "File patterns to ignore during discovery",
                            "default": ["__pycache__", "*.pyc", "__init__.py"],
                        },
                    },
                },
            },
        },
        # ===================================================================
        # Group 3: Advanced Configuration (For advanced users) - Complex and professional
        # ===================================================================
        # MCP protocol middleware configuration (works with all transports: stdio, HTTP, SSE)
        "middleware": {
            "type": "array",
            "description": textwrap.dedent("""
                MCP protocol layer middleware configuration.
                These middleware operate at the MCP protocol level and work with all transport types
                (stdio, streamable-http, sse). They can intercept and modify MCP requests/responses,
                add logging, implement rate limiting, handle errors, and provide other cross-cutting concerns.

                Available built-in middleware types:
                - timing: Performance monitoring and request timing
                - logging: Request/response logging with configurable detail levels
                - rate_limiting: Request rate limiting and throttling
                - error_handling: Centralized error handling and transformation
                - custom: Custom middleware implementation (requires class path)
            """).strip(),
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["timing", "logging", "rate_limiting", "error_handling", "custom"],
                        "description": "Middleware type - built-in types or 'custom' for custom implementations",
                    },
                    "config": {
                        "type": "object",
                        "description": "Middleware-specific configuration parameters",
                        "additionalProperties": True,
                        "default": {},
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether this middleware is enabled",
                        "default": True,
                    },
                    "class": {
                        "type": "string",
                        "description": "Custom middleware class path (required when type='custom')",
                    },
                    "args": {
                        "type": "array",
                        "description": "Custom middleware constructor arguments (for type='custom')",
                        "default": [],
                    },
                    "kwargs": {
                        "type": "object",
                        "description": "Custom middleware constructor keyword arguments (for type='custom')",
                        "default": {},
                    },
                },
                "required": ["type"],
                "additionalProperties": False,
                "if": {"properties": {"type": {"const": "custom"}}},
                "then": {"required": ["type", "class"]},
            },
        },
        # Authentication configuration - used to create AuthProvider objects (passed through FastMCP's auth parameter)
        "auth": {
            "type": "object",
            "properties": {
                "provider": {
                    "type": "string",
                    "enum": ["oauth", "none"],
                    "description": textwrap.dedent("""
                        Authentication provider type:
                        - 'none': Use FastMCP default behavior (automatically checks for JWT environment variables)
                        - 'oauth': Use OAuth2 authorization flow with explicit configuration

                        JWT Environment Variables (when provider='none'):
                        - FASTMCP_AUTH_BEARER_PUBLIC_KEY: JWT verification public key (PEM format)
                        - FASTMCP_AUTH_BEARER_ISSUER: JWT issuer URL (e.g., https://auth0.com/, https://okta.com/oauth2/default)
                        - FASTMCP_AUTH_BEARER_AUDIENCE: JWT audience claim validation (optional)
                        - FASTMCP_AUTH_BEARER_JWKS_URI: JWKS endpoint for dynamic key retrieval (optional)

                        Compatible with: Auth0, Okta, Azure AD, AWS Cognito, and other JWT-issuing identity providers.
                    """).strip(),
                    "default": "none",
                },
                # OAuth2 Authentication - complete OAuth2 authorization code flow
                "oauth": {
                    "type": "object",
                    "description": "OAuth2 authorization code flow configuration",
                    "properties": {
                        "issuer_url": {
                            "type": "string",
                            "format": "uri",
                            "description": "OAuth2 authorization server URL",
                        },
                        "client_id": {
                            "type": "string",
                            "description": "OAuth2 client identifier",
                        },
                        "client_secret": {
                            "type": "string",
                            "description": "OAuth2 client secret (supports environment variable references)",
                        },
                        "redirect_uri": {
                            "type": "string",
                            "format": "uri",
                            "description": "OAuth2 redirect URI after authorization",
                        },
                        "scopes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Required OAuth2 scopes (include mcp:read, mcp:write, mcp:admin as needed)",
                            "default": ["openid", "profile", "mcp:read"],
                        },
                        "response_type": {
                            "type": "string",
                            "enum": ["code", "token", "id_token"],
                            "description": "OAuth2 response type",
                            "default": "code",
                        },
                        "service_documentation_url": {
                            "type": "string",
                            "format": "uri",
                            "description": "Service documentation URL",
                        },
                    },
                    "required": ["issuer_url", "client_id", "client_secret", "redirect_uri"],
                    "additionalProperties": False,
                },
            },
            "additionalProperties": False,
            "anyOf": [
                {"properties": {"provider": {"const": "oauth"}}, "required": ["oauth"]},
                {"properties": {"provider": {"const": "none"}}},
            ],
        },
        # External MCP server configuration - follows FastMCP MCPConfig standards
        "mcpServers": {
            "type": "object",
            "description": textwrap.dedent("""
                Configuration for external MCP servers following FastMCP MCPConfig standard.
                Supports local scripts (stdio), remote HTTP endpoints (streamable-http/sse).
                This matches the standard MCPConfig format used by FastMCP clients.
            """).strip(),
            "patternProperties": {
                "^[a-zA-Z][a-zA-Z0-9_-]*$": {
                    "type": "object",
                    "description": "Individual MCP server configuration",
                    "oneOf": [
                        {
                            "description": "Local script server (stdio transport)",
                            "properties": {
                                "command": {
                                    "type": "string",
                                    "description": "Command to execute (e.g., 'python', 'node')",
                                },
                                "args": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Command arguments including script path",
                                    "maxItems": 20,
                                },
                                "env": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                    "description": "Environment variables for the server process",
                                    "maxProperties": 30,
                                },
                                "transport": {
                                    "type": "string",
                                    "enum": ["stdio"],
                                    "description": "Transport protocol (optional - defaults to 'stdio')",
                                },
                                "timeout": {
                                    "type": "integer",
                                    "minimum": 5,
                                    "maximum": 120,
                                    "default": 30,
                                    "description": "Startup timeout in seconds",
                                },
                            },
                            "required": ["command", "args"],
                            "additionalProperties": False,
                        },
                        {
                            "description": "Remote HTTP server (streamable-http/sse transport)",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "format": "uri",
                                    "description": "HTTP endpoint URL for the MCP server",
                                },
                                "transport": {
                                    "type": "string",
                                    "enum": ["streamable-http", "sse"],
                                    "description": "HTTP transport protocol (optional - auto-inferred)",
                                },
                                "headers": {
                                    "type": "object",
                                    "additionalProperties": {"type": "string"},
                                    "description": "HTTP headers for authentication or other purposes",
                                    "maxProperties": 20,
                                },
                                "timeout": {
                                    "type": "number",
                                    "minimum": 1,
                                    "maximum": 300,
                                    "default": 30,
                                    "description": "Request timeout in seconds",
                                },
                                "verify_ssl": {
                                    "type": "boolean",
                                    "description": "Verify SSL certificates",
                                    "default": True,
                                },
                            },
                            "required": ["url"],
                            "additionalProperties": False,
                        },
                    ],
                },
            },
            "additionalProperties": False,
        },
    },
}
