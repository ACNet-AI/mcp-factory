"""MCP Factory CLI Helpers

Provides helper classes and functions for CLI operations.
"""

from __future__ import annotations

import os
import textwrap
from pathlib import Path
from typing import Any

import questionary
import yaml
from questionary import Style
from rich.console import Console

# Import the new error filter
from .error_filter import UserFriendlyErrorHandler

# Custom CLI style - matches mcp-factory design
MCP_FACTORY_STYLE = Style(
    [
        ("qmark", "fg:#00bcd4 bold"),  # Question mark - cyan
        ("question", "bold"),  # Question text - bold
        ("answer", "fg:#4caf50 bold"),  # Submitted answer - green
        ("pointer", "fg:#00bcd4 bold"),  # Selection pointer - cyan
        ("highlighted", "fg:#00bcd4 bold"),  # Highlighted option - cyan
        ("selected", "fg:#4caf50"),  # Selected item - green
        ("separator", "fg:#757575"),  # Separator - gray
        ("instruction", "fg:#757575"),  # Usage instructions - gray
        ("text", "fg:#90a4ae"),  # Default value text - light gray-blue (elegant)
        ("disabled", "fg:#9e9e9e italic"),  # Disabled option - gray italic
    ]
)


class BaseCLIHelper:
    """Base CLI helper - Provides common user interaction functionality"""

    def __init__(self) -> None:
        self.console = Console()

    def show_success_message(self, message: str) -> None:
        """Display success message"""
        self.console.print(f"✅ {message}", style="bold green")

    def show_error_message(self, message: str) -> None:
        """Display error message"""
        self.console.print(f"❌ {message}", style="bold red")

    def show_warning_message(self, message: str) -> None:
        """Display warning message"""
        self.console.print(f"⚠️ {message}", style="bold yellow")

    def show_info_message(self, message: str) -> None:
        """Display info message"""
        self.console.print(f"ℹ️ {message}", style="blue")

    def confirm_action(self, message: str, default: bool = False) -> bool:
        """Confirm action"""
        result = questionary.confirm(message, default=default, style=MCP_FACTORY_STYLE).ask()
        return bool(result)

    def text_input(self, message: str, default: str = "") -> str:
        """Text input"""
        result = questionary.text(message, default=default, style=MCP_FACTORY_STYLE).ask()
        return str(result) if result else ""

    def select_choice(self, message: str, choices: list[str]) -> str:
        """Single selection"""
        result = questionary.select(message, choices=choices, style=MCP_FACTORY_STYLE).ask()
        return str(result) if result else ""

    def multi_select(self, message: str, choices: list[dict[str, str]]) -> list[str]:
        """Multiple selection"""
        result = questionary.checkbox(message, choices=choices, style=MCP_FACTORY_STYLE).ask()
        return result or []

    def press_to_continue(self, message: str = "Press Enter to continue") -> None:
        """Wait for user to press key to continue"""
        questionary.press_any_key_to_continue(message, style=MCP_FACTORY_STYLE).ask()

    def show_separator(self, title: str = "") -> None:
        """Display separator line"""
        if title:
            self.console.print(f"\n{title}", style="bold cyan")
            self.console.print("=" * len(title), style="cyan")
        else:
            self.console.print("-" * 50, style="dim")


