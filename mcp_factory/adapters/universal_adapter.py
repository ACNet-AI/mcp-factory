"""Universal MCP Adapter - Universal existing system to MCP tool converter.

Specialized for converting existing Python class methods to MCP tools. Unlike FastAPI-MCP,
we adapt Python methods rather than HTTP API endpoints, providing multiple adaptation
strategies and automated code generation capabilities.

Core Features:
    - Automatically discover and analyze all methods of Python classes
    - Support singleton, fresh instance, and static method invocation strategies
    - Preserve original method parameter signatures and type annotations
    - Generate standard MCP tool function wrappers
    - Automatically manage Python imports and module structure
    - Unified success/error return format
"""

import inspect
import textwrap
from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path
from typing import Any


class AdapterStrategy(ABC):
    """Adapter strategy abstract base class"""

    @abstractmethod
    def generate_adapter_code(self, target_class: type, method_name: str, method_info: dict[str, Any]) -> str:
        """Generate adapter code"""
        pass

    @abstractmethod
    def get_required_imports(self, target_class: type) -> list[str]:
        """Get required import statements"""
        pass


class SingletonStrategy(AdapterStrategy):
    """Singleton strategy: use module-level singleton instance"""

    def __init__(self, instance_creation_code: str):
        """Initialize singleton strategy.

        Args:
            instance_creation_code: Instance creation code, e.g. "MyClass()" or "MyClass('./config')"
        """
        self.instance_creation_code = instance_creation_code

    def generate_adapter_code(self, target_class: type, method_name: str, method_info: dict[str, Any]) -> str:
        """Generate singleton adapter code"""

        # Generate call parameters
        call_params = []
        for param_name in method_info["parameters"].keys():
            call_params.append(f"{param_name}={param_name}")

        adapter_code = textwrap.dedent(f'''
            # Module-level singleton instance
            _instance = None

            def _get_instance():
                """Get singleton instance."""
                global _instance
                if _instance is None:
                    _instance = {self.instance_creation_code}
                return _instance

            def {method_name}({method_info["func_signature_params"]}) -> dict[str, Any]:
                """{method_info["docstring"]}"""
                try:
                    # Get singleton instance
                    instance = _get_instance()

                    # Call target method
                    result = instance.{method_name}({", ".join(call_params)})

                    return {{
                        "status": "success",
                        "method": "{method_name}",
                        "result": result
                    }}
                except Exception as e:
                    return {{
                        "status": "error",
                        "method": "{method_name}",
                        "error": str(e)
                    }}
            ''')
        return adapter_code.strip()

    def get_required_imports(self, target_class: type) -> list[str]:
        """Get required imports"""
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class FreshInstanceStrategy(AdapterStrategy):
    """Create new instance strategy for each call"""

    def __init__(self, instance_creation_code: str):
        self.instance_creation_code = instance_creation_code

    def generate_adapter_code(self, target_class: type, method_name: str, method_info: dict[str, Any]) -> str:
        """Generate new instance adapter code"""
        # Generate call parameters
        call_params = []
        for param_name in method_info["parameters"].keys():
            call_params.append(f"{param_name}={param_name}")

        adapter_code = textwrap.dedent(f'''
            def {method_name}({method_info["func_signature_params"]}) -> dict[str, Any]:
                """{method_info["docstring"]}"""
                try:
                    # Create new instance
                    instance = {self.instance_creation_code}

                    # Call target method
                    result = instance.{method_name}({", ".join(call_params)})

                    return {{
                        "status": "success",
                        "method": "{method_name}",
                        "result": result
                    }}
                except Exception as e:
                    return {{
                        "status": "error",
                        "method": "{method_name}",
                        "error": str(e)
                    }}
            ''')
        return adapter_code.strip()

    def get_required_imports(self, target_class: type) -> list[str]:
        """Get required imports"""
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class StaticMethodStrategy(AdapterStrategy):
    """Static method strategy：Directly call class static methods"""

    def generate_adapter_code(self, target_class: type, method_name: str, method_info: dict[str, Any]) -> str:
        """Generate static method adapter code"""
        class_name = target_class.__name__

        # Generate call parameters
        call_params = []
        for param_name in method_info["parameters"].keys():
            call_params.append(f"{param_name}={param_name}")

        adapter_code = textwrap.dedent(f'''
            def {method_name}({method_info["func_signature_params"]}) -> dict[str, Any]:
                """{method_info["docstring"]}"""
                try:
                    # Directly call static method
                    result = {class_name}.{method_name}({", ".join(call_params)})

                    return {{
                        "status": "success",
                        "method": "{method_name}",
                        "result": result
                    }}
                except Exception as e:
                    return {{
                        "status": "error",
                        "method": "{method_name}",
                        "error": str(e)
                    }}
            ''')
        return adapter_code.strip()

    def get_required_imports(self, target_class: type) -> list[str]:
        """Get required imports"""
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class UniversalMCPAdapter:
    """UniversalMCPadapter"""

    def __init__(self, target_class: type, strategy: AdapterStrategy):
        """InitializeUniversal adapter.

        Args:
            target_class: Target class (existing system class to convert)
            strategy: Adaptation strategy
        """
        self.target_class = target_class
        self.strategy = strategy

    def discover_methods(
        self, include_private: bool = False, method_filter: Callable[[str, Callable], bool] | None = None
    ) -> list[str]:
        """Automatically discover all methods of the class.

        Args:
            include_private: Whether to include private methods
            method_filter: Method filter function, receives (method_name, method_obj), returns bool

        Returns:
            List of convertible method names
        """
        methods = []
        for name, method in inspect.getmembers(self.target_class, predicate=inspect.ismethod):
            # Skip private methods
            if not include_private and name.startswith("_"):
                continue

            # Apply custom filter
            if method_filter and not method_filter(name, method):
                continue

            methods.append(name)

        # Also check class methods and static methods
        for name in dir(self.target_class):
            if name.startswith("_") and not include_private:
                continue

            attr = getattr(self.target_class, name)
            if callable(attr) and name not in methods:
                if method_filter and not method_filter(name, attr):
                    continue
                methods.append(name)

        return sorted(methods)

    def analyze_method_signature(self, method_name: str) -> dict[str, Any]:
        """
        Analyze method signature, extract parameter information

        Args:
            method_name: Method name

        Returns:
            Dict[str, Any]: Dictionary containing parameter information
        """
        method = getattr(self.target_class, method_name)
        sig = inspect.signature(method)

        parameters = {}
        for param_name, param in sig.parameters.items():
            # Skip self parameter
            if param_name == "self":
                continue

            # Handle type annotations, ensure correct string representation
            if param.annotation != inspect.Parameter.empty:
                if hasattr(param.annotation, "__name__"):
                    # Basic types like str, int, bool
                    type_str = param.annotation.__name__
                else:
                    # Complex types like List[str], Optional[int] etc.
                    type_str = str(param.annotation)
            else:
                type_str = "Any"

            param_info = {
                "name": param_name,
                "type": type_str,
                "default": param.default if param.default != inspect.Parameter.empty else None,
                "required": param.default == inspect.Parameter.empty,
            }
            parameters[param_name] = param_info

        return {
            "method_name": method_name,
            "parameters": parameters,
            "return_type": sig.return_annotation if sig.return_annotation != inspect.Parameter.empty else "Any",
            "docstring": method.__doc__ or f"Method: {method_name}",
        }

    def _generate_function_signature_params(self, parameters: dict[str, Any]) -> str:
        """Generate function signature parameter part"""
        # Ensure correct parameter order (required parameters first, optional parameters last)
        required_params = []
        optional_params = []

        for param_name, param_info in parameters.items():
            param_type = param_info["type"]
            if param_info["default"] is not None:
                if isinstance(param_info["default"], str):
                    optional_params.append(f"{param_name}: {param_type} = '{param_info['default']}'")
                else:
                    optional_params.append(f"{param_name}: {param_type} = {param_info['default']}")
            else:
                required_params.append(f"{param_name}: {param_type}")

        # Merge parameters: required parameters first, optional parameters last
        all_params = required_params + optional_params
        return ", ".join(all_params)

    def generate_mcp_tool_function(self, method_info: dict[str, Any]) -> str:
        """Generate MCP tool function code.

        Args:
            method_info: Method information dictionary

        Returns:
            Generated MCP tool function code
        """
        method_name = method_info["method_name"]
        parameters = method_info["parameters"]
        docstring = method_info["docstring"]

        # Generate function signature parameters
        func_signature_params = self._generate_function_signature_params(parameters)

        # Enhanced method information
        enhanced_method_info = {**method_info, "func_signature_params": func_signature_params}

        # Use strategy to generate adapter code
        adapter_code = self.strategy.generate_adapter_code(self.target_class, method_name, enhanced_method_info)

        # Detect required type imports
        typing_imports = self._detect_type_imports(func_signature_params, docstring)
        pathlib_needed = self._needs_pathlib_import(func_signature_params, docstring)

        # Generate import section
        imports = ["from typing import Dict, Any"]
        if typing_imports:
            additional_types = [t for t in typing_imports if t not in ["Dict", "Any"]]
            if additional_types:
                imports[0] = f"from typing import {', '.join(sorted(['Dict', 'Any'] + additional_types))}"

        if pathlib_needed:
            imports.append("from pathlib import Path")

        # Add imports required by strategy
        strategy_imports = self.strategy.get_required_imports(self.target_class)
        imports.extend(strategy_imports)

        imports_section = "\n".join(imports)

        full_code = f"{imports_section}\n\n{adapter_code}"
        return full_code

    def _detect_type_imports(self, function_code: str, docstring: str = "") -> list[str]:
        """Detect typing module imports needed in code"""
        import re

        typing_types = [
            "Dict",
            "List",
            "Tuple",
            "Set",
            "FrozenSet",
            "Optional",
            "Union",
            "Any",
            "Callable",
            "Iterable",
            "Iterator",
            "Generator",
            "Type",
            "TypeVar",
            "Generic",
            "Protocol",
            "Literal",
            "Final",
            "ClassVar",
        ]

        found_types = []
        all_text = function_code + " " + docstring

        for type_name in typing_types:
            pattern = rf"\b{re.escape(type_name)}\b(?=[\[\s\|\],:])"
            if re.search(pattern, all_text):
                found_types.append(type_name)

        return found_types

    def _needs_pathlib_import(self, function_code: str, docstring: str = "") -> bool:
        """Detect if pathlib import is needed"""
        import re

        all_text = function_code + " " + docstring
        pattern = r"\bPath\b(?=[\[\s\|\],:])"
        return bool(re.search(pattern, all_text))

    def auto_generate_tools(
        self,
        project_path: str,
        methods: list[str] | None = None,
        method_filter: Callable[[str, Callable], bool] | None = None,
    ) -> list[str]:
        """
        Automatically generate MCP tool files

        Args:
            project_path: Target project path
            methods: List of methods to convert, None means all methods
            method_filter: Method filter function

        Returns:
            List[str]: List of generated tool files
        """
        if methods is None:
            methods = self.discover_methods(method_filter=method_filter)

        generated_files = []

        for method_name in methods:
            try:
                # Analyze method signature
                method_info = self.analyze_method_signature(method_name)

                # Generate MCP tool function code
                tool_code = self.generate_mcp_tool_function(method_info)

                # Write tool file
                tool_file_path = Path(project_path) / "tools" / f"{method_name}.py"
                tool_file_path.parent.mkdir(exist_ok=True)

                with open(tool_file_path, "w", encoding="utf-8") as f:
                    f.write(tool_code + "\n")

                generated_files.append(str(tool_file_path))

                # Update tools module __init__.py
                self._update_tools_init(project_path, method_name)

            except Exception as e:
                print(f"⚠️  Skip method {method_name}: {e}")
                continue

        return generated_files

    def _update_tools_init(self, project_path: str, tool_name: str):
        """Update tools module __init__.pyfiles"""
        init_file = Path(project_path) / "tools" / "__init__.py"

        # Read existing content
        if init_file.exists():
            with open(init_file, encoding="utf-8") as f:
                content = f.read()
        else:
            content = "__all__ = []\n# Auto-generated imports\n"

        # Check if tool is already included
        if tool_name not in content:
            # Update __all__ list
            if f"'{tool_name}'" not in content:
                all_line_start = content.find("__all__ = [")
                if all_line_start != -1:
                    all_line_end = content.find("]", all_line_start) + 1
                    current_all = content[all_line_start:all_line_end]

                    # Extract existing tool list
                    import re

                    tools = re.findall(r"'([^']+)'", current_all)
                    tools.append(tool_name)
                    tools.sort()

                    new_all = f"__all__ = {tools}"
                    content = content[:all_line_start] + new_all + content[all_line_end:]

            # Add import statement
            import_statement = f"from .{tool_name} import {tool_name}"
            if import_statement not in content:
                content += f"\n{import_statement}"

        # Write updated content
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(content)


