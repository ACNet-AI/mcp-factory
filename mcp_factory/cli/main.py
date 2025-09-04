# !/usr/bin/env python3
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

from ..factory import MCPFactory

# =============================================================================
# Utility Functions
# =============================================================================


def is_verbose(ctx: click.Context) -> bool:
    """Check if verbose mode is enabled"""
    return bool(ctx.obj.get("verbose", False) if ctx.obj else False)


def success_message(message: str) -> None:
    """Display success message with green color"""
    click.echo(click.style(f"✅ {message}", fg="green"))


def error_message(message: str) -> None:
    """Display error message with red color"""
    click.echo(click.style(f"❌ {message}", fg="red"), err=True)


def info_message(message: str) -> None:
    """Display info message with blue color"""
    click.echo(click.style(f"💬 {message}", fg="blue"))


def warning_message(message: str) -> None:
    """Display warning message with yellow color"""
    click.echo(click.style(f"⚠️ {message}", fg="yellow"))


def _run_server_file_directly(server_path: Path, transport: str | None, host: str | None, port: int | None) -> None:
    """Run server.py file directly using Python subprocess

    Args:
        server_path: Path to the server.py file
        transport: Transport protocol override
        host: Host address override
        port: Port number override
    """
    import os
    import subprocess

    # Get the directory containing the server.py file
    server_dir = server_path.parent

    # Set up environment
    env = os.environ.copy()

    # Add transport overrides as environment variables if provided
    if transport:
        env["MCPF_TRANSPORT"] = transport
    if host:
        env["MCPF_HOST"] = host
    if port:
        env["MCPF_PORT"] = str(port)

    # Run the server.py file directly
    try:
        # Change to the server directory and run the file
        result = subprocess.run(
            [sys.executable, str(server_path.name)],
            cwd=str(server_dir),
            env=env,
            # Don't capture output - let server communicate directly with parent process
        )

        # Exit with the same code as the server process
        sys.exit(result.returncode)

    except KeyboardInterrupt:
        click.echo("\n🛑 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        error_message(f"Failed to run server file: {e}")
        sys.exit(1)


def get_factory(workspace: str | None = None) -> MCPFactory:
    """Get MCPFactory instance"""
    if workspace:
        # If user specified workspace, perform intelligent path processing
        workspace_path = Path(workspace)

        # If it's an absolute path, use it directly
        if workspace_path.is_absolute():
            workspace_root = workspace
        else:
            # If it's a relative path, convert to absolute path to avoid ambiguity
            workspace_root = str(workspace_path.resolve())

        # Optional: create directory in advance if it doesn't exist (to avoid subsequent errors)
        try:
            Path(workspace_root).mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            # If unable to create, let MCPFactory handle the error
            pass
    else:
        # Smart selection of workspace_root：
        # 1. If current directory name is "workspace", use current directory
        # 2. If we're already in a project directory that has a workspace subdirectory, use it
        # 3. Otherwise use default "./workspace"
        try:
            current_dir = Path.cwd()
            if current_dir.name == "workspace":
                workspace_root = str(current_dir)  # Use absolute path
            elif (current_dir / "workspace").exists() and (current_dir / "workspace").is_dir():
                workspace_root = str(current_dir / "workspace")  # Use absolute path
            else:
                workspace_root = str(current_dir / "workspace")  # Use absolute path
        except (OSError, FileNotFoundError):
            # If we can't get current directory (e.g., it was deleted), use safe default
            workspace_root = "./workspace"

    return MCPFactory(workspace_root=workspace_root)


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
        from ..config.manager import load_config_file

        config = load_config_file(config_file)
        return len(config.get("mcpServers", {}))
    except Exception:
        return 0


def _get_mounted_servers_info(config_file: str | None) -> dict[str, Any]:
    """Get mounted servers detailed information"""
    if not config_file:
        return {}

    try:
        from ..config.manager import load_config_file

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
    """🖥️ Server Management (supports both server name and ID)"""
    ctx.ensure_object(dict)


def _filter_servers_by_status(servers: list[dict[str, Any]], status_filter: str | None) -> list[dict[str, Any]]:
    """Filter servers by status"""
    if not status_filter:
        return servers
    return [s for s in servers if s.get("status") == status_filter]


def _add_mount_info_to_servers(servers: list[dict[str, Any]]) -> None:
    """Add mount information to servers list"""
    for server in servers:
        mount_count = _get_mounted_servers_count(server.get("config_file"))
        server["Mounts"] = f"🔗{mount_count}" if mount_count > 0 else "➖"


def _output_servers_as_json(servers: list[dict[str, Any]], show_mounts: bool) -> None:
    """Output servers in JSON format"""
    if show_mounts:
        for server in servers:
            server["mounted_servers"] = _get_mounted_servers_info(server.get("config_file"))
    click.echo(json.dumps(servers, indent=2))


def _output_servers_as_table(servers: list[dict[str, Any]], show_mounts: bool) -> None:
    """Output servers in table format"""
    if not servers:
        click.echo("📭 No servers found")
        return

    # Modify server data to display simplified ID
    display_servers = []
    for server in servers:
        display_server = server.copy()
        # Only show first 8 characters of ID
        if "id" in display_server:
            display_server["id"] = display_server["id"][:8] + "..."
        display_servers.append(display_server)

    headers = ["ID", "Name", "Status", "Host", "Port"]
    if show_mounts:
        headers.append("Mounts")
        _add_mount_info_to_servers(display_servers)

    table = format_table(display_servers, headers)
    click.echo(table)

    # Add usage tips
    click.echo("\n💡 Tip: You can use server name or ID to manage servers")
    click.echo("   Example: mcpf server status my-server-name")
    click.echo("   Or: mcpf server delete abc12345...")


def _display_mount_details(servers: list[dict[str, Any]]) -> None:
    """Display detailed mount information for servers"""
    for server in servers:
        mounted_info = _get_mounted_servers_info(server.get("config_file"))
        if mounted_info:
            click.echo(f"\n🔗 Mounted servers for {server.get('Name', server.get('ID'))}:")
            for mount_name, mount_info in mounted_info.items():
                status_icon = "🟢" if mount_info.get("status") == "running" else "🔴"
                click.echo(f"  {status_icon} {mount_name} ({mount_info.get('type', 'unknown')})")


def _display_server_status(server_id: str, status: str) -> None:
    """Display server status with appropriate icon"""
    click.echo(f"📊 Server status: {server_id}")
    click.echo("-" * 40)

    if status == "running":
        click.echo(f"Status: 🟢 {status}")
    elif status == "stopped":
        click.echo(f"Status: 🔴 {status}")
    else:
        click.echo(f"Status: 🟡 {status}")


def _display_server_details(server_info: dict[str, Any]) -> None:
    """Display server details excluding status"""
    for key, value in server_info.items():
        if key != "status":
            click.echo(f"{key}: {value}")


def _display_mount_info_details(mounted_info: dict[str, Any]) -> None:
    """Display detailed mounted server information"""
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


def _show_mount_information(server_info: dict[str, Any]) -> None:
    """Show mount information for a server"""
    config_file = server_info.get("config_file")
    mounted_info = _get_mounted_servers_info(config_file)

    if mounted_info:
        _display_mount_info_details(mounted_info)
    else:
        click.echo("\n📭 No mounted external servers")


@server.command("list")
@click.option(
    "--status-filter",
    type=click.Choice(["created", "starting", "running", "stopping", "stopped", "error", "restarting"]),
    help="Filter by status",
)
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.option("--show-mounts", "-m", is_flag=True, help="Show mounted external servers")
@click.pass_context
def list_servers(ctx: click.Context, status_filter: str | None, output_format: str, show_mounts: bool) -> None:
    """List all servers"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        servers = factory.list_servers()

        # Filter servers by status
        servers = _filter_servers_by_status(servers, status_filter)

        # Output in requested format
        if output_format == "json":
            _output_servers_as_json(servers, show_mounts)
        else:
            _output_servers_as_table(servers, show_mounts)
            # Show detailed mount information if requested
            if show_mounts:
                _display_mount_details(servers)

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="list_servers", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.argument("server_identifier")
@click.option("--show-mounts", "-m", is_flag=True, help="Show mounted external server details")
@click.pass_context
def status(ctx: click.Context, server_identifier: str, show_mounts: bool) -> None:
    """View server status (supports both server name and ID)"""
    try:
        from .helpers import ServerNameResolver

        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        resolver = ServerNameResolver()

        # Resolve server identifier
        server_id = resolver.resolve_server_identifier(factory, server_identifier)
        if not server_id:
            sys.exit(1)

        # Show resolved server information
        resolver.show_resolved_server_info(factory, server_id)

        server_info = factory.get_server_status(server_id)

        if not server_info:
            error_message(f"Server '{server_id}' does not exist")
            sys.exit(1)

        # Display basic status and details
        status_value = server_info.get("status", "unknown")
        _display_server_status(server_id, status_value)
        _display_server_details(server_info)

        # Display mounted server information if requested
        if show_mounts:
            _show_mount_information(server_info)

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="server_status", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.argument("server_identifier")
@click.option("--force", "-f", is_flag=True, help="Force deletion without confirmation")
@click.option("--batch", "-b", is_flag=True, help="Enable batch mode for multiple servers")
@click.pass_context
def delete(ctx: click.Context, server_identifier: str, force: bool, batch: bool) -> None:
    """Delete server (supports both server name and ID, or multiple with comma separation)"""
    try:
        from .helpers import ServerNameResolver

        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        resolver = ServerNameResolver()

        # Handle multiple servers (comma-separated)
        if "," in server_identifier or batch:
            server_identifiers = [s.strip() for s in server_identifier.split(",")]
            success_count = 0

            info_message(f"Batch delete mode: {len(server_identifiers)} server(s)")

            for identifier in server_identifiers:
                try:
                    server_id = resolver.resolve_server_identifier(factory, identifier)
                    if not server_id:
                        warning_message(f"Server '{identifier}' not found, skipping")
                        continue

                    server_info = factory.get_server_status(server_id)
                    server_name = server_info.get("name", "N/A") if server_info else "N/A"

                    if not force:
                        import click

                        if not click.confirm(f"Delete server '{server_name}' ({server_id[:8]}...)?"):
                            info_message(f"Skipped: {server_name}")
                            continue

                    if factory.delete_server(server_id):
                        success_message(f"Deleted: {server_name} ({server_id[:8]}...)")
                        success_count += 1
                    else:
                        error_message(f"Failed to delete: {server_name}")

                except Exception as e:
                    error_message(f"Error deleting '{identifier}': {e}")

            info_message(f"Batch delete completed: {success_count}/{len(server_identifiers)} servers deleted")
            return

        # Single server deletion
        server_id = resolver.resolve_server_identifier(factory, server_identifier)
        if not server_id:
            sys.exit(1)

        # Show resolved server information
        resolver.show_resolved_server_info(factory, server_id)

        server_info = factory.get_server_status(server_id)
        server_name = server_info.get("name", "N/A") if server_info else "N/A"

        if not force:
            warning_message(f"About to delete server '{server_name}'")
            import click

            if not click.confirm("Are you sure you want to continue?"):
                info_message("Operation cancelled")
                return

        if factory.delete_server(server_id):
            success_message(f"Server '{server_name}' deleted successfully")
        else:
            error_message(f"Failed to delete server '{server_name}'")
            sys.exit(1)

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="server_delete", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.argument("server_identifier")
@click.pass_context
def restart(ctx: click.Context, server_identifier: str) -> None:
    """Restart server (supports both server name and ID)"""
    try:
        from .helpers import ServerNameResolver

        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        resolver = ServerNameResolver()

        # Resolve server identifier
        server_id = resolver.resolve_server_identifier(factory, server_identifier)
        if not server_id:
            sys.exit(1)

        # Show resolved server information
        resolver.show_resolved_server_info(factory, server_id)

        factory.restart_server(server_id)
        success_message(f"Server '{server_id}' restart completed")
        info_message(f"Server ID: {server_id[:8]}...")

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="server_restart", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.argument("server_identifier")
@click.pass_context
def stop(ctx: click.Context, server_identifier: str) -> None:
    """Stop server (supports both server name and ID)"""
    try:
        from .helpers import ServerNameResolver

        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        resolver = ServerNameResolver()

        # Resolve server identifier
        server_id = resolver.resolve_server_identifier(factory, server_identifier)
        if not server_id:
            sys.exit(1)

        # Show resolved server information
        resolver.show_resolved_server_info(factory, server_id)

        # Update server state to stopped
        factory._state_manager.update_server_state(server_id, status="stopped")
        factory._state_manager.record_server_event(server_id, "stopped", {"stop_reason": "manual"})

        success_message(f"Server '{server_id}' stopped successfully")
        info_message(f"Server ID: {server_id[:8]}...")

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="server_stop", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.option("--force", "-f", is_flag=True, help="Force cleanup without confirmation")
@click.option("--keep-configs", is_flag=True, help="Keep configuration files")
@click.pass_context
def clear(ctx: click.Context, force: bool, keep_configs: bool) -> None:
    """Clear workspace (remove all servers and optionally configs)"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        servers = factory.list_servers()

        if not servers:
            info_message("Workspace is already clean - no servers found")
            return

        # Show what will be cleared
        warning_message(f"About to clear workspace: {factory.workspace_root}")
        info_message(f"This will remove {len(servers)} server(s):")
        for server in servers:
            info_message(f"  • {server['name']} ({server['id'][:8]}...)")

        if not keep_configs:
            warning_message("Configuration files will also be removed")
        else:
            info_message("Configuration files will be preserved")

        # Confirm if not forced
        if not force:
            import click

            if not click.confirm("Are you sure you want to continue?"):
                info_message("Operation cancelled")
                return

        # Clear all servers
        cleared_count = 0
        for server in servers:
            if factory.delete_server(server["id"]):
                cleared_count += 1

        # Clear config files if requested
        configs_cleared = 0
        if not keep_configs:
            configs_dir = factory.workspace_root / "configs"
            if configs_dir.exists():
                for config_file in configs_dir.glob("*.yaml"):
                    try:
                        config_file.unlink()
                        configs_cleared += 1
                    except Exception as e:
                        warning_message(f"Failed to remove {config_file.name}: {e}")

        # Summary
        success_message("Workspace cleared successfully")
        info_message(f"Removed {cleared_count} server(s)")
        if not keep_configs and configs_cleared > 0:
            info_message(f"Removed {configs_cleared} configuration file(s)")

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="workspace_clear", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.argument("config_source", required=False)
@click.option("--name", help="Override server name")
@click.option("--transport", type=click.Choice(["stdio", "http", "sse"]), help="Override transport method")
@click.option("--host", help="Override host address")
@click.option("--port", type=int, help="Override port number")
@click.option("--project-mode", is_flag=True, help="Force project mode (use project directory directly)")
@click.option("--server-file", help="Run specific server.py file directly")
@click.pass_context
def run(
    ctx: click.Context,
    config_source: str | None,
    name: str | None,
    transport: str | None,
    host: str | None,
    port: int | None,
    project_mode: bool,
    server_file: str | None,
) -> None:
    """Run server using FastMCP (supports config file, project directory, or server.py file)

    Examples:
      mcp-factory server run config.yaml                    # Config file mode
      mcp-factory server run my-project --project-mode      # Project directory mode
      mcp-factory server run /path/to/project --project-mode # Project directory mode
      mcp-factory server run --server-file /path/to/server.py # Direct server.py mode
    """
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

        # Handle --server-file option (highest priority)
        if server_file:
            server_path = Path(server_file)
            if not server_path.exists() or not server_path.is_file():
                error_message(f"Server file not found: {server_file}")
                sys.exit(1)
            click.echo(f"🚀 Running server file directly: {server_file}")
            return _run_server_file_directly(server_path, transport, host, port)

        # Validate that config_source is provided when not using --server-file
        if not config_source:
            error_message("CONFIG_SOURCE is required when not using --server-file")
            sys.exit(1)

        # Determine source type and mode
        config_path = Path(config_source)

        if project_mode:
            # Force project mode - expect directory
            if config_path.exists() and config_path.is_dir():
                source = config_source
                click.echo(f"🚀 Starting server in project mode: {config_source}")
            else:
                # Try to resolve as project name in workspace
                project_dir = factory.workspace_root / "projects" / config_source
                if project_dir.exists() and project_dir.is_dir():
                    source = str(project_dir)
                    click.echo(f"🚀 Starting server in project mode: {config_source}")
                else:
                    error_message(f"Project directory not found: {config_source}")
                    sys.exit(1)
        else:
            # Auto-detect mode based on path
            if config_path.exists() and config_path.is_file():
                # It's a config file
                source = config_source
                click.echo(f"🚀 Starting server from config file: {config_source}")
            elif config_path.exists() and config_path.is_dir():
                # It's a directory - check if it has server.py (project mode) or config.yaml (config mode)
                server_py = config_path / "server.py"
                config_yaml = config_path / "config.yaml"

                if server_py.exists():
                    click.echo("📁 Detected project directory with server.py")
                    if config_yaml.exists():
                        click.echo("⚙️  Found both server.py and config.yaml - using project mode")
                        click.echo("💡 Tip: Use --project-mode to skip this detection")
                    source = config_source  # Use directory for project mode
                    click.echo(f"🚀 Starting server in project mode: {config_source}")
                elif config_yaml.exists():
                    # Directory with config.yaml but no server.py - use config mode
                    source = str(config_yaml)
                    click.echo(f"🚀 Starting server from project config: {config_source}")
                else:
                    error_message(f"Directory '{config_source}' has no server.py or config.yaml")
                    sys.exit(1)
            else:
                # Try to resolve as project name in workspace
                project_dir = factory.workspace_root / "projects" / config_source
                if project_dir.exists() and project_dir.is_dir():
                    # Found project directory - check for server.py vs config.yaml
                    server_py = project_dir / "server.py"
                    config_yaml = project_dir / "config.yaml"

                    if server_py.exists():
                        source = str(project_dir)  # Use directory for project mode
                        click.echo(f"🚀 Starting server in project mode: {config_source}")
                    elif config_yaml.exists():
                        source = str(config_yaml)  # Use config file
                        click.echo(f"🚀 Starting server from project config: {config_source}")
                    else:
                        error_message(f"Project '{config_source}' has no server.py or config.yaml")
                        sys.exit(1)
                else:
                    error_message(f"Config file or project not found: {config_source}")
                    sys.exit(1)

        # Use Factory's run_server method for core logic
        factory.run_server(source=source, name=name, transport=transport, host=host, port=port)

        # Don't show success message for run command as server takes over stdout in stdio mode
        # The server itself will handle the output after this point

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="server_run", verbose=is_verbose(ctx))
        sys.exit(1)


