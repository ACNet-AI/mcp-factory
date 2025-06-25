# Changelog

This document records all significant changes to the MCP Factory project.

## [1.0.0] - 2025-06-25

### 🎯 Major Refactoring - Stable Release
- **Architecture Simplification** - Focus on MCP server creation, building and management
- **Lightweight Design** - Remove complex factory management interfaces, switch to configuration-driven approach
- **Feature Separation** - Separate factory MCP server application into independent project

### ✨ Core Features
- **MCPFactory** - Lightweight server factory class
- **ManagedServer** - Managed server with authentication and permission management support
- **Project Builder** - Automatically generate MCP project structure
- **Configuration Management** - YAML-based configuration system
- **CLI Tools** - Simple and easy-to-use command line interface

### 🔧 Breaking Changes
- Authentication configuration changed to parameter passing approach
- Removed authentication provider management methods (such as `create_auth_provider`)
- Maintain complete authentication and permission checking functionality

---

## Migration Guide

### From 0.x to 1.0.0
1. Update imports: `from mcp_factory import MCPFactory`
2. Pass authentication configuration through `auth` parameter or configuration file
3. For factory server applications, use the independent `mcp-factory-server` project

---

## Version Notes
- **Major version**: Incompatible API changes
- **Minor version**: Backward-compatible functional additions
- **Patch version**: Backward-compatible bug fixes 