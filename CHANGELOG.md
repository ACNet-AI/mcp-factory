# Changelog

This document records all significant changes to the MCP Factory project.

## [1.2.1] - 2025-08-31

### 🔧 Bug Fixes
- **Type Safety** - Fixed all mypy type annotation errors across the codebase
- **Test Updates** - Updated outdated test assertions to match current API behavior
- **Code Quality** - Resolved all ruff linting issues and improved code formatting
- **Privacy Protection** - Removed .cursor configuration files from version control history

### 🧪 Testing Improvements
- **API Compatibility** - Updated tests to expect dict return types instead of strings for management tools info
- **Component Discovery** - Enhanced test coverage for component scanning and discovery functionality
- **Parameter Generation** - Fixed test expectations for tool parameter schema structure

## [1.2.0] - 2025-08-30

### 🏗️ Architecture Improvements
- **Authentication Architecture Refactor** - Moved `installation_id` from project config to local auth cache (`~/.mcp-factory/auth_cache.json`)
- **Security Enhancement** - Resolved security concerns with storing sensitive installation_id in shareable project configurations
- **Simplified Configuration** - Removed complex user configuration modules in favor of streamlined auth cache system
- **Publisher Optimization** - Enhanced publisher.py with direct authentication cache management

### ⬆️ Dependency Updates
- **FastMCP Upgrade** - Updated from v2.10.6 to v2.11.3 with latest features and improvements
- **Core Dependencies** - Updated all major dependencies to latest stable versions:
  - `aiohttp`: 3.12.13 → 3.12.15
  - `jsonschema`: 4.24.0 → 4.25.1  
  - `mcp`: 1.10.1 → 1.13.1
  - `ruff`: 0.12.1 → 0.12.11
  - `uvicorn`: 0.34.3 → 0.35.0

### 🔧 Code Quality
- **Linting Fixes** - Resolved all Ruff code quality issues and formatting inconsistencies
- **Type Safety** - Maintained full compatibility with updated dependencies
- **Clean Architecture** - Removed temporary test files and cleaned project structure

### 🚀 FastMCP 2.11.3 Benefits
- **Enhanced Stability** - Improved error handling and middleware support
- **Better Performance** - Optimized sub-process reuse and connection management  
- **New Capabilities** - Access to elicitation support and output schema features
- **Improved Developer Experience** - Automatic type conversion and reduced boilerplate code

## [1.1.1] - 2025-07-25

### 🐛 Bug Fixes
- **Git Initialization** - Fixed Git repository initialization failures in test environments
- **Test Stability** - Resolved 41 failing tests related to missing Git user configuration
- **Code Quality** - Fixed all Ruff formatting and MyPy type checking issues

### 🔧 Improvements
- **Testing Environment** - Automatic Git user configuration when global settings are missing
- **CI/CD Stability** - Enhanced test reliability across different environments
- **Code Standards** - Improved code formatting consistency

## [1.1.0] - 2025-07-25

### ✨ New Features
- **Project Publishing System** - Automated GitHub repository creation and MCP Hub registration
- **GitHub App Integration** - Seamless authentication and deployment workflow  
- **CLI Publishing Command** - New `mcpf project publish` command for one-click publishing
- **Smart Publishing Flow** - API-first with manual fallback options

### 🌍 Internationalization
- **Complete English Translation** - All documentation and code comments now in English
- **New Publishing Guide** - Comprehensive guide for project publishing workflow

### 🔧 Improvements  
- **FastMCP Upgrade** - Updated to v2.10.5 with enhanced features
- **Enhanced CLI** - Improved server management and user experience
- **Architecture Refactoring** - Better component management and organization
- **Type Safety** - Improved MyPy type checking and code quality

### 🧪 Testing & Quality
- **E2E Testing** - New end-to-end test framework
- **Code Formatting** - Enhanced Ruff configuration and automated formatting
- **Dependency Updates** - Latest compatible versions for all dependencies

### 📚 Documentation
- **Publishing Guide** - New comprehensive publishing documentation
- **CLI Guide Updates** - Enhanced CLI documentation with new commands
- **Configuration Guide** - Updated with publishing configuration options
- **Troubleshooting** - Added publishing-related troubleshooting section

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