#!/usr/bin/env python3
"""Advanced Server Example

This example demonstrates the advanced features of FastMCP-Factory, including:
1. Creating and managing authentication providers
2. Controlling server creation using command line parameters
3. lifespan - Server lifecycle management
4. tool_serializer - Custom tool result serialization
5. tags and dependencies - Server metadata

Usage:
  # Create authentication provider
  python -m examples.advanced_example create-auth --id test-auth --type auth0 --domain example.auth0.com --client-id xxxx --client-secret xxxx
  
  # List authentication providers
  python -m examples.advanced_example list-auth
  
  # Create and run advanced server
  python -m examples.advanced_example run-server --config examples/advanced_config.yaml --auth-provider test-auth
  
  # List all servers
  python -m examples.advanced_example list-servers
"""

import argparse
import asyncio
import datetime
import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Set, Union

from fastmcp_factory import FastMCPFactory
from fastmcp_factory.auth import AuthProviderRegistry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 1. Custom lifecycle manager
@asynccontextmanager
async def server_lifespan(server: Any) -> Any:
    """Custom server lifecycle manager.
    
    This will execute initialization logic when the server starts,
    and cleanup logic when the server shuts down.
    
    The dictionary returned by the lifecycle can be accessed in the server via self.state.
    """
    start_time = datetime.datetime.now()
    logger.info(f"Server starting... [{start_time}]")
    
    # Simulate resource initialization
    resources = {
        "start_time": start_time,
        "cache": {},
        "connections": 0,
    }
    
    # Generate lifecycle state
    yield resources
    
    # Execute when server shuts down
    run_time = datetime.datetime.now() - start_time
    logger.info(f"Server shutting down... Runtime: {run_time}")
    logger.info(f"Connections processed: {resources['connections']}")


# 2. Custom tool result serializer
def custom_serializer(result: Any) -> str:
    """Custom tool result serializer.
    
    Handles complex types that FastMCP cannot natively serialize.
    """
    if isinstance(result, complex):
        return f"{result.real}+{result.imag}j"
    elif isinstance(result, datetime.datetime):
        return result.isoformat()
    elif isinstance(result, bytes):
        return f"bytes:{result.hex()}"
    elif isinstance(result, set):
        return json.dumps(list(result))
    # Default handling
    return str(result)


# 3. Custom server tools
def register_custom_tools(server: Any) -> None:
    """Register custom tools to the server."""
    
    @server.tool(
        name="math_operations",
        description="Perform mathematical operations, supporting complex numbers",
    )
    def math_operations(operation: str, a: float, b: float = 0) -> Union[float, complex]:
        """Perform basic mathematical operations.
        
        Args:
            operation: Operation type (add, subtract, multiply, divide, complex)
            a: First number
            b: Second number (represents imaginary part for complex operation)
            
        Returns:
            Operation result
        """
        if operation == "add":
            return a + b
        elif operation == "subtract":
            return a - b
        elif operation == "multiply":
            return a * b
        elif operation == "divide":
            if b == 0:
                raise ValueError("Divisor cannot be zero")
            return a / b
        elif operation == "complex":
            return complex(a, b)
        else:
            raise ValueError(f"Unsupported operation: {operation}")
    
    @server.tool(
        name="server_info",
        description="Get server information and status",
    )
    def server_info() -> Dict[str, Any]:
        """Get current server information and status."""
        if not hasattr(server, "state"):
            return {"error": "Server state not available"}
        
        # Update connection count
        server.state["connections"] += 1
        
        # Return server information
        return {
            "name": server.name,
            "tags": list(server.tags) if hasattr(server, "tags") else [],
            "dependencies": server.dependencies if hasattr(server, "dependencies") else [],
            "uptime": str(datetime.datetime.now() - server.state["start_time"]),
            "connections": server.state["connections"],
        }


