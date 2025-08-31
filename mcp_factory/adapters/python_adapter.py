"""Python Class Adapter - Convert Python classes to MCP tools.

This adapter specializes in converting existing Python class methods into MCP tools,
supporting different invocation strategies and automatic method discovery.
"""

import importlib
import inspect
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from .base import (
    AdapterType,
    BaseAdapter,
    CapabilityInfo,
    ConnectivityResult,
    DiscoveryError,
    GenerationError,
    SourceInfo,
    generate_tool_template,
)
from .cache import cached_method


class PythonStrategy(ABC):
    """Strategy for Python class method invocation"""

    @abstractmethod
    def generate_invocation_code(self, class_name: str, method_name: str, params: list[str]) -> str:
        """Generate code for method invocation"""
        pass

    @abstractmethod
    def get_required_imports(self, target_class: type) -> list[str]:
        """Get required import statements"""
        pass


class SingletonStrategy(PythonStrategy):
    """Singleton strategy: use module-level singleton instance"""

    def __init__(self, instance_creation_code: str):
        self.instance_creation_code = instance_creation_code

    def generate_invocation_code(self, class_name: str, method_name: str, params: list[str]) -> str:
        param_str = ", ".join(params) if params else ""
        return f'''
        # Singleton instance management
        if not hasattr({method_name}, '_instance'):
            {method_name}._instance = {self.instance_creation_code}

        # Execute method
        result = {method_name}._instance.{method_name}({param_str})

        return {{
            "success": True,
            "result": result,
            "method": "{method_name}",
            "strategy": "singleton"
        }}'''

    def get_required_imports(self, target_class: type) -> list[str]:
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class FreshInstanceStrategy(PythonStrategy):
    """Fresh instance strategy: create new instance for each call"""

    def __init__(self, instance_creation_code: str):
        self.instance_creation_code = instance_creation_code

    def generate_invocation_code(self, class_name: str, method_name: str, params: list[str]) -> str:
        param_str = ", ".join(params) if params else ""
        return f'''
        # Create fresh instance
        instance = {self.instance_creation_code}

        # Execute method
        result = instance.{method_name}({param_str})

        return {{
            "success": True,
            "result": result,
            "method": "{method_name}",
            "strategy": "fresh_instance"
        }}'''

    def get_required_imports(self, target_class: type) -> list[str]:
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class StaticMethodStrategy(PythonStrategy):
    """Static method strategy: call methods directly on class"""

    def generate_invocation_code(self, class_name: str, method_name: str, params: list[str]) -> str:
        param_str = ", ".join(params) if params else ""
        return f'''
        # Call static/class method
        result = {class_name}.{method_name}({param_str})

        return {{
            "success": True,
            "result": result,
            "method": "{method_name}",
            "strategy": "static_method"
        }}'''

    def get_required_imports(self, target_class: type) -> list[str]:
        module_name = target_class.__module__
        class_name = target_class.__name__
        return [f"from {module_name} import {class_name}"]


