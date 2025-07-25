"""Component manager for project component lifecycle management

This module provides the ComponentManager class for:
1. Auto-discovering project components from file system
2. Loading component functions from project modules
3. Registering components to server instances
4. Enforcing __all__ export control for precise component management
5. Managing component metadata and structure
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Import constants from project module
from .constants import ALLOWED_MODULE_TYPES

logger = logging.getLogger(__name__)


class ComponentManager:
    """Component manager for project component lifecycle management"""

    @staticmethod
    def register_components(server: Any, project_path: Path) -> None:
        """Register project components to server

        Args:
            server: Server instance
            project_path: Project path (used as base path for component resolution)
        """
        try:
            config = getattr(server, "_config", {})
            components_config = config.get("components", {})

            if not components_config:
                logger.warning("Project has no component configuration: %s", project_path)
                return

            total_registered = 0
            for component_type in ["tools", "resources", "prompts"]:
                declared_modules = components_config.get(component_type, [])
                if not declared_modules:
                    continue

                functions = []
                for module_config in declared_modules:
                    if module_config.get("enabled", True):
                        # 🎯 Complete path resolution here
                        resolved_file_path = ComponentManager._resolve_component_path(
                            project_path, component_type, module_config["module"]
                        )

                        if resolved_file_path:
                            module_functions = ComponentManager._load_component_functions_from_file(resolved_file_path)
                            functions.extend(module_functions)

                registered_count = ComponentManager._register_functions_to_server(server, component_type, functions)
                total_registered += registered_count

            logger.info("Component registration completed: %s functions", total_registered)
        except Exception as e:
            logger.error("Failed to register components: %s", e)
            # Don't throw exception, allow server to continue creation

    @staticmethod
    def _resolve_component_path(project_path: Path, component_type: str, module_name: str) -> Path | None:
        """Simplified component path resolution

        Args:
            project_path: Component base path (project directory or shared-components directory)
            component_type: Component type (tools, resources, prompts)
            module_name: Simple module name (e.g.: weather_tools)

        Returns:
            Resolved file path or None
        """
        # Only support simple module name pattern
        if not module_name.endswith(".py"):
            module_name_with_ext = f"{module_name}.py"
        else:
            module_name_with_ext = module_name

        resolved_path = project_path / component_type / module_name_with_ext

        if resolved_path.exists():
            logger.debug("Found component file: %s", resolved_path)
            return resolved_path
        else:
            logger.warning("Component file not found: %s", resolved_path)
            return None

    @staticmethod
    def _load_component_functions_from_file(file_path: Path) -> list[tuple[Callable[..., Any], str, str]]:
        """Load all functions from a specific component file

        Args:
            file_path: Absolute path to the component file

        Returns:
            List[Tuple[Callable, str, str]]: Function list (function, name, description)
        """
        import importlib.util
        import sys

        try:
            # Extract module name (remove path and extension)
            clean_module_name = file_path.stem

            spec = importlib.util.spec_from_file_location(clean_module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error("Failed to create module spec for: %s", file_path)
                return []

            module = importlib.util.module_from_spec(spec)
            sys.modules[clean_module_name] = module
            spec.loader.exec_module(module)

            # Require __all__ to be explicitly defined
            if not hasattr(module, "__all__") or not isinstance(module.__all__, list):
                logger.error("Module %s must define __all__ as a list of exportable functions", clean_module_name)
                return []

            functions = []
            for attr_name in module.__all__:
                attr = getattr(module, attr_name, None)
                if attr and callable(attr) and hasattr(attr, "__doc__") and attr.__doc__:
                    description = attr.__doc__
                    functions.append((attr, attr_name, description))

            logger.debug("Successfully loaded %s functions from %s", len(functions), file_path)
            return functions
        except Exception as e:
            logger.error("Failed to load module %s: %s", file_path, e)
            return []

    @staticmethod
    def _register_functions_to_server(
        server: Any, component_type: str, functions: list[tuple[Callable[..., Any], str, str]]
    ) -> int:
        """Register functions to server

        Args:
            server: Server instance
            component_type: Component type
            functions: Function list

        Returns:
            int: Number of successfully registered functions
        """
        registered_count = 0
        for func, name, description in functions:
            try:
                if component_type == "tools":
                    server.tool(name=name, description=description)(func)
                elif component_type == "resources" and hasattr(server, "resource"):
                    server.resource(name=name, description=description)(func)
                elif component_type == "prompts" and hasattr(server, "prompt"):
                    server.prompt(name=name, description=description)(func)
                else:
                    continue
                registered_count += 1
            except Exception as e:
                logger.error("Failed to register %s %s: %s", component_type, name, e)
        return registered_count

    # ========================================================================
    # Component Discovery Methods (moved from Builder)
    # ========================================================================

    @staticmethod
    def discover_project_components(project_path: Path) -> dict[str, Any]:
        """Auto-discover project components

        Args:
            project_path: Project path

        Returns:
            Component configuration dictionary
        """
        logger.info("Auto-discovering project components")
        components_config = {}
        total_components = 0

        for component_type in ALLOWED_MODULE_TYPES:
            component_dir = project_path / component_type
            if component_dir.exists() and component_dir.is_dir():
                discovered_modules = ComponentManager._scan_component_directory(component_dir, component_type)
                if discovered_modules:
                    components_config[component_type] = discovered_modules
                    total_components += len(discovered_modules)
                logger.debug("Discovered %s %s modules", len(discovered_modules), component_type)

        if total_components > 0:
            logger.info("Auto-discovered %s components total", total_components)
            return components_config
        logger.debug("No components discovered, returning empty config")
        return {}

    @staticmethod
    def _scan_component_directory(component_dir: Path, component_type: str) -> list[dict[str, Any]]:
        """Scan component directory

        Args:
            component_dir: Component directory path
            component_type: Component type

        Returns:
            Component configuration list
        """
        modules = []

        # Scan functions in __init__.py
        init_file = component_dir / "__init__.py"
        if init_file.exists():
            init_functions = ComponentManager._scan_init_file_functions(init_file, component_type)
            modules.extend(init_functions)

        # Scan independent .py files
        for py_file in component_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            module_name = py_file.stem
            description = ComponentManager._extract_module_description(py_file)

            module_config = {
                "name": module_name,
                "description": description or f"{component_type.rstrip('s')} module: {module_name}",
                "file": str(py_file.relative_to(component_dir.parent)),
            }
            modules.append(module_config)
            logger.debug("Found %s module: %s", component_type, module_name)

        return modules

    @staticmethod
    def _extract_module_description(module_file: Path) -> str | None:
        """Extract description from module file

        Args:
            module_file: Module file path

        Returns:
            Module description or None
        """
        try:
            with open(module_file, encoding="utf-8") as f:
                content = f.read()

            # Try to extract docstring
            docstring_match = re.search(r'"""([^"]+)"""', content)
            if docstring_match:
                return docstring_match.group(1).strip()

            # Try to extract single-line comment
            comment_match = re.search(r"^#\s*(.+)", content, re.MULTILINE)
            if comment_match:
                return comment_match.group(1).strip()

            return None

        except Exception as e:
            logger.debug("Failed to extract description from %s: %s", module_file, e)
        return None

    @staticmethod
    def _scan_init_file_functions(init_file: Path, component_type: str) -> list[dict[str, Any]]:
        """Scan functions in __init__.py file

        Args:
            init_file: __init__.py file path
            component_type: Component type

        Returns:
            Function configuration list
        """
        functions = []

        try:
            with open(init_file, encoding="utf-8") as f:
                content = f.read()

            # Use regex to match function definitions
            function_pattern = r"^def (\w+)\("
            matches = re.findall(function_pattern, content, re.MULTILINE)

            for function_name in matches:
                description = ComponentManager._extract_function_description(content, function_name)
                function_config = {
                    "name": function_name,
                    "description": description or f"{component_type.rstrip('s')}: {function_name}",
                    "file": str(init_file.relative_to(init_file.parent.parent)),
                }
                functions.append(function_config)
                logger.debug("Found %s function in __init__.py: %s", component_type, function_name)

        except Exception as e:
            logger.debug("Failed to scan __init__.py functions: %s", e)

        return functions

    @staticmethod
    def _extract_function_description(content: str, function_name: str) -> str | None:
        """Extract description from function definition

        Args:
            content: File content
            function_name: Function name

        Returns:
            Function description or None
        """
        try:
            # Find function definition
            pattern = rf"def {re.escape(function_name)}\([^)]*\):[^\"]*\"\"\"([^\"]+)\"\"\""
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()

            return None

        except Exception as e:
            logger.debug("Failed to extract description for function %s: %s", function_name, e)
        return None

    @staticmethod
    def update_all_exports(content: str, function_name: str) -> str:
        """Update __all__ exports list in module content

        Args:
            content: Current module content
            function_name: Function name to add to __all__

        Returns:
            Updated module content with __all__ list
        """
        # Check if __all__ already exists
        all_pattern = r"__all__\s*=\s*\[(.*?)\]"
        all_match = re.search(all_pattern, content, re.DOTALL)

        if all_match:
            # Extract existing exports
            existing_exports = all_match.group(1)

            # Parse existing function names
            name_pattern = r'["\']([^"\']+)["\']'
            existing_names = re.findall(name_pattern, existing_exports)

            # Add new function if not already present
            if function_name not in existing_names:
                existing_names.append(function_name)

                # Rebuild __all__ list
                quoted_names = [f'"{name}"' for name in sorted(existing_names)]
                new_all_content = f"__all__ = [{', '.join(quoted_names)}]"

                # Replace existing __all__
                content = re.sub(all_pattern, new_all_content, content, flags=re.DOTALL)
        else:
            # Add __all__ for first function
            new_all_line = f'__all__ = ["{function_name}"]\n'

            # Find best insertion point (after module comment, before any function)
            lines = content.split("\n")
            insert_index = 0

            # Skip initial comments and blank lines
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    insert_index = i
                    break

            # Insert __all__ at the found position
            lines.insert(insert_index, new_all_line)
            content = "\n".join(lines)

        return content
