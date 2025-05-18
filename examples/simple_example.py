"""
FastMCP-Factory Simple Example

This example demonstrates the basic functionality and usage of FastMCP-Factory

Usage: python -m examples.simple_example
"""

import asyncio
from typing import Dict, Any

from fastmcp_factory import FastMCPFactory
from fastmcp_factory.auth.auth0 import Auth0Provider


async def main() -> None:
    """Main function"""
    print("=== FastMCP-Factory Simple Example ===\n")
    
    # Create Auth0 authentication provider (provide valid parameters in production)
    auth_provider = Auth0Provider(
        domain="example.auth0.com",
        client_id="your-client-id", 
        client_secret="your-client-secret"
    )
    
    # Create factory instance
    factory = FastMCPFactory(auth_server_provider=auth_provider)
    
    # Create manageable server
    server = factory.create_managed_server(
        name="demo-server",
        instructions="Example server",
        auto_register=True,
        auth={"issuer_url": "https://example.auth0.com"}
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
    
    # Register data processing tools
    @server.tool(name="process_data", description="Process JSON data")
    def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Process input JSON data
        
        Args:
            data: Input JSON data
            
        Returns:
            Dict[str, Any]: Processed JSON data
        """
        result = {
            "processed": True,
            "original": data,
            "count": len(data) if isinstance(data, dict) else 0
        }
        return result
    
    # Get and print tool list
    tools = await server.get_tools()
    print("Registered tools:")
    for tool in tools:
        print(f"  - {tool}")
    
    # Simple tool call demonstration
    print("\nTool call demonstration:")
    print(f"  add(5, 3) = {add(5, 3)}")
    print(f"  multiply(4, 7) = {multiply(4, 7)}")
    
    data_result = process_data({"name": "Example", "value": 42})
    print(f"  process_data result: {data_result}")
    
    # Create second server
    server2 = factory.create_managed_server(
        name="helper-server",
        instructions="Helper server"
    )
    
    # Server composition demonstration
    print("\nServer composition demonstration:")
    await server.mount("helper", server2)
    print(f"  Mounted server: helper")
    
    # List all servers managed by factory
    servers = factory.list_servers()
    print("\nServers managed by factory:")
    for srv_name in servers:
        print(f"  - {srv_name}")
    
    print("\n=== Example End ===")
    print("In a real application, use server.run() to start the server")

if __name__ == "__main__":
    asyncio.run(main()) 