#!/usr/bin/env python3
"""FastMCP-Factory Demo Server

This demo server demonstrates how to use MCPFactory to create and configure MCP servers,
including tool registration, configuration management, and management tools usage.

Usage: python examples/demo/server.py
"""

import asyncio
import logging
import os
import socket
from typing import Any

import yaml

from mcp_factory.factory import MCPFactory
from mcp_factory.server import ManagedServer

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Server configuration
CONFIG: dict[str, Any] = {
    "server": {
        "name": "demo-server",
        "instructions": "FastMCP-Factory demo server providing calculation functionality and management tools",
        "host": "localhost",
        "port": 8888,
        "transport": "streamable-http",
    },
    "tools": {"expose_management_tools": True},
    "advanced": {"log_level": "INFO", "streamable_http_path": "/api/mcp"},
}


def is_port_in_use(host: str, port: int) -> bool:
    """Check if port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def create_config_file() -> str:
    """Create configuration file and return path"""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(CONFIG, f, allow_unicode=True, default_flow_style=False)
    return config_path


def register_demo_tools(server: ManagedServer) -> None:
    """Register demo tools"""

    @server.tool(name="add", description="Calculate the sum of two numbers")
    def add(a: float, b: float) -> float:
        """Calculate the sum of two numbers"""
        logger.info(f"Execute addition: {a} + {b}")
        return a + b

    @server.tool(name="multiply", description="Calculate the product of two numbers")
    def multiply(a: float, b: float) -> float:
        """Calculate the product of two numbers"""
        logger.info(f"Execute multiplication: {a} * {b}")
        return a * b


async def get_tools_count(server: ManagedServer) -> tuple[int, int]:
    """Get tools count statistics"""
    tools = await server.get_tools()

    # Categorize tools statistics
    management_tools = [tool for tool in tools if str(tool).startswith("manage_")]
    normal_tools = [tool for tool in tools if not str(tool).startswith("manage_")]

    return len(management_tools), len(normal_tools)


def print_server_status(mgmt_count: int, normal_count: int) -> None:
    """Print server status information"""
    print("\n" + "=" * 50)
    print("📊 Tool Registration Statistics")
    print(f"   Management tools: {mgmt_count} tools")
    print(f"   Business tools: {normal_count} tools")
    print(f"   Total: {mgmt_count + normal_count} tools")
    print("=" * 50)

    if mgmt_count > 0:
        print("✅ Management tools registered successfully")
        print("   FastMCP-Factory factory mode working normally")
    else:
        print("⚠️  No management tools found")
        print("   Please check the expose_management_tools setting in configuration")


def main() -> None:
    """Main function"""
    print("🚀 FastMCP-Factory Demo Server")
    print("=" * 50)

    # Create configuration file
    config_path = create_config_file()
    print(f"📝 Configuration file: {config_path}")

    # Check port
    host = CONFIG["transport"]["host"]
    port = CONFIG["transport"]["port"]

    if is_port_in_use(host, port):
        print(f"❌ Error: Port {port} is already in use")
        print(f"   Please modify the port setting in {config_path}")
        return

    # Create factory and server
    print("🏭 Creating MCPFactory instance...")
    factory = MCPFactory()

    print("🔧 Creating ManagedServer using factory...")
    server = factory.create_managed_server(
        config_path=config_path,
        expose_management_tools=CONFIG["tools"]["expose_management_tools"],
        **CONFIG["server"],
    )

    # Register demo tools
    print("🛠️  Registering demo tools...")
    register_demo_tools(server)

    # Get tools statistics
    print("📊 Counting registered tools...")
    mgmt_count, normal_count = asyncio.run(get_tools_count(server))

    # Display server status
    print_server_status(mgmt_count, normal_count)

    # Server startup information
    path = CONFIG["advanced"]["streamable_http_path"]
    print(f"\n🌐 Server address: http://{host}:{port}{path}")
    print("📱 Client usage:")
    print("   python examples/demo/client.py       # Standard mode")
    print("   python examples/demo/client.py --mgmt # Management tools mode")
    print("\n⏹️  Press Ctrl+C to stop server")
    print("=" * 50)

    # Start server
    try:
        server.run(
            transport=CONFIG["transport"]["transport"],
            host=CONFIG["transport"]["host"],
            port=CONFIG["transport"]["port"],
            streamable_http_path=path,
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"\n❌ Server startup failed: {e}")
        logger.exception("Server startup exception")


if __name__ == "__main__":
    main()
