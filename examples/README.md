# MCP-Factory Examples

This directory contains practical examples of MCP-Factory to help you understand how to use this library to create and manage MCP servers.

## 🚀 Quick Experience - Demo

**The fastest way to get started!** If you want to experience MCP-Factory immediately, run the demo directly:

```bash
# Start demo server
python examples/demo/server.py

# Run client test (open new terminal)
python examples/demo/client.py            # Standard mode
python examples/demo/client.py --mgmt     # Management tools mode
```

Demo includes:
- ✨ **Complete server-client interaction example**
- 🧮 **Basic tools** (addition, multiplication calculator)
- 🔧 **Management tools** (configuration reload, tool management, etc.)
- 📊 **Detailed runtime status display**

> 💡 **Tip**: Demo is located in the `examples/demo/` directory with independent README documentation.

## 📚 Examples Overview

| Example File | Complexity | Main Features | Use Case |
|---------|-------|---------|---------|
| `demo/` | ⭐ | **Quick experience**, server-client interaction | **Get started immediately** |
| `basic_server.py` | ⭐ | Basic server creation, tool registration | Beginner introduction |
| `factory_complete.py` | ⭐⭐⭐ | Factory pattern, project management, hot reload | Core architecture learning |
| `mounting_servers.py` | ⭐⭐⭐⭐ | External server mounting, microservices | Distributed systems |
| `production_ready.py` | ⭐⭐⭐⭐⭐ | Enterprise deployment, security, monitoring | Production environment |

## 🚀 Quick Start

### 0. Quick Experience (Recommended for beginners)
```bash
# Simplest way to experience
python examples/demo/server.py
python examples/demo/client.py
```

### 1. Run Basic Example
```bash
# Simplest introductory example
python examples/basic_server.py

# View help
python examples/basic_server.py --help
```

### 2. Experience Complete Factory Features
```bash
# Run complete factory pattern server
python examples/factory_complete.py

# Use custom configuration
python examples/factory_complete.py --config examples/configs/factory.yaml
```

### 3. Test Server Mounting
```bash
# Run example with external server mounting
python examples/mounting_servers.py

# Check mounted external server status
curl http://localhost:8082/api/mcp
```

### 4. Production Environment Deployment
```bash
# Run production-grade configuration
python examples/production_ready.py --config examples/configs/production.yaml
```

## 📁 Directory Structure

```
examples/
├── README.md                 # This document
├── demo/                     # Quick experience demo
│   ├── server.py            # Demo server
│   ├── client.py            # Demo client
│   ├── config.yaml          # Demo configuration
│   └── README.md            # Demo documentation
├── shared.py                 # Shared tools and helper functions
├── basic_server.py          # Beginner-level basic server
├── factory_complete.py      # Complete factory pattern example
├── mounting_servers.py      # External server mounting example
├── production_ready.py      # Production-grade deployment example
└── configs/                 # Configuration files directory
    ├── basic.yaml           # Basic configuration
    ├── factory.yaml         # Factory pattern configuration  
    ├── mounting.yaml        # Mounting configuration
    └── production.yaml      # Production environment configuration
```

## 📖 Detailed Examples Documentation

### 🎯 demo/ - Quick Experience Demo
**Get started immediately** | **Complexity: ⭐**

Complete server-client interaction demonstration, most suitable for beginners to experience quickly:
- Demo server (server.py) - Use MCPFactory to create server with management tools
- Demo client (client.py) - Connect to server and test various functions
- Simple tool registration (addition, multiplication calculator)
- Management tools display (configuration reload, tool management, etc.)
- Detailed runtime status and error handling

```bash
# Quick experience
python examples/demo/server.py  # Start server
python examples/demo/client.py # Test client (new terminal)
```

### 🌟 basic_server.py - Basic Server
**Suitable for beginners** | **Complexity: ⭐**

Demonstrates basic usage of MCP-Factory:
- Create simple MCP server
- Register basic tool functions
- Use built-in management tools
- Configure logging and debugging

