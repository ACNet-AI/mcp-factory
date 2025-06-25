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
  --workspace PATH   Specify workspace directory path (default: ./workspace)
  -v, --verbose      Enable verbose output
  -q, --quiet        Silent mode
  --help             Show this message and exit.

Commands:
  auth      Authentication management.
  config    Configuration management.
  project   Project management.
  server    Server management.
  health    System health check.
```

### 2. **Generate Configuration Template**

```bash
# Generate configuration template using config command
$ mcpf config template --name my-server --description "My MCP server"
# Configuration template with specified name and description

# Generate template and save to file
$ mcpf config template --name my-server --description "My MCP server" -o my-config.yaml
✅ Template saved to: my-config.yaml

# Include mounted server examples
$ mcpf config template --name my-server --description "My MCP server" --with-mounts
```

### 3. **Validate Configuration File**

```bash
$ mcpf config validate test-server.yaml
✅ Configuration file validation passed: test-server.yaml

# Detailed validation with mount checking
$ mcpf config validate test-server.yaml --check-mounts
```

### 4. **Quick Start Project**

```bash
$ mcpf project quick
# Interactive project creation wizard

# Initialize project with specific parameters
$ mcpf project init --name demo-server --port 8080 --debug --start-server
ℹ️ Project initialized: demo-server
🌐 Server started at: http://localhost:8080/api/mcp
⏹️  Press Ctrl+C to stop server
```

### 5. **Run Server with Configuration File**

```bash
$ mcpf server run test-server.yaml
ℹ️ Starting server: test-server
🌐 Access URL: http://localhost:8888/api/mcp
⏹️  Press Ctrl+C to stop server
```

### 6. **List All Resources**

```bash
$ mcpf server list
📊 Server List:
  🖥️  demo-server: demo-server - Created by mcpf CLI
  🖥️  test-server: Test server

$ mcpf config list
📄 Configuration files in current directory:
  📋 test-server.yaml
  📋 my-config.yaml
```

### 7. **Project Management**

```bash
# Build project from configuration
$ mcpf project build config.yaml
✅ Project built successfully

# Initialize new project
$ mcpf project init --name my-project --description "My project" --auto-discovery
```

## 🎯 **Real-world Usage Scenarios**

### **Scenario 1: Quick Start for Beginners**

```bash
# 1. Use interactive project creation
mcpf project quick

# 2. Or create with parameters and start immediately
mcpf project init --name hello-world --start-server
```

### **Scenario 2: Configuration-based Deployment**

```bash
# 1. Generate configuration template
mcpf config template --name production --description "Production server" -o production.yaml

# 2. Edit configuration file (modify port, authentication, etc.)
# 3. Validate configuration
mcpf config validate production.yaml

# 4. Run production server
mcpf server run production.yaml
```

### **Scenario 3: Development Environment Setup**

```bash
# 1. Generate development configuration with mounts
mcpf config template --name dev-server --description "Development server" --with-mounts -o dev-config.yaml

# 2. Validate configuration including mounts
mcpf config validate dev-config.yaml --check-mounts

# 3. Start development server
mcpf server run dev-config.yaml
```

## 📋 **Complete Command Reference**

| Command | Purpose | Options |
|---------|---------|---------|
| `mcpf config template` | Generate configuration template | `--name`, `--description`, `-o output_file`, `--with-mounts` |
| `mcpf config validate` | Validate configuration file | `config_file`, `--check-mounts` |
| `mcpf config list` | List configuration files | (no options) |
| `mcpf server run` | Run server | `config_file` |
| `mcpf server list` | List servers | `--status-filter`, `--format`, `--show-mounts` |
| `mcpf server status` | Get server status | `server_id`, `--show-mounts` |
| `mcpf server delete` | Delete server | `server_id`, `--force` |
| `mcpf server restart` | Restart server | `server_id` |
| `mcpf project init` | Initialize project | `--name`, `--description`, `--host`, `--port`, `--transport`, `--auth`, `--auto-discovery`, `--debug`, `--start-server` |
| `mcpf project build` | Build project | `config_file` |
| `mcpf project quick` | Interactive project creation | (no options) |
| `mcpf auth help` | Authentication help | (no options) |
| `mcpf auth check` | Check authentication | `--fastmcp` |
| `mcpf health` | System health check | `--check-config`, `--check-env` |

## 🔧 **Advanced Usage**

### **Health Check**

```bash
# Complete system health check
mcpf health --check-config --check-env
```

### **Verbose Output**

```bash
# Enable verbose output to see more information
mcpf --verbose server run config.yaml
```

### **Custom Workspace**

```bash
# Use custom workspace directory
mcpf --workspace ./my-workspace server list
```

This CLI tool greatly simplifies the creation and management of MCP servers, allowing users to get started quickly and efficiently manage server instances. 