"""MCP Factory Adapters - Unified adapter system for converting various sources to MCP tools.

This module provides a clean, unified interface for working with different types of adapters:
- Python classes
- HTTP APIs
- CLI commands
- Multi-source management

Usage:
    from mcp_factory.adapters import adapt

    # Simple usage - auto-detect type
    tools = adapt("my.module.MyClass")
    tools = adapt("https://api.example.com")
    tools = adapt("docker ps")

    # Explicit type specification
    tools = adapt.python("my.module.MyClass", strategy="singleton")
    tools = adapt.http("https://api.example.com", timeout=30)
    tools = adapt.cli("docker ps", shell=True)
"""

from typing import Any

# Import core components
from .base import (
    AdapterError,
    AdapterType,
    BaseAdapter,
    CapabilityInfo,
    ConnectivityError,
    ConnectivityResult,
    DiscoveryError,
    GenerationError,
    SourceInfo,
    auto_detect_adapter_type,
)
from .cli_adapter import CliAdapter, create_cli_adapter
from .http_adapter import HttpApiAdapter, create_http_adapter
from .multi_adapter import AdapterRegistry, MultiSourceAdapter, create_multi_adapter

# Import specific adapters
from .python_adapter import PythonClassAdapter, create_python_adapter


class AdaptInterface:
    """Unified interface for creating adapters"""

    def __call__(self, source_path: str, **kwargs: Any) -> BaseAdapter:
        """Auto-detect and create appropriate adapter

        Args:
            source_path: Path/URL to the source
            **kwargs: Additional configuration options

        Returns:
            BaseAdapter: Configured adapter instance
        """
        adapter_type = auto_detect_adapter_type(source_path)
        if adapter_type is None:
            raise ValueError(f"Could not auto-detect adapter type for: {source_path}")

        if adapter_type == AdapterType.PYTHON_CLASS:
            return self.python(source_path, **kwargs)
        elif adapter_type == AdapterType.HTTP_API:
            return self.http(source_path, **kwargs)
        elif adapter_type == AdapterType.CLI_COMMAND:
            return self.cli(source_path, **kwargs)
        else:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")

    def python(
        self,
        class_path: str,
        strategy: str = "singleton",
        instance_creation: str | None = None,
        include_methods: list[str] | None = None,
        exclude_methods: list[str] | None = None,
    ) -> PythonClassAdapter:
        """Create Python class adapter

        Args:
            class_path: Full path to Python class (e.g., "my.module.MyClass")
            strategy: Invocation strategy ("singleton", "fresh", "static")
            instance_creation: Custom instance creation code
            include_methods: List of method patterns to include
            exclude_methods: List of method patterns to exclude

        Returns:
            PythonClassAdapter: Configured Python adapter
        """
        return create_python_adapter(
            class_path=class_path,
            strategy=strategy,
            instance_creation=instance_creation,
            include_methods=include_methods,
            exclude_methods=exclude_methods,
        )

    def http(
        self,
        base_url: str,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
        use_fastmcp: bool = True,
        endpoints: list[dict[str, Any]] | None = None,
    ) -> HttpApiAdapter:
        """Create HTTP API adapter

        Args:
            base_url: Base URL of the HTTP API
            timeout: Request timeout in seconds
            headers: Additional HTTP headers
            use_fastmcp: Whether to use FastMCP for OpenAPI discovery
            endpoints: Manual endpoint configuration

        Returns:
            HttpApiAdapter: Configured HTTP adapter
        """
        return create_http_adapter(
            base_url=base_url, timeout=timeout, headers=headers, use_fastmcp=use_fastmcp, endpoints=endpoints
        )

    def cli(
        self,
        command: str,
        shell: bool = False,
        timeout: int = 30,
        working_dir: str | None = None,
        env_vars: dict[str, str] | None = None,
        parameters: list[dict[str, Any]] | None = None,
        variants: list[dict[str, Any]] | None = None,
    ) -> CliAdapter:
        """Create CLI command adapter

        Args:
            command: Command to execute
            shell: Whether to use shell execution
            timeout: Command timeout in seconds
            working_dir: Working directory for command execution
            env_vars: Environment variables
            parameters: Command parameter definitions
            variants: Command variants with different arguments

        Returns:
            CliAdapter: Configured CLI adapter
        """
        return create_cli_adapter(
            command=command,
            shell=shell,
            timeout=timeout,
            working_dir=working_dir,
            env_vars=env_vars,
            parameters=parameters,
            variants=variants,
        )

    def multi(self) -> MultiSourceAdapter:
        """Create multi-source adapter for managing multiple sources

        Returns:
            MultiSourceAdapter: Multi-source adapter instance
        """
        return create_multi_adapter()


# Create the main interface instance
adapt = AdaptInterface()


# Convenience functions for backward compatibility
def create_adapter(source_path: str, adapter_type: str | None = None, **kwargs: Any) -> BaseAdapter:
    """Create adapter with optional type specification"""
    if adapter_type:
        if adapter_type == "python_class":
            return adapt.python(source_path, **kwargs)
        elif adapter_type == "http_api":
            return adapt.http(source_path, **kwargs)
        elif adapter_type == "cli_command":
            return adapt.cli(source_path, **kwargs)
        else:
            raise ValueError(f"Unsupported adapter type: {adapter_type}")
    else:
        return adapt(source_path, **kwargs)


# Export public interface
__all__ = [
    # Main interface
    "adapt",
    # Base classes and types
    "BaseAdapter",
    "CapabilityInfo",
    "ConnectivityResult",
    "SourceInfo",
    "AdapterType",
    # Specific adapters
    "PythonClassAdapter",
    "HttpApiAdapter",
    "CliAdapter",
    "MultiSourceAdapter",
    # Registry and factory
    "AdapterRegistry",
    # Exceptions
    "AdapterError",
    "ConnectivityError",
    "DiscoveryError",
    "GenerationError",
    # Convenience functions
    "create_adapter",
    "create_python_adapter",
    "create_http_adapter",
    "create_cli_adapter",
    "create_multi_adapter",
    # Utilities
    "auto_detect_adapter_type",
]
