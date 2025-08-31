#!/usr/bin/env python3
"""Multi-Adapter System Demo

Demonstrates how to convert different types of existing systems (Python classes, HTTP APIs, CLI commands)
into MCP tools using the new unified multi-adapter architecture.
"""

from pathlib import Path

from mcp_factory.adapters import adapt


def demo_python_class_adapter():
    """Demonstrate Python class adaptation"""
    print("🐍 Python Class Adaptation Demo")
    print("=" * 50)

    # Create multi-source adapter
    adapter = adapt.multi()

    # Add Python class source - adapt mcp_factory.MCPFactory
    adapter.add_source(
        source_path="mcp_factory.MCPFactory",
        adapter_type="python_class",
        config={
            "instance_creation": "MCPFactory('./workspace')",
            "include_methods": ["create_server", "build_project", "list_servers"],
        },
    )

    # Discover capabilities
    capabilities = adapter.discover_all_capabilities()
    print(f"Discovered Python methods: {len(capabilities.get('python_class', []))}")

    for cap in capabilities.get("python_class", [])[:3]:
        print(f"  - {cap['name']}: {cap['description']}")

    return adapter


def demo_http_api_adapter():
    """Demonstrate HTTP API adaptation"""
    print("\n🌐 HTTP API Adaptation Demo")
    print("=" * 50)

    adapter = adapt.multi()

    # Add HTTP API source - Example FastAPI service
    adapter.add_source(
        source_type="http_api",
        source_path="https://httpbin.org",  # Public test API
        config={
            "endpoints": [
                {
                    "name": "get_user_agent",
                    "method": "GET",
                    "path": "/user-agent",
                    "description": "Get user agent information",
                },
                {
                    "name": "post_data",
                    "method": "POST",
                    "path": "/post",
                    "parameters": [
                        {"name": "data", "type": "string", "required": True, "location": "body"},
                        {"name": "format", "type": "string", "required": False, "location": "query"},
                    ],
                    "description": "Send POST data",
                },
            ]
        },
    )

    # Discover capabilities
    capabilities = adapter.discover_all_capabilities()
    print(f"Discovered HTTP endpoints: {len(capabilities.get('http_api', []))}")

    for cap in capabilities.get("http_api", []):
        print(f"  - {cap['name']}: {cap['description']}")

    return adapter


def demo_cli_adapter():
    """Demonstrate CLI command adaptation"""
    print("\n💻 CLI Command Adaptation Demo")
    print("=" * 50)

    adapter = adapt.multi()

    # Add CLI command source
    adapter.add_source(
        source_type="cli",
        source_path="system_commands",
        config={
            "commands": [
                {
                    "name": "list_files",
                    "command": "ls",
                    "arguments": [
                        {"name": "path", "type": "string", "required": True, "description": "Directory path"},
                        {
                            "name": "all",
                            "type": "boolean",
                            "required": False,
                            "flag": "-a",
                            "description": "Show hidden files",
                        },
                    ],
                    "description": "List directory files",
                },
                {
                    "name": "disk_usage",
                    "command": "du",
                    "arguments": [
                        {"name": "path", "type": "string", "required": True, "description": "Check path"},
                        {
                            "name": "human_readable",
                            "type": "boolean",
                            "required": False,
                            "flag": "-h",
                            "description": "Human readable format",
                        },
                    ],
                    "description": "Check disk usage",
                },
            ]
        },
    )

    # Discover capabilities
    capabilities = adapter.discover_all_capabilities()
    print(f"Discovered CLI commands: {len(capabilities.get('cli', []))}")

    for cap in capabilities.get("cli", []):
        print(f"  - {cap['name']}: {cap['description']}")

    return adapter


