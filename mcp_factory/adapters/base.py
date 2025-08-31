"""Base classes and utilities for MCP Factory Adapters.

This module provides the foundation for all adapter implementations:
- BaseAdapter: Abstract base class for all adapters
- Common utilities for type conversion, code generation, etc.
- Shared data structures and enums
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AdapterType(Enum):
    """Supported adapter types"""

    PYTHON_CLASS = "python_class"
    HTTP_API = "http_api"
    CLI_COMMAND = "cli_command"


@dataclass
class SourceInfo:
    """Source information for adapters"""

    adapter_type: AdapterType
    source_path: str
    config: dict[str, Any]


@dataclass
class CapabilityInfo:
    """Information about a discovered capability"""

    name: str
    description: str
    parameters: list[dict[str, Any]]
    capability_type: str
    metadata: dict[str, Any]


@dataclass
class ConnectivityResult:
    """Result of connectivity test"""

    success: bool
    message: str
    details: dict[str, Any] | None = None


class BaseAdapter(ABC):
    """Abstract base class for all adapters"""

    def __init__(self, source_info: SourceInfo):
        self.source_info = source_info
        self.config = source_info.config
        self.name = self.config.get("name", self.source_info.source_path.split("/")[-1].split(".")[0])

        # Initialize cache if enabled
        cache_enabled = self.config.get("cache_enabled", True)
        if cache_enabled:
            from .cache import AdapterCache

            self._cache: AdapterCache | None = AdapterCache()
        else:
            self._cache = None

    @abstractmethod
    def discover_capabilities(self) -> list[CapabilityInfo]:
        """Discover available capabilities from the source"""
        pass

    @abstractmethod
    def generate_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate MCP tool code for a capability"""
        pass

    @abstractmethod
    def test_connectivity(self) -> ConnectivityResult:
        """Test connectivity to the source"""
        pass

    def get_adapter_info(self) -> dict[str, Any]:
        """Get adapter information"""
        return {
            "type": self.source_info.adapter_type.value,
            "source": self.source_info.source_path,
            "config": self.config,
        }


class AdapterError(Exception):
    """Base exception for adapter errors"""

    pass


class ConnectivityError(AdapterError):
    """Raised when connectivity test fails"""

    pass


class DiscoveryError(AdapterError):
    """Raised when capability discovery fails"""

    pass


class GenerationError(AdapterError):
    """Raised when tool code generation fails"""

    pass


# Utility functions


def convert_type(param_type: str) -> str:
    """Convert parameter type to Python type annotation"""
    type_mapping = {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "List[Any]",
        "object": "Dict[str, Any]",
    }
    return type_mapping.get(param_type.lower(), "Any")


def generate_parameter_signature(parameters: list[dict[str, Any]]) -> str:
    """Generate function parameter signature from parameter list"""
    if not parameters:
        return ""

    param_defs = []
    for param in parameters:
        param_name = param["name"]
        param_type = convert_type(param.get("type", "string"))
        required = param.get("required", True)

        if required:
            param_defs.append(f"{param_name}: {param_type}")
        else:
            param_defs.append(f"{param_name}: {param_type} = None")

    return ", ".join(param_defs)


def generate_parameter_docs(parameters: list[dict[str, Any]]) -> str:
    """Generate parameter documentation"""
    if not parameters:
        return "        No parameters"

    param_docs = []
    for param in parameters:
        name = param["name"]
        desc = param.get("description", "No description")
        required = "Required" if param.get("required", True) else "Optional"
        param_docs.append(f"        {name}: {required} - {desc}")

    return "\n".join(param_docs)


def generate_tool_template(
    tool_name: str, parameters: list[dict[str, Any]], description: str, implementation_code: str
) -> str:
    """Generate standard MCP tool template"""

    param_signature = generate_parameter_signature(parameters)
    param_docs = generate_parameter_docs(parameters)

    # Add proper indentation to implementation code
    indented_impl = "\n".join(f"    {line}" if line.strip() else line for line in implementation_code.split("\n"))

    template = f'''"""Generated MCP tool: {tool_name}"""

from typing import Any, Dict, List


def {tool_name}({param_signature}) -> Dict[str, Any]:
    """
    {description}

    Parameters:
{param_docs}

    Returns:
        Dict[str, Any]: Tool execution result
    """
    try:
{indented_impl}
    except Exception as e:
        return {{
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }}
'''

    return template


def auto_detect_adapter_type(source_path: str) -> AdapterType | None:
    """Auto-detect adapter type from source path"""
    if source_path.startswith(("http://", "https://")):
        return AdapterType.HTTP_API
    elif "." in source_path and not source_path.startswith("/"):
        # Looks like Python module path
        return AdapterType.PYTHON_CLASS
    else:
        # Assume CLI command
        return AdapterType.CLI_COMMAND
