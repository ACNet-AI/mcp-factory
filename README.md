# mcp-factory

[![PyPI](https://img.shields.io/pypi/v/mcp-factory.svg)](https://pypi.org/project/mcp-factory/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/mcp-factory/)

A server factory based on [fastmcp](https://github.com/jlowin/fastmcp), supporting automatic registration of methods as tools, remote invocation, and permission-based management.

## Features

- 🔧 **Auto Tool Registration** - Automatically register FastMCP native methods as callable tools
- 🚀 **Remote Invocation** - Provide MCP-based remote method invocation
- 🔐 **Permission Control** - Server management based on authentication mechanisms
- 🏭 **Factory Pattern** - Batch creation and management of server instances
- 🔄 **Server Composition** - Support secure server mounting and importing operations
- 🔁 **Config Hot Reload** - Update configuration without restarting

## Installation

```bash
pip install mcp-factory  # Using pip
# or
uv install mcp-factory   # Using uv (recommended)
```

## Quick Start

```python
from mcp_factory import FastMCPFactory

# Create factory instance
factory = FastMCPFactory()

# Create authentication provider
factory.create_auth_provider(
    provider_id="demo-auth0",
    provider_type="auth0",
    config={
        "domain": "your-domain.auth0.com",
        "client_id": "your-client-id",
        "client_secret": "your-client-secret"
    }
)

# Create server with configuration file
server = factory.create_managed_server(
    config_path="config.yaml",
    auth_provider_id="demo-auth0",
    expose_management_tools=True
)

# Register custom tool
@server.tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    return a + b

# Start server
server.run()
```

## Configuration

Minimal configuration example:

```yaml
server:
  name: "my-mcp-server"
  instructions: "This is an example MCP server"
  host: "0.0.0.0"
  port: 8000

auth:
  provider_id: "demo-auth0"

tools:
  expose_management_tools: true
```

> For complete configuration examples, please refer to [examples/config.example.yaml](examples/config.example.yaml)

## Advanced Features

### Configuration Hot Reload

```python
# Reload configuration from specified path
result = server.reload_config("new_config.yaml")
print(result)  # Output: Server configuration reloaded (from new_config.yaml)
```

### Server Composition

```python
# Create two servers
server1 = factory.create_managed_server(config_path="main_config.yaml")
server2 = factory.create_managed_server(config_path="compute_config.yaml")

# Securely mount server
await server1.mount("compute", server2)

# Unmount server
server1.unmount("compute")
```

### Auto-registered Management Tools

When setting `expose_management_tools=True`, the server automatically registers management tools:

```python
# Get all auto-registered management tools
tools = await server.get_tools()
for tool in tools:
    if tool.name.startswith("manage_"):
        print(f"Management Tool: {tool.name} - {tool.description}")

# Example management tools
await server.manage_reload_config()  # Reload configuration
await server.manage_get_server_info()  # Get server information
await server.manage_list_mounted_servers()  # List mounted servers
```

> **Note**: MCP-Factory fully supports the native features of FastMCP, including lifecycle management (lifespan), tool serializers (tool_serializer), etc. Please refer to the FastMCP documentation for details.

## Common APIs

```python
# Authentication provider management
factory.create_auth_provider(provider_id="id", provider_type="auth0", config={})
factory.list_auth_providers()
factory.remove_auth_provider("id")

# Server management
factory.list_servers()
factory.delete_server("name")
factory.get_server("name")
```

For more examples and complete API documentation, please refer to the `examples/` directory.

## Roadmap

The following features are planned for future versions:

- **Command Line Tool** - Provide `mcpf` command-line tool to simplify the creation and management of servers and authentication providers
- **More Authentication Providers** - Add support for various authentication mechanisms such as OAuth2, JWT, etc.
- **Multi-environment Configuration** - Support configuration management for development, testing, production, and other environments