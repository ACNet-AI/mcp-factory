"""CLI utility functions module.

Provides CLI-related utility functions including output formatting and configuration helpers.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import click
import yaml

from mcp_factory import FastMCPFactory, config_validator

# Singleton Factory manager
_factory_instance: Optional[FastMCPFactory] = None


def get_factory(config_dir: str) -> FastMCPFactory:
    """Get or create Factory instance (singleton pattern)."""
    global _factory_instance

    if _factory_instance is None:
        factory_config_path = os.path.join(config_dir, "factory.yaml")
        if os.path.exists(factory_config_path):
            _factory_instance = FastMCPFactory(factory_config_path)
        else:
            _factory_instance = FastMCPFactory()

    return _factory_instance


def success_message(message: str) -> None:
    """Output success message (green)."""
    click.echo(click.style(f"✅ {message}", fg="green"))


def error_message(message: str) -> None:
    """Output error message (red)."""
    click.echo(click.style(f"❌ {message}", fg="red"), err=True)


def warning_message(message: str) -> None:
    """Output warning message (yellow)."""
    click.echo(click.style(f"⚠️ {message}", fg="yellow"))


def info_message(message: str) -> None:
    """Output info message (blue)."""
    click.echo(click.style(f"ℹ️ {message}", fg="blue"))


def verbose_message(message: str, verbose: bool = False) -> None:
    """Output verbose message (only in verbose mode)."""
    if verbose:
        click.echo(click.style(f"🔍 {message}", fg="cyan"))


def get_config_template(template_type: str = "full") -> str:
    """Get configuration template content.

    Args:
        template_type: Template type ("full", "simple", "minimal")

    Returns:
        Template content string
    """
    # Get project root directory
    cli_dir = Path(__file__).parent
    project_root = cli_dir.parent.parent

    if template_type == "simple":
        template_path = project_root / "demo" / "config.yaml"
    elif template_type == "minimal":
        return """# Minimal MCP server configuration
server:
  name: "my-mcp-server"
  instructions: "My MCP server"
  host: "localhost"
  port: 8888
  transport: "streamable-http"

tools:
  expose_management_tools: true
"""
    else:  # full
        template_path = project_root / "examples" / "config.example.yaml"

    try:
        return template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        error_message(f"Template file not found: {template_path}")
        return ""


def validate_config_file(config_path: str, verbose: bool = False) -> bool:
    """Validate configuration file.

    Args:
        config_path: Configuration file path
        verbose: Whether to show detailed information

    Returns:
        Whether validation passed
    """
    if not os.path.exists(config_path):
        error_message(f"Configuration file not found: {config_path}")
        return False

    try:
        is_valid, config, errors = config_validator.validate_config_file(config_path)

        if is_valid:
            success_message(f"Configuration file validation passed: {config_path}")
            if verbose and config:
                info_message("Configuration content:")
                click.echo(yaml.dump(config, indent=2, default_flow_style=False))
            return True
        else:
            error_message(f"Configuration file validation failed: {config_path}")
            for error in errors:
                click.echo(f"  • {error}")
            return False

    except Exception as e:
        error_message(f"Error validating configuration file: {e}")
        return False


def create_server_config(
    name: str,
    port: int = 8888,
    host: str = "localhost",
    auth_provider: Optional[str] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    """Create server configuration dictionary.

    Args:
        name: Server name
        port: Port number
        host: Host address
        auth_provider: Authentication provider ID
        debug: Debug mode

    Returns:
        Configuration dictionary
    """
    config = {
        "server": {
            "name": name,
            "instructions": f"{name} - Created by mcpf CLI",
            "host": host,
            "port": port,
            "transport": "streamable-http",
            "debug": debug,
        },
        "tools": {
            "expose_management_tools": True,
        },
        "advanced": {
            "log_level": "DEBUG" if debug else "INFO",
            "streamable_http_path": "/api/mcp",
        },
    }

    if auth_provider:
        config["auth"] = {"provider_id": auth_provider}

    return config


def save_config_file(config: Dict[str, Any], file_path: str) -> bool:
    """Save configuration to file.

    Args:
        config: Configuration dictionary
        file_path: File path

    Returns:
        Whether save was successful
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, indent=2, default_flow_style=False, allow_unicode=True)

        success_message(f"Configuration file saved: {file_path}")
        return True

    except Exception as e:
        error_message(f"Failed to save configuration file: {e}")
        return False


def find_config_files(directory: str = ".") -> list[str]:
    """Find configuration files in directory.

    Args:
        directory: Search directory

    Returns:
        List of found configuration files
    """
    config_patterns = ["*.yaml", "*.yml"]
    config_files: list[str] = []

    for pattern in config_patterns:
        config_files.extend(str(f) for f in Path(directory).glob(pattern))

    return config_files


def get_config_dir(ctx: click.Context) -> str:
    """Get configuration directory from click context."""
    return ctx.obj.get("config_dir", os.path.expanduser("~/.mcpf"))


def is_verbose(ctx: click.Context) -> bool:
    """Get verbose flag from click context."""
    return ctx.obj.get("verbose", False)


def is_quiet(ctx: click.Context) -> bool:
    """Get quiet flag from click context."""
    return ctx.obj.get("quiet", False)