def create_universal_adapter(
    target_class: type, strategy_type: str = "singleton", instance_creation_code: str | None = None
) -> UniversalMCPAdapter:
    """Convenience function: create Universal adapter.

    Args:
        target_class: Target class
        strategy_type: Strategy type ("singleton", "fresh", "static")
        instance_creation_code: Instance creation code (for singleton and fresh strategies)

    Returns:
        Configured adapter instance
    """
    if strategy_type == "singleton":
        if instance_creation_code is None:
            instance_creation_code = f"{target_class.__name__}()"
        strategy = SingletonStrategy(instance_creation_code)
    elif strategy_type == "fresh":
        if instance_creation_code is None:
            instance_creation_code = f"{target_class.__name__}()"
        strategy = FreshInstanceStrategy(instance_creation_code)
    elif strategy_type == "static":
        strategy = StaticMethodStrategy()
    else:
        raise ValueError(f"Unsupported strategy type: {strategy_type}")

    return UniversalMCPAdapter(target_class, strategy)


# Convenience function: automatically generate MCP tools for any class
def auto_generate_class_tools(
    target_class: type,
    project_path: str,
    strategy_type: str = "singleton",
    instance_creation_code: str | None = None,
    methods: list[str] | None = None,
    method_filter: Callable[[str, Callable], bool] | None = None,
) -> list[str]:
    """Convenience function: automatically generate MCP tools for any class.

    Args:
        target_class: Target class
        project_path: Target MCP project path
        strategy_type: Adaptation strategytype
        instance_creation_code: Instance creation code
        methods: List of methods to convert
        method_filter: Method filter function

    Returns:
        List of generated tool files
    """
    adapter = create_universal_adapter(target_class, strategy_type, instance_creation_code)
    return adapter.auto_generate_tools(project_path, methods, method_filter)
