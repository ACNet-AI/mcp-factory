# Complete Middleware Guide

## 📖 Overview

MCP Factory provides a powerful middleware system that supports middleware integration at different levels:

1. **Factory Level**: Configure middleware through `MCPFactory.create_server()`
2. **Project Level**: Directly configure and use middleware in generated projects
3. **Custom Development**: Develop your own enterprise-grade middleware

## 🏗️ Architecture Design

### Independent Middleware Module

Middleware functionality is implemented through the independent `mcp_factory.middleware` module:

```python
from mcp_factory.middleware import load_middleware_from_config

# Load middleware
middleware_instances = load_middleware_from_config(config)
```

### Design Advantages

1. **Single Responsibility Principle**: Middleware module focuses on middleware loading logic
2. **Code Reuse**: Factory and project levels share the same middleware loading code
3. **Modular Design**: Easy to test and maintain
4. **Extensibility**: Leaves room for future middleware functionality expansion

## 🔧 Basic Usage

### Built-in Middleware Types

Based on FastMCP official middleware implementation:

#### 1. Error Handling Middleware (error_handling)

```yaml
- type: error_handling
  config:
    include_traceback: true    # Whether to include error stack trace
    transform_errors: true     # Whether to transform error format
  enabled: true
```

#### 2. Rate Limiting Middleware (rate_limiting)

```yaml
- type: rate_limiting
  config:
    max_requests_per_second: 10.0  # Maximum requests per second
    burst_capacity: 20             # Burst capacity
    global_limit: true             # Global limit
  enabled: true
```

#### 3. Performance Timing Middleware (timing)

```yaml
- type: timing
  config:
    log_level: 20  # Log level (INFO=20, DEBUG=10)
  enabled: true
```

#### 4. Request Logging Middleware (logging)

```yaml
- type: logging
  config:
    include_payloads: true      # Whether to log request payloads
    max_payload_length: 1000    # Maximum payload length
    log_level: 20              # Log level
  enabled: true
```

### Basic Configuration Example

```yaml
server:
  name: "My MCP Server"
  instructions: "Server description"

middleware:
  - type: error_handling
    enabled: true
  - type: timing
    enabled: true
  - type: logging
    config:
      include_payloads: true
    enabled: true
```

## 🏭 Project-Level Usage

### Using in Generated Projects

1. **Configure when creating project**:

```python
from mcp_factory import MCPFactory

factory = MCPFactory()
project_config = {
    "server": {"name": "My Server"},
    "middleware": [
        {"type": "timing", "enabled": True},
        {"type": "logging", "enabled": True}
    ]
}

project_path = factory.build_project("my_project", project_config)
```

2. **Run project**:

```bash
cd my_project
python server.py
```

### Manual Middleware Loading

```python
from mcp_factory.middleware import load_middleware_from_config

# Load middleware
config = {"middleware": [...]}
middleware_instances = load_middleware_from_config(config)
```

## 🛠️ Custom Middleware Development

### Basic Structure

```python
class CustomMiddleware:
    def __init__(self, **config):
        # Initialize middleware
        self.config = config
        
    async def __call__(self, request, call_next):
        # Pre-processing
        # ...
        
        try:
            response = await call_next(request)
            # Post-processing
            # ...
            return response
        except Exception as e:
            # Error handling
            # ...
            raise
```

### Implementation Requirements

1. **Constructor**: Accept `**config` parameters
2. **`__call__` method**: Implement middleware logic, must be `async` method
3. **Request processing**: Call `await call_next(request)` to continue processing chain
4. **Error handling**: Catch and handle exceptions

### Enterprise-Grade Examples

#### Enterprise-Grade Examples

For complete implementations of enterprise-grade middleware, see:
- **Authentication Middleware**: `examples/custom_middleware.py` - API key authentication with anonymous access control
- **Audit Logging Middleware**: `examples/custom_middleware.py` - Security audit logging with sensitive data masking
- **Caching Middleware**: `examples/custom_middleware.py` - Intelligent response caching with TTL management

### Configuration in Projects

```yaml
middleware:
  - type: custom
    class: "my_project.middleware.AuthenticationMiddleware"
    config:
      api_keys: ["key1", "key2"]
      allow_anonymous: false
    enabled: true
  
  - type: custom
    class: "my_project.middleware.AuditMiddleware"
    config:
      log_file: "audit.log"
      include_payloads: true
    enabled: true
```

## 📋 Configuration Reference

### Complete Configuration Example