def demo_mixed_sources():
    """Demonstrate mixed source adaptation"""
    print("\n🔄 Mixed Source Adaptation Demo")
    print("=" * 50)

    # Create an adapter containing multiple sources
    adapter = adapt.multi()

    # 1. Python class source
    adapter.add_source(
        source_type="python_class",
        source_path="mcp_factory.MCPFactory",
        config={"methods_filter": ["create_server", "list_servers"]},
    )

    # 2. HTTP API source
    adapter.add_source(
        source_type="http_api",
        source_path="https://api.github.com",
        config={
            "endpoints": [
                {
                    "name": "get_user",
                    "method": "GET",
                    "path": "/users/{username}",
                    "parameters": [{"name": "username", "type": "string", "required": True, "location": "path"}],
                    "description": "Get GitHub user information",
                }
            ]
        },
    )

    # 3. CLI command source
    adapter.add_source(
        source_type="cli",
        source_path="git_commands",
        config={
            "commands": [
                {
                    "name": "git_status",
                    "command": "git",
                    "arguments": [
                        {"name": "command", "type": "string", "required": True, "description": "Git command"}
                    ],
                    "description": "Execute Git command",
                }
            ]
        },
    )

    # Discover all capabilities
    all_capabilities = adapter.discover_all_capabilities()

    print("Summary of capabilities discovered from mixed sources:")
    for source_type, capabilities in all_capabilities.items():
        print(f"  {source_type}: {len(capabilities)} capabilities")
        for cap in capabilities[:2]:  # Only show first 2
            print(f"    - {cap['name']}")

    return adapter, all_capabilities


def demo_generate_mcp_tools():
    """Demonstrate Generate MCP tools"""
    print("\n🛠️ Generate MCP Tools Demo")
    print("=" * 50)

    # Get mixed source adapter
    adapter, all_capabilities = demo_mixed_sources()

    # Create temporary project directory
    project_path = "./demo_mcp_server"
    Path(project_path).mkdir(exist_ok=True)

    # Select capabilities to generate
    selected_capabilities = []
    for capabilities in all_capabilities.values():
        selected_capabilities.extend(capabilities[:1])  # Select 1 of each type

    print(f"\nPreparing to generate {len(selected_capabilities)} MCP tools:")
    for cap in selected_capabilities:
        print(f"  - {cap['name']} ({cap['type']})")

    # Generate tool files
    generated_files = adapter.generate_tools_for_project(
        project_path=project_path, selected_capabilities=selected_capabilities
    )

    print(f"\n✅ Successfully generated {len(generated_files)} tool files:")
    for file_path in generated_files:
        print(f"  📄 {file_path}")

        # Show generated code preview
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")
            print("     Preview (first 10 lines):")
            for i, line in enumerate(lines[:10]):
                print(f"       {i + 1:2d}: {line}")
            if len(lines) > 10:
                print(f"       ... ({len(lines) - 10} more lines)")
        print()


def demo_connectivity_test():
    """Demonstrate connectivity testing"""
    print("\n🔌 Connectivity Testing Demo")
    print("=" * 50)

    adapter = adapt.multi()

    # Add various sources for testing
    test_sources = [
        ("python_class", "mcp_factory.MCPFactory", {}),
        ("http_api", "https://httpbin.org", {}),
        ("http_api", "https://invalid-domain-12345.com", {}),  # Intentionally failing example
        ("cli", "test_commands", {"commands": [{"name": "test", "command": "echo"}]}),
    ]

    for source_type, source_path, config in test_sources:
        adapter.add_source(source_type, source_path, config)

    # Test all connections
    results = adapter.test_all_connections()

    print("Connectivity test results:")
    for source_id, is_connected in results.items():
        status = "✅ Connection successful" if is_connected else "❌ Connection failed"
        print(f"  {source_id}: {status}")


def main():
    """Main demo function"""
    print("🚀 Multi-source Adapter System Complete Demonstration")
    print("=" * 80)

    try:
        # 1. Demonstrate individual adapters
        demo_python_class_adapter()
        demo_http_api_adapter()
        demo_cli_adapter()

        # 2. Mixed source demonstration
        demo_mixed_sources()

        # 3. Generate tools demonstration
        demo_generate_mcp_tools()

        # 4. Connectivity testing
        demo_connectivity_test()

        print("\n🎉 Demo completed!")
        print("\n💡 Usage instructions:")
        print("1. MultiSourceAdapter Supports unified adaptation of Python classes, HTTP APIs, CLI commands")
        print("2. Automatically discover system capabilities and generate corresponding MCP tools")
        print("3. Supports mixed sources, one project can contain multiple types of tools")
        print("4. Provides connectivity testing to ensure source systems are available")

    except Exception as e:
        print(f"❌ Error occurred during demonstration: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
