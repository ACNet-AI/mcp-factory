# Examples and Tutorials

This page provides example code and usage tutorials for MCP Factory to help you get started quickly.

## 📂 Example Code

> **Location**: [`examples/`](../examples/) directory

### 🚀 Basic Examples

**File**: [`examples/basic_server.py`](../examples/basic_server.py)

Demonstrates core functionality:
- Creating and managing servers
- Basic server configuration
- Simple tool registration

```bash
# Run basic example
python -m examples.basic_server
```

### 🏭 Factory Complete Example

**File**: [`examples/factory_complete.py`](../examples/factory_complete.py)

Demonstrates advanced factory functionality:
- Complete server lifecycle management
- Configuration hot reloading
- Component discovery and registration
- Server mounting capabilities

```bash
# Run factory complete example
python -m examples.factory_complete
```

### 🚀 Production Ready Example

**File**: [`examples/production_ready.py`](../examples/production_ready.py)

Demonstrates production deployment features:
- Authentication integration
- Advanced configuration management
- Error handling and monitoring
- Performance optimization

```bash
# Run production ready example
python -m examples.production_ready
```

### 🔗 Server Mounting Example

**File**: [`examples/mounting_servers.py`](../examples/mounting_servers.py)

Demonstrates server composition:
- External MCP server mounting
- Multi-server coordination
- Routing and management

```bash
# Run mounting example
python -m examples.mounting_servers
```

### 📄 Configuration Examples

**Directory**: [`examples/configs/`](../examples/configs/)

Complete configuration file examples with different use cases:
- `basic.yaml` - Minimal configuration
- `factory.yaml` - Factory-specific features
- `mounting.yaml` - Server mounting configuration
- `production.yaml` - Production deployment settings

## 📚 Tutorial Scenarios

### 🎯 Beginner Getting Started Scenarios

#### 1. First Server
```bash
# Quick start temporary server
mcpf server quick

# Or using configuration template
mcpf config template --name my-first-server --description "My first server" -o server.yaml
mcpf server run server.yaml
```

#### 2. Adding Custom Tools
```python
from mcp_factory import MCPFactory

factory = MCPFactory()
server = factory.create_server("my-server", "config.yaml")

@server.tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    """Simple addition tool"""
    return a + b

server.run()
```

#### 3. Configure Management Tools
> 📖 **Configuration Details**: See [Configuration Reference](configuration.md) for complete configuration options.

```yaml
# config.yaml
server:
  name: "tutorial-server"
  instructions: "Tutorial MCP server"

tools:
  expose_management_tools: true  # Enable management tools
```

### 🔐 Authentication Configuration Scenarios

> 📖 **Authentication Setup**: For detailed authentication configuration, see [Configuration Reference](configuration.md#authentication-configuration).

#### 1. Basic Authentication Setup
```yaml
server:
  name: "secure-server"
  instructions: "Authenticated MCP server"

auth:
  provider_id: "my-auth-provider"

tools:
  expose_management_tools: true
```

### 🏗️ Production Deployment Scenarios

> 📖 **Production Configuration**: See [Configuration Reference](configuration.md#production-configuration) for complete production settings.

#### 1. Build and Publish Project
```bash
# Build project with production configuration
mcpf project build production.yaml

# Publish to GitHub for community access
mcpf project publish my-production-server
```

#### 2. Deployment Commands
```bash
# Validate configuration
mcpf config validate production.yaml

# Start production server
mcpf server run production.yaml
```

### 🔄 Server Composition Scenarios

#### 1. Create Multiple Servers
```python
# Main server
main_server = factory.create_server("main-server", "main-config.yaml")

# Compute server
compute_server = factory.create_server("compute-server", "compute-config.yaml")

# Mount compute server to main server
await main_server.mount("compute", compute_server)
```

#### 2. Use Management Tools
```bash
# List mounted servers
curl -X POST http://localhost:8080/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "manage_list_mounted_servers"}}'
```

### 📤 Project Publishing Scenarios

#### 1. Quick Publishing
```bash
# Initialize and publish in one go
mcpf project init --name weather-server --description "Weather information server"
mcpf project publish weather-server
```

#### 2. Complete Publishing Workflow
```bash
# 1. Create project
mcpf project init --name my-api-server --description "Custom API server"

# 2. Build project (with automatic Git initialization)
mcpf project build config.yaml

# 3. Configure publishing information (edit pyproject.toml)
# [tool.mcp-servers-hub]
# name = "my-api-server"
# description = "Custom API server for data processing"
# author = "Your Name <email@example.com>"
# categories = ["api", "tools"]

# 4. Publish to GitHub
mcpf project publish my-api-server

# 5. Verify publication
# Check: https://github.com/ACNet-AI/mcp-servers-hub
```

#### 3. Publishing with Custom Configuration
```python
from mcp_factory import MCPFactory

# Create factory and project
factory = MCPFactory()
project_config = {
    "name": "data-processor",
    "description": "Advanced data processing server",
    "author": "Data Team",
    "categories": ["data", "processing", "analytics"]
}

# Build and publish
project_path = factory.build_project("data-processor", project_config)
factory.publish_project(project_path, github_username="your-username")
```

## 🧪 Testing and Validation

### Server Testing
```bash
# Check server status
curl http://localhost:8080/api/mcp

# List available tools
curl -X POST http://localhost:8080/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'

# Call tool
curl -X POST http://localhost:8080/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "add", "arguments": {"a": 5, "b": 3}}}'
```

### Configuration Validation
```bash
# Validate configuration file
mcpf config validate config.yaml

# Detailed validation with mount checking
mcpf config validate config.yaml --check-mounts
```

## 📖 Additional Resources

- [Getting Started Guide](getting-started.md) - Step-by-step setup instructions
- [Configuration Reference](configuration.md) - Complete configuration documentation
- [Publishing Guide](publishing-guide.md) - GitHub project publishing and deployment guide
- [CLI Guide](cli-guide.md) - Command-line tool usage
- [Architecture Overview](architecture/README.md) - System architecture documentation

> 💡 **Tip**: Start with the basic examples and gradually explore more advanced features. Each example includes detailed comments explaining the key concepts.

## 📋 Example Comparison

| Example | Difficulty | Main Features | Use Case |
|---------|------------|---------------|----------|
| `basic_server.py` | 🟢 Simple | Core functionality demo | Learning basic concepts |
| `factory_complete.py` | 🟠 Medium | CLI + advanced features | Production applications |
| `production_ready.py` | 🟠 Medium | CLI + advanced features | Production applications |
| `mounting_servers.py` | 🟠 Medium | CLI + advanced features | Production applications |
| CLI Quick Start | 🟢 Simple | One-click startup | Quick testing |
| Configuration File Mode | 🟡 Normal | Structured configuration | Formal development |
| Publishing Workflow | 🟡 Normal | GitHub integration + Hub registration | Open source sharing |

## 🔗 Related Resources

- 📖 [Getting Started](getting-started.md) - 5-minute getting started guide
- ⚙️ [Configuration Reference](configuration.md) - Detailed configuration documentation
- 💻 [CLI Guide](cli-guide.md) - Command-line tool usage
- 🔧 [Troubleshooting](troubleshooting.md) - Common problem solving

---

> 💡 **Tip**: Recommended viewing order: Basic Examples → CLI Quick Start → Advanced Examples → Production Configuration 