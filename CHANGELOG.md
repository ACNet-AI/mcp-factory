# Changelog

This document records all significant changes to the MCP Factory project.

## [1.5.0] - 2025-10-13

### 🚀 Major Features
- **Complete Billing System** - Comprehensive billing infrastructure with multi-provider support (3,600+ lines)
  - BillingManager with usage tracking and subscription management
  - Lago billing engine integration (1,077 lines)
  - Multiple payment gateway support (Stripe, Local, Custom)
  - Flexible billing models: subscription, pay-per-use, prepaid, free
  - UUID-based unique transaction IDs for usage tracking
- **Proxy Architecture** - Flexible proxy metadata system and authorization
  - ProxyConfig and AuthorizedProxies models for whitelist management
  - Proxy authorization validation in ManagedServer
  - Support for multiple proxy types (shared, dedicated, enterprise)
  - Full proxy information pass-through without interpretation

### 🔧 Authorization Enhancements
- **Billing Integration** - Seamless integration with authorization via BillingAuthIntegration
- **Proxy Access Control** - Add ManagedServer.verify_proxy_access() for proxy validation
- **Enhanced Models** - Add ProxyConfig and AuthorizedProxies to authorization models
- **Improved Naming** - Rename billing modes for clarity (proxy → pay_per_use)

### 📊 Usage Tracking Improvements
- **Standardized Parameters** - Consistent naming (amount → quantity) across all interfaces
- **Enhanced Metadata** - Complete context preservation in usage records
- **Proxy Authorization** - Add proxy_authorized validation status to usage records
- **Clear Responsibilities** - Server records quantity, proxy handles pricing

### 🏗️ Server Integration
- **Billing Integration** - Add comprehensive billing system to ManagedServer (+873 lines)
- **Coordination Layer** - Billing and authorization coordination
- **Automatic Tracking** - Usage tracking with request context
- **Tool-Level Checks** - Billing and permission validation per tool
- **Self-Service Tools** - User billing management tools

### 🔨 Code Quality & Cleanup
- **Codebase Optimization** - Remove 15 redundant example files (-2,700 lines)
- **New Demo** - Add usage_tracking_demo.py showing complete workflow
- **Test Coverage** - Enhanced test suite with 1,157 tests passing
- **CI Improvements** - Fix test configuration and import paths for better CI compatibility

### ⬆️ Dependencies
- **FastMCP** - Updated from 2.12.0 to 2.12.4
- **Core Updates** - 34 dependencies updated to latest versions

### 📚 Documentation
- **Authorization Guide** - Expanded documentation (+480 lines)
- **Architecture Clarity** - Clear separation between server and proxy responsibilities

### 💡 Architecture Impact
- Clean separation: developer server (permissions + usage quantity) vs proxy platform (pricing + billing)
- Flexible metadata approach supporting diverse proxy architectures
- Extensible billing system supporting multiple providers

## [1.4.0] - 2025-09-04

### 🚀 Major Features
- **Enterprise Authorization System** - Complete RBAC permission management based on Casbin
- **Authorization Module** - New `mcp_factory.authorization` package with manager, models, audit, and cache
- **Permission Management Tools** - 20+ MCP tools for user and role management
- **Audit Logging** - Complete permission change history tracking
- **Authorization Demo** - Comprehensive example showing enterprise permission management

### 🏗️ Architecture Improvements
- **Modular Design** - Refactored authorization module into 5 specialized services (PermissionEngine, RoleService, DebugService, SaaSService)
- **Code Quality** - Achieved zero MyPy errors and zero Ruff warnings across the entire codebase
- **Type Safety** - Complete type annotations for better IDE support and error detection
- **Maintainability** - Reduced complexity from 1,623-line monolith to focused, single-responsibility modules

### 🔧 API Changes
- **ManagedServer Parameter** - Changed `enable_permission_check` to `authorization` for clarity
- **Module Restructure** - Migrated from `auth.py` to `authorization/` package structure
- **Data Directory** - Authorization system now uses user data directory (`~/.mcp-factory/`) instead of project root
- **Backward Compatibility** - 100% API compatibility maintained during refactoring

### 🧪 Testing & Quality
- **Test Coverage** - All 910 tests passing with comprehensive authorization system coverage
- **Code Standards** - Zero linting errors, complete type checking, and clean code structure
- **Documentation Updates** - Updated architecture docs to reflect new modular authorization system

### 📚 Documentation
- **Authorization Guide** - Complete documentation for permission system setup and usage
- **Architecture Updates** - Reflected new authorization module in overall architecture docs

## [1.3.0] - 2025-08-31

### 🚀 Major Features
- **New Adapter Architecture** - Unified interface with `adapt.python()`, `adapt.http()`, `adapt.cli()`, and `adapt.multi()`
- **Performance Optimization** - Caching system with TTL support and async processing
- **Multi-Source Support** - Enhanced multi-adapter management with concurrent operations

### 🔧 Quality Improvements
- **Code Quality** - Zero MyPy errors, all Ruff checks passed, 954 tests passing
- **Project Structure** - Reorganized examples and documentation
- **Performance** - 5-50x improvement with intelligent caching

## [1.2.1] - 2025-08-31

### 🔧 Bug Fixes
- **Type Safety** - Fixed all mypy type annotation errors across the codebase
- **Test Updates** - Updated outdated test assertions to match current API behavior
- **Code Quality** - Resolved all ruff linting issues and improved code formatting

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