class ProjectCLIHelper(BaseCLIHelper):
    """Project-related CLI helper"""

    def collect_project_info(self) -> dict[str, Any]:
        """Collect basic project information"""
        self.console.print("🚀 Project Initialization Wizard", style="bold cyan")
        self.show_separator()

        name = self.text_input("📝 Project Name:")
        description = self.text_input("📝 Project Description:")

        return {
            "name": name,
            "description": description,
        }

    def collect_server_config(self) -> dict[str, Any]:
        """Collect server configuration information"""
        self.console.print("⚙️ Server Configuration", style="bold yellow")

        host = self.text_input("🌐 Host Address:", default="localhost")
        port = self.text_input("🔌 Port Number:", default="8000")

        transport = self.select_choice("🚀 Transport Method:", choices=["stdio", "sse", "http"])

        enable_auth = self.confirm_action("🔐 Enable Authentication?")
        enable_debug = self.confirm_action("🐛 Enable Debug Mode?")

        return {
            "host": host,
            "port": int(port) if port.isdigit() else 8000,
            "transport": transport,
            "auth": enable_auth,
            "debug": enable_debug,
        }

    def show_project_summary(self, config: dict[str, Any]) -> None:
        """Display project configuration summary"""
        self.show_separator("📋 Project Configuration Summary")

        for key, value in config.items():
            if isinstance(value, bool):
                display_value = "✅" if value else "❌"
            else:
                display_value = str(value)
            self.console.print(f"   {key}: {display_value}")

    def confirm_server_start(self) -> bool:
        """Confirm whether to start server immediately"""
        return self.confirm_action("🚀 Start server immediately?", default=True)


