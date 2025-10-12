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
| `factory_complete.py` | ⭐⭐⭐ | Factory pattern, project management, **middleware integration** | Core architecture learning |
| `middleware_demo.py` | ⭐⭐⭐ | **Comprehensive middleware usage**, configuration strategies | **Middleware learning** |
| `mounting_servers.py` | ⭐⭐⭐⭐ | External server mounting, microservices | Distributed systems |
| `production_ready.py` | ⭐⭐⭐⭐⭐ | Enterprise deployment, security, monitoring | Production environment |
| `custom_middleware.py` | ⭐⭐⭐⭐ | **Custom middleware development** | Advanced customization |
| `complete_server_demo.py` | ⭐⭐⭐⭐ | **Complete real-world server** | Authorization, billing, and file management integration |
| `proxy_mode_integration_demo.py` | ⭐⭐⭐⭐⭐ | **🔥 Proxy Mode Integration** | **Zero-setup billing for developers** |
| `complete_proxy_system_demo.py` | ⭐⭐⭐⭐⭐ | **🆕 Complete Proxy System** | Full two-layer proxy architecture |
| `credit_system_demo.py` | ⭐⭐⭐⭐⭐ | **🆕 Revolutionary Credit System** | Two-layer proxy, automatic revenue sharing |
| `unified_wallet_demo.py` | ⭐⭐⭐⭐⭐ | **🆕 Unified Wallet Experience** | One wallet for all services, seamless UX |

## 🚀 Quick Start

### 0. 🔥 Proxy Mode Integration (Recommended for Developers)

**For developers who want to create billing-enabled services with zero setup:**

```bash
# Experience the complete developer onboarding flow
python examples/proxy_mode_integration_demo.py
```

**What you get automatically:**
- ✅ **Zero Infrastructure Setup**: No Lago/Stripe accounts needed
- ✅ **Auto Developer Registration**: Platform account created automatically  
- ✅ **Service Registration**: Your service listed on MCP Factory platform
- ✅ **Real-time Billing**: Credit-based billing with instant revenue sharing
- ✅ **Professional Analytics**: Built-in revenue and usage tracking
- ✅ **Complete Project Structure**: Ready-to-deploy MCP server

**Configuration Example:**
```yaml
billing:
  enabled: true
  mode: "proxy"  # 🔑 Use MCP Factory proxy
  developer:
    developer_id: "your_dev_id"
    email: "you@example.com"
  service:
    pricing:
      basic_call: 1.0    # 1 credit per call
      premium_call: 5.0  # 5 credits per call
```

### 1. Quick Experience (Recommended for beginners)
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

### 💰 NEW! Credit System Demo
```bash
python examples/credit_system_demo.py
```
**🚀 Revolutionary two-layer proxy credit system with automatic revenue sharing!**

### 🎯 NEW! Unified Wallet Demo  
```bash
python examples/unified_wallet_demo.py
```
**✨ Experience the seamless unified wallet - one account for ALL services!**

**Key Features:**
- 👥 **Users**: One wallet, all services - ultimate simplicity!
- 🔧 **Developers**: Zero complexity - just tag your service calls!
- 💰 **Platform**: Intelligent routing with automatic revenue sharing
- 🎯 **Seamless**: Cross-service usage without any friction

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
├── multi_adapter_demo.py    # Multi-adapter system demonstration
├── factory_complete.py      # Complete factory pattern example
├── external_servers_demo.py # External server integration demo
├── production_ready.py      # Production-grade deployment example
└── configs/                 # Configuration files directory
    ├── basic.yaml           # Basic configuration
    ├── factory.yaml         # Factory pattern configuration  
    ├── external_servers.yaml # External servers configuration
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

### 🔧 middleware_demo.py - Comprehensive Middleware Examples
**Middleware Learning** | **Complexity: ⭐⭐⭐**

**5 Complete Demo Scenarios**, demonstrating middleware configuration and usage:
1. **Basic Middleware** - timing + logging introductory examples
2. **Production Stack** - Enterprise-grade 4-layer middleware configuration
3. **Custom Middleware** - Seamless integration with custom_middleware.py
4. **Enterprise Stack** - Complete 5-layer middleware demonstration 🆕
5. **Performance Comparison** - Performance analysis with/without middleware

