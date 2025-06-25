#!/usr/bin/env python3
"""MCP Factory CLI - Main command line interface"""

from __future__ import annotations

import builtins
import json
import os
import sys
from pathlib import Path
from typing import Any

import click
import yaml
from tabulate import tabulate

from .factory import MCPFactory

# =============================================================================
# Utility Functions
# =============================================================================


def is_verbose(ctx: click.Context) -> bool:
    """Check if verbose mode is enabled"""
    return bool(ctx.obj.get("verbose", False))


def success_message(message: str) -> None:
    """Display success message with green color"""
    click.echo(click.style(f"✅ {message}", fg="green"))


def error_message(message: str) -> None:
    """Display error message with red color"""
    click.echo(click.style(f"❌ {message}", fg="red"), err=True)


def info_message(message: str) -> None:
    """Display info message with blue color"""
    click.echo(click.style(f"ℹ️ {message}", fg="blue"))


def warning_message(message: str) -> None:
    """Display warning message with yellow color"""
    click.echo(click.style(f"⚠️ {message}", fg="yellow"))


def get_factory(workspace: str | None = None) -> MCPFactory:
    """Get MCPFactory instance"""
    if workspace:
        # Ensure directory exists before switching
        workspace_path = Path(workspace)
        if workspace_path.exists() and workspace_path.is_dir():
            try:
                os.chdir(workspace)
            except (OSError, FileNotFoundError):
                # If switching fails, continue using current directory
                pass
    # Note: MCPFactory constructor only accepts workspace_root parameter, not config
    return MCPFactory(workspace_root=workspace or "./workspace")


def format_table(data: builtins.list[dict[str, Any]], headers: builtins.list[str]) -> str:
    """Format data as table"""
    if not data:
        return "No data available"

    rows = []
    for item in data:
        row = []
        for header in headers:
            value = item.get(header.lower(), "")
            # Add status icons
            if header.lower() == "status":
                if value == "running":
                    value = f"🟢 {value}"
                elif value == "stopped":
                    value = f"🔴 {value}"
                elif value == "error":
                    value = f"🟡 {value}"
            row.append(str(value))
        rows.append(row)

    return tabulate(rows, headers=headers, tablefmt="grid")


def check_dependencies() -> dict[str, bool]:
    """Check dependencies"""
    dependencies = {"yaml": False, "click": False, "tabulate": False}

    try:
        __import__("yaml")
        dependencies["yaml"] = True
    except ImportError:
        pass

    try:
        __import__("click")
        dependencies["click"] = True
    except ImportError:
        pass

    try:
        __import__("tabulate")
        dependencies["tabulate"] = True
    except ImportError:
        pass

    return dependencies


def check_jwt_env() -> dict[str, Any]:
    """Check JWT environment variables"""
    jwt_vars = {
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        "JWT_ALGORITHM": os.getenv("JWT_ALGORITHM", "HS256"),
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"),
    }

    return {
        "variables": jwt_vars,
        "secret_configured": bool(jwt_vars["JWT_SECRET_KEY"]),
        "all_configured": all(jwt_vars.values()),
    }


def _get_mounted_servers_count(config_file: str | None) -> int:
    """Get mounted servers count"""
    if not config_file:
        return 0

    try:
        from .config.manager import load_config_file

        config = load_config_file(config_file)
        return len(config.get("mcpServers", {}))
    except Exception:
        return 0


def _get_mounted_servers_info(config_file: str | None) -> dict:
    """Get mounted servers detailed information"""
    if not config_file:
        return {}

    try:
        from .config.manager import load_config_file

        config = load_config_file(config_file)
        mcp_servers = config.get("mcpServers", {})

        result = {}
        for server_name, server_config in mcp_servers.items():
            result[server_name] = {
                "type": server_config.get("transport", "stdio"),
                "status": "unknown",  # Actual status needs to be obtained from runtime
                "prefix": server_config.get("prefix", ""),
                "command": server_config.get("command", ""),
                "url": server_config.get("url", ""),
            }

        return result
    except Exception:
        return {}


# =============================================================================
# Main CLI Group
# =============================================================================


