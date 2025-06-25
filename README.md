# MCP Factory

<div align="center">

![MCP Factory](https://img.shields.io/badge/MCP-Factory-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11+-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-red?style=for-the-badge)

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

#### 1. Create project using factory

```python
from mcp_factory import MCPFactory

# Create factory instance
factory = MCPFactory(workspace_root="./workspace")

# Build new MCP project
project_path = factory.build_project(
    "my-server", 
    {"server": {"description": "My first MCP server"}}
)

# Create server instance
server_id = factory.create_server(
    name="my-server",
    source=project_path
)
```

#### 2. Directly create managed server

```python
from mcp_factory import ManagedServer

# Create managed server
server = ManagedServer(
    name="example-server",
    instructions="This is an example server"
)

# Add tools
@server.tool()
def hello(name: str) -> str:
    """Greet the specified user"""
    return f"Hello, {name}!"

# Run server
server.run()
```

#### 3. Using CLI tools

```bash
# Quickly create project
mcp-factory create my-project

# Run from configuration file
mcp-factory run config.yaml
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
│   └── cli/               # Command line tools
├── examples/              # Usage examples
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## 🛠️ Core Components

### MCPFactory

Factory main class, responsible for creating and managing MCP servers:

```python
factory = MCPFactory(workspace_root="./workspace")

# Build project
project_path = factory.build_project("server-name", config_dict)

# Create server
server_id = factory.create_server("server-name", source)

# Manage servers
servers = factory.list_servers()
```

### ManagedServer

Managed server class, providing complete MCP server functionality:

```python
server = ManagedServer(name="my-server")

# Add tools
@server.tool()
def my_tool(param: str) -> str:
    return f"Processing: {param}"

# Run server
server.run()
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
```

## 📖 Documentation

- [Configuration Guide](docs/configuration.md)
- [CLI Usage Guide](docs/cli-guide.md)
- [Architecture Documentation](docs/architecture/)

## 🤝 Contributing

Contributions are welcome! Please check our contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

> **Note**: This is the stable version of MCP Factory (v1.0.0), focusing on core factory functionality. If you need more advanced features like authentication, remote calls, etc., please consider using the [mcp-factory-server](https://github.com/ACNet-AI/mcp-factory-server) project. 