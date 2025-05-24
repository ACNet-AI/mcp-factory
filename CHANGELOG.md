# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-05-24

### Added
- **CLI Tool**: Brand new command-line interface (`mcpf`)
  - `mcpf template`: Generate configuration templates (minimal/simple/full)
  - `mcpf validate`: Validate configuration files
  - `mcpf run`: Run MCP servers
  - `mcpf quick`: Quickly create and run servers
  - `mcpf list`: List all servers and authentication providers
  - `mcpf auth`: Create authentication providers
- Added `click>=8.0.0` dependency for CLI functionality
- Complete CLI module structure: `mcp_factory.cli`

### Changed
- Enabled CLI entry point in pyproject.toml
- Updated README.md with CLI usage documentation

### Fixed
- Improved configuration template reuse and user experience optimization

## [0.1.1] - 2025-05-23

### Added
- Complete demo examples showing basic and advanced usage patterns
- Enhanced test coverage with performance benchmarks

### Changed
- Renamed `examples/advanced_config.yaml` to `examples/config.example.yaml` for better naming convention
- Improved configuration file structure and documentation
- Updated configuration examples with production-friendly defaults (localhost instead of 0.0.0.0, INFO instead of DEBUG logging)
- Applied consistent code formatting across all files using ruff

### Fixed
- Corrected test assertion message from "Detected duplicate transport parameter" to "Detected repeated transport parameter"
- Adjusted performance test threshold from 0.30 to 0.40 seconds to account for management tools registration overhead
- Removed unused `AuthProviderRegistry` import from examples

### Improved
- Enhanced English documentation and internationalization
- Better code organization and consistency
- More realistic performance test expectations

## [0.1.0] - 2025-05-22

### Added
- Initial release of FastMCP-Factory
- Core factory pattern implementation for FastMCP servers
- Managed server functionality with automatic tool registration
- Comprehensive authentication and authorization framework
- YAML-based configuration management
- Extensive test suite with >90% coverage
- Complete documentation and examples 