"""
FastMCP-Factory Configuration Hot Reload Example

This example demonstrates how to use the configuration hot reload feature of ManagedServer

Usage: python -m examples.reload_config_example
"""

import os
import json
import asyncio
import tempfile
from fastmcp_factory import FastMCPFactory

async def main() -> None:
    print("=== FastMCP-Factory Configuration Hot Reload Example ===\n")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = os.path.join(temp_dir, "config.json")
        
        # Create initial configuration
        config = {
            "server": {
                "name": "configurable-server",
                "description": "Server supporting hot reload"
            },
            "settings": {
                "max_tokens": 1000,
                "temperature": 0.7,
                "enabled_tools": ["add", "multiply"]
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"Created configuration file: {config_path}")
        print("Initial configuration content:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # Create server with factory
        factory = FastMCPFactory()
        server = factory.create_managed_server(
            name="config-server",
            instructions="Configuration hot reload example server"
        )
        
        # Register tools
        @server.tool(name="add", description="Calculate the sum of two numbers")
        def add(a: float, b: float) -> float:
            return a + b
        
        @server.tool(name="multiply", description="Calculate the product of two numbers")
        def multiply(a: float, b: float) -> float:
            return a * b
        
        @server.tool(name="divide", description="Calculate the quotient of two numbers")
        def divide(a: float, b: float) -> float:
            if b == 0:
                raise ValueError("Cannot divide by zero")
            return a / b
        
        # Check tools
        tools = await server.get_tools()
        print(f"\nServer has registered {len(tools)} tools")
        print("Currently enabled tools:", ", ".join(config["settings"]["enabled_tools"]))
        
        # Modify configuration
        print("\nModifying configuration file...")
        config["settings"]["enabled_tools"].append("divide")
        config["settings"]["temperature"] = 0.5
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print("Modified configuration content:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # Reload configuration
        print("\nReloading configuration...")
        result = server.reload_config(config_path)
        print(f"Reload result: {result}")
        
        # Check updated tools
        print("\nTool status after reload:")
        print("Enabled tools:", ", ".join(config["settings"]["enabled_tools"]))
        
        print("\n=== Example End ===")

if __name__ == "__main__":
    asyncio.run(main()) 