#!/usr/bin/env python3
"""FastMCP-Factory Demo Client

This client connects to the demo server, tests tool call functionality and demonstrates the use of management tools.

Usage:
    python examples/demo/client.py         # Standard mode
    python examples/demo/client.py --mgmt  # Management tools detailed mode
"""

import argparse
import asyncio
import json
import logging
import sys
from typing import Any

from fastmcp import Client

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Server configuration
SERVER_URL = "http://localhost:8888/api/mcp"


def print_header(title: str) -> None:
    """Print title header"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_section(title: str) -> None:
    """Print section title"""
    print(f"\n🔹 {title}")
    print("-" * 40)


def format_tool_name(name: str) -> str:
    """Format tool name display"""
    if name.startswith("manage_"):
        return f"🔧 {name}"
    return f"⚡ {name}"


async def test_connection(client: Client) -> bool:
    """Test connection and return whether successful"""
    try:
        tools = await client.get_tools()
        print(f"✅ Connection successful! Found {len(tools)} tools")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Please ensure the server is running at http://localhost:8888")
        return False


async def show_tools_overview(client: Client) -> tuple[list[Any], list[Any]]:
    """Show tools overview and return categorized tool lists"""
    tools = await client.get_tools()

    # Categorize tools
    management_tools = [tool for tool in tools if tool.name.startswith("manage_")]
    normal_tools = [tool for tool in tools if not tool.name.startswith("manage_")]

    print_section("Tool Classification Statistics")
    print(f"💼 Management tools: {len(management_tools)} tools")
    print(f"⚡ Business tools: {len(normal_tools)} tools")
    print(f"📊 Total: {len(tools)} tools")

    return management_tools, normal_tools


async def test_business_tools(client: Client) -> None:
    """Test business tools functionality"""
    print_section("Test Business Tools")

    try:
        # Test addition
        print("🧮 Testing addition tool...")
        result = await client.call_tool("add", {"a": 10, "b": 15})
        print(f"   add(10, 15) = {extract_result(result)}")

        # Test multiplication
        print("🧮 Testing multiplication tool...")
        result = await client.call_tool("multiply", {"a": 6, "b": 7})
        print(f"   multiply(6, 7) = {extract_result(result)}")

        print("✅ Business tools test completed")

    except Exception as e:
        print(f"❌ Business tools test failed: {e}")


async def test_management_tools(client: Client) -> None:
    """Test management tools functionality"""
    print_section("Test Management Tools")

    try:
        # Test configuration reload tool
        print("🔄 Testing configuration reload tool...")
        result = await client.call_tool("manage_reload_config", {})
        reload_result = extract_result(result)
        print(f"   Configuration reload result: {reload_result}")

        print("✅ Management tools test completed")

    except Exception as e:
        print(f"❌ Management tools test failed: {e}")
        print("   Note: Some management tools may require specific parameters or permissions")


async def show_detailed_management_tools(client: Client, tools: list[Any]) -> None:
    """Show detailed management tools information"""
    print_section(f"Detailed Management Tools List ({len(tools)} tools)")

    # Categorize by functionality
    categories = {
        "Server Management": ["get_server_info", "reload_config", "clear_cache"],
        "Tool Management": ["list_tools", "get_tool_info", "toggle_tool"],
        "User Management": ["get_current_user", "set_user_context", "clear_user_context"],
        "Configuration Management": ["get_config", "update_config", "validate_config"],
        "Other Functions": [],
    }

    # Categorize tools
    categorized: dict[str, list[Any]] = {cat: [] for cat in categories}

    for tool in tools:
        tool_name = tool.name.replace("manage_", "")
        categorized_flag = False

        for category, keywords in categories.items():
            if category == "Other Functions":
                continue
            for keyword in keywords:
                if keyword in tool_name:
                    categorized[category].append(tool)
                    categorized_flag = True
                    break
            if categorized_flag:
                break

        if not categorized_flag:
            categorized["Other Functions"].append(tool)

    # Display categorized tools
    for category, tools_in_cat in categorized.items():
        if tools_in_cat:
            print(f"\n📁 {category}:")
            for tool in sorted(tools_in_cat, key=lambda x: x.name):
                desc = tool.description if hasattr(tool, "description") else "No description"
                print(f"   🔧 {tool.name}")
                print(f"      {desc}")


async def run_standard_mode(client: Client) -> None:
    """Run standard test mode"""
    print_header("🚀 FastMCP-Factory Demo Client - Standard Mode")

    # Test connection
    if not await test_connection(client):
        return

    # Show tools overview
    management_tools, normal_tools = await show_tools_overview(client)

    # Test business tools
    if normal_tools:
        await test_business_tools(client)
    else:
        print("\n⚠️  No business tools found")

    # Test management tools
    if management_tools:
        await test_management_tools(client)
    else:
        print("\n⚠️  No management tools found")
        print("   Please check the expose_management_tools setting in server configuration")

    print_section("Test Summary")
    print("✅ Connection status: Normal")
    print(f"📊 Total tools: {len(management_tools) + len(normal_tools)}")
    print(f"💼 Management tools: {len(management_tools)} tools {'✅' if management_tools else '❌'}")
    print(f"⚡ Business tools: {len(normal_tools)} tools {'✅' if normal_tools else '❌'}")


async def run_management_mode(client: Client) -> None:
    """Run management tools detailed mode"""
    print_header("🔧 FastMCP-Factory Demo Client - Management Tools Mode")

    # Test connection
    if not await test_connection(client):
        return

    # Get tools list
    management_tools, normal_tools = await show_tools_overview(client)

    if not management_tools:
        print("\n❌ No management tools found")
        print("   Possible causes:")
        print("   1. expose_management_tools not enabled in server configuration")
        print("   2. FastMCP-Factory factory creation failed")
        print("   3. Error occurred during management tools registration process")
        return

    # Show detailed management tools information
    await show_detailed_management_tools(client, management_tools)

    # Demonstrate key management tools
    print_section("Management Tools Functionality Demo")
    await test_management_tools(client)


def extract_result(result: Any) -> Any:
    """Extract tool call result"""
    if isinstance(result, list) and len(result) > 0:
        # If it's a content list, extract text content
        if hasattr(result[0], "text"):
            content_text = "".join(item.text for item in result)
            try:
                # Try to parse as JSON
                return json.loads(content_text)
            except (json.JSONDecodeError, TypeError, ValueError):
                return content_text
        else:
            return result[0]
    return result


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="FastMCP-Factory Demo Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python examples/demo/client.py         # Standard mode, test basic functionality
    python examples/demo/client.py --mgmt  # Management tools mode, detailed display of management tools
        """,
    )
    parser.add_argument(
        "--mgmt", action="store_true", help="Enable management tools detailed mode (default: standard mode)"
    )
    parser.add_argument("--url", default=SERVER_URL, help=f"Server URL (default: {SERVER_URL})")
    return parser.parse_args()


async def main_async() -> None:
    """Async main function"""
    args = parse_args()

    # Create client
    client = Client(args.url)

    try:
        async with client:
            if args.mgmt:
                await run_management_mode(client)
            else:
                await run_standard_mode(client)

    except KeyboardInterrupt:
        print("\n\n👋 Client stopped")
    except Exception as e:
        print(f"\n❌ Client execution failed: {e}")
        logger.exception("Client exception")
        sys.exit(1)


def main() -> None:
    """Main function"""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()