async def run_advanced_server(args: argparse.Namespace) -> None:
    """Run advanced server with all advanced features."""
    # Create tags and dependencies lists
    server_tags: Set[str] = {"advanced-example", "demo", "custom-lifecycle"}
    server_dependencies: List[str] = ["demo-lib", "math-tools", "custom-serializer"]
    
    # Create factory
    factory = FastMCPFactory()
    
    # Get authentication provider (if specified)
    auth_provider = None
    if args.auth_provider:
        auth_provider = factory.get_auth_provider(args.auth_provider)
        if auth_provider:
            logger.info(f"Using authentication provider: {args.auth_provider}")
        else:
            logger.warning(f"Authentication provider not found: {args.auth_provider}")
    
    # Create server with advanced parameters
    server = factory.create_managed_server(
        config_path=args.config,
        # Advanced parameters passed via code API
        lifespan=server_lifespan,
        tool_serializer=custom_serializer,
        tags=server_tags,
        dependencies=server_dependencies,
        auth_provider_id=args.auth_provider,
        # Override parameters from configuration
        host="127.0.0.1",  # Local access only
        debug=True,        # Enable debug mode
    )
    
    # Register custom tools
    register_custom_tools(server)
    
    # Print server information
    logger.info(f"Created advanced server: {server.name}")
    logger.info(f"Tags: {server.tags}")
    logger.info(f"Dependencies: {server.dependencies}")
    
    # Wait for user input to exit
    print("\nServer configured successfully.")
    print("Press Ctrl+C to stop the server...")
    
    try:
        # Run server
        # Note: When using streamable-http transport, this will block until the server stops
        await server.run_async(transport="streamable-http")
    except KeyboardInterrupt:
        print("\nExit signal received, shutting down server...")


def main() -> None:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description="FastMCP-Factory Advanced Example")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create authentication provider command
    auth_parser = subparsers.add_parser("create-auth", help="Create authentication provider")
    auth_parser.add_argument("--id", required=True, help="Provider ID")
    auth_parser.add_argument("--type", required=True, choices=["auth0"], help="Provider type")
    auth_parser.add_argument("--domain", required=True, help="Auth0 domain")
    auth_parser.add_argument("--client-id", required=True, help="Client ID")
    auth_parser.add_argument("--client-secret", required=True, help="Client Secret")
    auth_parser.add_argument("--audience", help="Target audience (optional)")
    auth_parser.add_argument("--roles-namespace", help="Roles namespace (optional)")
    
    # List authentication providers command
    subparsers.add_parser("list-auth", help="List authentication providers")

    # Run server command
    run_parser = subparsers.add_parser("run-server", help="Run advanced server")
    run_parser.add_argument("--config", required=True, help="Server configuration file path")
    run_parser.add_argument("--auth-provider", help="Authentication provider ID to use")

    # List servers command
    subparsers.add_parser("list-servers", help="List all servers")

    # Parse arguments
    args = parser.parse_args()

    # Create factory
    factory = FastMCPFactory()

    # Handle commands
    if args.command == "create-auth":
        # Create authentication provider
        provider = factory.create_auth_provider(
            provider_id=args.id,
            provider_type=args.type,
            config={
                "domain": args.domain,
                "client_id": args.client_id,
                "client_secret": args.client_secret,
                "audience": args.audience,
                "roles_namespace": args.roles_namespace
            }
        )
        if provider:
            print(f"Authentication provider '{args.id}' (type: {args.type}) created successfully")
        else:
            print("Failed to create authentication provider")
            sys.exit(1)
    
    elif args.command == "list-auth":
        # List authentication providers
        providers = factory.list_auth_providers()
        if providers:
            print("Registered authentication providers:")
            for provider_id, provider_type in providers.items():
                print(f"  - {provider_id}: {provider_type}")
        else:
            print("No registered authentication providers")
            
    elif args.command == "run-server":
        # Run advanced server
        asyncio.run(run_advanced_server(args))
    
    elif args.command == "list-servers":
        # List all servers
        servers = factory.list_servers()
        if servers:
            print("Managed servers:")
            for name, info in servers.items():
                print(f"  - {name}: {info.get('instructions', '')}")
        else:
            print("No managed servers")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main() 