class PublishCLIHelper(BaseCLIHelper):
    """Publishing-related CLI helper"""

    def collect_project_configuration(self, existing_info: dict[str, str]) -> dict[str, Any]:
        """
        Collect project configuration information

        Args:
            existing_info: Existing project information

        Returns:
            User input configuration information
        """
        self.console.print("🚀 MCP Servers Hub Publishing Configuration Wizard", style="bold cyan")
        self.console.print(
            textwrap.dedent("""
                To publish your project to GitHub and register to MCP Servers Hub,
                some basic information is needed.
            """).strip(),
            style="dim",
        )
        self.console.print()

        # Collect basic information
        name = self.text_input("Project Name:", existing_info.get("name", ""))
        description = self.text_input("Project Description:", existing_info.get("description", ""))
        author = self.text_input("Author Name:", existing_info.get("author", ""))
        github_username = self.text_input("GitHub Username:", existing_info.get("github_username", ""))

        # Select categories
        categories = self.multi_select(
            "Select Project Categories:",
            choices=[
                {"name": "Tools", "value": "tools"},
                {"name": "Data Processing", "value": "data"},
                {"name": "Communication", "value": "communication"},
                {"name": "Productivity", "value": "productivity"},
                {"name": "AI Integration", "value": "ai"},
            ],
        )

        return {
            "name": name,
            "description": description,
            "author": author,
            "github_username": github_username,
            "categories": categories or ["tools"],
        }

    def confirm_git_operations(self, operation: str) -> bool:
        """
        Confirm Git operations

        Args:
            operation: Operation type ("commit" or "push")

        Returns:
            User confirmation result
        """
        if operation == "commit":
            return self.confirm_action("Uncommitted changes detected, auto-commit?", default=False)
        if operation == "push":
            return self.confirm_action("Unpushed commits detected, auto-push to GitHub?", default=False)
        return False

    def show_installation_guide(self, install_url: str, repo_name: str, project_name: str) -> None:
        """
        Display GitHub App installation guide

        Args:
            install_url: Installation URL
            repo_name: Repository name
            project_name: Project name
        """
        guide_text = textwrap.dedent(f"""
            🚀 Publish Project to GitHub and Register to MCP Servers Hub

            📍 Project: {project_name}
            📍 Repository: {repo_name}

            🔗 GitHub App installation required for automatic publishing

            📋 Installation Steps:
            1. About to open GitHub App installation page
            2. Select your account or organization
            3. ⭐ Important: Select "Only select repositories"
            4. ⭐ Important: Choose repository "{repo_name}"
            5. Click "Install" to complete installation

            💡 Notes:
            - GitHub App will monitor your repository changes
            - Registry updates automatically when you push code
            - You can manage permissions in GitHub settings anytime

            Press Enter to open installation page...
        """).strip()

        self.console.print(guide_text, style="cyan")
        self.press_to_continue("Press Enter to continue")

    def wait_for_installation_completion(self) -> None:
        """Wait for user to complete installation"""
        self.console.print("⏳ Please complete GitHub App installation in your browser", style="yellow")
        self.console.print("After installation, return to terminal and press Enter to continue...", style="dim")
        self.press_to_continue("Press Enter to continue")

    def handle_oauth_authentication(
        self, publisher: Any, project_name: str, project_path: str, force_update: bool = False
    ) -> dict[str, Any]:
        """
        Handle GitHub App OAuth authentication workflow

        Args:
            publisher: ProjectPublisher instance
            project_name: Name of the project
            project_path: Path to the project directory
            force_update: Force re-authentication even if config exists

        Returns:
            dict containing success status, github_username, installation_id, and error info
        """
        try:
            # Step 1: Start GitHub App installation session
            self.console.print("🚀 Starting GitHub App installation...", style="cyan")
            install_result = publisher.start_session_based_installation(project_name)

            if not install_result.get("success"):
                return {
                    "success": False,
                    "error": f"Failed to start installation: {install_result.get('error', 'Unknown error')}",
                }

            # Step 2: Get GitHub username (try to extract from project or ask user)
            github_username = ""
            try:
                # Try to extract from project metadata first
                metadata = publisher.extract_project_metadata(project_path)
                github_username = metadata.get("github_username", "")
            except Exception:
                pass

            if not github_username:
                github_username = self.text_input("GitHub Username:", "")
                if not github_username:
                    return {"success": False, "error": "GitHub username is required"}

            # Step 3: Create installation URL with suggested repository
            install_url = publisher.create_installation_url_for_user(github_username, project_name)
            repo_name = f"{github_username}/{project_name}"

            # Step 4: Show installation guide and open browser
            self.show_installation_guide(install_url, repo_name, project_name)

            import webbrowser

            try:
                webbrowser.open(install_url)
                self.console.print("🌐 Browser opened for GitHub App installation", style="green")
            except Exception as e:
                self.console.print(f"⚠️ Could not open browser automatically: {e}", style="yellow")
                self.console.print(f"Please manually open: {install_url}", style="yellow")

            # Step 5: Wait for user to complete installation
            self.wait_for_installation_completion()

            # Step 6: Check installation status and get installation_id
            self.console.print("🔍 Checking installation status...", style="cyan")

            # Give user a moment to complete installation
            import time

            time.sleep(2)

            status = publisher.check_user_installation_status(github_username)

            if status.get("installed"):
                installations = status.get("installations", [])
                if installations:
                    # Use the first (most recent) installation
                    installation_id = installations[0].get("id")
                    if installation_id:
                        self.console.print("✅ GitHub App installation verified!", style="green")
                        return {
                            "success": True,
                            "github_username": github_username,
                            "installation_id": str(installation_id),
                            "installation_info": installations[0],
                        }

                return {"success": False, "error": "Installation found but no valid installation ID available"}
            # Installation not found, but maybe user needs more time
            retry = self.confirm_action("Installation not detected. Would you like to retry checking?", default=True)
            if retry:
                time.sleep(3)
                # Retry once
                status = publisher.check_user_installation_status(github_username)
                if status.get("installed"):
                    installations = status.get("installations", [])
                    if installations:
                        installation_id = installations[0].get("id")
                        if installation_id:
                            self.console.print("✅ GitHub App installation verified on retry!", style="green")
                            return {
                                "success": True,
                                "github_username": github_username,
                                "installation_id": str(installation_id),
                                "installation_info": installations[0],
                            }

            return {
                "success": False,
                "timeout": True,
                "error": "GitHub App installation not detected. Please ensure the app is installed and try again.",
            }

        except KeyboardInterrupt:
            self.console.print("\n❌ Installation cancelled by user", style="red")
            return {"success": False, "user_cancelled": True, "error": "Installation cancelled by user"}
        except Exception as e:
            self.console.print(f"\n❌ Error during OAuth authentication: {e}", style="red")
            return {"success": False, "error": f"Authentication error: {e!s}"}

    def show_publish_success(self, repo_url: str = "", registry_url: str = "") -> None:
        """
        Display publish success message

        Args:
            repo_url: Repository URL
            registry_url: Registry URL
        """
        self.console.print("\n🎉 Project published successfully!", style="bold green")

        if repo_url:
            self.console.print(f"🔗 Repository URL: {repo_url}", style="green")

        if registry_url:
            self.console.print(f"📋 Registry URL: {registry_url}", style="green")

        success_message = textwrap.dedent("""
            ✅ Your MCP project has been successfully published and registered to the server hub!
        """).strip()

        self.console.print(f"\n{success_message}", style="bold green")