@server.command()
@click.pass_context
def quick(ctx: click.Context) -> None:
    """Quick start temporary server"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
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
# Project Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def project(ctx: click.Context) -> None:
    """📂 Project management"""
    ctx.ensure_object(dict)


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
@click.option("--no-git", is_flag=True, help="Skip git repository initialization")
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
    no_git: bool,
) -> None:
    """📂 Interactive project initialization wizard"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

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
        click.echo(f"   Git repository: {'❌' if no_git else '✅'}")

        # Generate configuration file following correct schema
        config_data = {
            "server": {
                "name": name,
                "instructions": f"This is {name} - {description}",
            },
            "transport": {
                "transport": transport,
                "host": host,
                "port": port,
                "log_level": "DEBUG" if debug else "INFO",
            },
        }

        if auth:
            config_data["auth"] = {"provider": "basic"}
        if auto_discovery:
            config_data["components"] = {"auto_discovery": {"enabled": True}}

        # Build project structure (this will create config.yaml inside the project)
        project_path = factory.build_project(name, config_data, git_init=not no_git)
        success_message(f"Project structure created: {project_path}")

        # Use the config file inside the project directory
        config_file = f"{project_path}/config.yaml"

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
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="project_init", verbose=is_verbose(ctx))
        sys.exit(1)


