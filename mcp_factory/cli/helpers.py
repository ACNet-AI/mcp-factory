"""
CLI Interactive Helper Module
Handles user input, configuration wizards and UI-related logic
"""

import textwrap
from typing import Any

import questionary
from questionary import Style
from rich.console import Console

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
        elif operation == "push":
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
