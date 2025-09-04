# !/usr/bin/env python3
"""
FastMCP-Factory External Servers Demo

Demonstrates external server integration and microservice architecture:
1. External MCP server configuration parsing
2. Local script server mounting
3. Remote HTTP server mounting
4. Server lifecycle management
5. Mounted server tool and resource proxying

Run with: python mounting_servers.py --config configs/mounting.yaml
"""

import argparse
import asyncio
import logging
import os
import tempfile

import yaml

from mcp_factory.factory import MCPFactory
from mcp_factory.mounting import ServerRegistry

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Server mounting example main function"""
    parser = argparse.ArgumentParser(description="Server mounting example")
    parser.add_argument("--config", default="configs/mounting.yaml", help="Configuration file path")
    parser.add_argument("--demo-mode", action="store_true", help="Demo mode, use built-in configuration")
    args = parser.parse_args()

    print("🔗 FastMCP-Factory Server Mounting Example")
    print("=" * 60)

    if args.demo_mode:
        await demo_mode()
    else:
        await run_with_config(args.config)


async def demo_mode():
    """Demo mode - using built-in configuration"""
    print("🎭 Demo mode starting")

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_workspace:
        print(f"📁 Workspace: {temp_workspace}")

        # 1. Demonstrate server registry configuration parsing
        await demo_server_registry()

        # 2. Demonstrate local server mounting
        await demo_local_server_mounting(temp_workspace)

        # 3. Demonstrate remote server mounting (simulation)
        await demo_remote_server_mounting()

        # 4. Demonstrate mounting lifecycle management
        await demo_mounting_lifecycle(temp_workspace)

        print("\n✨ Mounting example demonstration completed!")
        print("📖 Next step: Check production_ready.py to learn about production environment configuration")


async def run_with_config(config_path: str):
    """Run with configuration file"""
    if not os.path.exists(config_path):
        print(f"❌ Configuration file does not exist: {config_path}")
        print("💡 Tip: Use --demo-mode to run demo mode")
        return

    print(f"📖 Loading configuration file: {config_path}")

    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        factory = MCPFactory()

        # Create main server
        main_server = factory.create_managed_server(config_path=config_path, name="mounting-demo-server")

        print(f"✅ Main server created successfully: {main_server.name}")

        # If mcpServers in config, demonstrate mounting
        if "mcpServers" in config:
            print("🔗 Starting to mount external servers...")
            # This will be automatically mounted through lifespan
            print("✅ Server mounting configuration loaded")

        print("\n💡 Tip: In actual use, call server.run() to start server with mounting")

    except Exception as e:
        logger.error(f"Configuration file execution failed: {e}")


async def demo_server_registry():
    """Demonstrate server registry configuration parsing"""
    print("\n📋 Server registry demonstration")
    print("-" * 30)

    # Create virtual main server
    from mcp_factory.server import ManagedServer

    main_server = ManagedServer(name="demo-main-server", instructions="Main server for mounting demonstration")

    # Create server registry
    registry = ServerRegistry(main_server)

    # Example configuration
    demo_config = {
        "mcpServers": {
            "file-processor": {"command": "python", "args": ["./servers/file_processor.py"], "env": {"DEBUG": "true"}},
            "weather-api": {
                "url": "https://weather-api.example.com/mcp",
                "headers": {"Authorization": "Bearer token123"},
            },
            "realtime-stream": {"url": "https://stream.example.com/mcp/sse"},
        }
    }

    try:
        # Parse external server configuration
        server_configs = registry.parse_external_servers_config(demo_config)

        print(f"✅ Parsed {len(server_configs)} external servers:")
        for name, config in server_configs.items():
            transport = config.inferred_transport
            if config.is_local:
                print(f"  - {name}: Local script ({transport}) - {config.command} {' '.join(config.args)}")
            else:
                print(f"  - {name}: Remote service ({transport}) - {config.url}")

        # Register servers
        registry.register_servers(server_configs)
        registered = registry.list_registered_servers()
        print(f"📦 Registered servers: {registered}")

    except Exception as e:
        logger.error(f"Server registry demonstration failed: {e}")


async def demo_local_server_mounting(workspace: str):
    """Demonstrate local server mounting"""
    print("\n💻 Local server mounting demonstration")
    print("-" * 30)

    # Create a simple local server script
    local_server_script = os.path.join(workspace, "demo_local_server.py")

    script_content = '''# !/usr/bin/env python3
"""Simple demonstration MCP server"""
import asyncio
from mcp_factory.server import ManagedServer

async def main():
    server = ManagedServer(
        name="demo-local-server",
        instructions="Local server for demonstration"
    )

    @server.tool(name="local_hello", description="Local server greeting")
    def local_hello(name: str) -> str:
        return f"Greeting from local server: Hello, {name}!"

    print("🚀 Local demo server starting")
    await server.run_async()

if __name__ == "__main__":
    asyncio.run(main())
'''

    with open(local_server_script, "w", encoding="utf-8") as f:
        f.write(script_content)

    print(f"📝 Created demo script: {local_server_script}")

    # Demonstrate local server configuration
    from mcp_factory.mounting.models import ServerConfig

    local_config = ServerConfig(command="python", args=[local_server_script], env={"DEMO": "true"})

    print("✅ Local server configuration:")
    print(f"  - Command: {local_config.command}")
    print(f"  - Arguments: {local_config.args}")
    print(f"  - Transport: {local_config.inferred_transport}")
    print(f"  - Is local: {local_config.is_local}")


async def demo_remote_server_mounting():
    """Demonstrate remote server mounting (simulation)"""
    print("\n🌐 Remote server mounting demonstration")
    print("-" * 30)

    from mcp_factory.mounting.models import ServerConfig

    # HTTP server configuration
    http_config = ServerConfig(
        url="https://api.example.com/mcp", headers={"Authorization": "Bearer token123"}, timeout=30
    )

    print("🔗 HTTP server configuration:")
    print(f"  - URL: {http_config.url}")
    print(f"  - Transport: {http_config.inferred_transport}")
    print(f"  - Is remote: {http_config.is_remote}")
    print(f"  - Timeout: {http_config.timeout} seconds")

    # SSE server configuration
    sse_config = ServerConfig(url="https://stream.example.com/mcp/sse", headers={"Authorization": "Bearer sse-token"})

    print("\n📡 SSE server configuration:")
    print(f"  - URL: {sse_config.url}")
    print(f"  - Transport: {sse_config.inferred_transport}")
    print(f"  - Is remote: {sse_config.is_remote}")

    print("\n💡 Note: Remote servers will not actually connect in demo mode")


async def demo_mounting_lifecycle(workspace: str):
    """Demonstrate mounting lifecycle management"""
    print("\n♻️ Mounting lifecycle management demonstration")
    print("-" * 30)

    try:
        from mcp_factory.server import ManagedServer

        # Create main server
        main_server = ManagedServer(name="lifecycle-demo-server", instructions="Lifecycle demonstration server")

        # Create server registry
        registry = ServerRegistry(main_server)

        # Configure mounting options
        mount_options = {
            "auto_start": True,
            "health_check": True,
            "health_check_interval": 30,
            "auto_restart": False,
            "prefix_tools": True,
        }

        # Example server configuration
        from mcp_factory.mounting.models import ServerConfig

        server_configs = {
            "demo-service": ServerConfig(
                command="python", args=["-c", "print('Demo service running')"], env={"MODE": "demo"}
            )
        }

        registry.register_servers(server_configs)

        # Create lifecycle function
        registry.create_lifespan(mount_options)

        print("✅ Lifecycle manager created successfully")
        print(f"📋 Mount options: {mount_options}")
        print(f"🔧 Registered servers: {list(server_configs.keys())}")

        # Simulate lifecycle (in actual use, this would be called by FastMCP)
        print("\n🔄 Simulating lifecycle startup...")
        print("  - Initialize mounter")
        print("  - Auto-mount servers")
        print("  - Start health checks")
        print("✅ Lifecycle startup completed")

        print("\n💡 In actual use, the lifecycle will:")
        print("  - Automatically start external server processes")
        print("  - Establish connections and proxy tools")
        print("  - Perform periodic health checks")
        print("  - Clean up resources when server shuts down")

    except Exception as e:
        logger.error(f"Lifecycle demonstration failed: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example stopped")
    except Exception as e:
        logger.error(f"Example execution error: {e}")
        raise
