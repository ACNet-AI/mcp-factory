# Getting Started

This guide will help you get started with MCP Factory in 5 minutes.

## 🎯 What You'll Learn

- Install MCP Factory
- Create your first MCP server
- Use CLI tools to manage servers

## 📦 Step 1: Installation

```bash
# Recommended using uv (faster)
uv add mcp-factory

# Or use pip
pip install mcp-factory
```

## 🚀 Step 2: Quick Start Server

### Method 1: Use CLI Quick Start

```bash
# One-click server startup
mcpf quick --name hello-world --port 8888

# Output:
# ℹ️ Quick server starting: hello-world
# 🌐 Access URL: http://localhost:8888/api/mcp
# ⏹️  Press Ctrl+C to stop server
```

### Method 2: Use Python API

```python
from mcp_factory import MCPFactory

# Create factory
factory = MCPFactory()

# Generate minimal configuration
config_content = '''
server:
  name: "hello-world"
  instructions: "My first MCP server"
  host: "localhost"
  port: 8888

tools:
  expose_management_tools: true
'''

# Save configuration
with open("server.yaml", "w") as f:
    f.write(config_content)

# Create and run server
server = factory.create_managed_server("server.yaml")

# Add custom tool
@server.tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    return a + b

# Start server
server.run()
```

## 🧪 Step 3: Test Server

Open another terminal and test if the server is working properly:

```bash
# Test using curl
curl -X POST http://localhost:8888/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list"}'
```

## 🎉 Congratulations!

You have successfully created your first MCP server!

## 📋 Next Steps

### 🔧 Use Configuration File

```bash
# Generate configuration template
mcpf template --type simple > my-server.yaml

# Edit configuration file (optional)
# vim my-server.yaml

# Run server
mcpf run my-server.yaml
```

### 🔐 Add Authentication

```bash
# Create Auth0 authentication provider
mcpf auth my-auth \
  --type auth0 \
  --domain your-domain.auth0.com \
  --client-id your-client-id \
  --client-secret your-client-secret

# Reference authentication provider in configuration file
# auth:
#   provider_id: "my-auth"
```

### 📚 Learn More

- 📖 [CLI Usage Guide](cli-guide.md) - Master all CLI commands
- 🔧 [Configuration Reference](configuration.md) - Detailed configuration options
- 🔒 [Authentication Configuration](authentication.md) - Set up authentication and permissions
- 📝 [Example Collection](examples/README.md) - View more practical examples

## ❓ Having Issues?

- Check [Troubleshooting](troubleshooting.md)
- Submit an [Issue](https://github.com/your-repo/issues)
- Consult [API Reference](api-reference.md)

---

> 🎯 **Next Stop**: Recommended reading [CLI Usage Guide](cli-guide.md) to master all command-line tool features. 