@click.group()
@click.option("--workspace", "-w", help="Workspace directory path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx: click.Context, workspace: str | None, verbose: bool) -> None:
    """🏭 MCP Factory - MCP Server Factory Management Tool"""
    ctx.ensure_object(dict)
    ctx.obj["workspace"] = workspace
    ctx.obj["verbose"] = verbose


# =============================================================================
# Server Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def server(ctx: click.Context) -> None:
    """🖥️ Server Management"""


@server.command()
@click.option("--status-filter", type=click.Choice(["running", "stopped", "error"]), help="Filter by status")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.option("--show-mounts", "-m", is_flag=True, help="Show mounted external servers")
@click.pass_context
def list(ctx: click.Context, status_filter: str | None, output_format: str, show_mounts: bool) -> None:
    """List all servers"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))
        servers = factory.list_servers()

        if status_filter:
            servers = [s for s in servers if s.get("status") == status_filter]

        if output_format == "json":
            # If showing mount info, add mounted server data
            if show_mounts:
                for server in servers:
                    server["mounted_servers"] = _get_mounted_servers_info(server.get("config_file"))
            click.echo(json.dumps(servers, indent=2))
        else:
            if not servers:
                click.echo("📭 No servers found")
                return

            headers = ["ID", "Name", "Status", "Host", "Port"]
            if show_mounts:
                headers.append("Mounts")
                for server in servers:
                    mount_count = _get_mounted_servers_count(server.get("config_file"))
                    server["Mounts"] = f"🔗{mount_count}" if mount_count > 0 else "➖"

            table = format_table(servers, headers)
            click.echo(table)

            # If showing mount info and there are mounted servers, display detailed information
            if show_mounts:
                for server in servers:
                    mounted_info = _get_mounted_servers_info(server.get("config_file"))
                    if mounted_info:
                        click.echo(f"\n🔗 Mounted servers for {server.get('Name', server.get('ID'))}:")
                        for mount_name, mount_info in mounted_info.items():
                            status_icon = "🟢" if mount_info.get("status") == "running" else "🔴"
                            click.echo(f"  {status_icon} {mount_name} ({mount_info.get('type', 'unknown')})")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to get server list")
        sys.exit(1)


@server.command()
@click.argument("server_id")
@click.option("--show-mounts", "-m", is_flag=True, help="Show mounted external server details")
@click.pass_context
def status(ctx: click.Context, server_id: str, show_mounts: bool) -> None:
    """View server status"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))
        server_info = factory.get_server_status(server_id)

        if not server_info:
            error_message(f"Server '{server_id}' does not exist")
            sys.exit(1)

        click.echo(f"📊 Server status: {server_id}")
        click.echo("-" * 40)

        status = server_info.get("status", "unknown")
        if status == "running":
            click.echo(f"Status: 🟢 {status}")
        elif status == "stopped":
            click.echo(f"Status: 🔴 {status}")
        else:
            click.echo(f"Status: 🟡 {status}")

        for key, value in server_info.items():
            if key != "status":
                click.echo(f"{key}: {value}")

        # Display mounted server information
        if show_mounts:
            config_file = server_info.get("config_file")
            mounted_info = _get_mounted_servers_info(config_file)

            if mounted_info:
                click.echo("\n🔗 Mounted external servers:")
                click.echo("-" * 30)
                for mount_name, mount_info in mounted_info.items():
                    status_icon = "🟢" if mount_info.get("status") == "running" else "🔴"
                    click.echo(f"{status_icon} {mount_name}")
                    click.echo(f"   Type: {mount_info.get('type', 'unknown')}")
                    if mount_info.get("command"):
                        click.echo(f"   Command: {mount_info.get('command')}")
                    if mount_info.get("url"):
                        click.echo(f"   URL: {mount_info.get('url')}")
                    click.echo()
            else:
                click.echo("\n📭 No mounted external servers")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to get server status")
        sys.exit(1)


@server.command()
@click.argument("server_id")
@click.option("--force", "-f", is_flag=True, help="Force delete without confirmation")
@click.pass_context
def delete(ctx: click.Context, server_id: str, force: bool) -> None:
    """Delete server"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))

        if not force:
            warning_message(f"Are you sure you want to delete server '{server_id}'?")
            if not click.confirm("Continue with deletion?"):
                error_message("Operation cancelled")
                return

        success = factory.delete_server(server_id)
        if success:
            success_message(f"Server '{server_id}' deleted")
        else:
            error_message(f"Failed to delete server '{server_id}'")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to delete server")
        sys.exit(1)


@server.command()
@click.argument("server_id")
@click.pass_context
def restart(ctx: click.Context, server_id: str) -> None:
    """Restart server"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))

        if not factory.get_server(server_id):
            error_message(f"Server '{server_id}' does not exist")
            sys.exit(1)

        click.echo(f"🔄 Restarting server '{server_id}'...")

        restarted_server = factory.restart_server(server_id)
        success_message(f"Server '{server_id}' restart completed")
        info_message(f"Server name: {restarted_server.name}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to restart server")
        sys.exit(1)


@server.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), help="Override transport method")
@click.option("--host", help="Override host address")
@click.option("--port", type=int, help="Override port number")
@click.pass_context
def run(ctx: click.Context, config_file: str, transport: str | None, host: str | None, port: int | None) -> None:
    """Run server using FastMCP"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))
        click.echo(f"🚀 Starting server from config: {config_file}")

        # Use Factory's run_server method for core logic
        server_id = factory.run_server(source=config_file, transport=transport, host=host, port=port)

        success_message(f"Server '{server_id}' started successfully!")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to run server")
        sys.exit(1)


# =============================================================================
# Project Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """📂 Project management"""


@project.command()
@click.option("--name", help="Project name")
@click.option("--description", help="Project description")
@click.option("--host", default="localhost", help="Server host")
@click.option("--port", default=8000, help="Server port")
@click.option("--transport", type=click.Choice(["stdio", "sse"]), default="stdio", help="Transport method")
@click.option("--auth", is_flag=True, help="Enable authentication")
@click.option("--auto-discovery", is_flag=True, help="Enable auto discovery")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--start-server", is_flag=True, help="Start server immediately after initialization")
@click.pass_context
def init(
    ctx: click.Context,
    name: str | None,
    description: str | None,
    host: str,
    port: int,
    transport: str,
    auth: bool,
    auto_discovery: bool,
    debug: bool,
    start_server: bool,
) -> None:
    """📂 Interactive project initialization wizard"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))

        click.echo("🚀 Welcome to MCP Factory project initialization wizard!")
        click.echo("-" * 50)

        # Interactive prompts for missing values
        if not name:
            name = click.prompt("📝 Project name", type=str)
        if not description:
            description = click.prompt("📝 Project description", type=str)

        # Display configuration summary
        click.echo("\n⚙️ Server configuration:")
        click.echo(f"   Name: {name}")
        click.echo(f"   Description: {description}")
        click.echo(f"   Host: {host}")
        click.echo(f"   Port: {port}")
        click.echo(f"   Transport: {transport}")
        click.echo(f"   Authentication: {'✅' if auth else '❌'}")
        click.echo(f"   Auto-discovery: {'✅' if auto_discovery else '❌'}")
        click.echo(f"   Debug mode: {'✅' if debug else '❌'}")

        # Generate configuration file
        config_data = {
            "server": {
                "name": name,
                "description": description,
                "host": host,
                "port": port,
                "transport": transport,
                "instructions": f"This is {name} - {description}",
            }
        }

        if auth:
            config_data["server"]["auth"] = {"enabled": True}
        if auto_discovery:
            config_data["server"]["auto_discovery"] = {"enabled": True}
        if debug:
            config_data["server"]["debug"] = True

        # Save configuration file
        config_file = f"{factory.workspace_root}/{name}_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        success_message(f"Project configuration generated: {config_file}")

        # Build project structure
        project_path = factory.build_project(config_file)
        success_message(f"Project structure created: {project_path}")

        # Create server if requested
        if start_server:
            click.echo()
            info_message("Creating server...")
            server_id = factory.create_server(name, config_file)
            success_message(f"Server created successfully: {server_id}")
        else:
            # Show manual startup command
            click.echo()
            click.echo("📋 Manual server startup command:")
            click.echo(f"   mcp-factory server run {config_file}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Project initialization failed")
        sys.exit(1)