class ConfigCLIHelper(BaseCLIHelper):
    """Configuration-related CLI helper"""

    def collect_template_info(self) -> dict[str, Any]:
        """Collect configuration template information"""
        self.console.print("📝 Configuration Template Generation Wizard", style="bold cyan")
        self.show_separator()

        name = self.text_input("Project Name:")
        description = self.text_input("Project Description:")

        include_mounts = self.confirm_action("Include mount server examples?", default=False)

        return {
            "name": name,
            "description": description,
            "include_mounts": include_mounts,
        }

    def show_validation_results(self, results: dict[str, Any]) -> None:
        """Display configuration validation results"""
        self.show_separator("📋 Configuration Validation Results")

        if results.get("valid", False):
            self.show_success_message("Configuration file validation passed")
        else:
            self.show_error_message("Configuration file validation failed")

            errors = results.get("errors", [])
            for error in errors:
                self.console.print(f"  • {error}", style="red")

    def confirm_delete_server(self, server_id: str) -> bool:
        """Confirm server deletion"""
        self.show_warning_message(f"About to delete server '{server_id}'")
        return self.confirm_action("Confirm deletion? This action cannot be undone.", default=False)

    def check_configuration(self, config_file: str | None = None, auto_fix: bool = False) -> dict[str, Any]:
        """
        Check configuration for common issues

        Args:
            config_file: Path to configuration file (optional)
            auto_fix: Whether to automatically fix issues

        Returns:
            Dictionary containing check results
        """
        issues = []
        fixed_issues = []

        self.show_separator("🔍 Configuration Check")

        try:
            # 1. Check if config file exists
            if config_file:
                config_path = Path(config_file)
                if not config_path.exists():
                    issue = {
                        "type": "missing_file",
                        "severity": "critical",
                        "description": f"Configuration file '{config_file}' not found",
                        "auto_fixable": True,
                        "fix_suggestion": f"Create configuration file with: mcp-factory config template > {config_file}",
                    }
                    issues.append(issue)

                    if auto_fix:
                        if self._create_default_config(config_path):
                            fixed_issues.append(issue)
                            issues.remove(issue)
            else:
                # Check current directory for config files
                config_files = list(Path().glob("*.yaml")) + list(Path().glob("*.yml"))
                if not config_files:
                    issue = {
                        "type": "no_config_found",
                        "severity": "warning",
                        "description": "No configuration files found in current directory",
                        "auto_fixable": True,
                        "fix_suggestion": "Create a configuration file with: mcp-factory config template > config.yaml",
                    }
                    issues.append(issue)

                    if auto_fix:
                        if self._create_default_config(Path("config.yaml")):
                            fixed_issues.append(issue)
                            issues.remove(issue)
                            config_file = "config.yaml"

            # 2. Validate YAML syntax and structure
            if config_file and Path(config_file).exists():
                yaml_issues, yaml_fixed = self._check_yaml_issues(config_file, auto_fix)
                issues.extend(yaml_issues)
                fixed_issues.extend(yaml_fixed)

                # 3. Check required fields
                field_issues, field_fixed = self._check_required_fields(config_file, auto_fix)
                issues.extend(field_issues)
                fixed_issues.extend(field_fixed)

                # 4. Check data types
                type_issues, type_fixed = self._check_data_types(config_file, auto_fix)
                issues.extend(type_issues)
                fixed_issues.extend(type_fixed)

                # 5. Check environment variables
                env_issues = self._check_environment_variables(config_file)
                issues.extend(env_issues)

        except Exception as e:
            self.show_error_message(f"Configuration check failed: {e}")

        return {
            "issues": issues,
            "fixed_issues": fixed_issues,
            "has_errors": any(issue["severity"] == "critical" for issue in issues),
            "has_warnings": any(issue["severity"] == "warning" for issue in issues),
            "config_file": config_file,
        }

    def show_check_results(self, results: dict[str, Any]) -> None:
        """Display configuration check results"""
        issues = results.get("issues", [])
        fixed_issues = results.get("fixed_issues", [])

        # Show fixed issues first
        if fixed_issues:
            self.show_separator("✅ Auto-Fixed Issues")
            for issue in fixed_issues:
                self.console.print(f"  🔧 Fixed: {issue['description']}", style="green")

        # Show remaining issues
        if issues:
            self.show_separator("⚠️  Remaining Issues")

            critical_issues = [i for i in issues if i["severity"] == "critical"]
            warning_issues = [i for i in issues if i["severity"] == "warning"]

            if critical_issues:
                self.console.print("🚨 Critical Issues:", style="bold red")
                for issue in critical_issues:
                    self.console.print(f"  ❌ {issue['description']}", style="red")
                    if issue.get("fix_suggestion"):
                        self.console.print(f"     💡 Fix: {issue['fix_suggestion']}", style="blue")

            if warning_issues:
                self.console.print("\n⚠️  Warnings:", style="bold yellow")
                for issue in warning_issues:
                    self.console.print(f"  ⚠️  {issue['description']}", style="yellow")
                    if issue.get("fix_suggestion"):
                        self.console.print(f"     💡 Suggestion: {issue['fix_suggestion']}", style="blue")
        else:
            self.show_success_message("Configuration check passed! No issues found.")

        # Show summary
        if issues or fixed_issues:
            self.console.print("\n📊 Summary:")
            if fixed_issues:
                self.console.print(f"  ✅ Fixed: {len(fixed_issues)} issues", style="green")
            if issues:
                critical_count = len([i for i in issues if i["severity"] == "critical"])
                warning_count = len([i for i in issues if i["severity"] == "warning"])
                if critical_count:
                    self.console.print(f"  ❌ Critical: {critical_count} issues", style="red")
                if warning_count:
                    self.console.print(f"  ⚠️  Warnings: {warning_count} issues", style="yellow")

    def _create_default_config(self, config_path: Path) -> bool:
        """Create a default configuration file"""
        try:
            from ..config.manager import get_default_config

            default_config = get_default_config()

            with config_path.open("w") as f:
                yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

            self.show_success_message(f"Created default configuration: {config_path}")
            return True

        except Exception as e:
            self.show_error_message(f"Failed to create default config: {e}")
            return False

    def _check_yaml_issues(self, config_file: str, auto_fix: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Check for YAML syntax issues"""
        issues = []
        fixed_issues: list[dict[str, Any]] = []

        try:
            with open(config_file) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            issue = {
                "type": "yaml_syntax",
                "severity": "critical",
                "description": f"YAML syntax error: {e}",
                "auto_fixable": False,
                "fix_suggestion": "Please check YAML syntax, especially indentation and special characters",
            }
            issues.append(issue)
        except Exception as e:
            issue = {
                "type": "file_read_error",
                "severity": "critical",
                "description": f"Cannot read configuration file: {e}",
                "auto_fixable": False,
                "fix_suggestion": "Check file permissions and existence",
            }
            issues.append(issue)

        return issues, fixed_issues

    def _check_required_fields(
        self, config_file: str, auto_fix: bool
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Check for required configuration fields"""
        issues = []
        fixed_issues = []

        try:
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}

            changed = False

            # Check for server name
            if "server" not in config:
                config["server"] = {}
                changed = True

            server_config = config.get("server", {})

            if not server_config.get("name"):
                issue = {
                    "type": "missing_server_name",
                    "severity": "critical",
                    "description": "Server name is required",
                    "auto_fixable": True,
                    "fix_suggestion": "Add 'name' field under 'server' section",
                }

                if auto_fix:
                    server_config["name"] = "my-server"
                    config["server"] = server_config
                    changed = True
                    fixed_issues.append(issue)
                else:
                    issues.append(issue)

            # Check for transport
            if not server_config.get("transport"):
                issue = {
                    "type": "missing_transport",
                    "severity": "warning",
                    "description": "Transport method not specified",
                    "auto_fixable": True,
                    "fix_suggestion": "Add 'transport: stdio' or 'transport: ws' under 'server' section",
                }

                if auto_fix:
                    server_config["transport"] = "stdio"
                    config["server"] = server_config
                    changed = True
                    fixed_issues.append(issue)
                else:
                    issues.append(issue)

            # Save changes if auto-fix was applied
            if changed and auto_fix:
                with open(config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            issue = {
                "type": "validation_error",
                "severity": "critical",
                "description": f"Cannot validate configuration: {e}",
                "auto_fixable": False,
                "fix_suggestion": "Check configuration file format",
            }
            issues.append(issue)

        return issues, fixed_issues

    def _check_data_types(self, config_file: str, auto_fix: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Check for incorrect data types"""
        issues = []
        fixed_issues = []

        try:
            with open(config_file) as f:
                config = yaml.safe_load(f) or {}

            changed = False
            server_config = config.get("server", {})

            # Check port type
            if "port" in server_config:
                port_value = server_config["port"]
                if isinstance(port_value, str) and port_value.isdigit():
                    issue = {
                        "type": "port_type_error",
                        "severity": "warning",
                        "description": f"Port should be a number, not string: '{port_value}'",
                        "auto_fixable": True,
                        "fix_suggestion": f"Change port from '{port_value}' to {port_value}",
                    }

                    if auto_fix:
                        server_config["port"] = int(port_value)
                        config["server"] = server_config
                        changed = True
                        fixed_issues.append(issue)
                    else:
                        issues.append(issue)

            # Save changes if auto-fix was applied
            if changed and auto_fix:
                with open(config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            issue = {
                "type": "type_check_error",
                "severity": "warning",
                "description": f"Cannot check data types: {e}",
                "auto_fixable": False,
                "fix_suggestion": "Manual review recommended",
            }
            issues.append(issue)

        return issues, fixed_issues

    def _check_environment_variables(self, config_file: str) -> list[dict[str, Any]]:
        """Check for environment variable configuration"""
        issues = []

        # Common environment variables that might be needed
        important_env_vars = [
            ("JWT_SECRET_KEY", "Required for authentication"),
            ("LOG_LEVEL", "Controls logging verbosity"),
            ("MCP_HOST", "Server host configuration"),
            ("MCP_PORT", "Server port configuration"),
        ]

        for env_var, description in important_env_vars:
            if env_var not in os.environ:
                issue = {
                    "type": "missing_env_var",
                    "severity": "info",
                    "description": f"Environment variable '{env_var}' not set",
                    "auto_fixable": False,
                    "fix_suggestion": f"Set with: export {env_var}=<value> # {description}",
                }
                issues.append(issue)

        return issues


class ServerCLIHelper(BaseCLIHelper):
    """Server management-related CLI helper"""

    def show_server_list(self, servers: list[dict[str, Any]]) -> None:
        """Display server list"""
        if not servers:
            self.console.print("📭 No servers found", style="dim")
            return

        self.show_separator("📋 Server List")

        for server in servers:
            status_icon = self._get_status_icon(server.get("status", "unknown"))
            self.console.print(f"  {status_icon} {server.get('id', 'N/A')} - {server.get('name', 'N/A')}")

    def show_server_details(self, server: dict[str, Any]) -> None:
        """Display server details"""
        self.show_separator(f"📊 Server Details: {server.get('name', 'N/A')}")

        for key, value in server.items():
            if key == "status":
                value = f"{self._get_status_icon(value)} {value}"
            self.console.print(f"  {key}: {value}")

    def _get_status_icon(self, status: str) -> str:
        """Get status icon"""
        status_icons = {
            "running": "🟢",
            "stopped": "🔴",
            "error": "🟡",
            "unknown": "⚪",
        }
        return status_icons.get(status.lower(), "⚪")


class ServerNameResolver(BaseCLIHelper):
    """Server name resolver - supports server management by name"""

    def __init__(self) -> None:
        super().__init__()

    def resolve_server_identifier(self, factory: Any, name_or_id: str) -> str | None:
        """
        Resolve server name or ID to actual server ID

        Args:
            factory: MCPFactory instance
            name_or_id: Server name or ID

        Returns:
            str | None: Resolved server ID, None if not found
        """
        try:
            # Get all server information
            servers = factory.list_servers()

            if not servers:
                self.show_error_message("No servers found")
                return None

            # 1. Exact match: try as ID first
            exact_id_match = self._find_exact_id_match(servers, name_or_id)
            if exact_id_match:
                return exact_id_match

            # 2. Exact match: try as name
            exact_name_matches = self._find_exact_name_matches(servers, name_or_id)
            if len(exact_name_matches) == 1:
                server_id = exact_name_matches[0]["id"]
                return str(server_id) if server_id is not None else None
            if len(exact_name_matches) > 1:
                # Handle name conflicts
                return self._handle_name_conflicts(exact_name_matches, name_or_id)

            # 3. Fuzzy match: partial server name matching
            fuzzy_matches = self._find_fuzzy_matches(servers, name_or_id)
            if len(fuzzy_matches) == 1:
                self.show_info_message(f"Found fuzzy match: {fuzzy_matches[0]['name']}")
                server_id = fuzzy_matches[0]["id"]
                return str(server_id) if server_id is not None else None
            if len(fuzzy_matches) > 1:
                # Interactive selection
                return self._interactive_server_selection(fuzzy_matches, name_or_id)

            # 4. No match found
            self.show_error_message(f"Server with name or ID '{name_or_id}' not found")
            self._suggest_similar_servers(servers, name_or_id)
            return None

        except Exception as e:
            self.show_error_message(f"Error resolving server identifier: {e}")
            return None

    def _find_exact_id_match(self, servers: list[dict[str, Any]], identifier: str) -> str | None:
        """Find exact ID match"""
        for server in servers:
            if server.get("id") == identifier:
                server_id = server["id"]
                return str(server_id) if server_id is not None else None
        return None

    def _find_exact_name_matches(self, servers: list[dict[str, Any]], name: str) -> list[dict[str, Any]]:
        """Find exact name matches"""
        matches = []
        for server in servers:
            if server.get("name") == name:
                matches.append(server)
        return matches

    def _find_fuzzy_matches(self, servers: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
        """Find fuzzy matches"""
        matches = []
        query_lower = query.lower()

        for server in servers:
            server_name = server.get("name", "").lower()
            server_id = server.get("id", "").lower()

            # Check if name or ID contains query string
            if query_lower in server_name or query_lower in server_id:
                matches.append(server)

        return matches

    def _handle_name_conflicts(self, matches: list[dict[str, Any]], name: str) -> str | None:
        """Handle name conflicts"""
        self.show_warning_message(f"Found multiple servers named '{name}':")

        # Show conflicting servers
        choices = []
        for i, server in enumerate(matches):
            server_info = f"{server['name']} (ID: {server['id'][:8]}...)"
            choices.append(server_info)
            self.console.print(f"  {i + 1}. {server_info}")

        # Let user choose
        try:
            selected = self.select_choice("Please select the server to operate on:", choices)

            # Find corresponding server
            for i, choice in enumerate(choices):
                if choice == selected:
                    server_id = matches[i]["id"]
                    return str(server_id) if server_id is not None else None

        except (KeyboardInterrupt, EOFError):
            self.show_info_message("Operation cancelled")
            return None

        return None

    def _interactive_server_selection(self, matches: list[dict[str, Any]], query: str) -> str | None:
        """Interactive server selection"""
        self.show_info_message(f"Found multiple servers containing '{query}':")

        # Prepare choices
        choices = []
        for server in matches:
            server_status = self._get_status_icon(server.get("status", "unknown"))
            server_info = f"{server_status} {server['name']} (ID: {server['id'][:8]}...)"
            choices.append(server_info)

        # Add cancel option
        choices.append("❌ Cancel operation")

        try:
            selected = self.select_choice("Please select the server to operate on:", choices)

            # Handle cancel operation
            if selected == "❌ Cancel operation":
                self.show_info_message("Operation cancelled")
                return None

            # Find corresponding server
            for i, choice in enumerate(choices[:-1]):  # Exclude cancel option
                if choice == selected:
                    server_id = matches[i]["id"]
                    return str(server_id) if server_id is not None else None

        except (KeyboardInterrupt, EOFError):
            self.show_info_message("Operation cancelled")
            return None

        return None

    def _suggest_similar_servers(self, servers: list[dict[str, Any]], query: str) -> None:
        """Suggest similar servers"""
        if not servers:
            return

        self.show_info_message("Available servers:")
        for server in servers[:5]:  # Show only first 5
            status_icon = self._get_status_icon(server.get("status", "unknown"))
            self.console.print(f"  {status_icon} {server.get('name', 'N/A')} (ID: {server.get('id', 'N/A')[:8]}...)")

        if len(servers) > 5:
            self.console.print(f"  ... and {len(servers) - 5} more servers")

    def _get_status_icon(self, status: str) -> str:
        """Get status icon"""
        status_icons = {
            "running": "🟢",
            "stopped": "🔴",
            "error": "🟡",
            "unknown": "⚪",
        }
        return status_icons.get(status.lower(), "⚪")

    def show_resolved_server_info(self, factory: Any, server_id: str) -> None:
        """Show resolved server information"""
        try:
            server_info = factory.get_server_status(server_id)
            if server_info:
                name = server_info.get("name", "N/A")
                status = server_info.get("state", {}).get("status", "unknown")
                status_icon = self._get_status_icon(status)

                self.console.print(f"✅ Selected server: {status_icon} {name} (ID: {server_id[:8]}...)")
            else:
                self.show_warning_message(f"Unable to get details for server {server_id}")

        except Exception as e:
            self.show_warning_message(f"Error getting server information: {e}")


# Add smart error handling function
def handle_cli_error(error: Exception, operation: str | None = None, verbose: bool = False) -> None:
    """
    Handle CLI errors using intelligent error filtering

    Args:
        error: Exception that occurred
        operation: Description of the operation that failed
        verbose: Whether to show technical details
    """
    error_handler = UserFriendlyErrorHandler()
    error_info = error_handler.process_error(error, operation, verbose)

    # Display formatted error
    console = Console()
    error_display = error_handler.format_error_display(error_info)
    console.print(error_display, style="red")

    # If verbose mode is off but user might need more details
    if not verbose and error_info.get("technical_details"):
        console.print("\n💡 Use --verbose flag for technical details", style="dim")