@project.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.pass_context
def build(ctx: click.Context, config_file: str) -> None:
    """Build project"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

        # Load configuration from file
        from ..config.manager import load_config_file

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
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="project_build", verbose=is_verbose(ctx))
        sys.exit(1)


def _handle_dry_run_validation(publisher: Any, cli_helper: Any, project_path_obj: Path) -> None:
    """Handle dry-run validation workflow"""
    validation_result = publisher.validate_project(project_path_obj)

    if validation_result.success:
        success_message("Project validation passed, ready to publish")
        _display_project_info(publisher, project_path_obj)
    else:
        error_message("Project validation failed")
        for error in validation_result.data.get("errors", []):
            error_message(f"  - {error}")
        sys.exit(1)


def _display_project_info(publisher: Any, project_path_obj: Path) -> None:
    """Display project information during validation"""
    try:
        metadata = publisher.extract_project_metadata(project_path_obj)
        info_message(f"Project name: {metadata.get('name')}")
        info_message(f"Project description: {metadata.get('description')}")
        info_message(f"Author: {metadata.get('author')}")

        # Check Git status, GitHub App flow allows no remote repository
        try:
            # For GitHub App flow, allow missing remote
            git_status = publisher.check_git_status(project_path_obj, allow_no_remote=True)
            if git_status["valid"]:
                git_info = git_status["git_info"]
                if git_info.get("auto_create_repo"):
                    info_message("Git repository: Will be created automatically by GitHub App")
                else:
                    info_message(f"GitHub repository: {git_info['full_name']}")
                if git_status["needs_commit"]:
                    warning_message("Detected uncommitted changes")
                if git_status["needs_push"]:
                    warning_message("Detected unpushed commits")
            else:
                # Git check failed, but don't show error (possibly GitHub App flow)
                info_message("Git repository: Will be created automatically")
        except Exception:
            # Git check exception, possibly no remote repository (GitHub App flow)
            info_message("Git repository: Will be created automatically")
    except Exception as e:
        warning_message(f"Unable to extract project metadata: {e}")


def _collect_configuration(publisher: Any, cli_helper: Any, project_path_obj: Path) -> dict[str, Any]:
    """Collect project configuration (simplified with auth cache in publisher)"""
    has_config, existing_config = publisher.check_hub_configuration(project_path_obj)

    if not has_config:
        # Step 1: Collect basic project information
        existing_info = {}

        try:
            existing_info = publisher.extract_project_metadata(project_path_obj)
        except Exception as e:
            warning_message(f"Unable to extract project metadata: {e}")

        # Collect basic configuration
        basic_config = cli_helper.collect_project_configuration(existing_info)

        # Step 2: GitHub App installation to get GitHub username and installation_id
        info_message("🔐 GitHub App installation required for publishing...")
        oauth_result = cli_helper.handle_oauth_authentication(publisher, basic_config["name"], str(project_path_obj))

        if not oauth_result.get("success"):
            if oauth_result.get("user_cancelled"):
                info_message("Publishing cancelled by user")
                sys.exit(0)
            elif oauth_result.get("timeout"):
                warning_message("GitHub App installation timeout. Falling back to manual configuration...")
                # Fallback to manual GitHub username input
                github_username = cli_helper.text_input("GitHub Username:", "")
                oauth_result = {"github_username": github_username}
            else:
                error_message(f"GitHub App installation failed: {oauth_result.get('error', 'Unknown error')}")
                sys.exit(1)

        # Step 3: Save installation_id to auth cache (if available)
        if oauth_result.get("installation_id") and oauth_result.get("github_username"):
            publisher._save_installation_id(oauth_result["github_username"], oauth_result["installation_id"])
            info_message("✅ Installation saved to auth cache")

        # Step 4: Create project configuration (without installation_id)
        project_config = {
            **basic_config,
            "github_username": oauth_result.get("github_username", ""),
            # Note: installation_id is NOT saved to project config anymore
        }

        # Save project configuration (without sensitive data)
        if not publisher.add_hub_configuration(project_path_obj, project_config):
            cli_helper.show_error_message("Failed to save configuration")
            sys.exit(1)

        return project_config
    # Project has existing configuration
    github_username = existing_config.get("github_username")

    # Check if we have installation_id in auth cache
    installation_id = publisher._get_installation_id(github_username)

    if not installation_id:
        info_message("🔐 No installation found in auth cache, GitHub App installation required...")
        oauth_result = cli_helper.handle_oauth_authentication(
            publisher, existing_config.get("name", ""), str(project_path_obj)
        )

        if oauth_result.get("success"):
            # Save installation_id to auth cache
            if oauth_result.get("installation_id") and oauth_result.get("github_username"):
                publisher._save_installation_id(oauth_result["github_username"], oauth_result["installation_id"])
                info_message("✅ Installation saved to auth cache")

            # Update project config if github_username changed
            if oauth_result.get("github_username") != github_username:
                existing_config["github_username"] = oauth_result.get("github_username", github_username)
                publisher.add_hub_configuration(project_path_obj, existing_config)
                info_message("✅ Project configuration updated")
        else:
            error_message("GitHub App installation failed")
            sys.exit(1)
    else:
        info_message(f"✅ Using installation from auth cache for {github_username}")

    return dict(existing_config)


def _handle_git_operations(
    publisher: Any, cli_helper: Any, project_path_obj: Path, github_app_mode: bool = False
) -> None:
    """Handle Git status checking and operations

    Args:
        publisher: Project publisher instance
        cli_helper: CLI helper instance
        project_path_obj: Project path
        github_app_mode: If True, skip remote repository checks (GitHub App will create repo)
    """
    git_status = publisher.check_git_status(project_path_obj, allow_no_remote=github_app_mode)

    if not git_status["valid"]:
        # Don't exit immediately - let publisher.publish_project handle Git issues with smart fallback
        cli_helper.show_warning_message(f"Git configuration issue: {git_status.get('error', 'Unknown')}")
        cli_helper.show_warning_message("Will attempt automatic publishing via GitHub App...")
        return

    # Handle uncommitted changes
    if git_status["needs_commit"]:
        cli_helper.show_warning_message("Detected uncommitted changes")
        cli_helper.show_info_message("💡 These changes include configuration updates (e.g., updated Installation ID)")
        cli_helper.show_info_message("✅ Auto-committing configuration updates...")
        if not publisher.commit_changes(project_path_obj):
            cli_helper.show_error_message("Commit failed, please commit changes manually")
            sys.exit(1)
        else:
            cli_helper.show_success_message("Configuration updates committed successfully")

    # Handle unpushed commits (only if we have a remote repository)
    if git_status["needs_push"] and not git_status.get("auto_create_repo", False):
        cli_helper.show_warning_message("Detected unpushed commits")
        if cli_helper.confirm_git_operations("push"):
            if not publisher.push_changes(project_path_obj):
                cli_helper.show_error_message("Push failed, please push to GitHub manually")
                sys.exit(1)
        else:
            cli_helper.show_error_message("Please push your changes to GitHub first")
            sys.exit(1)
    elif git_status.get("auto_create_repo", False):
        cli_helper.show_info_message("Remote repository will be created automatically by GitHub App")


def _handle_publish_result(
    result: Any,
    publisher: Any,
    cli_helper: Any,
    project_path_obj: Path,
    config: dict[str, Any],
    github_app_status: dict[str, Any] | None = None,
) -> None:
    """Handle publishing result with GitHub App context"""
    if not result.success:
        # Check for API failure with repository creation issues
        if result.data and result.data.get("method") == "api_failed":
            error_type = result.data.get("error_type")

            # Handle repository already exists case (improved detection)
            if error_type in ["repository_already_exists", "repository_creation_failed"]:
                github_username = config.get("github_username", "")
                project_name = config.get("name", "")

                if github_username and project_name:
                    cli_helper.show_info_message("🔍 Checking if repository already exists...")

                    # Check if repository exists on GitHub
                    import requests

                    try:
                        repo_check_response = requests.get(
                            f"https://api.github.com/repos/{github_username}/{project_name}", timeout=10
                        )

                        if repo_check_response.status_code == 200:
                            repo_data = repo_check_response.json()
                            repo_url = repo_data.get("html_url", "")
                            clone_url = repo_data.get("clone_url", "")

                            cli_helper.show_info_message(f"✅ Repository already exists: {repo_url}")

                            if cli_helper.confirm_action(
                                "Set up Git remote and push code to existing repository?", default=True
                            ):
                                cli_helper.show_info_message("🔧 Setting up Git remote to existing repository...")

                                try:
                                    import subprocess

                                    # Set up Git remote
                                    try:
                                        subprocess.run(
                                            ["git", "remote", "get-url", "origin"],
                                            cwd=project_path_obj,
                                            capture_output=True,
                                            text=True,
                                            check=True,
                                        )
                                        # Remote exists, update it
                                        subprocess.run(
                                            ["git", "remote", "set-url", "origin", clone_url],
                                            cwd=project_path_obj,
                                            check=True,
                                        )
                                        cli_helper.show_info_message(f"🔧 Updated Git remote to: {clone_url}")
                                    except subprocess.CalledProcessError:
                                        # Remote doesn't exist, add it
                                        subprocess.run(
                                            ["git", "remote", "add", "origin", clone_url],
                                            cwd=project_path_obj,
                                            check=True,
                                        )
                                        cli_helper.show_info_message(f"🔧 Added Git remote: {clone_url}")

                                    # Push code and register to Hub
                                    cli_helper.show_info_message("ℹ️ Triggering initial registration...")
                                    if publisher.trigger_initial_registration(project_path_obj, config):
                                        cli_helper.show_info_message(
                                            "✅ Code pushed to repository and registered to Hub successfully!"
                                        )
                                        cli_helper.show_info_message(
                                            f"🔗 Your project will appear at https://github.com/{publisher.hub_repo} within minutes"
                                        )
                                        cli_helper.show_publish_success(
                                            repo_url, f"https://github.com/{publisher.hub_repo}"
                                        )
                                        return  # Success - exit without showing error
                                    cli_helper.show_error_message("⚠️ Failed to push code or register to Hub")

                                except subprocess.CalledProcessError as e:
                                    cli_helper.show_error_message(f"⚠️ Failed to set up Git remote: {e}")
                            else:
                                cli_helper.show_info_message("💡 Repository exists but Git remote not configured")
                                cli_helper.show_info_message(
                                    f"You can manually add remote: git remote add origin {clone_url}"
                                )
                                return  # User chose not to proceed

                        # If repository doesn't exist or we can't access it, fall through to normal error handling

                    except requests.RequestException:
                        # Network error, fall through to normal error handling
                        pass

        # Legacy check for older error format (keeping for compatibility)
        elif "Repository creation failed" in result.message and github_app_status and github_app_status.get("ready"):
            github_username = config.get("github_username", "")
            project_name = config.get("name", "")

            if github_username and project_name:
                cli_helper.show_info_message("🔍 Checking if repository already exists...")

                # Check if repository exists on GitHub
                import requests

                try:
                    repo_check_response = requests.get(
                        f"https://api.github.com/repos/{github_username}/{project_name}", timeout=10
                    )

                    if repo_check_response.status_code == 200:
                        repo_data = repo_check_response.json()
                        repo_url = repo_data.get("html_url", "")
                        clone_url = repo_data.get("clone_url", "")

                        cli_helper.show_info_message(f"✅ Repository already exists: {repo_url}")

                        if cli_helper.confirm_action(
                            "Set up Git remote and push code to existing repository?", default=True
                        ):
                            cli_helper.show_info_message("🔧 Setting up Git remote to existing repository...")

                            try:
                                import subprocess

                                # Set up Git remote
                                try:
                                    subprocess.run(
                                        ["git", "remote", "get-url", "origin"],
                                        cwd=project_path_obj,
                                        capture_output=True,
                                        text=True,
                                        check=True,
                                    )
                                    # Remote exists, update it
                                    subprocess.run(
                                        ["git", "remote", "set-url", "origin", clone_url],
                                        cwd=project_path_obj,
                                        check=True,
                                    )
                                    cli_helper.show_info_message(f"🔧 Updated Git remote to: {clone_url}")
                                except subprocess.CalledProcessError:
                                    # Remote doesn't exist, add it
                                    subprocess.run(
                                        ["git", "remote", "add", "origin", clone_url], cwd=project_path_obj, check=True
                                    )
                                    cli_helper.show_info_message(f"🔧 Added Git remote: {clone_url}")

                                # Push code and register to Hub
                                cli_helper.show_info_message("ℹ️ Triggering initial registration...")
                                if publisher.trigger_initial_registration(project_path_obj, config):
                                    cli_helper.show_info_message(
                                        "✅ Code pushed to repository and registered to Hub successfully!"
                                    )
                                    cli_helper.show_info_message(
                                        f"🔗 Your project will appear at https://github.com/{publisher.hub_repo} within minutes"
                                    )
                                    cli_helper.show_publish_success(
                                        repo_url, f"https://github.com/{publisher.hub_repo}"
                                    )
                                    return  # Success - exit without showing error
                                cli_helper.show_error_message("⚠️ Failed to push code or register to Hub")

                            except subprocess.CalledProcessError as e:
                                cli_helper.show_error_message(f"⚠️ Failed to set up Git remote: {e}")
                        else:
                            cli_helper.show_info_message("💡 Repository exists but Git remote not configured")
                            cli_helper.show_info_message(
                                f"You can manually add remote: git remote add origin {clone_url}"
                            )
                            return  # User chose not to proceed

                    # If repository doesn't exist or we can't access it, fall through to normal error handling

                except requests.RequestException:
                    # Network error, fall through to normal error handling
                    pass

        # Original error handling
        cli_helper.show_error_message(result.message)

        # If GitHub App was installed but API still failed, provide specific guidance
        if github_app_status and github_app_status.get("ready"):
            cli_helper.show_warning_message(
                "GitHub App is installed but automatic publishing failed. "
                "This might be a temporary issue - you can try again or use manual workflow."
            )

        sys.exit(1)

    if result.data.get("method") == "api":
        # Enhanced success message with GitHub App context
        repo_url = result.data.get("repo_url", "")
        registration_url = result.data.get("registration_url", "")

        cli_helper.show_publish_success(repo_url, registration_url)

        if github_app_status and github_app_status.get("ready"):
            cli_helper.show_info_message("✨ One-click publishing via GitHub App completed successfully!")

        # FIXED: Set up Git remote and push code for API publishing
        cli_helper.show_info_message("ℹ️ Setting up Git remote and pushing code...")

        # Extract clone URL from result
        clone_url = result.data.get("clone_url")

        # Set up Git remote if we have the clone URL
        if clone_url:
            try:
                import subprocess

                # Check if remote origin already exists
                try:
                    subprocess.run(
                        ["git", "remote", "get-url", "origin"],
                        cwd=project_path_obj,
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    # Remote exists, update it
                    subprocess.run(["git", "remote", "set-url", "origin", clone_url], cwd=project_path_obj, check=True)
                    cli_helper.show_info_message(f"🔧 Updated Git remote to: {clone_url}")
                except subprocess.CalledProcessError:
                    # Remote doesn't exist, add it
                    subprocess.run(["git", "remote", "add", "origin", clone_url], cwd=project_path_obj, check=True)
                    cli_helper.show_info_message(f"🔧 Added Git remote: {clone_url}")

                # Now trigger initial registration (push and Hub registration)
                cli_helper.show_info_message("ℹ️ Triggering initial registration...")
                if publisher.trigger_initial_registration(project_path_obj, config):
                    cli_helper.show_info_message("✅ Code pushed to repository and registered to Hub successfully!")
                    cli_helper.show_info_message(
                        f"🔗 Your project will appear at https://github.com/{publisher.hub_repo} within minutes"
                    )
                else:
                    cli_helper.show_error_message("⚠️ Failed to push code or register to Hub")
                    cli_helper.show_info_message(
                        "💡 Repository created successfully, but you may need to push code manually"
                    )

            except subprocess.CalledProcessError as e:
                cli_helper.show_error_message(f"⚠️ Failed to set up Git remote: {e}")
                cli_helper.show_info_message(
                    "💡 Repository created successfully, but you may need to set up Git remote manually"
                )
        else:
            cli_helper.show_error_message("⚠️ Could not determine repository clone URL")
            cli_helper.show_info_message(
                "💡 Repository created successfully, but you may need to set up Git remote manually"
            )
    elif result.data.get("method") == "manual":
        _handle_manual_installation(result.data, publisher, cli_helper, project_path_obj, config)
    else:
        success_message("Project published successfully!")


def _handle_manual_installation(
    data: dict[str, Any], publisher: Any, cli_helper: Any, project_path_obj: Path, config: dict[str, Any]
) -> None:
    """Handle manual GitHub App installation workflow"""
    cli_helper.show_installation_guide(data["install_url"], data["repo_name"], data["project_name"])

    import webbrowser

    webbrowser.open(data["install_url"])

    cli_helper.wait_for_installation_completion()

    cli_helper.show_info_message("Triggering initial registration...")
    if publisher.trigger_initial_registration(project_path_obj, config):
        cli_helper.show_publish_success()
        cli_helper.show_info_message(
            f"Your project will appear at https://github.com/{publisher.hub_repo} within minutes"
        )
    else:
        cli_helper.show_error_message("Failed to trigger registration")
        sys.exit(1)


@project.command()
@click.argument("project_path", type=click.Path(exists=True), default=".")
@click.option("--dry-run", is_flag=True, help="Validate project but don't actually publish")
@click.option("--skip-app-check", is_flag=True, help="Skip GitHub App installation check")
@click.pass_context
def publish(ctx: click.Context, project_path: str, dry_run: bool, skip_app_check: bool) -> None:
    """📤 Publish project to GitHub and register to MCP Servers Hub"""
    try:
        from ..cli.helpers import PublishCLIHelper
        from ..project import ProjectPublisher

        cli_helper = PublishCLIHelper()
        publisher = ProjectPublisher()
        project_path_obj = Path(project_path).resolve()

        if dry_run:
            _handle_dry_run_validation(publisher, cli_helper, project_path_obj)
        else:
            info_message("🚀 Publishing project to GitHub and MCP Servers Hub")

            # Collect configuration using OAuth-first authentication flow
            info_message("🔐 Using OAuth-first authentication flow...")
            config = _collect_configuration(publisher, cli_helper, project_path_obj)

            # GitHub App is ready if we have installation_id (from _collect_configuration)
            github_app_status = {"ready": True} if config.get("installation_id") else {"ready": False}

            if github_app_status.get("ready"):
                info_message("✅ GitHub App installation verified via installation_id")
            else:
                info_message("🔧 GitHub App ready - automatic repository creation will handle Git setup")

            # Handle Git operations - GitHub App vs Manual workflow
            if github_app_status and github_app_status.get("ready", False):
                info_message("🔧 GitHub App ready - automatic repository creation will handle Git setup")
                # For GitHub App flow, only check local Git repository, skip remote check
                if not (project_path_obj / ".git").exists():
                    # If no Git repository, automatically initialize
                    cli_helper.show_info_message("🔄 Initializing local Git repository...")
                    if not publisher.init_git_repository(project_path_obj, config["name"]):
                        cli_helper.show_error_message("Failed to initialize Git repository")
                        sys.exit(1)
                    cli_helper.show_success_message("✅ Local Git repository initialized")
                else:
                    # Check local Git status (don't check remote)
                    try:
                        # Check uncommitted changes
                        import subprocess

                        status_result = subprocess.run(
                            ["git", "status", "--porcelain"],
                            cwd=project_path_obj,
                            capture_output=True,
                            text=True,
                            check=True,
                        )
                        has_changes = bool(status_result.stdout.strip())

                        if has_changes:
                            cli_helper.show_warning_message("Detected uncommitted changes")
                            cli_helper.show_info_message(
                                "💡 These changes include configuration updates (e.g., updated Installation ID)"
                            )
                            cli_helper.show_info_message("✅ Auto-committing configuration updates...")
                            if not publisher.commit_changes(project_path_obj):
                                cli_helper.show_error_message("Commit failed, please commit changes manually")
                                sys.exit(1)
                            else:
                                cli_helper.show_success_message("Configuration updates committed successfully")
                    except subprocess.CalledProcessError as e:
                        cli_helper.show_warning_message(f"Git status check failed: {e}")
            else:
                # Traditional workflow requires complete Git check
                _handle_git_operations(publisher, cli_helper, project_path_obj, github_app_mode=False)

            # Execute publishing with retry for session issues
            result = publisher.publish_project(project_path, config)

            # Check for session reauth needs and retry once
            if not result.success and result.data and result.data.get("needs_reauth"):
                warning_message("🔄 Session expired, retrying with fresh authentication...")

                # Re-run OAuth to get new session
                oauth_result = cli_helper.handle_oauth_authentication(publisher, config["name"], str(project_path_obj))
                if oauth_result.get("success"):
                    # Update config with new session info
                    config.update(
                        {
                            "github_username": oauth_result.get("github_username", config.get("github_username", "")),
                            "installation_id": oauth_result.get("installation_id", ""),
                        }
                    )

                    # Retry publishing with new session
                    info_message("🔄 Retrying publish with fresh session...")
                    result = publisher.publish_project(project_path, config)
                else:
                    warning_message("⚠️ OAuth retry failed, falling back to manual workflow")

            # Handle result with GitHub App context
            _handle_publish_result(result, publisher, cli_helper, project_path_obj, config, github_app_status)

    except Exception as e:
        error_message(f"Error occurred during publish: {e}")
        if is_verbose(ctx):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


# =============================================================================
# Configuration Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def config(ctx: click.Context) -> None:
    """⚙️ Configuration management"""
    ctx.ensure_object(dict)


@config.command()
@click.option("--name", prompt=True, help="Project name")
@click.option("--description", prompt=True, help="Project description")
@click.option("--output", "-o", help="Output configuration file name (default: generated from name)")
@click.option("--with-mounts", "-m", is_flag=True, help="Include mounted server example configuration")
@click.option("--with-shared-components", "-c", is_flag=True, help="Include shared components configuration")
@click.pass_context
def template(
    ctx: click.Context, name: str, description: str, output: str, with_mounts: bool, with_shared_components: bool
) -> None:
    """Generate configuration template"""
    try:
        # Get workspace from context
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        workspace_root = factory.workspace_root

        # Create configs directory in workspace
        configs_dir = workspace_root / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)

        # Generate output filename if not provided
        if not output:
            # Sanitize name for filename
            safe_name = name.lower().replace(" ", "_").replace("-", "_")
            safe_name = "".join(c for c in safe_name if c.isalnum() or c == "_")
            output = f"{safe_name}.yaml"

        # Ensure output path is in configs directory
        output_path = configs_dir / output

        # Generate basic configuration template following correct schema
        config_template = {
            "server": {
                "name": name,
                "instructions": f"This is {name} - {description}",
            },
            "transport": {"transport": "stdio", "host": "127.0.0.1", "port": 8000, "log_level": "INFO"},
            "management": {"expose_management_tools": True},
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

        # Add shared components configuration if requested
        shared_components_info = ""
        if with_shared_components:
            # Check if shared components exist
            shared_components = factory.list_shared_components()
            has_components = any(len(comps) > 0 for comps in shared_components.values())

            if has_components:
                components_config = {}
                for comp_type, comp_list in shared_components.items():
                    if comp_list:
                        # Convert to object format as expected by schema
                        components_config[comp_type] = [{"module": comp["name"], "enabled": True} for comp in comp_list]

                config_template["components"] = components_config
                total_count = sum(len(comps) for comps in shared_components.values())
                shared_components_info = f" (with {total_count} shared components)"
            else:
                # Add example components configuration
                config_template["components"] = {
                    "tools": [{"module": "example_tools", "enabled": True}],
                    "resources": [{"module": "example_resources", "enabled": True}],
                    "prompts": [{"module": "example_prompts", "enabled": True}],
                }
                shared_components_info = " (with example components - create them using 'mcp-factory component create')"

        # Write configuration file with proper resource management
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                yaml.dump(config_template, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except OSError as e:
            raise click.ClickException(f"Failed to write configuration file: {e}") from e

        success_message(f"Configuration template generated: {output_path}{mount_info}{shared_components_info}")
        info_message(f"💡 Tip: Use 'mcp-factory config promote {output}' to convert to full project")

        if with_shared_components and not any(len(comps) > 0 for comps in factory.list_shared_components().values()):
            info_message("💡 Tip: Create shared components using 'mcp-factory component create'")

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
            from ..config.manager import load_config_file, validate_config

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


@config.command()
@click.argument("config_file", type=click.Path(exists=False), required=False)
@click.option("--fix", is_flag=True, help="Automatically fix issues when possible")
@click.option("--format", "output_format", type=click.Choice(["text", "json"]), default="text", help="Output format")
@click.pass_context
def check(ctx: click.Context, config_file: str | None, fix: bool, output_format: str) -> None:
    """Check configuration for common issues and optionally fix them"""
    try:
        from .helpers import ConfigCLIHelper

        cli_helper = ConfigCLIHelper()

        # Perform configuration check
        results = cli_helper.check_configuration(config_file, auto_fix=fix)

        if output_format == "json":
            import json

            click.echo(json.dumps(results, indent=2))
        else:
            cli_helper.show_check_results(results)

        # Exit with appropriate code
        if results.get("has_errors", False):
            sys.exit(1)
        elif results.get("has_warnings", False):
            sys.exit(2)  # Warning exit code
        else:
            sys.exit(0)  # Success

    except Exception as e:
        from .helpers import handle_cli_error

        handle_cli_error(e, operation="config_check", verbose=is_verbose(ctx))
        sys.exit(1)


@config.command("list")
@click.pass_context
def list_configs(ctx: click.Context) -> None:
    """List configuration files"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        workspace_root = factory.workspace_root
        configs_dir = workspace_root / "configs"

        if not configs_dir.exists():
            click.echo("📭 No configs directory found")
            click.echo("💡 Use 'mcp-factory config template' to create configuration files")
            return

        # Find YAML configuration files in configs directory
        config_files = list(configs_dir.glob("*.yaml")) + list(configs_dir.glob("*.yml"))

        if not config_files:
            click.echo("📭 No configuration files found in configs directory")
            click.echo("💡 Use 'mcp-factory config template' to create configuration files")
            return

        click.echo(f"📋 Configuration files in {configs_dir}:")
        for config_file in config_files:
            click.echo(f"   📄 {config_file.name}")

        click.echo("\n💡 Tips:")
        click.echo(f"   • Use files with: mcp-factory server run {configs_dir / 'filename.yaml'}")
        click.echo("   • Promote to project: mcp-factory config promote filename.yaml")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to list configuration files")
        sys.exit(1)


