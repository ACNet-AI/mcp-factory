"""Multi-Source Adapter System - Multi-source adapter system

Supports converting various types of existing systems to MCP tools:
- Python classes/methods
- HTTP API interfaces
- CLI command line tools
- RPC services
- GraphQL interfaces

Generates pure function tool files that conform to MCP server project architecture.
"""

from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class SourceInfo:
    """Input source information"""

    source_type: str  # "python_class", "http_api", "cli", "rpc", "graphql"
    source_path: str  # Source path or URL
    config: dict[str, Any]  # Configuration information


class BaseAdapter(ABC):
    """Adapter base class"""

    def __init__(self, source_info: SourceInfo):
        self.source_info = source_info

    @abstractmethod
    def discover_capabilities(self) -> list[dict[str, Any]]:
        """Discover system capabilities"""
        pass

    @abstractmethod
    def generate_mcp_tool(self, capability: dict[str, Any]) -> str:
        """Generate MCP tool code"""
        pass

    @abstractmethod
    def test_connectivity(self) -> bool:
        """Test connectivity"""
        pass

    def _generate_standard_tool_template(
        self, tool_name: str, parameters: list[dict[str, Any]], description: str, implementation_code: str
    ) -> str:
        """Generate standard MCP tool template"""

        # Generate import statements
        imports = ["from typing import Any, Dict"]

        # Generate parameter signature
        param_defs = []
        for param in parameters:
            param_type = self._convert_type(param.get("type", "string"))
            required = param.get("required", True)

            if required:
                param_defs.append(f"    {param['name']}: {param_type}")
            else:
                param_defs.append(f"    {param['name']}: {param_type} = None")

        param_signature = ",\n".join(param_defs) if param_defs else ""

        # Generate parameter documentation
        param_docs = []
        for param in parameters:
            req_text = "Required" if param.get("required", True) else "Optional"
            param_docs.append(f"        {param['name']}: {req_text} - {param.get('description', 'No description')}")
        param_docs_str = "\n".join(param_docs) if param_docs else "        No parameters"

        # Generate complete tool code
        tool_code = f'''{chr(10).join(imports)}

def {tool_name}(
{param_signature}
) -> Dict[str, Any]:
    """
    {description}

    Args:
{param_docs_str}

    Returns:
        Dict[str, Any]: Standardized response with status, method, and result/error
    """
    try:
{self._indent_code(implementation_code, 8)}

        return {{
            "status": "success",
            "method": "{tool_name}",
            "result": result
        }}

    except Exception as e:
        return {{
            "status": "error",
            "method": "{tool_name}",
            "error": str(e)
        }}
'''

        return tool_code

    def _convert_type(self, param_type: str) -> str:
        """Convert parameter type to Python type annotation"""
        type_mapping = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }
        return type_mapping.get(param_type.lower(), "str")

    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code"""
        lines = code.strip().split("\n")
        indent = " " * spaces
        return "\n".join(f"{indent}{line}" if line.strip() else line for line in lines)


class PythonClassAdapter(BaseAdapter):
    """Python class adapter - based on existing universal_adapter"""

    def discover_capabilities(self) -> list[dict[str, Any]]:
        """Discover Python class methods"""
        # Import universal_adapter logic
        from .universal_adapter import SingletonStrategy, UniversalMCPAdapter

        # Dynamically import target class
        module_path, class_name = self.source_info.source_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        target_class = getattr(module, class_name)

        strategy = SingletonStrategy(f"{class_name}()")
        adapter = UniversalMCPAdapter(target_class, strategy)
        methods = adapter.discover_methods()

        capabilities = []
        for method_name in methods:
            method_info = adapter.analyze_method_signature(method_name)
            capabilities.append(
                {
                    "name": method_name,
                    "type": "python_method",
                    "signature": method_info,
                    "description": f"Python method: {method_name}",
                }
            )

        return capabilities

    def generate_mcp_tool(self, capability: dict[str, Any]) -> str:
        """Generate MCP tool for Python method"""
        method_name = capability["name"]
        signature = capability["signature"]

        # Convert parameter format
        parameters = []
        for param_name, param_info in signature.get("parameters", {}).items():
            parameters.append(
                {
                    "name": param_name,
                    "type": param_info.get("annotation", "str"),
                    "required": param_info.get("default") == "NO_DEFAULT",
                    "description": f"Parameter {param_name}",
                }
            )

        # Generate implementation code
        module_path, class_name = self.source_info.source_path.rsplit(".", 1)
        instance_creation = self.source_info.config.get("instance_creation", f"{class_name}()")

        # Build parameter call
        param_names = [p["name"] for p in parameters]
        param_call = ", ".join(f"{name}={name}" for name in param_names)

        implementation_code = f"""# Import target class