**Real Integration**: Now you can actually call custom middleware, no longer commented out

```python
# Core Features Preview - Enterprise Middleware Stack
config = {
    "middleware": [
        {"type": "custom", "class": "examples.custom_middleware.AuthenticationMiddleware"},
        {"type": "custom", "class": "examples.custom_middleware.AuditMiddleware"},
        {"type": "custom", "class": "examples.custom_middleware.CacheMiddleware"},
        {"type": "error_handling", "enabled": True},
        {"type": "timing", "enabled": True}
    ]
}
```

### 🛠️ custom_middleware.py - Custom Middleware Development
**Advanced Customization** | **Complexity: ⭐⭐⭐⭐** | **New Name** 🆕

**3 Enterprise-Grade Middleware** complete implementations:
- **AuthenticationMiddleware** - API key authentication with anonymous access control
- **AuditMiddleware** - Security audit logging with sensitive data masking and JSON format recording
- **CacheMiddleware** - Intelligent response caching with TTL management and automatic cleanup

**Perfect Integration with middleware_demo.py**: Can be directly called and tested

**See complete implementation**: `examples/custom_middleware.py`

### 🚀 complete_server_demo.py - Complete Real-World Server
**Authorization, billing, and file management integration** | **Complexity: ⭐⭐⭐⭐**

**Complete real-world server implementation** demonstrating the integration of all major MCP Factory features:

**📋 Key Features:**
1. **Three-tier role system** - visitor/user/admin with configurable permissions
2. **File management operations** - read, write, delete, batch processing with role-based access
3. **Billing integration** - usage tracking, limits, and smart upgrade suggestions
4. **Real-world architecture** - proper error handling, logging, and user feedback

**🎯 Use Cases:**
- Learn complete server implementation patterns
- Understand authorization and billing integration
- See real-world error handling and user experience
- Reference for production server development

```bash
# Run complete server demo
python examples/complete_server_demo.py
```

**Core Feature Preview:**
```python
# Complete server with all features
server = ManagedServer(
    name="file-server",
    authorization=True,
    billing=True,
    expose_management_tools=True
)

# Role-based file operations with billing checks
@server.tool("read_file")
async def read_file(user_id: str, filename: str):
    # Permission and billing check
    permission_result = server.check_permission_with_billing(
        user_id, "file", "read", "basic"
    )
    
    if not permission_result["allowed"]:
        return {
            "error": permission_result["reason"],
            "upgrade_suggestion": permission_result["upgrade_suggestion"]
        }
    
    # Actual file operation
    return await perform_file_read(filename)
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

### Configuration Files Overview

- **`basic.yaml`** - Minimal configuration for simple servers
- **`factory.yaml`** - Development environment with hot reload and debugging
- **`mounting.yaml`** - Multi-server mounting with rate limiting
- **`production.yaml`** - Enterprise-grade production configuration

**See complete configurations**: `examples/configs/` directory

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

## 🚀 New: Essential Developer Features Demo

The `essential_developer_features_demo.py` showcases the most practical developer wallet features:

### Key Features Demonstrated
- **📊 Lago-based Revenue Analytics** - Real-time revenue tracking using Lago transactions
- **🎯 Service Performance Metrics** - Detailed analysis of service usage and revenue
- **💸 Payout Management** - Multi-method payout with Lago wallet integration
- **📋 Transaction History** - Direct access to Lago transaction data
- **📈 Multi-period Reporting** - Compare revenue across different time periods

### Why This Demo Matters
- ✅ **Maximizes Lago Integration** - Uses 80% of Lago's existing capabilities
- ✅ **Production Ready** - Based on proven, stable APIs
- ✅ **Developer Focused** - Provides actionable business insights
- ✅ **Low Maintenance** - Minimal custom code, maximum value

### Quick Start
```bash
python examples/essential_developer_features_demo.py
```

This demo represents the **optimal balance** between functionality and simplicity, making it the recommended starting point for understanding MCP Factory's developer wallet capabilities. 