# fastmcp-factory

[![PyPI](https://img.shields.io/pypi/v/fastmcp-factory.svg)](https://pypi.org/project/fastmcp-factory/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/fastmcp-factory/)

Manageable server factory based on [fastmcp](https://github.com/jlowin/fastmcp), automatically registering native methods as tools, supporting remote invocation and permission-based management control.

## Features

- 🔧 **Auto Tool Registration**: Automatically register FastMCP's native methods as callable tools
- 🚀 **Remote Invocation**: Provide MCP-based remote method calling
- 🔐 **Permission Control**: Implement server management based on authentication mechanisms
- 🏭 **Factory Pattern**: Batch creation of managed server instances
- 🔄 **Server Composition**: Support secure server mounting and importing operations
- 🔁 **Config Hot Reload**: Update configuration without restarting services

## Installation

```bash
# Using pip
pip install fastmcp-factory

# Or using uv (recommended)
uv install fastmcp-factory
```

## Quick Start

```python
from fastmcp_factory import FastMCPFactory
from fastmcp_factory.auth.auth0 import Auth0Provider

# Create Auth0 authentication provider
auth_provider = Auth0Provider(
    domain="your-domain.auth0.com",
    client_id="your-client-id",
    client_secret="your-client-secret"
)

# Create factory instance
factory = FastMCPFactory(auth_server_provider=auth_provider)

# Create managed server (auto-register FastMCP methods as tools)
server = factory.create_managed_server(
    name="demo-server", 
    instructions="Example server",
    auto_register=True,
    auth={"issuer_url": "https://your-domain.auth0.com"}
)

# Register custom tool
@server.tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

# Start server
server.run(host="0.0.0.0", port=8000)
```

## Auto-registered Management Tools

When setting `auto_register=True`, the server automatically registers the following management tools:

```python
# Get all auto-registered management tools
tools = await server.get_tools()
for tool in tools:
    if tool.name.startswith("mcp_"):
        print(f"Management Tool: {tool.name} - {tool.description}")

# Example management tools
await server.mcp_reload_config()  # Reload configuration
await server.mcp_get_server_info()  # Get server information
await server.mcp_list_mounted_servers()  # List mounted servers
await server.mcp_get_auth_config()  # Get authentication configuration
```

## Configuration Hot Reload

```python
# Reload configuration from specified path
result = server.reload_config("/path/to/config.json")
print(result)  # Output: Server configuration reloaded (from /path/to/config.json)
```

## Server Composition

```python
# Create two servers
server1 = factory.create_managed_server(name="main-server")
server2 = factory.create_managed_server(name="compute-server")

# Securely mount server
await server1.mount("compute", server2)

# Unmount server
server1.unmount("compute")
```

## License

This project is licensed under the [Apache License 2.0](LICENSE).