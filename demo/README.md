# FastMCP-Factory Demo

This directory contains the FastMCP-Factory demonstration project, showing how to use the factory pattern to create and manage MCP servers.

## 📁 File Structure

```
demo/
├── README.md          # This file
├── server.py          # Demo server (using FastMCPFactory)
├── client.py          # Multi-functional client
└── config.yaml        # Server configuration file
```

## 🚀 Quick Start

### 1. Start Server

```bash
python demo/server.py
```

The server will:
- Create ManagedServer instance using FastMCPFactory
- Automatically load configuration file `config.yaml`
- Register calculation tools (addition, multiplication)
- Enable management tools (24 management tools)
- Provide service at `http://localhost:8888/api/mcp`

### 2. Run Client

**Standard mode** (test basic functionality):
```bash
python demo/client.py
```

**Management tools mode** (detailed display of management tools):
```bash
python demo/client.py --mgmt
```

## 🔧 Feature Demonstration

### Server Features
- **Factory Pattern**: Demonstrates the use of `FastMCPFactory`
- **Configuration Management**: Shows loading and application of YAML configuration files
- **Tool Registration**: 
  - Regular tools: `add` (addition), `multiply` (multiplication)
  - Management tools: About 24 FastMCP native management tools
- **Network Service**: HTTP transport mode

### Client Features
- **Connection Testing**: Verify server connection status
- **Tool Discovery**: Automatically discover available tools
- **Functionality Testing**: Test calculation tools and management tools
- **Categorized Display**: Distinguish between regular tools and management tools
- **Two Modes**: Standard mode and management tools detailed mode

## ⚙️ Configuration Guide

`config.yaml` contains the following configuration:

```yaml
server:
  name: demo-server
  instructions: Simple calculation server
  host: localhost
  port: 8888
  transport: streamable-http

tools:
  expose_management_tools: true    # Enable management tools

advanced:
  log_level: DEBUG
  streamable_http_path: /api/mcp
```

### Key Configuration Items
- `expose_management_tools: true` - Enable management tools registration
- `streamable_http_path` - HTTP API path
- `log_level` - Log level

## 🛠️ Technical Features

### FastMCP-Factory Integration
- Use factory pattern to create server instances
- Support configuration file-driven server creation
- Automatically handle runtime parameter separation (compatible with FastMCP 2.4.0)

### Management Tools
- Automatically register FastMCP native management tools
- Support server information query, configuration reload and other functions
- All management tools prefixed with `manage_`

### Error Handling
- Port occupation check
- Connection status verification
- Graceful error recovery

## 🔍 Troubleshooting

### Common Issues

1. **Port Occupied**
   ```
   Error: Port 8888 is already in use, please choose another port
   ```
   Solution: Modify the `port` setting in `config.yaml`

2. **Connection Failed**
   ```
   Error: [Errno 61] Connection refused
   ```
   Solution: Ensure the server is started and the port is correct

3. **Management Tools Not Registered**
   - Check if `expose_management_tools` in `config.yaml` is set to `true`
   - View tool registration statistics in server startup logs

### Debug Mode

Detailed information is displayed when starting the server:
```
===== Tool Registration Status =====
Management tools: 24 registered
Regular tools: 2 registered
====================================
```

## 📚 Related Documentation

- [FastMCP-Factory Documentation](../README.md)
- [Examples Collection](../examples/README.md)
- [API Reference](../docs/)

## 🤝 Contributing

If you find issues or have improvement suggestions, please submit an Issue or Pull Request. 