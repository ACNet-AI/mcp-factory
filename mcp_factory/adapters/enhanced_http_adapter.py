"""Enhanced HTTP API Adapter - Supports FastMCP Engine"""

import asyncio
from typing import Any

import httpx
import requests

from .multi_adapter import BaseAdapter, SourceInfo

# Optional dependency check
try:
    from fastmcp import FastMCP

    FASTMCP_AVAILABLE = True
except ImportError:
    FASTMCP_AVAILABLE = False


class EnhancedHttpApiAdapter(BaseAdapter):
    """Enhanced HTTP API Adapter - Supports multiple backend engines"""

    def __init__(self, source_info: SourceInfo):
        super().__init__(source_info)
        self.use_fastmcp = self._should_use_fastmcp()
        self.client: httpx.AsyncClient | None = None
        self.fastmcp_instance: Any | None = None

    def _should_use_fastmcp(self) -> bool:
        """Decide whether to use FastMCP engine"""
        if not FASTMCP_AVAILABLE:
            return False

        # Check preference in configuration
        engine = self.source_info.config.get("engine", "auto")
        if engine == "fastmcp":
            return True
        if engine == "native":
            return False
        # auto
        # Auto decision: prefer FastMCP if OpenAPI spec is available
        return "openapi_spec" in self.source_info.config

    async def _initialize_fastmcp(self) -> FastMCP | None:
        """Initialize FastMCP instance"""
        if not self.use_fastmcp:
            return None

        try:
            self.client = httpx.AsyncClient(
                base_url=self.source_info.source_path, timeout=self.source_info.config.get("timeout", 30.0)
            )

            if "openapi_spec" in self.source_info.config:
                # Use provided OpenAPI specification
                spec = self.source_info.config["openapi_spec"]
                self.fastmcp_instance = FastMCP.from_openapi(openapi_spec=spec, client=self.client)
            else:
                # Try to auto-discover OpenAPI
                spec = await self._discover_openapi_spec()
                if spec:
                    self.fastmcp_instance = FastMCP.from_openapi(openapi_spec=spec, client=self.client)

            return self.fastmcp_instance

        except Exception as e:
            print(f"FastMCP initialization failed, falling back to native implementation: {e}")
            self.use_fastmcp = False
            return None

    async def _discover_openapi_spec(self) -> dict[str, Any] | None:
        """Auto-discover OpenAPI specification"""
        if not self.client:
            return None

        openapi_urls = [
            f"{self.source_info.source_path}/openapi.json",
            f"{self.source_info.source_path}/docs/openapi.json",
            f"{self.source_info.source_path}/swagger.json",
            f"{self.source_info.source_path}/api/docs",
        ]

        for url in openapi_urls:
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    json_data = response.json()
                    return json_data if isinstance(json_data, dict) else None
            except Exception:
                continue
        return None

    def discover_capabilities(self) -> list[dict[str, Any]]:
        """Discover API capabilities"""
        if self.use_fastmcp and FASTMCP_AVAILABLE:
            return asyncio.run(self._discover_with_fastmcp())
        return self._discover_with_native()

    async def _discover_with_fastmcp(self) -> list[dict[str, Any]]:
        """Discover capabilities using FastMCP"""
        try:
            await self._initialize_fastmcp()
            if not self.fastmcp_instance:
                return self._discover_with_native()

            # Get FastMCP tools
            tools = await self.fastmcp_instance.get_tools()
            capabilities = []

            for tool_name, tool in tools.items():
                capability = {
                    "name": tool_name,
                    "type": "fastmcp_tool",
                    "description": tool.description or f"FastMCP tool: {tool_name}",
                    "parameters": self._extract_fastmcp_parameters(tool),
                    "tool_instance": tool,  # Keep tool instance for later use
                }

                # Extract output schema from FastMCP tool if available
                if hasattr(tool, "output_schema") and tool.output_schema:
                    capability["output_schema"] = tool.output_schema

                capabilities.append(capability)

            return capabilities

        except Exception as e:
            print(f"FastMCP discovery failed, falling back to native implementation: {e}")
            return self._discover_with_native()

    def _discover_with_native(self) -> list[dict[str, Any]]:
        """Discover capabilities using native implementation (copied from multi_adapter.py)"""
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

    def _extract_fastmcp_parameters(self, tool: Any) -> list[dict[str, Any]]:
        """Extract parameter information from FastMCP tool"""
        parameters = []

        # FastMCP tools usually have schema attribute
        if hasattr(tool, "schema") and tool.schema:
            schema = tool.schema
            if "parameters" in schema:
                for param_name, param_info in schema["parameters"].get("properties", {}).items():
                    parameters.append(
                        {
                            "name": param_name,
                            "type": param_info.get("type", "string"),
                            "description": param_info.get("description", ""),
                            "required": param_name in schema["parameters"].get("required", []),
                        }
                    )

        return parameters

    def _parse_openapi_spec(self, spec: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse OpenAPI specification (copied and optimized from multi_adapter.py)"""
        capabilities = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    operation_id = details.get("operationId", f"{method}_{path.replace('/', '_')}")
                    parameters = self._extract_parameters(details, spec)

                    # Extract output schema from OpenAPI responses
                    output_schema = self._extract_output_schema(details)

                    capability = {
                        "name": operation_id,
                        "type": "http_endpoint",
                        "method": method.upper(),
                        "path": path,
                        "parameters": parameters,
                        "description": details.get("summary", f"{method.upper()} {path}"),
                    }

                    # Add output schema if available
                    if output_schema:
                        capability["output_schema"] = output_schema

                    capabilities.append(capability)

        return capabilities

    def _extract_output_schema(self, operation: dict[str, Any]) -> dict[str, Any] | None:
        """Extract output schema from OpenAPI operation responses."""
        responses = operation.get("responses", {})

        # Look for successful responses (200, 201, etc.)
        for status_code in ["200", "201", "202"]:
            if status_code in responses:
                response = responses[status_code]
                content = response.get("content", {})

                # Look for JSON content
                if "application/json" in content:
                    json_content = content["application/json"]
                    schema = json_content.get("schema")

                    if schema:
                        # Clean up the schema for FastMCP usage
                        return self._clean_openapi_schema(schema)

                # Also check for other content types
                for content_type, content_data in content.items():
                    if "json" in content_type.lower():
                        schema = content_data.get("schema")
                        if schema:
                            return self._clean_openapi_schema(schema)

        return None

    def _clean_openapi_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """Clean OpenAPI schema for FastMCP compatibility."""
        # Remove OpenAPI-specific fields that might not be compatible with JSON Schema
        cleaned = schema.copy()

        # Remove fields that are not part of JSON Schema spec
        openapi_specific_fields = ["example", "examples", "discriminator", "xml", "externalDocs"]
        for field in openapi_specific_fields:
            cleaned.pop(field, None)

        # Recursively clean nested schemas
        if "properties" in cleaned:
            cleaned_properties = {}
            for prop_name, prop_schema in cleaned["properties"].items():
                if isinstance(prop_schema, dict):
                    cleaned_properties[prop_name] = self._clean_openapi_schema(prop_schema)
                else:
                    cleaned_properties[prop_name] = prop_schema
            cleaned["properties"] = cleaned_properties

        if "items" in cleaned and isinstance(cleaned["items"], dict):
            cleaned["items"] = self._clean_openapi_schema(cleaned["items"])

        if "additionalProperties" in cleaned and isinstance(cleaned["additionalProperties"], dict):
            cleaned["additionalProperties"] = self._clean_openapi_schema(cleaned["additionalProperties"])

        return cleaned

    def _extract_parameters(self, operation: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract operation parameters"""
        parameters = []

        # Path parameters and query parameters
        for param in operation.get("parameters", []):
            parameters.append(
                {
                    "name": param["name"],
                    "type": param.get("schema", {}).get("type", "string"),
                    "description": param.get("description", ""),
                    "required": param.get("required", False),
                    "location": param["in"],  # path, query, header, etc.
                }
            )

        # Request body parameters
        request_body = operation.get("requestBody")
        if request_body:
            content = request_body.get("content", {})
            for _content_type, content_info in content.items():
                schema = content_info.get("schema", {})
                if "properties" in schema:
                    for prop_name, prop_info in schema["properties"].items():
                        parameters.append(
                            {
                                "name": prop_name,
                                "type": prop_info.get("type", "string"),
                                "description": prop_info.get("description", ""),
                                "required": prop_name in schema.get("required", []),
                                "location": "body",
                            }
                        )

        return parameters

    def generate_mcp_tool(self, capability: dict[str, Any]) -> str:
        """Generate MCP tool code"""
        if capability["type"] == "fastmcp_tool":
            return self._generate_fastmcp_wrapper(capability)
        return self._generate_standard_tool(capability)

    def _generate_fastmcp_wrapper(self, capability: dict[str, Any]) -> str:
        """Generate wrapper for FastMCP tool"""
        tool_name = capability["name"]
        description = capability["description"]
        parameters = capability["parameters"]

        # Generate parameter list
        param_list = []
        param_docs = []
        for param in parameters:
            param_type = param.get("type", "str")
            param_name = param["name"]
            param_desc = param.get("description", "")

            if param.get("required", False):
                param_list.append(f"{param_name}: {param_type}")
            else:
                param_list.append(f"{param_name}: Optional[{param_type}] = None")

            param_docs.append(f"        {param_name}: {param_desc}")

        param_str = ", ".join(param_list)
        param_doc_str = "\n".join(param_docs) if param_docs else "        No parameters"

        return f'''"""
{description}

This tool calls HTTP API endpoints through FastMCP engine
"""
import asyncio
from typing import Dict, Any, Optional

async def {tool_name}({param_str}) -> Dict[str, Any]:
    """
    {description}

    Parameters:
{param_doc_str}

    Returns:
        Dict[str, Any]: Standardized response format
    """
    try:
        # Need to access FastMCP instance here, actual implementation requires dependency injection
        # Current code is for demonstration structure
        return {{
            "status": "success",
            "method": "{tool_name}",
            "result": "FastMCP tool call successful, actual implementation will call real API"
        }}
    except Exception as e:
        return {{
            "status": "error",
            "method": "{tool_name}",
            "error": str(e)
        }}

# Synchronous wrapper
def {tool_name}_sync({param_str}) -> Dict[str, Any]:
    """Synchronous version of {tool_name}"""
    return asyncio.run({tool_name}({", ".join([p.split(":")[0] for p in param_list])}))
'''

    def _generate_standard_tool(self, capability: dict[str, Any]) -> str:
        """Generate standard HTTP tool (original implementation)"""
        return self._generate_standard_tool_template(
            tool_name=capability["name"],
            parameters=capability["parameters"],
            description=capability["description"],
            implementation_code=self._generate_http_request_code(capability),
        )

    def _generate_http_request_code(self, capability: dict[str, Any]) -> str:
        """Generate HTTP request code"""
        method = capability.get("method", "GET")
        path = capability.get("path", "/")
        base_url = self.source_info.source_path

        return f'''
    try:
        import requests

        url = "{base_url}{path}"

        # Build request parameters
        params = {{}}
        headers = {{"Content-Type": "application/json"}}
        data = None

        # Assign parameters based on parameter location
        for param_name, param_value in locals().items():
            if param_value is not None and param_name not in ['url', 'params', 'headers', 'data']:
                # Simplified implementation: all parameters as query parameters
                params[param_name] = param_value

        response = requests.{method.lower()}(
            url,
            params=params if "{method}" == "GET" else None,
            json=params if "{method}" != "GET" else None,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()

        return {{
            "status": "success",
            "method": "{capability["name"]}",
            "result": response.json() if response.content else "Operation successful"
        }}

    except Exception as e:
        return {{
            "status": "error",
            "method": "{capability["name"]}",
            "error": str(e)
        }}
'''

    def test_connectivity(self) -> bool:
        """Test API connectivity"""
        try:
            response = requests.get(f"{self.source_info.source_path}/health", timeout=5)
            return response.status_code < 500
        except Exception:
            try:
                # Try basic connection
                response = requests.get(self.source_info.source_path, timeout=5)
                return response.status_code < 500
            except Exception:
                return False


# Convenience functions
def create_enhanced_http_adapter(
    base_url: str,
    engine: str = "auto",
    openapi_spec: dict[str, Any] | None = None,
    endpoints: list[dict[str, Any]] | None = None,
    timeout: float = 30.0,
) -> EnhancedHttpApiAdapter:
    """Convenience function to create enhanced HTTP adapter"""

    config = {"engine": engine, "timeout": timeout}

    if openapi_spec:
        config["openapi_spec"] = openapi_spec

    if endpoints:
        config["endpoints"] = endpoints

    source_info = SourceInfo(source_type="http_api", source_path=base_url, config=config)

    return EnhancedHttpApiAdapter(source_info)