class PythonClassAdapter(BaseAdapter):
    """Adapter for Python classes"""

    def __init__(self, source_info: SourceInfo):
        super().__init__(source_info)

        # Parse strategy from config
        strategy_type = self.config.get("strategy", "singleton")
        instance_code = self.config.get("instance_creation")

        self.target_class = self._load_target_class()
        self.strategy = self._create_strategy(strategy_type, instance_code)

        # Method filtering options
        self.include_private = self.config.get("include_private", False)
        self.method_filter = self._create_method_filter()

    def _load_target_class(self) -> type:
        """Load target class from source path"""
        try:
            module_path, class_name = self.source_info.source_path.rsplit(".", 1)
            module = importlib.import_module(module_path)
            target_class = getattr(module, class_name)
            if not isinstance(target_class, type):
                raise DiscoveryError(f"{self.source_info.source_path} is not a class")
            return target_class
        except (ValueError, ImportError, AttributeError) as e:
            raise DiscoveryError(f"Failed to load class {self.source_info.source_path}: {e}") from e

    def _create_strategy(self, strategy_type: str, instance_code: str | None) -> PythonStrategy:
        """Create invocation strategy"""
        class_name = self.target_class.__name__

        if strategy_type == "singleton":
            code = instance_code or f"{class_name}()"
            return SingletonStrategy(code)
        elif strategy_type == "fresh":
            code = instance_code or f"{class_name}()"
            return FreshInstanceStrategy(code)
        elif strategy_type == "static":
            return StaticMethodStrategy()
        else:
            raise ValueError(f"Unsupported strategy: {strategy_type}")

    def _create_method_filter(self) -> Callable[[str, Callable], bool] | None:
        """Create method filter from config"""
        include_patterns = self.config.get("include_methods", [])
        exclude_patterns = self.config.get("exclude_methods", [])

        if not include_patterns and not exclude_patterns:
            return None

        def filter_func(name: str, method: Callable) -> bool:
            # Check include patterns
            if include_patterns:
                if not any(self._match_pattern(name, pattern) for pattern in include_patterns):
                    return False

            # Check exclude patterns
            if exclude_patterns:
                if any(self._match_pattern(name, pattern) for pattern in exclude_patterns):
                    return False

            return True

        return filter_func

    def _match_pattern(self, name: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        if "*" not in pattern:
            return name == pattern

        # Simple wildcard matching
        if pattern.endswith("*"):
            return name.startswith(pattern[:-1])
        elif pattern.startswith("*"):
            return name.endswith(pattern[1:])
        else:
            # More complex patterns could be added here
            return name == pattern

    @cached_method("python_discover", ttl=1800)  # Cache for 30 minutes
    def discover_capabilities(self) -> list[CapabilityInfo]:
        """Discover Python class methods"""
        try:
            methods = self._discover_methods()
            capabilities = []

            for method_name in methods:
                method_info = self._analyze_method_signature(method_name)

                capability = CapabilityInfo(
                    name=method_name,
                    description=f"Python method: {self.target_class.__name__}.{method_name}",
                    parameters=method_info["parameters"],
                    capability_type="python_method",
                    metadata={
                        "class_name": self.target_class.__name__,
                        "module": self.target_class.__module__,
                        "signature": method_info["signature"],
                        "strategy": self.config.get("strategy", "singleton"),
                    },
                )
                capabilities.append(capability)

            return capabilities

        except Exception as e:
            raise DiscoveryError(f"Failed to discover capabilities: {e}") from e

    def _discover_methods(self) -> list[str]:
        """Discover all methods of the class"""
        methods = []

        # Get instance methods and functions
        for name, method in inspect.getmembers(self.target_class, predicate=inspect.isfunction):
            if not self.include_private and name.startswith("_"):
                continue

            if self.method_filter and not self.method_filter(name, method):
                continue

            methods.append(name)

        # Get other callable attributes
        for name in dir(self.target_class):
            if name.startswith("_") and not self.include_private:
                continue

            if name in methods:
                continue

            attr = getattr(self.target_class, name)
            if callable(attr):
                if self.method_filter and not self.method_filter(name, attr):
                    continue
                methods.append(name)

        return sorted(methods)

    def _analyze_method_signature(self, method_name: str) -> dict[str, Any]:
        """Analyze method signature and extract parameter information"""
        try:
            method = getattr(self.target_class, method_name)
            sig = inspect.signature(method)

            parameters = []
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue

                param_info = {
                    "name": param_name,
                    "type": self._get_param_type(param),
                    "required": param.default == inspect.Parameter.empty,
                    "description": f"Parameter {param_name}",
                }

                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters.append(param_info)

            return {"signature": str(sig), "parameters": parameters, "return_type": self._get_return_type(method)}

        except Exception:
            # Return basic info if signature analysis fails
            return {"signature": f"{method_name}(...)", "parameters": [], "return_type": "Any"}

    def _get_param_type(self, param: inspect.Parameter) -> str:
        """Get parameter type as string"""
        if param.annotation != inspect.Parameter.empty:
            if hasattr(param.annotation, "__name__"):
                return str(param.annotation.__name__)
            else:
                return str(param.annotation)
        return "Any"

    def _get_return_type(self, method: Callable) -> str:
        """Get return type as string"""
        try:
            sig = inspect.signature(method)
            if sig.return_annotation != inspect.Signature.empty:
                if hasattr(sig.return_annotation, "__name__"):
                    return str(sig.return_annotation.__name__)
                else:
                    return str(sig.return_annotation)
        except Exception:
            pass
        return "Any"

    @cached_method("python_generate", ttl=7200)  # Cache for 2 hours
    def generate_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate MCP tool code for Python method"""
        try:
            method_name = capability.name
            class_name = self.target_class.__name__

            # Generate parameter names for invocation
            param_names = [p["name"] for p in capability.parameters]

            # Generate invocation code using strategy
            impl_code = self.strategy.generate_invocation_code(class_name, method_name, param_names)

            # Generate imports
            imports = self.strategy.get_required_imports(self.target_class)
            import_section = "\n".join(imports)

            # Generate complete tool code
            tool_code = generate_tool_template(
                tool_name=method_name,
                parameters=capability.parameters,
                description=capability.description,
                implementation_code=impl_code,
            )

            # Add imports at the top
            final_code = f"{import_section}\n\n{tool_code}"

            return final_code

        except Exception as e:
            raise GenerationError(f"Failed to generate tool code for {capability.name}: {e}") from e

    def test_connectivity(self) -> ConnectivityResult:
        """Test connectivity to Python class"""
        try:
            # Try to instantiate the class if using instance strategies
            strategy_type = self.config.get("strategy", "singleton")

            if strategy_type in ["singleton", "fresh"]:
                instance_code = self.config.get("instance_creation", f"{self.target_class.__name__}()")
                # Try to evaluate the instance creation code
                eval(instance_code, {self.target_class.__name__: self.target_class})

            return ConnectivityResult(
                success=True,
                message=f"Successfully connected to {self.target_class.__name__}",
                details={
                    "class": self.target_class.__name__,
                    "module": self.target_class.__module__,
                    "strategy": strategy_type,
                },
            )

        except Exception as e:
            return ConnectivityResult(
                success=False,
                message=f"Failed to connect to {self.target_class.__name__}: {e}",
                details={"error": str(e)},
            )


# Convenience functions


def create_python_adapter(
    class_path: str,
    strategy: str = "singleton",
    instance_creation: str | None = None,
    include_methods: list[str] | None = None,
    exclude_methods: list[str] | None = None,
) -> PythonClassAdapter:
    """Create Python class adapter with simplified configuration"""

    config = {"strategy": strategy, "include_private": False}

    if instance_creation:
        config["instance_creation"] = instance_creation

    if include_methods:
        config["include_methods"] = include_methods

    if exclude_methods:
        config["exclude_methods"] = exclude_methods

    source_info = SourceInfo(adapter_type=AdapterType.PYTHON_CLASS, source_path=class_path, config=config)

    return PythonClassAdapter(source_info)
