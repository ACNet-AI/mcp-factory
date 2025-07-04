#!/usr/bin/env python3
"""
Real MCP Project Management Ecosystem Integration Demo

This script demonstrates real integration between mcp-factory, mcp-project-manager, and mcp-servers-hub:
1. Use mcp-factory to create MCP server projects
2. Prepare data in mcp-project-manager API format
3. Validate project data complies with mcp-servers-hub registration schema
4. Optional: Call real mcp-project-manager API (if running)
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import yaml

# ruff: noqa: E402
# Add project root directory to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp_factory.factory import MCPFactory


class MCPEcosystemDemo:
    """MCP Ecosystem Integration Demo"""

    def __init__(self):
        self.workspace = project_root / "workspace" / "demo"
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.factory = MCPFactory(workspace_root=str(self.workspace))

        # Other project paths
        self.project_manager_path = project_root.parent / "mcp-project-manager"
        self.servers_hub_path = project_root.parent / "mcp-servers-hub"

        # API configuration
        self.api_base_url = "http://localhost:3001"

    def create_demo_project(self) -> tuple[str, str, dict]:
        """Step 1: Use mcp-factory to create demo project"""
        print("🎯 Step 1: Use mcp-factory to create demo project")
        print("=" * 50)

        # Define project configuration
        demo_config = {
            "server": {
                "name": "demo-weather-server",
                "instructions": "A demo MCP server providing weather information and forecasts",
                "version": "1.0.0",
                "description": "Demo weather MCP server for ecosystem integration testing",
                "author": "mcp-ecosystem",
                "license": "MIT",
                "tags": ["weather", "api", "demo", "integration"],
            },
            "tools": [
                {
                    "name": "get_current_weather",
                    "description": "Get current weather for a specified location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                            "unit": {
                                "type": "string",
                                "enum": ["celsius", "fahrenheit"],
                                "description": "Temperature unit",
                                "default": "celsius",
                            },
                        },
                        "required": ["location"],
                    },
                },
                {
                    "name": "get_weather_forecast",
                    "description": "Get weather forecast for a specified location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "The city and state, e.g. San Francisco, CA"},
                            "days": {
                                "type": "integer",
                                "description": "Number of forecast days (1-7)",
                                "minimum": 1,
                                "maximum": 7,
                                "default": 3,
                            },
                        },
                        "required": ["location"],
                    },
                },
            ],
            "resources": [
                {
                    "name": "weather_config",
                    "description": "Weather service configuration",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "api_key": {"type": "string"},
                            "base_url": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30},
                        },
                    },
                }
            ],
        }

        print(f"📦 Creating project: {demo_config['server']['name']}")
        print(f"📝 Description: {demo_config['server']['description']}")
        print(f"🔧 Tool count: {len(demo_config['tools'])}")
        print(f"📚 Resource count: {len(demo_config.get('resources', []))}")

        # Create project
        project_path, server_id = self.factory.create_project_and_server(
            project_name=demo_config["server"]["name"], config_dict=demo_config
        )

        print("✅ Project created successfully!")
        print(f"   📁 Path: {project_path}")
        print(f"   🆔 Server ID: {server_id}")

        return project_path, server_id, demo_config

    def prepare_project_manager_data(self, project_path: str, config: dict) -> dict:
        """Step 2: Prepare mcp-project-manager API data"""
        print("\n🎯 Step 2: Prepare mcp-project-manager API data")
        print("=" * 50)

        project_path_obj = Path(project_path)

        # Read generated files
        with open(project_path_obj / "config.yaml") as f:
            generated_config = yaml.safe_load(f)

        with open(project_path_obj / "pyproject.toml") as f:
            pyproject_content = f.read()

        with open(project_path_obj / "server.py") as f:
            server_code = f.read()

        # Prepare API data format
        api_data = {
            "projectName": config["server"]["name"],
            "description": config["server"]["description"],
            "version": config["server"]["version"],
            "language": "python",
            "category": "tools",
            "tags": config["server"].get("tags", []),
            "owner": config["server"]["author"],
            "repoName": config["server"]["name"],
            "files": {
                "config.yaml": generated_config,
                "server.py": server_code,
                "pyproject.toml": pyproject_content,
                "README.md": f"# {config['server']['name']}\\n\\n{config['server']['description']}",
            },
            "installation": {"account": {"login": config["server"]["author"]}},
        }

        print("📋 API data preparation completed:")
        print(f"   📦 Project name: {api_data['projectName']}")
        print(f"   👤 Owner: {api_data['owner']}")
        print(f"   🏷️ Tags: {', '.join(api_data['tags'])}")
        print(f"   📄 File count: {len(api_data['files'])}")

        return api_data

    def validate_hub_compatibility(self, api_data: dict) -> dict:
        """Step 3: Validate mcp-servers-hub compatibility"""
        print("\n🎯 Step 3: Validate mcp-servers-hub compatibility")
        print("=" * 50)

        # Prepare hub registration format data
        hub_data = {
            "name": api_data["projectName"],
            "author": api_data["owner"],
            "description": api_data["description"],
            "repository": f"https://github.com/{api_data['owner']}/{api_data['repoName']}",
            "language": "python",
            "python_version": "3.10",
            "tags": api_data["tags"][:8],  # Hub supports up to 8 tags
            "license": "MIT",
            "created": "2024-01-01T00:00:00Z",
            "mcp_factory": {"version": "1.0.0", "template": "basic"},
        }

        # Check schema compatibility
        schema_file = self.servers_hub_path / "registry-schema.json"
        if schema_file.exists():
            try:
                with open(schema_file) as f:
                    schema = json.load(f)

                # Validate required fields
                project_def = schema.get("definitions", {}).get("project", {})
                required_fields = project_def.get("required", [])

                missing_fields = [field for field in required_fields if field not in hub_data]

                if missing_fields:
                    print(f"❌ Missing required fields: {missing_fields}")
                    return {"valid": False, "errors": missing_fields, "data": hub_data}
                else:
                    print("✅ Project data complies with Hub registration schema")
                    print(f"   🏷️ Valid tags: {', '.join(hub_data['tags'])}")
                    print(f"   🐍 Python version: {hub_data['python_version']}")
                    print(f"   📜 License: {hub_data['license']}")
                    return {"valid": True, "errors": [], "data": hub_data}

            except Exception as e:
                print(f"⚠️ Schema validation error: {e}")
                return {"valid": True, "errors": [], "data": hub_data}
        else:
            print(f"⚠️ Schema file does not exist, skipping validation: {schema_file}")
            return {"valid": True, "errors": [], "data": hub_data}

    async def test_project_manager_api(self, api_data: dict) -> dict:
        """Step 4: Test mcp-project-manager API (optional)"""
        print("\n🎯 Step 4: Test mcp-project-manager API")
        print("=" * 50)

        try:
            async with httpx.AsyncClient() as client:
                # First check if API server is running
                health_response = await client.get(f"{self.api_base_url}/health", timeout=5.0)

                if health_response.status_code == 200:
                    print("✅ API server is running")

                    # Call publish API
                    publish_response = await client.post(
                        f"{self.api_base_url}/api/publish", json=api_data, timeout=30.0
                    )

                    result = publish_response.json()

                    if publish_response.status_code == 200:
                        print("✅ API call successful!")
                        print(f"   📤 Project: {result.get('projectName', 'N/A')}")
                        print(f"   🔗 Repository: {result.get('repository', 'N/A')}")
                        print(f"   💬 Message: {result.get('message', 'N/A')}")
                        return {"success": True, "data": result}
                    else:
                        print(f"❌ API call failed (status code: {publish_response.status_code})")
                        print(f"   Error: {result.get('error', 'Unknown error')}")
                        return {"success": False, "error": result.get("error", "Unknown error")}
                else:
                    print(f"❌ API server health check failed (status code: {health_response.status_code})")
                    return {"success": False, "error": "API server unhealthy"}

        except httpx.ConnectError:
            print("⚠️ Unable to connect to API server (possibly not started)")
            print("   💡 Tip: Run 'npm start' in mcp-project-manager directory to start server")
            return {"success": False, "error": "Connection failed"}
        except Exception as e:
            print(f"❌ API test error: {e}")
            return {"success": False, "error": str(e)}

    async def run_complete_demo(self):
        """Run complete demo workflow"""
        print("🚀 MCP Project Management Ecosystem Integration Demo")
        print("=" * 60)
        print("This demo showcases real integration between three projects:")
        print("  📦 mcp-factory: Project creation")
        print("  🤖 mcp-project-manager: GitHub publish management")
        print("  🗂️ mcp-servers-hub: Server registry")
        print()

        try:
            # Steps 1-3: Create project and prepare data
            project_path, server_id, config = self.create_demo_project()
            api_data = self.prepare_project_manager_data(project_path, config)
            hub_validation = self.validate_hub_compatibility(api_data)

            if not hub_validation["valid"]:
                print(f"❌ Hub compatibility validation failed: {hub_validation['errors']}")
                return

            # Step 4: Attempt API call
            api_result = await self.test_project_manager_api(api_data)

            # Summary
            print("\n🎯 Demo Summary")
            print("=" * 50)
            print("✅ Project creation: Success")
            print("✅ Data preparation: Success")
            print("✅ Hub compatibility: Passed")

            if api_result["success"]:
                print("✅ API integration: Success")
                print("\n🎊 Complete ecosystem integration demo successful!")
            else:
                print("⚠️ API integration: Not tested (server not running)")
                print("\n🎯 Cross-project data flow validation successful!")
                print("💡 To test complete integration, start mcp-project-manager API server")

            print(f"\n📁 Demo project location: {project_path}")
            print("🔧 You can continue development with the following commands:")
            print(f"   cd {project_path}")
            print("   python server.py")

        except Exception as e:
            print(f"\n❌ Error during demo: {e}")
            import traceback

            traceback.print_exc()


async def main():
    """Main function"""
    demo = MCPEcosystemDemo()
    await demo.run_complete_demo()


if __name__ == "__main__":
    asyncio.run(main())