from {module_path} import {class_name}

# Create instance
instance = {instance_creation}

# Call method
result = instance.{method_name}({param_call})"""

        return self._generate_standard_tool_template(
            tool_name=method_name,
            parameters=parameters,
            description=capability["description"],
            implementation_code=implementation_code,
        )

    def test_connectivity(self) -> bool:
        """Test if Python class can be imported"""
        try:
            module_path, class_name = self.source_info.source_path.rsplit(".", 1)
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            return True
        except (ImportError, AttributeError):
            return False


class HttpApiAdapter(BaseAdapter):
    """HTTP API adapter"""

    def discover_capabilities(self) -> list[dict[str, Any]]:
        """Discover API endpoints via OpenAPI/Swagger"""
        base_url = self.source_info.source_path
        capabilities = []

        # Try to get OpenAPI documentation
        openapi_urls = [
            f"{base_url}/openapi.json",
            f"{base_url}/docs/openapi.json",
            f"{base_url}/swagger.json",
            f"{base_url}/api/docs",
        ]

        for url in openapi_urls:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    openapi_spec = response.json()
                    capabilities = self._parse_openapi_spec(openapi_spec)
                    break
            except Exception:
                continue

        # If no OpenAPI documentation, use configured endpoints
        if not capabilities and "endpoints" in self.source_info.config:
            for endpoint in self.source_info.config["endpoints"]:
                capabilities.append(
                    {
                        "name": endpoint["name"],
                        "type": "http_endpoint",
                        "method": endpoint.get("method", "GET"),
                        "path": endpoint["path"],
                        "parameters": endpoint.get("parameters", []),
                        "description": endpoint.get(
                            "description", f"HTTP {endpoint.get('method', 'GET')} {endpoint['path']}"
                        ),
                    }
                )

        return capabilities

    def _parse_openapi_spec(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse OpenAPI specification"""
        capabilities = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    capabilities.append(
                        {
                            "name": details.get("operationId", f"{method}_{path.replace('/', '_')}"),
                            "type": "http_endpoint",
                            "method": method.upper(),
                            "path": path,
                            "parameters": self._extract_parameters(details),
                            "description": details.get("summary", f"HTTP {method.upper()} {path}"),
                        }
                    )

        return capabilities

    def _extract_parameters(self, details: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract API parameters"""
        parameters = []

        # Path parameters
        for param in details.get("parameters", []):
            parameters.append(
                {
                    "name": param["name"],
                    "type": param.get("schema", {}).get("type", "string"),
                    "required": param.get("required", False),
                    "location": param.get("in", "query"),
                    "description": param.get("description", f"Parameter {param['name']}"),
                }
            )

        # Request body parameters
        request_body = details.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            if "application/json" in content:
                schema = content["application/json"].get("schema", {})
                if "properties" in schema:
                    for prop_name, prop_info in schema["properties"].items():
                        parameters.append(
                            {
                                "name": prop_name,
                                "type": prop_info.get("type", "string"),
                                "required": prop_name in schema.get("required", []),
                                "location": "body",
                                "description": prop_info.get("description", f"Body parameter {prop_name}"),
                            }
                        )

        return parameters

    def generate_mcp_tool(self, capability: dict[str, Any]) -> str:
        """Generate MCP tool for HTTP API"""
        tool_name = capability["name"]
        method = capability["method"]
        path = capability["path"]
        parameters = capability["parameters"]
        base_url = self.source_info.source_path

        # Generate HTTP request implementation code
        implementation_code = self._generate_http_request_code(method, path, parameters, base_url)

        return self._generate_standard_tool_template(
            tool_name=tool_name,
            parameters=parameters,
            description=capability["description"],
            implementation_code=implementation_code,
        )

    def _generate_http_request_code(
        self, method: str, path: str, parameters: list[dict[str, Any]], base_url: str
    ) -> str:
        """Generate HTTP request code"""
        lines = []
        lines.append("import requests")
        lines.append("")
        lines.append(f'url = "{base_url}{path}"')

        # HandlePath parameters
        path_params = [p for p in parameters if p.get("location") == "path"]
        if path_params:
            for param in path_params:
                lines.append(f'url = url.replace("{{{param["name"]}}}", str({param["name"]}))')

        # Handle query parameters
        query_params = [p for p in parameters if p.get("location") == "query"]
        if query_params:
            lines.append("params = {}")
            for param in query_params:
                if param.get("required", False):
                    lines.append(f'params["{param["name"]}"] = {param["name"]}')
                else:
                    lines.append(f"if {param['name']} is not None:")
                    lines.append(f'    params["{param["name"]}"] = {param["name"]}')

        # Handle request body
        body_params = [p for p in parameters if p.get("location") == "body"]
        if body_params:
            lines.append("data = {}")
            for param in body_params:
                if param.get("required", False):
                    lines.append(f'data["{param["name"]}"] = {param["name"]}')
                else:
                    lines.append(f"if {param['name']} is not None:")
                    lines.append(f'    data["{param["name"]}"] = {param["name"]}')

        # Generate request
        request_line = f"response = requests.{method.lower()}(url"
        if query_params:
            request_line += ", params=params"
        if body_params:
            request_line += ", json=data"
        request_line += ")"
        lines.append(request_line)

        lines.append("")
        lines.append("if response.status_code >= 400:")
        lines.append('    raise Exception(f"HTTP {response.status_code}: {response.text}")')
        lines.append("")
        lines.append('if response.headers.get("content-type", "").startswith("application/json"):')
        lines.append("    result = response.json()")
        lines.append("else:")
        lines.append("    result = response.text")

        return "\n".join(lines)

    def test_connectivity(self) -> bool:
        """Test HTTP API connectivity"""
        try:
            response = requests.get(self.source_info.source_path, timeout=5)
            return response.status_code < 500
        except Exception:
            return False


class CliAdapter(BaseAdapter):
    """CLI command line adapter"""

    def discover_capabilities(self) -> list[dict[str, Any]]:
        """Discover CLI commands"""
        capabilities = []

        # Read command definitions from configuration
        commands = self.source_info.config.get("commands", [])

        for cmd in commands:
            capabilities.append(
                {
                    "name": cmd["name"],
                    "type": "cli_command",
                    "command": cmd["command"],
                    "arguments": cmd.get("arguments", []),
                    "description": cmd.get("description", f"CLI command: {cmd['command']}"),
                }
            )

        return capabilities

    def generate_mcp_tool(self, capability: dict[str, Any]) -> str:
        """Generate MCP tool for CLI command"""
        tool_name = capability["name"]
        base_command = capability["command"]
        arguments = capability["arguments"]

        # Convert parameter format
        parameters = []
        for arg in arguments:
            parameters.append(
                {
                    "name": arg["name"],
                    "type": arg.get("type", "string"),
                    "required": arg.get("required", True),
                    "description": arg.get("description", f"Argument {arg['name']}"),
                }
            )

        # Generate CLI execution code
        implementation_code = self._generate_cli_execution_code(base_command, arguments)

        return self._generate_standard_tool_template(
            tool_name=tool_name,
            parameters=parameters,
            description=capability["description"],
            implementation_code=implementation_code,
        )

    def _generate_cli_execution_code(self, base_command: str, arguments: list[dict[str, Any]]) -> str:
        """Generate CLI execution code"""
        lines = []
        lines.append("import subprocess")
        lines.append("")
        lines.append(f'cmd = ["{base_command}"]')
        lines.append("")

        # Build command parameters
        for arg in arguments:
            if arg.get("required", True):
                if arg.get("flag"):
                    lines.append(f'cmd.extend(["{arg["flag"]}", str({arg["name"]})])')
                else:
                    lines.append(f"cmd.append(str({arg['name']}))")
            else:
                lines.append(f"if {arg['name']} is not None:")
                if arg.get("flag"):
                    lines.append(f'    cmd.extend(["{arg["flag"]}", str({arg["name"]})])')
                else:
                    lines.append(f"    cmd.append(str({arg['name']}))")

        lines.append("")
        lines.append("process_result = subprocess.run(")
        lines.append("    cmd,")
        lines.append("    capture_output=True,")
        lines.append("    text=True,")
        lines.append("    timeout=30")
        lines.append(")")
        lines.append("")
        lines.append("if process_result.returncode != 0:")
        lines.append(
            '    raise Exception(f"Command failed with code {process_result.returncode}: {process_result.stderr}")'
        )
        lines.append("")
        lines.append("result = {")
        lines.append('    "stdout": process_result.stdout,')
        lines.append('    "stderr": process_result.stderr,')
        lines.append('    "returncode": process_result.returncode')
        lines.append("}")

        return "\n".join(lines)

    def test_connectivity(self) -> bool:
        """Test CLI command availability"""
        try:
            base_command = self.source_info.config.get("commands", [{}])[0].get("command", "")
            if not base_command:
                return False

            result = subprocess.run([base_command, "--help"], capture_output=True, timeout=5)
            return result.returncode in [0, 1]  # Many commands return 1 for --help
        except Exception:
            return False


class AdapterFactory:
    """Adapter factory class"""

    @staticmethod
    def create_adapter(source_info: SourceInfo) -> BaseAdapter:
        """Create adapter based on source information"""
        source_type = source_info.source_type.lower()

        if source_type == "python_class":
            return PythonClassAdapter(source_info)
        elif source_type == "http_api":
            # Check if enhanced HTTP adapter should be used
            use_enhanced = source_info.config.get("use_enhanced", True)
            if use_enhanced:
                try:
                    from .enhanced_http_adapter import EnhancedHttpApiAdapter

                    return EnhancedHttpApiAdapter(source_info)
                except ImportError:
                    # Fall back to standard implementation
                    return HttpApiAdapter(source_info)
            else:
                return HttpApiAdapter(source_info)
        elif source_type == "cli":
            return CliAdapter(source_info)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    @classmethod
    def auto_detect_source_type(cls, source_path: str) -> str:
        """Auto-detect source type"""
        if source_path.startswith(("http://", "https://")):
            return "http_api"
        elif "." in source_path and not source_path.startswith("/"):
            # Looks like Python module path
            return "python_class"
        else:
            return "cli"


class MultiSourceAdapter:
    """Multi-source adapter main class"""

    def __init__(self):
        self.adapters: list[BaseAdapter] = []

    def add_source(self, source_type: str, source_path: str, config: dict[str, Any] = None) -> None:
        """Add input source"""
        source_info = SourceInfo(source_type=source_type, source_path=source_path, config=config or {})

        adapter = AdapterFactory.create_adapter(source_info)
        self.adapters.append(adapter)

    def discover_all_capabilities(self) -> dict[str, list[dict[str, Any]]]:
        """Discover all system capabilities"""
        all_capabilities = {}

        for adapter in self.adapters:
            source_type = adapter.source_info.source_type
            capabilities = adapter.discover_capabilities()

            if source_type not in all_capabilities:
                all_capabilities[source_type] = []
            all_capabilities[source_type].extend(capabilities)

        return all_capabilities

    def generate_tools_for_project(
        self, project_path: str, selected_capabilities: list[dict[str, Any]] = None
    ) -> list[str]:
        """For projectGenerate MCP tool"""
        generated_files = []
        project_path_obj = Path(project_path)

        if selected_capabilities is None:
            # If not specified, generate all capabilities
            all_caps = self.discover_all_capabilities()
            selected_capabilities = []
            for caps in all_caps.values():
                selected_capabilities.extend(caps)

        # Process grouped by adapter
        adapter_caps = {}
        for cap in selected_capabilities:
            for adapter in self.adapters:
                cap_type = cap["type"].replace("_endpoint", "").replace("_command", "").replace("_method", "")
                if adapter.source_info.source_type == cap_type:
                    if adapter not in adapter_caps:
                        adapter_caps[adapter] = []
                    adapter_caps[adapter].append(cap)

        # Generate tool files
        for adapter, capabilities in adapter_caps.items():
            for capability in capabilities:
                tool_code = adapter.generate_mcp_tool(capability)

                # Write tool file - filename same as function name
                tool_file_path = project_path_obj / "tools" / f"{capability['name']}.py"
                tool_file_path.parent.mkdir(exist_ok=True, parents=True)

                with open(tool_file_path, "w", encoding="utf-8") as f:
                    f.write(tool_code)

                generated_files.append(str(tool_file_path))

        # Update __init__.py in tools directory
        self._update_tools_init(project_path_obj / "tools")

        return generated_files

    def _update_tools_init(self, tools_dir: Path) -> None:
        """Update __init__.py in tools directoryfiles"""
        init_file = tools_dir / "__init__.py"

        # Get all .py files (except __init__.py)
        tool_files = [f.stem for f in tools_dir.glob("*.py") if f.name != "__init__.py"]

        init_content = '''"""
Auto-generated tools module
All tool functions are automatically discovered and registered by ComponentManager
"""

# Tool functions are automatically discovered from individual .py files
# No manual imports needed - ComponentManager handles registration

__all__ = [
'''

        for tool_name in sorted(tool_files):
            init_content += f'    "{tool_name}",\n'

        init_content += "]\n"

        with open(init_file, "w", encoding="utf-8") as f:
            f.write(init_content)

    def test_all_connections(self) -> dict[str, bool]:
        """Test all connections"""
        results = {}
        for adapter in self.adapters:
            source_id = f"{adapter.source_info.source_type}:{adapter.source_info.source_path}"
            results[source_id] = adapter.test_connectivity()

        return results
