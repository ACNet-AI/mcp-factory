# Configuration Reference

This document provides detailed information about all MCP Factory configuration options.

## 🗂️ Configuration File Structure

```yaml
# Complete configuration file example
server:           # Server basic configuration (required)
  name: "my-server"
  instructions: "Server description"
  host: "localhost"
  port: 8080

auth:             # Authentication configuration (optional)
  provider_id: "my-auth"
  
tools:            # Tools configuration (optional)
  expose_management_tools: true
  
advanced:         # Advanced configuration (optional)
  debug: false
  cors_origins: ["*"]
```

## 🎯 Required Configuration

### server section

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | ✅ | - | Server name for identification |
| `instructions` | string | ✅ | - | Server functionality description |
| `host` | string | ❌ | "localhost" | Bind host address |
| `port` | integer | ❌ | 8080 | Port number (1-65535) |

```yaml
server:
  name: "calculator-server"
  instructions: "A simple calculator service"
  host: "0.0.0.0"    # Listen on all interfaces
  port: 8888         # Custom port
```

## 🔐 Authentication Configuration

### auth section

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `provider_id` | string | ✅ | Authentication provider ID (must be created first) |

```yaml
auth:
  provider_id: "production-auth0"  # Reference to created authentication provider
```

#### Creating Authentication Provider

```bash
# Auth0 provider
mcpf auth production-auth0 \
  --type auth0 \
  --domain your-tenant.auth0.com \
  --client-id "your-client-id" \
  --client-secret "your-client-secret"
```

## 🛠️ Tools Configuration

### tools section

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `expose_management_tools` | boolean | ❌ | false | Whether to expose management tools |

```yaml
tools:
  expose_management_tools: true   # Enable management tools
```

#### Management Tools List

Available management tools when enabled:
- `manage_reload_config` - Reload configuration
- `manage_get_server_info` - Get server information
- `manage_list_mounted_servers` - List mounted servers
- `manage_mount_server` - Mount other servers
- `manage_unmount_server` - Unmount servers

## ⚙️ Advanced Configuration

### advanced section

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `debug` | boolean | ❌ | false | Debug mode |
| `cors_origins` | array | ❌ | ["*"] | CORS allowed origins |
| `cors_methods` | array | ❌ | ["GET", "POST"] | Allowed HTTP methods |
| `cors_headers` | array | ❌ | ["Content-Type"] | Allowed request headers |
| `max_connections` | integer | ❌ | 100 | Maximum connections |
| `timeout` | integer | ❌ | 30 | Request timeout (seconds) |

```yaml
advanced:
  debug: true
  cors_origins: 
    - "http://localhost:3000"
    - "https://your-app.com"
  cors_methods: ["GET", "POST", "PUT", "DELETE"]
  cors_headers: 
    - "Content-Type"
    - "Authorization"
    - "X-Custom-Header"
  max_connections: 200
  timeout: 60
```

## 📝 Configuration Templates

### Minimal Configuration

```yaml
server:
  name: "minimal-server"
  instructions: "Minimal MCP server"
```

### Basic Configuration

```yaml
server:
  name: "basic-server"
  instructions: "Basic MCP server with management tools"
  port: 8888

tools:
  expose_management_tools: true
```

### Production Configuration

```yaml
server:
  name: "production-server"
  instructions: "Production MCP server"
  host: "0.0.0.0"
  port: 8080

auth:
  provider_id: "production-auth0"

tools:
  expose_management_tools: true

advanced:
  debug: false
  cors_origins: ["https://your-app.com"]
  cors_methods: ["GET", "POST"]
  cors_headers: ["Content-Type", "Authorization"]
  max_connections: 500
  timeout: 30
```

### Development Configuration

```yaml
server:
  name: "dev-server"
  instructions: "Development MCP server"
  host: "localhost"
  port: 8888

tools:
  expose_management_tools: true

advanced:
  debug: true
  cors_origins: ["*"]
  max_connections: 50
  timeout: 60
```

## 🔍 Configuration Validation

### Using CLI Validation

```bash
# Validate configuration file
mcpf validate config.yaml

# Detailed validation information
mcpf validate config.yaml --verbose
```

### Common Validation Errors

1. **YAML Syntax Error**
```yaml
# ❌ Error: Incorrect indentation
server:
name: "test"

# ✅ Correct: Use 2-space indentation
server:
  name: "test"
```

2. **Missing Required Fields**
```yaml
# ❌ Error: Missing instructions
server:
  name: "test"

# ✅ Correct: Include all required fields
server:
  name: "test"
  instructions: "Test server"
```

3. **Invalid Port Number**
```yaml
# ❌ Error: Port number out of range
server:
  port: 70000

# ✅ Correct: Use valid port number
server:
  port: 8080
```

## 🌍 Environment Variables

Support overriding configuration through environment variables:

| Environment Variable | Configuration Item | Example |
|---------------------|-------------------|---------|
| `MCPF_HOST` | `server.host` | `MCPF_HOST=0.0.0.0` |
| `MCPF_PORT` | `server.port` | `MCPF_PORT=9000` |
| `MCPF_DEBUG` | `advanced.debug` | `MCPF_DEBUG=true` |

```bash
# Run with environment variables
MCPF_PORT=9000 MCPF_DEBUG=true mcpf run config.yaml
```

## 📁 Configuration File Location

### Default Search Paths

MCP Factory searches for configuration files in the following order:

1. Path specified on command line
2. `./config.yaml`
3. `~/.mcpf/config.yaml`
4. `/etc/mcpf/config.yaml`

### Custom Configuration Directory

```bash
# Use custom configuration directory
mcpf --config-dir /path/to/configs run server.yaml
```

## ⚡ Best Practices

### 1. Configuration Separation

```bash
# Use different configurations for different environments
mcpf run config.dev.yaml      # Development
mcpf run config.staging.yaml  # Staging
mcpf run config.prod.yaml     # Production
```

### 2. Security Configuration

```yaml
# Production environment security configuration
server:
  host: "127.0.0.1"  # Local access only
  
auth:
  provider_id: "secure-auth"

advanced:
  debug: false        # Disable debugging
  cors_origins: 
    - "https://trusted-domain.com"  # Restrict origins
```

### 3. Performance Optimization

```yaml
advanced:
  max_connections: 1000   # Adjust based on server performance
  timeout: 10            # Set reasonable timeout
```

---

> 📚 **Related Documentation**: 
> - [Getting Started](getting-started.md) - Basic configuration usage
> - [CLI Guide](cli-guide.md) - Command-line configuration management
> - [Troubleshooting](troubleshooting.md) - Configuration problem solving 