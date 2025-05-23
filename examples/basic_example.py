#!/usr/bin/env python3
"""
FastMCP-Factory Basic Example

This example demonstrates the basic functionality and configuration hot-reload features of FastMCP-Factory.

Usage: python -m examples.basic_example
"""

import asyncio
import json
import os
import tempfile
import yaml
from typing import Dict, Any

from mcp_factory import FastMCPFactory
from mcp_factory.auth.auth0 import Auth0Provider


async def main() -> None:
    """Example main function"""
    print("=== FastMCP-Factory Basic Example ===\n")
    
    # Create temporary configuration file
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "server_config.yaml")
        
        # Create initial configuration
        config: Dict[str, Any] = {
            "server": {
                "name": "demo-server",
                "instructions": "Basic example server",
                "host": "localhost",
                "port": 8080,
                "debug": True,
            },
            "auth": {
                "issuer_url": "https://example.auth0.com",
                "client_id": "your-client-id",
                "audience": "your-api-audience"
            },
            "tools": {
                "enabled_tools": ["add", "multiply"],
            },
            "advanced": {
                "log_level": "INFO",
            }
        }
        
        # Save configuration to YAML file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        
        print(f"Created configuration file: {config_path}")
        print("Initial configuration content:")
        print(yaml.dump(config, allow_unicode=True))
        
        # Create Auth0 authentication provider (example parameters, provide valid values when actually using)
        auth_provider = Auth0Provider(
            domain="example.auth0.com",
            client_id="your-client-id", 
            client_secret="your-client-secret"
        )
        
        # Create factory instance
        factory = FastMCPFactory()
        
        # Register authentication provider
        factory.create_auth_provider(
            provider_id="demo-auth0",
            provider_type="auth0",
            config={
                "domain": "example.auth0.com",
                "client_id": "your-client-id", 
                "client_secret": "your-client-secret"
            }
        )
        
        # Display authentication providers
        print("\nRegistered authentication providers:")
        for provider_id, provider_type in factory.list_auth_providers().items():
            print(f"  - {provider_id}: {provider_type}")
        
        # Create server from configuration file
        server = factory.create_managed_server(
            config_path=config_path,
            auth_provider_id="demo-auth0",
        )
        
        # Register calculation tools
        @server.tool(name="add", description="Calculate the sum of two numbers")
        def add(a: float, b: float) -> float:
            """Calculate the sum of two numbers"""
            return a + b
        
        @server.tool(name="multiply", description="Calculate the product of two numbers")
        def multiply(a: float, b: float) -> float:
            """Calculate the product of two numbers"""
            return a * b
        
        @server.tool(name="divide", description="Calculate the quotient of two numbers")
        def divide(a: float, b: float) -> float:
            """Calculate the quotient of two numbers"""
            if b == 0:
                raise ValueError("Divisor cannot be zero")
            return a / b
        
        # Get and print tool list
        tools = await server.get_tools()
        print("\nRegistered tools:")
        for tool in tools:
            print(f"  - {tool}")
        
        # Display enabled tools
        enabled_tools = config["tools"]["enabled_tools"]
        print(f"Currently enabled tools: {', '.join(enabled_tools)}")
        
        # Simple tool call demonstration
        print("\nTool call demonstration:")
        print(f"  add(5, 3) = {add(5, 3)}")
        print(f"  multiply(4, 7) = {multiply(4, 7)}")
        
        # Configuration modification demonstration
        print("\nModifying configuration file...")
        tools_config = config["tools"]
        if isinstance(tools_config, dict) and "enabled_tools" in tools_config:
            enabled_tools_list = tools_config["enabled_tools"]
            if isinstance(enabled_tools_list, list):
                enabled_tools_list.append("divide")
        
        advanced_config = config["advanced"]
        if isinstance(advanced_config, dict):
            advanced_config["log_level"] = "DEBUG"
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True)
        
        print("Modified configuration content:")
        print(yaml.dump(config, allow_unicode=True))
        
        # Reload configuration
        print("\nReloading configuration...")
        result = server.reload_config(config_path)
        print(f"Reload result: {result}")
        
        # Check updated tool status
        print("\nTool status after reload:")
        updated_enabled_tools = config["tools"]["enabled_tools"]
        print(f"Enabled tools: {', '.join(updated_enabled_tools)}")
        
        # Server composition demonstration
        print("\nServer composition demonstration:")
        server2 = factory.create_managed_server(
            config_path=config_path,
            name="helper-server",
            instructions="Helper server"
        )
        server.mount("helper", server2)
        print("Helper server mounted: helper")
        
        # List all servers managed by the factory
        servers = factory.list_servers()
        print("\nServers managed by the factory:")
        for srv_name, srv_info in servers.items():
            print(f"  - {srv_name}: {srv_info.get('instructions', '')}")
        
    print("\n=== Example Completed ===")
    print("In a real application, use server.run() to start the server")


if __name__ == "__main__":
    asyncio.run(main()) 