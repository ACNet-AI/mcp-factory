# Examples and Tutorials

This page provides example code and usage tutorials for MCP Factory to help you get started quickly.

## 📂 Example Code

> **Location**: [`examples/`](../examples/) directory

### 🚀 Basic Examples

**File**: [`examples/basic_example.py`](../examples/basic_example.py)

Demonstrates core functionality:
- Creating and managing servers
- Registering and using tools
- Configuration hot reloading
- Mounting sub-servers
- Authentication providers

```bash
# Run basic example
python -m examples.basic_example
```

### 🔧 Advanced Examples

**File**: [`examples/advanced_example.py`](../examples/advanced_example.py)

Demonstrates advanced functionality:
- Command-line interface
- Authentication provider management
- Lifecycle management
- Custom tool serialization
- Tags and dependency management

```bash
# Create authentication provider
python -m examples.advanced_example create-auth \
  --id test-auth --type auth0 \
  --domain example.auth0.com \
  --client-id xxxx --client-secret xxxx

# Run advanced server
python -m examples.advanced_example run-server \
  --config examples/config.example.yaml \
  --auth-provider test-auth
```

### 📄 Configuration Examples

**File**: [`examples/config.example.yaml`](../examples/config.example.yaml)

Complete configuration file template with all supported configuration options and detailed comments.

## 📚 Tutorial Scenarios

### 🎯 Beginner Getting Started Scenarios

#### 1. First Server
```bash
# Quick start
mcpf quick --name my-first-server --port 8888

# Or use configuration file
mcpf template --type minimal > server.yaml
mcpf run server.yaml
```

#### 2. Adding Custom Tools
```python
from mcp_factory import FastMCPFactory

factory = FastMCPFactory()
server = factory.create_managed_server("config.yaml")

@server.tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    """Simple addition tool"""
    return a + b

server.run()
```

#### 3. Configure Management Tools
```yaml
# config.yaml
server:
  name: "tutorial-server"
  instructions: "Tutorial MCP server"

tools:
  expose_management_tools: true  # Enable management tools
```

### 🔐 Authentication Configuration Scenarios

#### 1. Create Auth0 Authentication
```bash
# Create using CLI
mcpf auth production-auth \
  --type auth0 \
  --domain your-tenant.auth0.com \
  --client-id "your-client-id" \
  --client-secret "your-client-secret"
```

#### 2. Use Authentication in Configuration
```yaml
server:
  name: "secure-server"
  instructions: "Authenticated MCP server"

auth:
  provider_id: "production-auth"

tools:
  expose_management_tools: true
```

### 🏗️ Production Deployment Scenarios

#### 1. Production Configuration
```yaml
server:
  name: "production-mcp-server"
  instructions: "Production ready MCP server"
  host: "0.0.0.0"
  port: 8080

auth:
  provider_id: "production-auth0"

tools:
  expose_management_tools: true

advanced:
  debug: false
  cors_origins: ["https://your-app.com"]
  max_connections: 500
  timeout: 30
```

#### 2. Deployment Commands
```bash
# Validate configuration
mcpf validate production.yaml

# Start production server
mcpf run production.yaml --host 0.0.0.0 --port 8080
```

### 🔄 Server Composition Scenarios

#### 1. Create Multiple Servers
```python
# Main server
main_server = factory.create_managed_server("main-config.yaml")

# Compute server
compute_server = factory.create_managed_server("compute-config.yaml")

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
mcpf validate config.yaml

# Detailed validation information
mcpf validate config.yaml --verbose
```

## 📋 Example Comparison

| Example | Difficulty | Main Features | Use Case |
|---------|------------|---------------|----------|
| `basic_example.py` | 🟢 Simple | Core functionality demo | Learning basic concepts |
| `advanced_example.py` | 🟠 Medium | CLI + advanced features | Production applications |
| CLI Quick Start | 🟢 Simple | One-click startup | Quick testing |
| Configuration File Mode | 🟡 Normal | Structured configuration | Formal development |

## 🔗 Related Resources

- 📖 [Getting Started](getting-started.md) - 5-minute getting started guide
- ⚙️ [Configuration Reference](configuration.md) - Detailed configuration documentation
- 💻 [CLI Guide](cli-guide.md) - Command-line tool usage
- 🔧 [Troubleshooting](troubleshooting.md) - Common problem solving

---

> 💡 **Tip**: Recommended viewing order: Basic Examples → CLI Quick Start → Advanced Examples → Production Configuration 