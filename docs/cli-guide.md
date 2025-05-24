# MCP Factory CLI Guide

This document demonstrates the actual usage of the `mcpf` CLI tool.

## 🚀 **CLI Feature Demonstration**

### 1. **View Help Information**

```bash
$ mcpf --help
Usage: mcpf [OPTIONS] COMMAND [ARGS]...

  MCP Factory - Create and manage MCP servers with ease

Options:
  --version          Show the version and exit.
  --config-dir PATH  Specify configuration directory path (default: ~/.mcpf)
  -v, --verbose      Enable verbose output
  -q, --quiet        Silent mode
  --help             Show this message and exit.

Commands:
  auth      Create authentication provider.
  list      List all servers and authentication providers.
  quick     Quickly create and run server.
  run       Run MCP server.
  template  Generate configuration template.
  validate  Validate configuration file.
```

### 2. **Generate Configuration Template**

```bash
# Generate minimal configuration
$ mcpf template --type minimal
# Minimal MCP server configuration
server:
  name: "my-mcp-server"
  instructions: "My MCP server"
  host: "localhost"
  port: 8888
  transport: "streamable-http"

tools:
  expose_management_tools: true

# Generate full configuration template and save to file
$ mcpf template --type full -o my-config.yaml
✅ Template saved to: my-config.yaml
```

### 3. **Validate Configuration File**

```bash
$ mcpf validate test-server.yaml
✅ Configuration file validation passed: test-server.yaml
```

### 4. **Quick Start Server**

```bash
$ mcpf quick --name demo-server --port 8080 --debug
ℹ️ Quick server starting: demo-server
🌐 Access URL: http://localhost:8080/api/mcp
⏹️  Press Ctrl+C to stop server
```

### 5. **Run Server with Configuration File**

```bash
$ mcpf run test-server.yaml
ℹ️ Starting server: test-server
🌐 Access URL: http://localhost:8888/api/mcp
⏹️  Press Ctrl+C to stop server
```

### 6. **List All Resources**

```bash
$ mcpf list
📊 Server List:
  🖥️  demo-server: demo-server - Created by mcpf CLI
  🖥️  test-server: Test server

🔐 Authentication Providers:
  (No authentication providers)

📄 Configuration files in current directory:
  📋 test-server.yaml
  📋 my-config.yaml
```

### 7. **Create Authentication Provider**

```bash
$ mcpf auth my-auth0 --type auth0 --domain example.auth0.com --client-id xxx --client-secret yyy
✅ Authentication provider 'my-auth0' (auth0) created successfully
```

## 🎯 **Real-world Usage Scenarios**

### **Scenario 1: Quick Start for Beginners**

```bash
# 1. Quickly start a test server
mcpf quick --name hello-world

# Server starts immediately, ready for development and testing
```

### **Scenario 2: Configuration-based Deployment**

```bash
# 1. Generate configuration template
mcpf template --type simple > production.yaml

# 2. Edit configuration file (modify port, authentication, etc.)
# 3. Validate configuration
mcpf validate production.yaml

# 4. Run production server
mcpf run production.yaml --port 80
```

### **Scenario 3: Development Environment Setup**

```bash
# 1. Create development authentication provider
mcpf auth dev-auth --type auth0 --domain dev.auth0.com --client-id xxx --client-secret yyy

# 2. Generate development configuration
mcpf template --type full > dev-config.yaml
# (Edit configuration file, add authentication provider)

# 3. Start development server
mcpf run dev-config.yaml --debug
```

## 📋 **Complete Command Reference**

| Command | Purpose | Options |
|---------|---------|---------|
| `mcpf template` | Generate configuration template | `--type {minimal,simple,full}`, `-o output_file` |
| `mcpf validate` | Validate configuration file | `config_file` |
| `mcpf run` | Run server | `config_file`, `--host`, `--port`, `--debug` |
| `mcpf quick` | Quick start server | `--name`, `--port`, `--host`, `--auth`, `--debug`, `--save-config` |
| `mcpf list` | List resources | (no options) |
| `mcpf auth` | Create authentication provider | `provider_id`, `--type`, `--domain`, `--client-id`, `--client-secret`, `--audience`, `--roles-namespace` |

## 🔧 **Advanced Usage**

### **Save Quick Server Configuration**

```bash
# Create server and save configuration for future use
mcpf quick --name production-server --port 8888 --save-config prod.yaml
```

### **Verbose Output**

```bash
# Enable verbose output to see more information
mcpf --verbose run config.yaml
```

### **Custom Configuration Directory**

```bash
# Use custom configuration directory
mcpf --config-dir ./my-configs list
```

This CLI tool greatly simplifies the creation and management of MCP servers, allowing users to get started quickly and efficiently manage server instances. 