```yaml
server:
  name: "Enterprise MCP Server"
  instructions: "Enterprise-grade MCP server with comprehensive middleware"

middleware:
  # 1. Authentication middleware (executed first)
  - type: custom
    class: "examples.custom_middleware.AuthenticationMiddleware"
    config:
      api_keys: ["secret-key-1", "secret-key-2"]
      header_name: "X-API-Key"
      allow_anonymous: false
    enabled: true

  # 2. Audit middleware
  - type: custom
    class: "examples.custom_middleware.AuditMiddleware"
    config:
      log_file: "enterprise_audit.log"
      include_payloads: true
      sensitive_fields: ["password", "token", "api_key"]
    enabled: true

  # 3. Cache middleware
  - type: custom
    class: "examples.custom_middleware.CacheMiddleware"
    config:
      cache_ttl: 300
      max_cache_size: 100
      cacheable_methods: ["get_tools", "get_resource"]
    enabled: true

  # 4. Built-in middleware
  - type: error_handling
    config:
      include_traceback: false
      transform_errors: true
    enabled: true

  - type: rate_limiting
    config:
      max_requests_per_second: 10.0
      burst_capacity: 20
      global_limit: true
    enabled: true

  - type: timing
    config:
      log_level: 20
    enabled: true

  - type: logging
    config:
      include_payloads: false
      max_payload_length: 100
      log_level: 30
    enabled: true

tools:
  expose_management_tools: true

runtime:
  transport: "stdio"
  log_level: "INFO"
```

## 🎯 Best Practices

### 1. Middleware Ordering

Middleware execution follows the order defined in configuration:

1. **Authentication** - First line of defense
2. **Authorization** - Check permissions
3. **Audit** - Log security events
4. **Rate Limiting** - Prevent abuse
5. **Caching** - Performance optimization
6. **Error Handling** - Graceful error management
7. **Timing** - Performance monitoring
8. **Logging** - Request/response logging

### 2. Error Handling

```python
async def __call__(self, request, call_next):
    try:
        # Pre-processing
        response = await call_next(request)
        # Post-processing
        return response
    except Exception as e:
        # Log error
        logger.error(f"Middleware error: {e}")
        # Re-raise or transform error
        raise
```

### 3. Performance Considerations

- **Lightweight processing**: Keep middleware logic simple
- **Async/await**: Use proper async patterns
- **Resource cleanup**: Clean up resources in finally blocks
- **Caching**: Cache expensive operations

### 4. Security Best Practices

- **Input validation**: Validate all inputs
- **Sensitive data**: Sanitize logs and audit trails
- **Error messages**: Don't expose internal details
- **Rate limiting**: Implement proper rate limiting

## 🔍 Debugging and Monitoring

### Logging Configuration

```python
import logging

# Configure middleware logging
logging.getLogger("mcp_factory.middleware").setLevel(logging.DEBUG)
logging.getLogger("examples.custom_middleware").setLevel(logging.INFO)
```

### Common Issues

1. **Middleware not loading**: Check class path and imports
2. **Configuration errors**: Validate YAML syntax
3. **Performance issues**: Profile middleware execution
4. **Memory leaks**: Monitor cache sizes and cleanup

### Testing Middleware

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_custom_middleware():
    middleware = CustomMiddleware(config_param="value")
    
    request = MockRequest()
    call_next = AsyncMock()
    
    await middleware(request, call_next)
    
    call_next.assert_called_once_with(request)
```

## 📚 Examples and References

- **Basic Examples**: `examples/middleware_demo.py`
- **Custom Implementations**: `examples/custom_middleware.py`
- **Configuration Files**: `examples/configs/`
- **FastMCP Documentation**: [FastMCP Middleware](https://github.com/jlowin/fastmcp)

## 🚀 Advanced Topics

### Dynamic Middleware Loading

```python
from mcp_factory.middleware import load_middleware_from_config

# Load middleware at runtime
config = load_config_from_file("config.yaml")
middleware_instances = load_middleware_from_config(config)
```

### Middleware Composition

```python
# Combine multiple middleware
middleware_stack = [
    AuthenticationMiddleware(**auth_config),
    AuditMiddleware(**audit_config),
    CacheMiddleware(**cache_config)
]
```

### Custom Middleware Registry

```python
# Register custom middleware types
from mcp_factory.middleware import register_middleware_type

register_middleware_type("my_auth", MyAuthenticationMiddleware)
```

This comprehensive guide covers all aspects of middleware usage in MCP Factory, from basic configuration to advanced custom development. 