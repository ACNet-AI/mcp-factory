#!/usr/bin/env python3
"""MCP Factory CLI - Main entry file.

Provides mcpf command-line tool for creating and managing MCP servers.
"""

import os
import sys
import tempfile
from typing import Any, Dict, Optional

import click

from mcp_factory.cli import CLI_DESCRIPTION, CLI_NAME, __version__
from mcp_factory.cli.utils import (
    create_server_config,
    error_message,
    find_config_files,
    get_config_dir,
    get_config_template,
    get_factory,
    info_message,
    is_verbose,
    save_config_file,
    success_message,
    validate_config_file,
    verbose_message,
)


@click.group(name=CLI_NAME, help=CLI_DESCRIPTION)
@click.version_option(version=__version__, prog_name=CLI_NAME)
@click.option(
    "--config-dir",
    default=None,
    help="Specify configuration directory path (default: ~/.mcpf)",
    type=click.Path(),
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Silent mode")
@click.pass_context
def cli(ctx: click.Context, config_dir: Optional[str], verbose: bool, quiet: bool) -> None:
    """MCP Factory CLI - Create and manage MCP servers."""
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Set global configuration
    ctx.obj["config_dir"] = config_dir or os.path.expanduser("~/.mcpf")
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    # Create configuration directory
    os.makedirs(ctx.obj["config_dir"], exist_ok=True)


@cli.command()
@click.option(
    "--type",
    "-t",
    default="simple",
    type=click.Choice(["full", "simple", "minimal"]),
    help="Template type (default: simple)",
)
@click.option("--output", "-o", help="Output file path")
@click.pass_context
def template(ctx: click.Context, type: str, output: Optional[str]) -> None:
    """Generate configuration template."""
    verbose = is_verbose(ctx)

    verbose_message(f"Generating {type} type configuration template", verbose)

    template_content = get_config_template(type)
    if not template_content:
        sys.exit(1)

    if output:
        # Save to file
        try:
            output_dir = os.path.dirname(output)
            if output_dir:  # Only create directory if it's not empty
                os.makedirs(output_dir, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(template_content)
            success_message(f"Template saved to: {output}")
        except Exception as e:
            error_message(f"Failed to save template: {e}")
            sys.exit(1)
    else:
        # Output to terminal
        click.echo(template_content)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.pass_context
def validate(ctx: click.Context, config_file: str) -> None:
    """Validate configuration file."""
    verbose = is_verbose(ctx)

    if not validate_config_file(config_file, verbose):
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--host", "-h", help="Override host address")
@click.option("--port", "-p", type=int, help="Override port number")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def run(
    ctx: click.Context, config_file: str, host: Optional[str], port: Optional[int], debug: bool
) -> None:
    """Run MCP server."""
    config_dir = get_config_dir(ctx)
    verbose = is_verbose(ctx)

    # Validate configuration file
    verbose_message(f"Validating configuration file: {config_file}", verbose)
    if not validate_config_file(config_file, verbose):
        sys.exit(1)

    try:
        # Get Factory instance
        factory = get_factory(config_dir)

        # Create server
        verbose_message("Creating server instance", verbose)
        override_params: Dict[str, Any] = {}
        if host:
            override_params["host"] = host
        if port:
            override_params["port"] = port
        if debug:
            override_params["debug"] = debug

        server = factory.create_managed_server(config_path=config_file, **override_params)

        info_message(f"Starting server: {server.name}")
        click.echo(
            f"🌐 Access URL: http://{server._runtime_kwargs.get('host', 'localhost')}:{server._runtime_kwargs.get('port', 8888)}/api/mcp"
        )
        click.echo("⏹️  Press Ctrl+C to stop server")

        # Run server
        server.run()

    except KeyboardInterrupt:
        success_message("\nServer stopped")
    except Exception as e:
        error_message(f"Failed to run server: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def list(ctx: click.Context) -> None:
    """List all servers and authentication providers."""
    config_dir = get_config_dir(ctx)

    try:
        factory = get_factory(config_dir)

        # List servers
        servers = factory.list_servers()
        click.echo("📊 Server List:")
        if servers:
            for name, info in servers.items():
                click.echo(f"  🖥️  {name}: {info.get('instructions', 'No description')}")
        else:
            click.echo("  (No servers)")

        # List authentication providers
        providers = factory.list_auth_providers()
        click.echo("\n🔐 Authentication Providers:")
        if providers:
            for provider_id, provider_type in providers.items():
                click.echo(f"  🔑 {provider_id} ({provider_type})")
        else:
            click.echo("  (No authentication providers)")

        # List configuration files
        config_files = find_config_files(".")
        if config_files:
            click.echo("\n📄 Configuration files in current directory:")
            for config_file in config_files:
                click.echo(f"  📋 {config_file}")

    except Exception as e:
        error_message(f"Failed to list resources: {e}")
        sys.exit(1)


@cli.command()
@click.argument("provider_id")
@click.option(
    "--type", "-t", required=True, type=click.Choice(["auth0"]), help="Authentication provider type"
)
@click.option("--domain", required=True, help="Auth0 domain")
@click.option("--client-id", required=True, help="Client ID")
@click.option("--client-secret", required=True, help="Client secret")
@click.option("--audience", help="Target audience (optional)")
@click.option("--roles-namespace", help="Roles namespace (optional)")
@click.pass_context
def auth(
    ctx: click.Context,
    provider_id: str,
    type: str,
    domain: str,
    client_id: str,
    client_secret: str,
    audience: Optional[str],
    roles_namespace: Optional[str],
) -> None:
    """Create authentication provider."""
    config_dir = get_config_dir(ctx)
    verbose = is_verbose(ctx)

    try:
        factory = get_factory(config_dir)

        config = {
            "domain": domain,
            "client_id": client_id,
            "client_secret": client_secret,
        }

        if audience:
            config["audience"] = audience
        if roles_namespace:
            config["roles_namespace"] = roles_namespace

        verbose_message(f"Creating {type} authentication provider: {provider_id}", verbose)

        provider = factory.create_auth_provider(
            provider_id=provider_id, provider_type=type, config=config
        )

        if provider:
            success_message(
                f"Authentication provider '{provider_id}' ({type}) created successfully"
            )
        else:
            error_message("Failed to create authentication provider")
            sys.exit(1)

    except Exception as e:
        error_message(f"Failed to create authentication provider: {e}")
        sys.exit(1)


@cli.command("quick")
@click.option("--name", "-n", help="Server name")
@click.option("--port", "-p", default=8888, help="Server port (default: 8888)")
@click.option("--host", "-h", default="localhost", help="Server host (default: localhost)")
@click.option("--auth", help="Authentication provider ID")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option("--save-config", help="Save configuration to file")
@click.pass_context
def quick_server(
    ctx: click.Context,
    name: Optional[str],
    port: int,
    host: str,
    auth: Optional[str],
    debug: bool,
    save_config: Optional[str],
) -> None:
    """Quickly create and run server."""
    config_dir = get_config_dir(ctx)
    verbose = is_verbose(ctx)

    # Generate server name
    if not name:
        name = f"quick-server-{port}"

    verbose_message(f"Creating quick server: {name}", verbose)

    try:
        # Create configuration
        config = create_server_config(
            name=name, port=port, host=host, auth_provider=auth, debug=debug
        )

        # Save configuration file (if specified)
        temp_config_file = None
        if save_config:
            if save_config_file(config, save_config):
                config_file = save_config
            else:
                sys.exit(1)
        else:
            # Create temporary configuration file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False, encoding="utf-8"
            ) as f:
                import yaml

                yaml.dump(config, f, indent=2, default_flow_style=False, allow_unicode=True)
                temp_config_file = f.name
                config_file = temp_config_file
                verbose_message(f"Using temporary configuration file: {config_file}", verbose)

        # Get Factory and create server
        factory = get_factory(config_dir)
        server = factory.create_managed_server(config_path=config_file)

        info_message(f"Quick server starting: {name}")
        click.echo(f"🌐 Access URL: http://{host}:{port}/api/mcp")
        click.echo("⏹️  Press Ctrl+C to stop server")

        # Run server
        try:
            server.run()
        finally:
            # Clean up temporary file
            if temp_config_file and os.path.exists(temp_config_file):
                os.unlink(temp_config_file)
                verbose_message(
                    f"Cleaned up temporary configuration file: {temp_config_file}", verbose
                )

    except KeyboardInterrupt:
        success_message("\nQuick server stopped")
    except Exception as e:
        error_message(f"Failed to start quick server: {e}")
        if temp_config_file and os.path.exists(temp_config_file):
            os.unlink(temp_config_file)
        sys.exit(1)


def main() -> None:
    """CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled", err=True)
        sys.exit(1)
    except Exception as e:
        error_message(f"CLI execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