@config.command()
@click.argument("config_name")
@click.option("--to-project", help="Target project name (default: derived from config name)")
@click.option("--keep-config", is_flag=True, help="Keep original config file after promotion")
@click.pass_context
def promote(ctx: click.Context, config_name: str, to_project: str, keep_config: bool) -> None:
    """Promote configuration file to full project"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        workspace_root = factory.workspace_root
        configs_dir = workspace_root / "configs"

        # Find config file
        config_path = configs_dir / config_name
        if not config_path.exists():
            # Try with .yaml extension
            if not config_name.endswith((".yaml", ".yml")):
                config_path = configs_dir / f"{config_name}.yaml"
                if not config_path.exists():
                    config_path = configs_dir / f"{config_name}.yml"

        if not config_path.exists():
            error_message(f"Configuration file not found: {config_name}")
            error_message(f"Available configs in {configs_dir}:")
            config_files = list(configs_dir.glob("*.yaml")) + list(configs_dir.glob("*.yml"))
            for cf in config_files:
                error_message(f"   📄 {cf.name}")
            sys.exit(1)

        # Load configuration
        from ..config.manager import load_config_file

        config_dict = load_config_file(config_path)

        # Determine project name
        if not to_project:
            # Derive from config name
            to_project = config_path.stem

        info_message(f"🔄 Promoting {config_path.name} to project '{to_project}'...")

        # Create project using the configuration
        project_path = factory.build_project(to_project, config_dict)
        success_message(f"✅ Project created: {project_path}")

        # Handle original config file
        if not keep_config:
            config_path.unlink()
            info_message(f"🗑️  Removed original config file: {config_path}")
        else:
            info_message(f"📁 Original config file preserved: {config_path}")

        # Show next steps
        click.echo("\n🎉 Success! Configuration promoted to full project.")
        click.echo(f"📂 Project location: {project_path}")
        click.echo("💡 Next steps:")
        click.echo(f"   • Add functionality: cd {project_path}")
        click.echo(f"   • Create server: mcp-factory server create {to_project} {project_path}")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to promote configuration to project")
        sys.exit(1)


# =============================================================================
# Shared Components Management Commands
# =============================================================================


@config.group()
@click.pass_context
def component(ctx: click.Context) -> None:
    """🧩 Shared component management"""
    ctx.ensure_object(dict)


@component.command()
@click.option(
    "--type", "component_type", type=click.Choice(["tools", "resources", "prompts"]), prompt=True, help="Component type"
)
@click.option("--name", prompt=True, help="Component name")
@click.option("--description", prompt=True, help="Component description")
@click.option("--function-name", prompt=True, help="Function name")
@click.option("--parameters", help="Function parameter definition (format: name:type,name:type)")
@click.option("--return-type", default="str", help="Return type (default: str)")
@click.pass_context
def create(
    ctx: click.Context,
    component_type: str,
    name: str,
    description: str,
    function_name: str,
    parameters: str | None,
    return_type: str,
) -> None:
    """Create shared component"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

        # Simplified parameter parsing
        param_dict = {}
        if parameters:
            try:
                for param in parameters.split(","):
                    if ":" in param:
                        param_name, param_type = param.strip().split(":", 1)
                        param_dict[param_name.strip()] = param_type.strip()
            except Exception:
                click.echo("⚠️  Parameter format error, using default parameters")
                param_dict = {}

        # Build function definition
        functions = [
            {
                "name": function_name,
                "description": description,
                "template_data": {"parameters": param_dict, "return_type": return_type},
            }
        ]

        # Create shared component
        component_path = factory.create_shared_component(component_type, name, functions)

        success_message(f"Shared component created successfully: {component_path}")
        info_message(f"File location: {component_path}")
        info_message(
            "💡 Tip: Use 'mcp-factory config template --with-shared-components' to create configuration referencing this component"
        )

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to create shared component")
        sys.exit(1)


