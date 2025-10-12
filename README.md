# MCP Factory

<div align="center">

![MCP Factory](https://img.shields.io/badge/MCP-Factory-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-Apache--2.0-red?style=for-the-badge)

**A factory framework focused on MCP server creation and management**

</div>

## 🎯 Overview

MCP Factory is a lightweight MCP (Model Context Protocol) server creation factory. It focuses on simplifying the building, configuration and management process of MCP servers, enabling developers to quickly create and deploy MCP servers.

### 🌟 Key Features

- **🏭 Server Factory** - Quickly create and configure MCP server instances
- **📁 Project Building** - Automatically generate complete MCP project structure
- **🔧 Configuration Management** - Flexible YAML configuration system
- **🔗 Server Mounting** - Support multi-server mounting and management
- **🛠️ CLI Tools** - Simple and easy-to-use command line interface
- **🔐 Permission Control** - Scope-based access control with 4-level permission system
- **⚙️ Management Tools** - FastMCP native methods exposed as server tools (20+ tools)
- **🛡️ Production Security** - Automatic security validation and flexible authentication

## 🚀 Quick Start

### Installation

```bash
pip install mcp-factory
```

### Basic Usage

#### 📋 Programmatic Mode
```python
from mcp_factory import MCPFactory

factory = MCPFactory(workspace_root="./workspace")
config = {
    "server": {"name": "api-server", "description": "Dynamic API server"},
    "components": {
        "tools": [{"module": "greeting_tools", "enabled": True}]
    }
}
server_id = factory.create_server("api-server", config)
```

#### 📄 Configuration File Mode
```yaml
# config.yaml
server:
  name: file-server
  description: "Server from configuration file"

management:
  expose_management_tools: true
  authorization: true

auth:
  provider: "none"  # or "oauth" for OAuth2 flow

components:
  tools:
    - module: "file_tools"
      enabled: true
```

```python
factory = MCPFactory(workspace_root="./workspace")
server_id = factory.create_server("file-server", "config.yaml")
```

#### 🏗️ Project Mode
```bash
mcp-factory project create my-server
```

#### 🚀 Direct Server Creation
```python
from mcp_factory import ManagedServer

server = ManagedServer(name="direct-server")

@server.tool()
def calculate(x: float, y: float, operation: str) -> float:
    """Perform mathematical calculations"""
    return x + y if operation == "add" else x * y

server.run()
```

## 🎛️ Operation Modes

| Mode | Best For | Key Features |
|------|----------|-------------|
| **📋 Dictionary** | Enterprise Integration, Testing | Programmatic control, dynamic configuration |
| **📄 Config File** | DevOps, Team Collaboration | Environment-specific deployment, standardized templates |
| **🏗️ Project** | Professional Development | Complex applications, full security features |

## 🛠️ CLI Usage

```bash
# Create new project
mcp-factory project create my-project

# Create shared component
mcp-factory config component create --type tools --name "auth_tools"

# Quick start temporary server
mcp-factory server quick

# Run server from config file or project name
mcp-factory server run config.yaml
mcp-factory server run my-project

# Run with custom transport
mcp-factory server run config.yaml --transport http --host 0.0.0.0 --port 8080

# Publish project to GitHub
mcp-factory project publish my-project

# List all servers
mcp-factory server list
```

### 🔐 Authentication Setup

**JWT Authentication (via environment variables)**
```bash
export FASTMCP_AUTH_BEARER_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
export FASTMCP_AUTH_BEARER_ISSUER="https://your-auth-server.com"
export FASTMCP_AUTH_BEARER_AUDIENCE="your-app-name"
```

**OAuth2 Authentication (via configuration)**
```yaml
auth:
  provider: "oauth"
  oauth:
    issuer_url: "https://your-auth-server.com"
    client_id: "your-client-id"
    scopes: ["openid", "mcp:read", "mcp:write", "mcp:admin"]
```

**Required Token Scopes:**
- `mcp:read` - readonly management tools
- `mcp:write` - modify management tools  
- `mcp:admin` - destructive management tools
- `mcp:external` - external system tools

## 🏗️ Architecture

### Core Components

- **MCPFactory** - Main factory class supporting all operation modes
- **ManagedServer** - Server class with decorator-based tool registration
- **Configuration System** - Flexible YAML configuration management
- **Project Builder** - Automatic project structure generation

### 🔧 Management Tools System

Our servers automatically register **20+ management tools** from FastMCP native methods with 4-level permission control:

**Permission Levels:** readonly → modify → destructive → external

**Key Tools:** `manage_get_tools`, `manage_add_tool`, `manage_remove_tool`, `manage_mount`, `manage_import_server`, etc.

## 📚 Examples & Testing

Check the [examples/](examples/) directory for complete usage examples:
- [Basic Server](examples/basic_server.py) - Simple MCP server
- [Factory Complete](examples/factory_complete.py) - Complete workflow
- [Server Mounting](examples/mounting_servers.py) - Multi-server mounting
- [Management Tools Demo](examples/demo/) - Interactive management tools

```bash
# Run tests
pytest

# Generate coverage report
pytest --cov=mcp_factory
```

## 📖 Documentation

- [Getting Started Guide](docs/getting-started.md) - Quick setup and basic usage
- [Configuration Guide](docs/configuration.md) - Detailed configuration options
- [CLI Usage Guide](docs/cli-guide.md) - Command-line interface documentation
- [Authorization System](docs/authorization/) - Permission management and security
- [Architecture Documentation](docs/architecture/) - System architecture and design

## 📄 License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details. 