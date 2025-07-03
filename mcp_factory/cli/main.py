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

    # Smart selection of workspace_root：
    # 1. If workspace parameter is explicitly specified, use it
    # 2. If current directory name is "workspace", use current directory
    # 3. If we're already in a project directory that has a workspace subdirectory, use it
    # 4. Otherwise use default "./workspace"
    if workspace:
        workspace_root = workspace
    else:
        try:
            current_dir = Path.cwd()
            if current_dir.name == "workspace":
                workspace_root = "."
            elif (current_dir / "workspace").exists() and (current_dir / "workspace").is_dir():
                # If there's already a workspace directory, use it to avoid nesting
                workspace_root = "workspace"
            else:
                workspace_root = "./workspace"
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


def _get_mounted_servers_info(config_file: str | None) -> dict:
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
    """🖥️ Server Management"""
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

    headers = ["ID", "Name", "Status", "Host", "Port"]
    if show_mounts:
        headers.append("Mounts")
        _add_mount_info_to_servers(servers)

    table = format_table(servers, headers)
    click.echo(table)


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
@click.option("--status-filter", type=click.Choice(["running", "stopped", "error"]), help="Filter by status")
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
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
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
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

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
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)

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
        factory = get_factory(ctx.obj.get("workspace") if ctx.obj else None)
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

        # Build project structure (this will create config.yaml inside the project)
        project_path = factory.build_project(name, config_data)
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

        git_status = publisher.check_git_status(project_path_obj)
        if git_status["valid"]:
            git_info = git_status["git_info"]
            info_message(f"GitHub repository: {git_info['full_name']}")
            if git_status["needs_commit"]:
                warning_message("Detected uncommitted changes")
            if git_status["needs_push"]:
                warning_message("Detected unpushed commits")
        else:
            warning_message(f"Unable to detect Git information: {git_status.get('error', 'Unknown error')}")
    except Exception as e:
        warning_message(f"Unable to extract project metadata: {e}")


def _collect_configuration(publisher: Any, cli_helper: Any, project_path_obj: Path) -> dict[str, Any]:
    """Collect project configuration"""
    has_config, existing_config = publisher.check_hub_configuration(project_path_obj)

    if not has_config:
        try:
            existing_info = publisher.extract_project_metadata(project_path_obj)
            git_info = publisher.detect_git_info(project_path_obj)
            existing_info["github_username"] = git_info.get("owner", "")
        except Exception:
            existing_info = {}

        config = cli_helper.collect_project_configuration(existing_info)

        if not publisher.add_hub_configuration(project_path_obj, config):
            cli_helper.show_error_message("Failed to save configuration")
            sys.exit(1)
        return dict(config) if isinstance(config, dict) else {}
    else:
        return dict(existing_config)


def _handle_git_operations(publisher: Any, cli_helper: Any, project_path_obj: Path) -> None:
    """Handle Git status checking and operations"""
    git_status = publisher.check_git_status(project_path_obj)

    if not git_status["valid"]:
        cli_helper.show_error_message(f"Git check failed: {git_status.get('error', 'Unknown')}")
        sys.exit(1)

    # Handle uncommitted changes
    if git_status["needs_commit"]:
        cli_helper.show_warning_message("Detected uncommitted changes")
        if cli_helper.confirm_git_operations("commit"):
            if not publisher.commit_changes(project_path_obj):
                cli_helper.show_error_message("Commit failed, please commit changes manually")
                sys.exit(1)
        else:
            cli_helper.show_error_message("Please commit or stage your changes first")
            sys.exit(1)

    # Handle unpushed commits
    if git_status["needs_push"]:
        cli_helper.show_warning_message("Detected unpushed commits")
        if cli_helper.confirm_git_operations("push"):
            if not publisher.push_changes(project_path_obj):
                cli_helper.show_error_message("Push failed, please push to GitHub manually")
                sys.exit(1)
        else:
            cli_helper.show_error_message("Please push your changes to GitHub first")
            sys.exit(1)


def _handle_publish_result(
    result: Any, publisher: Any, cli_helper: Any, project_path_obj: Path, config: dict[str, Any]
) -> None:
    """Handle publishing result"""
    if not result.success:
        cli_helper.show_error_message(result.message)
        sys.exit(1)

    if result.data.get("method") == "api":
        cli_helper.show_publish_success(result.data.get("repo_url", ""), result.data.get("registration_url", ""))
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
@click.pass_context
def publish(ctx: click.Context, project_path: str, dry_run: bool) -> None:
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

            # Collect configuration
            config = _collect_configuration(publisher, cli_helper, project_path_obj)

            # Handle Git operations
            _handle_git_operations(publisher, cli_helper, project_path_obj)

            # Execute publishing
            result = publisher.publish_project(project_path, config)

            # Handle result
            _handle_publish_result(result, publisher, cli_helper, project_path_obj, config)

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

        # Write configuration file with proper resource management
        try:
            with open(output, "w") as f:
                yaml.dump(config_template, f, default_flow_style=False, sort_keys=False)
        except OSError as e:
            raise click.ClickException(f"Failed to write configuration file: {e}") from e

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


@config.command("list")
@click.pass_context
def list_configs(ctx: click.Context) -> None:
    """List configuration files"""
    try:
        workspace = (ctx.obj.get("workspace") if ctx.obj else None) or "."
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