@component.command("list")
@click.option(
    "--type", "component_type", type=click.Choice(["tools", "resources", "prompts"]), help="Filter component type"
)
@click.pass_context
def list_components(ctx: click.Context, component_type: str | None) -> None:
    """List existing shared components"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        components = factory.list_shared_components()

        # Filter component type
        if component_type:
            components = {component_type: components.get(component_type, [])}

        # Count total components
        total_components = sum(len(comps) for comps in components.values())

        if total_components == 0:
            info_message("No shared components found")
            info_message("💡 Tip: Use 'mcp-factory config component create' to create new shared components")
            return

        click.echo(f"📋 Shared component list (Total: {total_components})")
        click.echo("=" * 50)

        for comp_type, comp_list in components.items():
            if not comp_list:
                continue

            click.echo(f"\n🧩 {comp_type.title()} ({len(comp_list)} items)")
            click.echo("-" * 30)

            for comp in comp_list:
                click.echo(f"  📄 {comp['name']}")
                click.echo(f"     File: {comp['file']}")
                if comp["functions"]:
                    click.echo(f"     Functions: {', '.join(comp['functions'])}")
                click.echo()

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to list shared components")
        sys.exit(1)


@component.command()
@click.option("--type", "component_type", type=click.Choice(["tools", "resources", "prompts"]), help="Component type")
@click.option("--name", help="Component name")
@click.pass_context
def info(ctx: click.Context, component_type: str | None, name: str | None) -> None:
    """Show shared component detailed information"""
    try:
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
        components = factory.list_shared_components()

        found = False

        for comp_type, comp_list in components.items():
            # Filter component type
            if component_type and comp_type != component_type:
                continue

            for comp in comp_list:
                # Filter component name
                if name and comp["name"] != name:
                    continue

                found = True
                click.echo(f"📄 {comp['name']} ({comp_type})")
                click.echo("-" * 40)
                click.echo(f"File path: {comp['path']}")
                click.echo(f"Relative path: {comp['file']}")

                if comp["functions"]:
                    click.echo(f"Exported functions: {', '.join(comp['functions'])}")
                else:
                    click.echo("Exported functions: None")

                click.echo(f"💡 Open with editor: {comp['path']}")
                click.echo()

        if not found:
            if name:
                error_message(f"No shared component named '{name}' found")
            else:
                error_message("No matching shared components found")

    except Exception as e:
        if is_verbose(ctx):
            error_message(f"Detailed error: {e!s}")
        else:
            error_message("Failed to get component information")
        sys.exit(1)


# =============================================================================
# Authentication Management Commands
# =============================================================================


@cli.group()
@click.pass_context
def auth(ctx: click.Context) -> None:
    """🔐 Authentication management"""
    ctx.ensure_object(dict)


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
def env(ctx: click.Context, fastmcp: bool) -> None:
    """Check authentication environment variables"""
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


def _check_system_dependencies() -> None:
    """Check system dependencies health"""
    click.echo("🔍 Checking system dependencies:")
    deps = check_dependencies()

    for name, status in deps.items():
        status_icon = "✅" if status else "❌"
        click.echo(f"  {status_icon} {name}")


def _check_jwt_environment() -> None:
    """Check JWT environment variables"""
    click.echo("\n🔐 Checking JWT environment:")
    jwt_info = check_jwt_env()

    for var, info in jwt_info.items():
        if info["present"]:
            click.echo(f"  ✅ {var}: {info['status']}")
        else:
            click.echo(f"  ❌ {var}: Not set")


def _check_configuration_files(factory: Any) -> int:
    """Check configuration files health"""
    click.echo("\n📄 Checking configuration files:")
    config_issues = 0

    try:
        servers = factory.list_servers()
        click.echo(f"  ✅ Found {len(servers)} server configurations")

        for server in servers:
            config_file = server.get("config_file")
            if config_file:
                try:
                    with open(config_file) as f:
                        yaml.safe_load(f)
                    click.echo(f"    ✅ {config_file}")
                except Exception as e:
                    click.echo(f"    ❌ {config_file}: {e}")
                    config_issues += 1
            else:
                click.echo(f"    ⚠️  {server.get('Name', 'Unknown')}: No config file")
                config_issues += 1

    except Exception as e:
        click.echo(f"  ❌ Configuration check failed: {e}")
        config_issues += 1

    return config_issues


def _display_health_summary(config_issues: int, deps: dict[str, bool], jwt_info: dict[str, Any]) -> None:
    """Display overall health summary"""
    click.echo("\n📊 Health Summary:")

    total_issues = config_issues
    dep_issues = len([d for d in deps.values() if not d])
    jwt_issues = len([j for j in jwt_info.values() if not j["present"]])

    total_issues += dep_issues + jwt_issues

    if total_issues == 0:
        click.echo("  🎉 All systems healthy!")
    else:
        click.echo(f"  ⚠️  Found {total_issues} issues")
        if dep_issues > 0:
            click.echo(f"    - {dep_issues} dependency issues")
        if jwt_issues > 0:
            click.echo(f"    - {jwt_issues} JWT environment issues")
        if config_issues > 0:
            click.echo(f"    - {config_issues} configuration issues")


@cli.command()
@click.option("--check-config", is_flag=True, help="Check configuration files")
@click.option("--check-env", is_flag=True, help="Check JWT environment variables")
@click.pass_context
def health(ctx: click.Context, check_config: bool, check_env: bool) -> None:
    """🏥 System health check"""
    try:
        click.echo("🏥 MCP Factory Health Check")
        click.echo("=" * 40)

        # Always check system dependencies
        _check_system_dependencies()
        deps = check_dependencies()

        # Check JWT environment if requested or by default
        jwt_info = {}
        if check_env or not (check_config or check_env):
            _check_jwt_environment()
            jwt_info = check_jwt_env()

        # Check configuration files if requested or by default
        config_issues = 0
        if check_config or not (check_config or check_env):
            factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
            config_issues = _check_configuration_files(factory)

        # Display summary
        _display_health_summary(config_issues, deps, jwt_info)

    except Exception as e:
        error_message(f"Health check failed: {e}")
        if is_verbose(ctx):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        sys.exit(1)


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Main entry point for the CLI"""
    cli()


if __name__ == "__main__":
    main()
