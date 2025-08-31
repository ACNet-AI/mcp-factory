"""Multi-Source Adapter - Manage multiple adapters as a unified system."""

import asyncio
from typing import Any

from .async_utils import ConcurrentDiscovery
from .base import AdapterType, BaseAdapter, CapabilityInfo, SourceInfo, auto_detect_adapter_type
from .cache import cached_method
from .cli_adapter import CliAdapter
from .http_adapter import HttpApiAdapter
from .python_adapter import PythonClassAdapter


class AdapterRegistry:
    """Registry for adapter types"""

    _adapters = {
        AdapterType.PYTHON_CLASS: PythonClassAdapter,
        AdapterType.HTTP_API: HttpApiAdapter,
        AdapterType.CLI_COMMAND: CliAdapter,
    }

    @classmethod
    def create_adapter(cls, source_info: SourceInfo) -> BaseAdapter:
        """Create adapter instance based on source info"""
        adapter_class = cls._adapters.get(source_info.adapter_type)
        if not adapter_class:
            raise ValueError(f"Unsupported adapter type: {source_info.adapter_type}")

        return adapter_class(source_info)  # type: ignore[abstract]


class MultiSourceAdapter:
    """Multi-source adapter for managing multiple adapters"""

    def __init__(self) -> None:
        self.adapters: list[BaseAdapter] = []
        self._adapter_map: dict[str, BaseAdapter] = {}

    def add_source(
        self,
        source_path: str,
        adapter_type: str | None = None,
        config: dict[str, Any] | None = None,
        name: str | None = None,
    ) -> str:
        """Add a source to the multi-adapter"""
        # Auto-detect adapter type if not provided
        if adapter_type is None:
            detected_type = auto_detect_adapter_type(source_path)
            if detected_type is None:
                raise ValueError(f"Could not auto-detect adapter type for: {source_path}")
            adapter_type_enum = detected_type
        else:
            try:
                adapter_type_enum = AdapterType(adapter_type)
            except ValueError as e:
                raise ValueError(f"Unsupported adapter type: {adapter_type}") from e

        # Create source info
        source_info = SourceInfo(adapter_type=adapter_type_enum, source_path=source_path, config=config or {})

        # Create adapter
        adapter = AdapterRegistry.create_adapter(source_info)

        # Generate unique name if not provided
        if name is None:
            name = f"{adapter_type_enum.value}_{len(self.adapters)}"

        # Add to collections
        self.adapters.append(adapter)
        self._adapter_map[name] = adapter

        return name

    @cached_method("multi_discover", ttl=1800)  # Cache for 30 minutes
    def discover_all_capabilities(self) -> dict[str, list[CapabilityInfo]]:
        """Discover capabilities from all adapters"""
        # Use async discovery for better performance
        return asyncio.run(self._async_discover_all_capabilities())

    async def _async_discover_all_capabilities(self) -> dict[str, list[CapabilityInfo]]:
        """Async version of discover_all_capabilities"""
        adapters = list(self._adapter_map.values())

        if not adapters:
            return {}

        # Use concurrent discovery for better performance
        capabilities_map = await ConcurrentDiscovery.discover_multiple_sources(adapters, max_concurrency=5)

        # Map back to original names
        result = {}
        for name, adapter in self._adapter_map.items():
            adapter_name = adapter.name
            if adapter_name in capabilities_map:
                result[name] = capabilities_map[adapter_name]
            else:
                result[name] = []

        return result


def create_multi_adapter() -> MultiSourceAdapter:
    """Create a new multi-source adapter"""
    return MultiSourceAdapter()
