# FastMCP-Factory Examples

This directory contains usage examples for FastMCP-Factory to help you understand how to use the library to create and manage MCP servers.

## Example Files

### 1. basic_example.py

Basic example demonstrating the core features of FastMCP-Factory:

- Creating and managing servers
- Registering and using tools
- Configuration hot reload
- Mounting sub-servers
- Authentication providers

How to run:

```bash
python -m examples.basic_example
```

### 2. advanced_example.py

Advanced example demonstrating the advanced features of FastMCP-Factory:

- Command-line interface
- Authentication provider management
- Lifecycle management
- Custom tool serialization
- Tags and dependencies management
- Logging configuration

How to run:

```bash
# Create authentication provider
python -m examples.advanced_example create-auth --id test-auth --type auth0 --domain example.auth0.com --client-id xxxx --client-secret xxxx

# List authentication providers
python -m examples.advanced_example list-auth

# Create and run advanced server
python -m examples.advanced_example run-server --config examples/config.example.yaml --auth-provider test-auth

# List all servers
python -m examples.advanced_example list-servers
```

### 3. config.example.yaml

Complete configuration example file, containing all configuration options supported by FastMCP-Factory with detailed comments. 