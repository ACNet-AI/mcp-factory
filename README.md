# MCP Factory

<div align="center">

![MCP Factory](https://img.shields.io/badge/MCP-Factory-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-Apache--2.0-red?style=for-the-badge)

**A factory framework focused on MCP server creation and management**

</div>

## 🎯 Overview

MCP Factory is a lightweight MCP (Model Context Protocol) server creation factory. It focuses on simplifying the building, configuration and management process of MCP servers, enabling developers to quickly create and deploy MCP servers.

### 🌟 Core Features

- **🏭 Server Factory** - Quickly create and configure MCP server instances
- **📁 Project Building** - Automatically generate complete MCP project structure
- **🔧 Configuration Management** - Flexible YAML configuration system
- **🔗 Server Mounting** - Support multi-server mounting and management
- **🛠️ CLI Tools** - Simple and easy-to-use command line interface

## 🎛️ Three Operation Modes

MCP Factory supports three distinct operation modes, each designed for different use cases and user groups:

### 📋 1. Configuration Dictionary Mode - Programmatic Integration
```python
# Dynamic configuration example
config = {"server": {"name": "api-server"}, "tools": [...]}
server_id = factory.create_server("dynamic-server", config)
```

**Best for:**
- 🏢 **Enterprise Integration** - Embedding MCP servers in existing Python applications
- 🧪 **Testing & Prototyping** - Quick validation in Jupyter notebooks or unit tests
- 🔄 **Dynamic Configuration** - Generating configurations from databases or APIs
- ⚡ **Batch Operations** - Creating multiple similar servers programmatically

### 📄 2. Configuration File Mode - Declarative Deployment
```yaml
# config.yaml example
server:
  name: production-service
tools:
  - module: "auth_tools"
    enabled: true
```

**Best for:**
- 🚀 **DevOps & Deployment** - Environment-specific configurations (dev/staging/prod)
- 👥 **Team Collaboration** - Standardized configuration templates
- 🎓 **Learning & Simple Use Cases** - Low barrier to entry for newcomers
- 🔧 **Lightweight Services** - Quick deployment of simple MCP servers

### 🏗️ 3. Project Mode - Full Development Experience
```
my-mcp-project/
├── config.yaml           # Project configuration
├── tools/                # Custom tools
├── resources/            # Resources
└── server.py            # Entry point
```

**Best for:**
- 👨‍💻 **Professional Development** - Complex MCP applications with multiple components
- 🏗️ **Large Scale Projects** - Team development with code organization
- 🔄 **Long-term Maintenance** - Projects requiring continuous iteration
- 🧩 **Advanced Features** - Middleware, external mounting, complex architectures

### 🎯 Choosing the Right Mode

| Use Case | Recommended Mode | Why |
|----------|------------------|-----|
| Quick API integration | Dictionary | Programmatic control |
| Multi-environment deployment | Config File | Environment flexibility |
| Complex team project | Project | Full development structure |
| Learning MCP | Config File | Simple to start |
| Enterprise microservice | Dictionary | Dynamic integration |
| Production deployment | Config File | DevOps friendly |

## 🚀 Quick Start

### Installation

```bash
pip install mcp-factory
```

Or using uv:

```bash
uv add mcp-factory
```

### Getting Started with Different Modes

#### 📋 Mode 1: Configuration Dictionary (Programmatic)

```python
from mcp_factory import MCPFactory

# Create factory instance
factory = MCPFactory(workspace_root="./workspace")

# Create server with dynamic configuration
config = {
    "server": {
        "name": "api-server", 
        "description": "Dynamic API server"
    },
    "tools": [
        {
            "module": "greeting_tools",
            "functions": [
                {
                    "name": "hello",
                    "description": "Greet a user",
                    "parameters": {"name": {"type": "str", "description": "User name"}}
                }
            ]
        }
    ]
}

# Create and run server
server_id = factory.create_server("api-server", config)
```

#### 📄 Mode 2: Configuration File (Declarative)

```yaml
# config.yaml
server:
  name: file-server
  description: "Server from configuration file"

tools:
  - module: "file_tools"
    enabled: true
    functions:
      - name: "read_file"
        description: "Read file contents"
        parameters:
          path:
            type: "str"
            description: "File path"
```

```python
from mcp_factory import MCPFactory

factory = MCPFactory(workspace_root="./workspace")

# Create server from config file
server_id = factory.create_server("file-server", "config.yaml")
```

#### 🏗️ Mode 3: Project Mode (Full Development)

```bash
# Use CLI to create complete project
mcp-factory project create my-advanced-server

# Or programmatically
from mcp_factory import MCPFactory

factory = MCPFactory(workspace_root="./workspace")

# Build complete project structure
project_path = factory.build_project(
    "my-advanced-server",
    {"server": {"description": "Advanced MCP server with full structure"}}
)

# Create server from project
server_id = factory.create_server("my-advanced-server", project_path)
```

#### 🚀 Alternative: Direct Server Creation

For simple use cases, you can also create servers directly without the factory:

```python
from mcp_factory import ManagedServer

server = ManagedServer(name="direct-server")

@server.tool()
def calculate(x: float, y: float, operation: str) -> float:
    """Perform mathematical calculations"""
    return x + y if operation == "add" else x * y

server.run()
```

#### 🛠️ CLI Usage

```bash
# Create new project
mcp-factory project create my-project

# Create shared component
mcp-factory config component create --type tools --name "auth_tools"

# Run server from config file
mcp-factory server run config.yaml

# Run with custom transport
mcp-factory server run config.yaml --transport http --host 0.0.0.0 --port 8080

# List all servers
mcp-factory server list
```

## 📁 Project Structure

```
mcp-factory/
├── mcp_factory/           # Core modules
│   ├── factory.py         # Factory main class
│   ├── server.py          # Managed server
│   ├── config/            # Configuration management
│   ├── project/           # Project building
│   ├── mounting/          # Server mounting
│   └── cli.py             # Command line tools
├── examples/              # Usage examples
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🛠️ Core Components

### MCPFactory
Factory main class for creating and managing MCP servers. Supports all three operation modes and provides workspace management capabilities.

### ManagedServer  
Managed server class providing complete MCP server functionality with decorator-based tool registration and built-in lifecycle management.

## 📚 Examples

Check the [examples/](examples/) directory for more usage examples:

- [Basic Server](examples/basic_server.py) - Create simple MCP server
- [Factory Complete Example](examples/factory_complete.py) - Complete workflow using factory
- [Server Mounting](examples/mounting_servers.py) - Multi-server mounting

## 🧪 Testing

```bash
# Run all tests
pytest

# Generate coverage report
pytest --cov=mcp_factory

# Type checking
mypy mcp_factory

# Code formatting
ruff format .
ruff check .
```

## 📖 Documentation

- [Configuration Guide](docs/configuration.md)
- [CLI Usage Guide](docs/cli-guide.md)
- [Architecture Documentation](docs/architecture/)

## 🤝 Contributing

Contributions are welcome! Please check our contribution guidelines.

## 📄 License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

---

> **Note**: This is the stable version of MCP Factory (v1.0.0), focusing on core factory functionality with full type safety and modern Python practices. 