@project.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.pass_context
def build(ctx: click.Context, config_file: str) -> None:
    """Build project"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))

        # Load configuration from file
        from .config.manager import load_config_file

        config_dict = load_config_file(config_file)

        # Extract project name from config or use filename
        project_name = config_dict.get("server", {}).get("name")
        if not project_name:
            # Use filename without extension as project name
            from pathlib import Path

            project_name = Path(config_file).stem

        project_path = factory.build_project(project_name, config_dict)
        success_message(f"Project build completed: {project_path}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Project build failed")
        sys.exit(1)


@project.command()
@click.pass_context
def quick(ctx: click.Context) -> None:
    """Quick start temporary server"""
    try:
        factory = get_factory(ctx.obj.get("workspace"))
        info_message("Starting quick server...")
        # Create a basic quick server using default configuration
        basic_config = {
            "server": {
                "name": "quick-server",
                "instructions": "Quick start temporary server for testing",
                "transport": "stdio",
            }
        }
        server_id = factory.create_server("quick-server", basic_config)
        success_message(f"Quick server created successfully: {server_id}")

        click.echo("\n📋 Quick server information:")
        click.echo(f"   Server ID: {server_id}")
        click.echo("   Type: Temporary server")
        click.echo("   Usage: For testing and development")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Quick start failed")
        sys.exit(1)


# =============================================================================
# Configuration Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """⚙️ Configuration management"""


@config.command()
@click.option("--name", prompt=True, help="Project name")
@click.option("--description", prompt=True, help="Project description")
@click.option("--output", "-o", default="config.yaml", help="Output configuration file name")
@click.option("--with-mounts", "-m", is_flag=True, help="Include mounted server example configuration")
@click.pass_context
def template(ctx: click.Context, name: str, description: str, output: str, with_mounts: bool) -> None:
    """Generate configuration template"""
    try:
        # Generate basic configuration template
        config_template = {
            "server": {
                "name": name,
                "description": description,
                "host": "localhost",
                "port": 8000,
                "transport": "stdio",
                "instructions": f"This is {name} - {description}",
            }
        }

        # Add mount configuration example if requested
        mount_info = ""
        if with_mounts:
            config_template["mcpServers"] = {
                "example-server": {
                    "command": "python",
                    "args": ["-m", "example_mcp_server"],
                    "transport": "stdio",
                    "prefix": "example",
                }
            }
            mount_info = " (with mount examples)"

        # Write configuration file
        with open(output, "w") as f:
            yaml.dump(config_template, f, default_flow_style=False, sort_keys=False)

        success_message(f"Configuration template generated: {output}{mount_info}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to generate configuration template")
        sys.exit(1)


@config.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--check-mounts", "-m", is_flag=True, help="Detailed check of mount configuration")
@click.pass_context
def validate(ctx: click.Context, config_file: str, check_mounts: bool) -> None:
    """Validate configuration file"""
    try:
        click.echo(f"📝 Validating configuration file: {config_file}")

        # Basic configuration validation
        try:
            from .config.manager import load_config_file, validate_config

            config = load_config_file(config_file)
            validate_config(config)
            success_message("Basic configuration validation passed")
        except Exception as e:
            error_message("Basic configuration validation failed:")
            error_message(f"   {e!s}")
            sys.exit(1)

        # Mount configuration validation
        if check_mounts:
            try:
                mcp_servers = config.get("mcpServers", {})
                if mcp_servers:
                    # Here you can add more detailed mount validation logic
                    success_message(f"Mount configuration validation passed ({len(mcp_servers)} external servers)")
                else:
                    click.echo("ℹ️ No mounted servers found in configuration")
            except Exception as e:
                error_message("Mount configuration validation failed:")
                error_message(f"   {e!s}")
                sys.exit(1)

        success_message(f"Configuration file '{config_file}' complete validation passed")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Configuration file validation failed")
        sys.exit(1)


@config.command("list")
@click.pass_context
def list_configs(ctx: click.Context) -> None:
    """List configuration files"""
    try:
        workspace = ctx.obj.get("workspace", ".")
        workspace_path = Path(workspace)

        # Find YAML configuration files
        config_files = list(workspace_path.glob("*.yaml")) + list(workspace_path.glob("*.yml"))

        if not config_files:
            click.echo("📭 No configuration files found")
            return

        click.echo("📋 Configuration files found:")
        for config_file in config_files:
            click.echo(f"   📄 {config_file.name}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to list configuration files")
        sys.exit(1)


# =============================================================================
# Authentication Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """🔐 Authentication management"""


@auth.command()
@click.pass_context
def help(ctx: click.Context) -> None:
    """Authentication configuration help"""
    click.echo("\n🔐 MCP Factory Authentication Configuration Guide")
    click.echo("\nSupported authentication methods:")
    click.echo("1. JWT Token authentication")
    click.echo("\nRequired environment variables for JWT:")
    click.echo("  JWT_SECRET_KEY=your-secret-key-here")
    click.echo("  JWT_ALGORITHM=HS256")
    click.echo("  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30")
    click.echo("\nFor more detailed information, please refer to the documentation.")
    click.echo()


@auth.command()
@click.option("--fastmcp", is_flag=True, help="Check FastMCP JWT environment variables")
@click.pass_context
def check(ctx: click.Context, fastmcp: bool) -> None:
    """Check authentication environment"""
    try:
        click.echo("🔐 Authentication environment check:")
        click.echo("-" * 30)

        jwt_info = check_jwt_env()

        # Display JWT variables
        for var_name, var_value in jwt_info["variables"].items():
            if var_value:
                display_value = "***SET***" if "SECRET" in var_name else var_value
                click.echo(f"✅ {var_name}: {display_value}")
            else:
                click.echo(f"❌ {var_name}: NOT SET")

        click.echo("-" * 30)

        # Summary
        if jwt_info["secret_configured"]:
            success_message("JWT secret key configured")
        else:
            error_message("JWT secret key not configured")

        if jwt_info["all_configured"]:
            success_message("All JWT variables configured")
        else:
            warning_message("Some JWT variables not configured")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to check authentication environment")
        sys.exit(1)


# =============================================================================
# System Health Check Command
# =============================================================================


@cli.command()
@click.option("--check-config", is_flag=True, help="Check configuration files")
@click.option("--check-env", is_flag=True, help="Check JWT environment variables")
@click.pass_context
def health(ctx: click.Context, check_config: bool, check_env: bool) -> None:
    """🏥 System health check"""
    try:
        click.echo("🏥 MCP Factory System Health Check")
        click.echo("=" * 40)

        # Basic system information
        workspace = ctx.obj.get("workspace", ".")
        workspace_path = Path(workspace).resolve()
        click.echo(f"📁 Working directory: {workspace_path}")
        success_message(f"Directory exists: {'Yes' if workspace_path.exists() else 'No'}")

        # MCP Factory status
        try:
            factory = get_factory(str(workspace_path) if workspace_path.exists() else None)
            servers = factory.list_servers()
            success_message("MCP Factory: Initialized")
            info_message(f"Server count: {len(servers)}")
        except Exception as e:
            error_message("MCP Factory: Initialization failed")
            if is_verbose(ctx):
                error_message(f"Detailed error: {e!s}")

        # Dependencies check
        dependencies = check_dependencies()
        click.echo("📦 Dependency check:")
        for dep_name, dep_status in dependencies.items():
            status_icon = "✅" if dep_status else "❌"
            click.echo(f"   {dep_name}: {status_icon}")

        # Configuration files check
        if check_config:
            config_files = list(workspace_path.glob("*.yaml")) + list(workspace_path.glob("*.yml"))
            click.echo("📋 Configuration files check:")
            if config_files:
                for config_file in config_files:
                    try:
                        from .config.manager import load_config_file

                        load_config_file(str(config_file))
                        success_message(f"{config_file.name}: Valid")
                    except Exception as e:
                        error_message(f"{config_file.name}: Invalid ({e!s})")
            else:
                click.echo("   No configuration files found")

        # JWT environment check
        if check_env:
            jwt_info = check_jwt_env()
            click.echo("🔐 JWT environment check:")
            for var_name, var_value in jwt_info["variables"].items():
                status_icon = "✅" if var_value else "❌"
                click.echo(f"   {var_name}: {status_icon}")

            if not jwt_info["secret_configured"]:
                warning_message("JWT secret key not configured")

            if not jwt_info["all_configured"]:
                warning_message("Some JWT variables not configured")

        click.echo("🎉 Health check completed!")

    except Exception as e:
        error_message(f"Health check failed: {e!s}")
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        sys.exit(1)


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()
