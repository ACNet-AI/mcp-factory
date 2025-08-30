"""MCP Factory Adapters - System Capability Adapter Module

This module provides various adapters for converting different types of system capabilities into MCP tools:
- PythonClassAdapter: Python class method adapter
- HttpApiAdapter: HTTP API endpoint adapter
- EnhancedHttpApiAdapter: Enhanced HTTP adapter (supports FastMCP)
- CliAdapter: Command line tool adapter
- MultiSourceAdapter: Multi-source unified adapter
"""

# Import core adapter classes
from .multi_adapter import (
    AdapterFactory,
    BaseAdapter,
    CliAdapter,
    HttpApiAdapter,
    MultiSourceAdapter,
    PythonClassAdapter,
    SourceInfo,
)

# Try to import enhanced HTTP adapter
try:
    from .enhanced_http_adapter import FASTMCP_AVAILABLE, EnhancedHttpApiAdapter, create_enhanced_http_adapter

    _enhanced_available = True
except ImportError:
    _enhanced_available = False
    # For backward compatibility, create placeholders
    EnhancedHttpApiAdapter = None
    create_enhanced_http_adapter = None
    FASTMCP_AVAILABLE = False

# Import universal adapter creation functions
from .universal_adapter import FreshInstanceStrategy, SingletonStrategy, StaticMethodStrategy, UniversalMCPAdapter


# Convenience functions
def create_python_adapter(class_path: str, strategy: str = "singleton"):
    """Create Python class adapter"""
    from .universal_adapter import FreshInstanceStrategy, SingletonStrategy, StaticMethodStrategy, UniversalMCPAdapter

    strategy_map = {"singleton": SingletonStrategy, "fresh": FreshInstanceStrategy, "static": StaticMethodStrategy}

    strategy_class = strategy_map.get(strategy, SingletonStrategy)
    return UniversalMCPAdapter(class_path, strategy_class())


def create_http_adapter(base_url: str, enhanced: bool = True, **kwargs):
    """Create HTTP API adapter"""
    if enhanced and _enhanced_available:
        return create_enhanced_http_adapter(base_url, **kwargs)
    else:
        # Fall back to standard implementation
        from .multi_adapter import HttpApiAdapter, SourceInfo

        source_info = SourceInfo(source_type="http_api", source_path=base_url, config=kwargs)
        return HttpApiAdapter(source_info)


def create_multi_source_adapter():
    """Create multi-source adapter"""
    return MultiSourceAdapter()


# Exported public interface
__all__ = [
    # Base adapter classes
    "BaseAdapter",
    "PythonClassAdapter",
    "HttpApiAdapter",
    "CliAdapter",
    "MultiSourceAdapter",
    "AdapterFactory",
    "SourceInfo",
    # Enhanced adapters (if available)
    "EnhancedHttpApiAdapter",
    "create_enhanced_http_adapter",
    "FASTMCP_AVAILABLE",
    # Universal adapters
    "UniversalMCPAdapter",
    "SingletonStrategy",
    "FreshInstanceStrategy",
    "StaticMethodStrategy",
    # Convenience functions
    "create_python_adapter",
    "create_http_adapter",
    "create_multi_source_adapter",
]
