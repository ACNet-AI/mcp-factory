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

## 🚀 Quick Start

### Installation

```bash
pip install mcp-factory
```

Or using uv:

```bash
uv add mcp-factory
```

### Basic Usage

Choose your preferred approach:

#### 📋 Programmatic Mode (Dictionary Configuration)

```python
from mcp_factory import MCPFactory

factory = MCPFactory(workspace_root="./workspace")

config = {
    "server": {
        "name": "api-server", 
        "description": "Dynamic API server"
    },
    "components": {
        "tools": [
            {
                "module": "greeting_tools",
                "enabled": True,
                "description": "Greeting tools module"
            }
        ]
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

components:
  tools:
    - module: "file_tools"
      enabled: true
      description: "File handling tools"
```

```python
from mcp_factory import MCPFactory

factory = MCPFactory(workspace_root="./workspace")
server_id = factory.create_server("file-server", "config.yaml")
```

#### 🏗️ Project Mode

```bash
# Create complete project structure
mcp-factory project create my-advanced-server

# Or programmatically
factory = MCPFactory(workspace_root="./workspace")
project_path = factory.build_project(
    "my-advanced-server",
    {"server": {"description": "Advanced MCP server with full structure"}}
)
server_id = factory.create_server("my-advanced-server", project_path)
```

#### 🚀 Direct Server Creation

For simple use cases without the factory:

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

| Mode | Best For | When to Use |
|------|----------|-------------|
| **📋 Dictionary** | Enterprise Integration, Testing | Programmatic control, dynamic configuration |
| **📄 Config File** | DevOps, Team Collaboration | Environment-specific deployment, standardized templates |
| **🏗️ Project** | Professional Development | Complex applications, long-term maintenance |

## 🛠️ CLI Usage

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

## 🏗️ Architecture

### Core Components

- **MCPFactory** - Main factory class supporting all operation modes
- **ManagedServer** - Server class with decorator-based tool registration
- **Configuration System** - Flexible YAML configuration management
- **Project Builder** - Automatic project structure generation

### Project Structure

```
mcp-factory/
├── mcp_factory/           # Core modules
│   ├── factory.py         # Factory main class
│   ├── server.py          # Managed server
│   ├── config/            # Configuration management
│   ├── project/           # Project building
│   ├── mounting/          # Server mounting
│   └── cli/               # Command line tools
├── examples/              # Usage examples
├── tests/                 # Test suite
└── docs/                  # Documentation
```

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