```python
# Core functionality preview
from mcp_factory.server import ManagedServer

server = ManagedServer(name="basic-server")
server.register_tool("echo", lambda text: f"Echo: {text}")
server.run()
```

### 🏭 factory_complete.py - Complete Factory Pattern  
**Core architecture learning** | **Complexity: ⭐⭐⭐**

Demonstrates complete functionality of MCP-Factory:
- Factory pattern server creation
- Project management and auto-discovery
- Configuration hot reload mechanism
- Authentication and authorization management
- Lifecycle hooks

```python
# Core functionality preview
from mcp_factory import MCPFactory

factory = MCPFactory()
server = factory.create_managed_server(
    config_path="configs/factory.yaml",
    expose_management_tools=True
)
```

### 🔗 mounting_servers.py - Server Mounting
**Distributed systems** | **Complexity: ⭐⭐⭐⭐**

Demonstrates how to integrate external MCP servers:
- Mount local script servers
- Connect to remote HTTP/SSE servers
- Microservice architecture pattern
- Service health checks and failure recovery
- Tool namespace management

```python
# Core functionality preview
from mcp_factory.mounting import ServerMounter

mounter = ServerMounter()
await mounter.mount_from_config("configs/mounting.yaml")
```

### 🏗️ production_ready.py - Production Environment
**Enterprise deployment** | **Complexity: ⭐⭐⭐⭐⭐**

Enterprise-grade production environment best practices:
- JWT authentication and authorization
- SSL/TLS secure transport
- Monitoring and health checks
- Error handling and recovery mechanisms
- Performance optimization and connection limits
- Log rotation and auditing

```python
# Core functionality preview
server = create_production_server(
    config_path="configs/production.yaml",
    enable_monitoring=True,
    enable_security=True
)
```

## ⚙️ Configuration Files Explained

### basic.yaml - Basic Configuration
```yaml
server:
  name: "basic-mcp-server"
  instructions: "Basic MCP server example"
runtime:
  transport: "stdio"
  log_level: "INFO"
```

### factory.yaml - Factory Pattern Configuration
```yaml
server:
  name: "factory-complete-server"
project:
  enabled: true
  auto_discovery: true
hot_reload:
  enabled: true
  watch_directories: ["./workspace"]
```

### mounting.yaml - Mounting Configuration
```yaml
mcpServers:
  weather-service:
    command: "python"
    args: ["-c", "print('Weather service')"]
    prefix: "weather"
  remote-api:
    url: "https://api.example.com"
    transport: "sse"
```

### production.yaml - Production Configuration
```yaml
auth:
  enabled: true
  provider: "jwt"
monitoring:
  enabled: true
  health_check_endpoint: "/health"
security:
  cors_enabled: true
  csrf_protection: true
```

## 🧪 Environment Verification

Run environment check tools:

```bash
# Check runtime environment
python examples/shared.py

# Run complete test suite
python test_examples.py
```

## 🔧 Troubleshooting

### Common Issues

1. **Module import errors**
   ```bash
   # Ensure MCP-Factory is installed
   pip install -e .
   ```

2. **Configuration file errors**
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('configs/basic.yaml'))"
   ```

3. **Port occupation issues**
   ```bash
   # Check port usage
   lsof -i :8080
   ```

4. **Permission issues**
   ```bash
   # Check file permissions
   ls -la examples/
   ```

## 📚 Learning Path Recommendations

1. **Beginners** → Start with `basic_server.py`
2. **Advanced users** → Learn factory pattern in `factory_complete.py`
3. **Architects** → Study microservice architecture in `mounting_servers.py`
4. **DevOps engineers** → Deploy enterprise-grade configuration in `production_ready.py`

## 🤝 Contributions and Feedback

If you find issues in the examples or have suggestions for improvement:

1. Submit an Issue to the project repository
2. Provide specific error information and reproduction steps
3. Suggest new example scenarios

## 📄 License

These examples follow the same license as the MCP-Factory main project. 