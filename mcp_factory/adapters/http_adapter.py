"""HTTP API Adapter - Convert HTTP APIs to MCP tools.

This adapter discovers HTTP API endpoints and converts them into MCP tools,
supporting both OpenAPI/Swagger documentation and manual configuration.
"""

import asyncio
from typing import Any
from urllib.parse import urljoin

from .base import (
    BaseAdapter,
    CapabilityInfo,
    ConnectivityResult,
    DiscoveryError,
    GenerationError,
    SourceInfo,
    generate_tool_template,
)
from .cache import cached_method

# Optional dependencies
try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

try:
    import importlib.util

    FASTMCP_AVAILABLE = importlib.util.find_spec("fastmcp") is not None
except ImportError:
    FASTMCP_AVAILABLE = False


class HttpApiAdapter(BaseAdapter):
    """Adapter for HTTP APIs"""

    def __init__(self, source_info: SourceInfo):
        super().__init__(source_info)

        if not HTTPX_AVAILABLE:
            raise ImportError("httpx is required for HTTP adapter. Install with: pip install httpx")

        self.base_url = source_info.source_path
        self.timeout = self.config.get("timeout", 30)
        self.headers = self.config.get("headers", {})
        self.use_fastmcp = self.config.get("use_fastmcp", True) and FASTMCP_AVAILABLE

        self.client: httpx.AsyncClient | None = None
        self.fastmcp_instance: Any | None = None

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized"""
        if self.client is None:
            self.client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)

    async def _close_client(self) -> None:
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()
            self.client = None

    @cached_method("http_discover", ttl=1800)  # Cache for 30 minutes
    def discover_capabilities(self) -> list[CapabilityInfo]:
        """Discover HTTP API capabilities"""
        try:
            return asyncio.run(self._async_discover_capabilities())
        except Exception as e:
            raise DiscoveryError(f"Failed to discover HTTP API capabilities: {e}") from e

    async def _async_discover_capabilities(self) -> list[CapabilityInfo]:
        """Async version of capability discovery"""
        await self._ensure_client()

        try:
            # Try to discover via OpenAPI/Swagger first
            capabilities = await self._discover_via_openapi()
            if capabilities:
                return capabilities

            # Try FastMCP if available
            if self.use_fastmcp:
                capabilities = await self._discover_via_fastmcp()
                if capabilities:
                    return capabilities

            # Fall back to manual configuration
            return self._discover_via_config()

        finally:
            await self._close_client()

    async def _discover_via_openapi(self) -> list[CapabilityInfo]:
        """Discover capabilities via OpenAPI/Swagger documentation"""
        openapi_urls = [
            "/openapi.json",
            "/swagger.json",
            "/api/openapi.json",
            "/api/swagger.json",
            "/docs/openapi.json",
        ]

        for url_path in openapi_urls:
            try:
                full_url = urljoin(self.base_url, url_path)
                if not self.client:
                    continue
                response = await self.client.get(full_url)

                if response.status_code == 200:
                    openapi_spec = response.json()
                    return self._parse_openapi_spec(openapi_spec)

            except Exception:
                continue

        return []

    def _parse_openapi_spec(self, spec: dict[str, Any]) -> list[CapabilityInfo]:
        """Parse OpenAPI specification to extract capabilities"""
        capabilities = []
        paths = spec.get("paths", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method.upper() not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
                    continue

                operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
                summary = operation.get("summary", f"{method.upper()} {path}")

                # Extract parameters
                parameters = []
                for param in operation.get("parameters", []):
                    param_info = {
                        "name": param["name"],
                        "type": param.get("schema", {}).get("type", "string"),
                        "required": param.get("required", False),
                        "description": param.get("description", ""),
                    }
                    parameters.append(param_info)

                # Extract request body parameters
                request_body = operation.get("requestBody", {})
                if request_body:
                    content = request_body.get("content", {})
                    for content_type, schema_info in content.items():
                        if "application/json" in content_type:
                            schema = schema_info.get("schema", {})
                            properties = schema.get("properties", {})
                            required_fields = schema.get("required", [])

                            for prop_name, prop_schema in properties.items():
                                param_info = {
                                    "name": prop_name,
                                    "type": prop_schema.get("type", "string"),
                                    "required": prop_name in required_fields,
                                    "description": prop_schema.get("description", ""),
                                }
                                parameters.append(param_info)

                capability = CapabilityInfo(
                    name=operation_id,
                    description=summary,
                    parameters=parameters,
                    capability_type="http_endpoint",
                    metadata={"path": path, "method": method.upper(), "base_url": self.base_url},
                )
                capabilities.append(capability)

        return capabilities

    async def _discover_via_fastmcp(self) -> list[CapabilityInfo]:
        """Discover capabilities via FastMCP"""
        # TODO: Implement FastMCP integration when API is stable
        return []

    def _extract_fastmcp_parameters(self, tool: Any) -> list[dict[str, Any]]:
        """Extract parameters from FastMCP tool definition"""
        parameters = []

        # FastMCP tools typically have a schema property
        schema = tool.get("schema", {})
        properties = schema.get("properties", {})
        required_fields = schema.get("required", [])

        for param_name, param_schema in properties.items():
            param_info = {
                "name": param_name,
                "type": param_schema.get("type", "string"),
                "required": param_name in required_fields,
                "description": param_schema.get("description", ""),
            }
            parameters.append(param_info)

        return parameters

    def _discover_via_config(self) -> list[CapabilityInfo]:
        """Discover capabilities via manual configuration"""
        endpoints = self.config.get("endpoints", [])
        capabilities = []

        for endpoint in endpoints:
            capability = CapabilityInfo(
                name=endpoint["name"],
                description=endpoint.get("description", f"HTTP endpoint: {endpoint['name']}"),
                parameters=endpoint.get("parameters", []),
                capability_type="http_endpoint",
                metadata={"path": endpoint["path"], "method": endpoint.get("method", "GET"), "base_url": self.base_url},
            )
            capabilities.append(capability)

        return capabilities

    @cached_method("http_generate", ttl=7200)  # Cache for 2 hours
    def generate_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate MCP tool code for HTTP endpoint"""
        try:
            if capability.metadata.get("fastmcp"):
                return self._generate_fastmcp_tool_code(capability)
            else:
                return self._generate_standard_tool_code(capability)

        except Exception as e:
            raise GenerationError(f"Failed to generate tool code for {capability.name}: {e}") from e

    def _generate_fastmcp_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate tool code for FastMCP-based capability"""
        impl_code = f'''
        # FastMCP tool implementation
        import httpx
        from fastmcp import FastMCP

        async with httpx.AsyncClient() as client:
            fastmcp = FastMCP.from_openapi(client=client, base_url="{self.base_url}")
            result = await fastmcp.call_tool("{capability.name}", locals())

            return {{
                "success": True,
                "result": result,
                "endpoint": "{capability.name}",
                "type": "fastmcp"
            }}'''

        return generate_tool_template(
            tool_name=capability.name,
            parameters=capability.parameters,
            description=capability.description,
            implementation_code=impl_code,
        )

    def _generate_standard_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate standard HTTP tool code"""
        method = capability.metadata.get("method", "GET")
        path = capability.metadata.get("path", "/")
        base_url = capability.metadata.get("base_url", self.base_url)

        # Generate parameter handling code
        param_handling = self._generate_parameter_handling(capability.parameters, method)

        impl_code = f'''
        # HTTP API call implementation
        import httpx

        {param_handling}

        async with httpx.AsyncClient(timeout={self.timeout}) as client:
            response = await client.{method.lower()}(
                url=f"{base_url}{path}",
                **request_kwargs
            )
            response.raise_for_status()

            return {{
                "success": True,
                "result": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                "status_code": response.status_code,
                "endpoint": "{path}",
                "method": "{method}"
            }}'''

        return generate_tool_template(
            tool_name=capability.name,
            parameters=capability.parameters,
            description=capability.description,
            implementation_code=impl_code,
        )

    def _generate_parameter_handling(self, parameters: list[dict[str, Any]], method: str) -> str:
        """Generate parameter handling code"""
        if not parameters:
            return "request_kwargs = {}"

        if method.upper() in ["GET", "DELETE"]:
            return """
        # Handle query parameters
        params = {}
        for key, value in locals().items():
            if key not in ['request_kwargs', 'params'] and value is not None:
                params[key] = value
        request_kwargs = {"params": params}"""
        else:
            return """
        # Handle request body
        data = {}
        for key, value in locals().items():
            if key not in ['request_kwargs', 'data'] and value is not None:
                data[key] = value
        request_kwargs = {"json": data}"""

    def test_connectivity(self) -> ConnectivityResult:
        """Test connectivity to HTTP API"""
        try:
            return asyncio.run(self._async_test_connectivity())
        except Exception as e:
            return ConnectivityResult(
                success=False, message=f"Failed to test connectivity: {e}", details={"error": str(e)}
            )

    async def _async_test_connectivity(self) -> ConnectivityResult:
        """Async version of connectivity test"""
        await self._ensure_client()

        try:
            # Try to make a simple request to the base URL
            if not self.client:
                return ConnectivityResult(
                    success=False,
                    message="HTTP client not initialized",
                    details={"error": "Client initialization failed"},
                )
            response = await self.client.get(self.base_url)

            return ConnectivityResult(
                success=True,
                message=f"Successfully connected to {self.base_url}",
                details={
                    "status_code": response.status_code,
                    "url": self.base_url,
                    "response_time": response.elapsed.total_seconds() if hasattr(response, "elapsed") else None,
                },
            )

        except Exception as e:
            return ConnectivityResult(
                success=False, message=f"Failed to connect to {self.base_url}: {e}", details={"error": str(e)}
            )
        finally:
            await self._close_client()


# Convenience functions


def create_http_adapter(
    base_url: str,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    use_fastmcp: bool = True,
    endpoints: list[dict[str, Any]] | None = None,
) -> HttpApiAdapter:
    """Create HTTP API adapter with simplified configuration"""

    config: dict[str, Any] = {"timeout": timeout, "use_fastmcp": use_fastmcp}

    if headers:
        config["headers"] = headers

    if endpoints:
        config["endpoints"] = endpoints

    from .base import AdapterType

    source_info = SourceInfo(adapter_type=AdapterType.HTTP_API, source_path=base_url, config=config)

    return HttpApiAdapter(source_info)
