#!/usr/bin/env python3
"""
FastMCP-Factory Factory and Project Management Example

Demonstrates MCPFactory core functionality:
1. Factory pattern for creating and managing servers
2. Project creation and build lifecycle
3. Authentication provider management
4. Configuration file management and hot reload
5. Server state persistence

Usage: python factory_complete.py
"""

import asyncio
import logging
import os
import tempfile
from typing import Any

import yaml

from mcp_factory.factory import MCPFactory

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Factory and project management example main function"""
    print("🏭 FastMCP-Factory Factory and Project Management Example")
    print("=" * 60)

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_workspace:
        print(f"📁 Workspace: {temp_workspace}")

        # 1. Create MCPFactory instance
        factory = MCPFactory(workspace_root=temp_workspace)
        print("✅ MCPFactory instance created successfully")

        # 2. Demonstrate project creation and building
        await demo_project_management(factory, temp_workspace)

        # 3. Demonstrate factory server management
        await demo_server_management(factory, temp_workspace)

        # 4. Demonstrate configuration management
        await demo_config_management(factory, temp_workspace)

        print("\n✨ Factory example demonstration completed!")
        print("📖 Next step: Check mounting_servers.py to learn about server mounting")


async def demo_project_management(factory: MCPFactory, workspace: str):
    """Demonstrate project creation and building"""
    print("\n📦 Project Management Demo")
    print("-" * 30)

    # Create project configuration
    project_config = {
        "server": {"name": "demo-project-server", "instructions": "Demo project server created by factory"},
        "tools": {"expose_management_tools": True},
    }

    try:
        # Use factory to create project and server
        project_path, server_id = factory.create_project_and_server("demo-project", project_config)

        print(f"✅ Project created successfully: {project_path}")
        print(f"✅ Server created successfully: {server_id}")

        # Get server instance
        server = factory.get_server(server_id)

        # Add project-specific tools to server
        @server.tool(name="project_info", description="Get project information")
        def get_project_info() -> dict[str, Any]:
            """Get current project information"""
            return {
                "project_name": "demo-project",
                "project_path": project_path,
                "server_id": server_id,
                "server_name": server.name,
                "tools_count": len(server._tools) if hasattr(server, "_tools") else 0,
            }

        # Test tool call
        project_info = get_project_info()
        print(f"📊 Project info: {project_info}")

        # Sync server to project filesystem
        sync_result = factory.sync_to_project(server_id)
        print(f"💾 Project sync result: {sync_result}")

    except Exception as e:
        logger.error(f"Project management demo failed: {e}")


async def demo_server_management(factory: MCPFactory, workspace: str):
    """Demonstrate factory server management"""
    print("\n🖥️ Server Management Demo")
    print("-" * 30)

    # Create config file server
    config_path = os.path.join(workspace, "server_config.yaml")
    server_config = {
        "server": {"name": "managed-server", "instructions": "Server managed through configuration file"},
        "transport": {"host": "localhost", "port": 8080},
        "advanced": {"log_level": "INFO"},
    }

    # Save configuration file
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(server_config, f, allow_unicode=True)

    try:
        # Create server from configuration file
        server_id = factory.create_server(name="config-managed-server", source=config_path)

        server = factory.get_server(server_id)
        print(f"✅ Config file server created successfully: {server.name}")

        # List all factory-managed servers
        servers = factory.list_servers()
        print("📋 Factory-managed servers:")
        for server_info in servers:
            print(f"  - {server_info['id']}: {server_info['name']}")

        # Get server status
        server_status = factory.get_server_status(server_id)
        print(f"📊 Server status: {server_status.get('status', 'unknown')}")

    except Exception as e:
        logger.error(f"Server management demo failed: {e}")


async def demo_config_management(factory: MCPFactory, workspace: str):
    """Demonstrate configuration management and hot reload"""
    print("\n⚙️ Configuration Management Demo")
    print("-" * 30)

    # Create hot-reloadable configuration
    config_path = os.path.join(workspace, "hot_reload_config.yaml")
    initial_config = {
        "server": {"name": "hot-reload-server", "instructions": "Server supporting hot reload"},
        "tools": {"enabled_tools": ["tool1", "tool2"]},
        "advanced": {"log_level": "INFO"},
    }

    # Save initial configuration
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(initial_config, f, allow_unicode=True)

    try:
        # Create server
        server_id = factory.create_server(name="hot-reload-server", source=config_path)

        server = factory.get_server(server_id)
        print(f"✅ Server created successfully: {server.name}")
        print(f"📋 Initial enabled tools: {initial_config['tools']['enabled_tools']}")

        # Simulate configuration modification
        updated_config = initial_config.copy()
        updated_config["tools"]["enabled_tools"].append("tool3")
        updated_config["advanced"]["log_level"] = "DEBUG"

        # Save updated configuration
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(updated_config, f, allow_unicode=True)

        print("📝 Configuration file updated")

        # Use factory's reload configuration functionality
        try:
            updated_server = factory.reload_server_config(server_id)
            print(f"🔄 Configuration reload successful: {updated_server.name}")
            print(f"📋 Updated enabled tools: {updated_config['tools']['enabled_tools']}")
        except Exception as reload_error:
            print(f"⚠️  Configuration reload failed: {reload_error}")

    except Exception as e:
        logger.error(f"Configuration management demo failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example stopped")
    except Exception as e:
        logger.error(f"Example execution error: {e}")
        raise
