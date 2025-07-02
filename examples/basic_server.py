#!/usr/bin/env python3
"""
MCP-Factory Basic Example

This is the simplest MCP server example, suitable for beginners to get started quickly:
1. Create the most basic MCP server
2. Register simple tool functions
3. Demonstrate basic configuration usage

Run with: python basic_server.py
"""

import asyncio
import logging

from mcp_factory.server import ManagedServer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Basic example main function"""
    print("🚀 MCP-Factory Basic Example")
    print("=" * 50)

    # 1. Create the simplest MCP server
    server = ManagedServer(
        name="basic-example-server",
        instructions="This is a basic example server demonstrating MCP-Factory's basic functionality",
    )

    print(f"✅ Server created successfully: {server.name}")

    # 2. Register basic tools - Math calculator
    @server.tool(name="add", description="Calculate the sum of two numbers")
    def add_numbers(a: float, b: float) -> float:
        """Calculate the sum of two numbers"""
        result = a + b
        logger.info("Calculation: %s + %s = %s", a, b, result)
        return result

    @server.tool(name="multiply", description="Calculate the product of two numbers")
    def multiply_numbers(a: float, b: float) -> float:
        """Calculate the product of two numbers"""
        result = a * b
        logger.info(f"Calculation: {a} × {b} = {result}")
        return result

    @server.tool(name="greet", description="Greet the user")
    def greet_user(name: str, language: str = "english") -> str:
        """Greet the user"""
        greetings = {
            "chinese": f"你好，{name}！欢迎使用 MCP-Factory！",
            "english": f"Hello, {name}! Welcome to MCP-Factory!",
            "spanish": f"¡Hola, {name}! ¡Bienvenido a MCP-Factory!",
        }
        greeting = greetings.get(language.lower(), greetings["english"])
        logger.info(f"Greeting user: {name} ({language})")
        return greeting

    # 3. Demonstrate tool information retrieval
    print("\n📋 Registered tools list:")
    tools = await server.get_tools()
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # 4. Demonstrate tool calls (simulation)
    print("\n🧪 Tool call demonstration:")
    print(f"  add(10, 5) = {add_numbers(10, 5)}")
    print(f"  multiply(3, 7) = {multiply_numbers(3, 7)}")
    print(f"  greet('Alice') = {greet_user('Alice')}")
    print(f"  greet('John', 'english') = {greet_user('John', 'english')}")

    # 5. Server information display
    print("\n📊 Server information:")
    print(f"  Name: {server.name}")
    print(f"  Description: {server.instructions}")
    print(f"  Tool count: {len(tools)}")

    print("\n✨ Basic example demonstration completed!")
    print("💡 Tip: In actual use, call server.run() to start the server")
    print("📖 Next step: Check factory_complete.py to learn about factory pattern")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Example stopped")
    except Exception as e:
        logger.error(f"Example execution error: {e}")
        raise
