"""Project Builder - MVP Version

Focus on actual file system building, working with Template and Config modules
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Any

import yaml

from mcp_factory.config import get_default_config, merge_configs, normalize_config, validate_config

from ..exceptions import ProjectError
from .components import ComponentManager
from .constants import ALLOWED_MODULE_TYPES
from .template import BasicTemplate
from .validator import ProjectValidator, ValidationError

# ============================================================================
# Configuration and Constants
# ============================================================================

# Configure logging
logger = logging.getLogger(__name__)

# Common error message templates
ERROR_PROJECT_NOT_FOUND = "Project not found: {}"
ERROR_VALIDATION_FAILED = "Validation failed for project '{}': {}"
ERROR_BUILD_FAILED = "Failed to build project '{}': {}"
ERROR_CONFIG_VALIDATION = "Configuration validation failed: {}"

# Success messages
SUCCESS_MESSAGES = {
    "project_created": "✅ Project '{}' created successfully!",
    "project_path": "📁 Project path: {}",
    "jwt_config": "🔐 JWT authentication configuration: .env template file created",
    "jwt_warning": "⚠️ Please edit .env file and set real JWT authentication parameters",
    "usage_hint": "💡 To add functionality use:",
}

# Usage example templates
USAGE_EXAMPLES = [
    "   builder.add_tool_function('{}', 'tool_name', 'description')",
    "   builder.add_resource_function('{}', 'resource_name', 'description')",
    "   builder.add_prompt_function('{}', 'prompt_name', 'description')",
]

# ============================================================================
# Exception Definitions
# ============================================================================


class ProjectBuildError(Exception):
    """Project build exception"""


# ============================================================================
# Main Builder Class
# ============================================================================


class Builder:
    """MVP Project Builder

    Design Philosophy:
    - Focus on file system building, don't duplicate Template and Config responsibilities
    - Simple and direct build process
    - Good integration with existing modules
    - Support incremental and repeated builds
    """

    def __init__(self, workspace_root: str) -> None:
        """Initialize builder

        Args:
            workspace_root: Workspace root directory
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.template = BasicTemplate()
        self.validator = ProjectValidator()
        logger.info("Builder initialized with workspace: %s", workspace_root)

    # ========================================================================
    # Public Interface - Core Build Functionality
    # ========================================================================

    def build_project(
        self,
        name: str,
        user_config: dict[str, Any] | None = None,
        force: bool = False,
        git_init: bool = True,
    ) -> str:
        """Build MCP server project

        Args:
            name: Project name
            user_config: User configuration parameters (optional)
            force: Whether to force rebuild (delete existing content)
            git_init: Whether to initialize git repository (default True)

        Returns:
            Created project path

        Raises:
            ProjectBuildError: Raised when build fails
        """
        logger.info("Starting to build project: %s", name)

        # Create projects directory in workspace if it doesn't exist
        projects_dir = self.workspace_root / "projects"
        projects_dir.mkdir(parents=True, exist_ok=True)

        # Create project in the projects subdirectory
        project_path = projects_dir / name

        try:
            # Validate project name
            self.validator.validate_project_name(name)

            # Handle existing project
            if project_path.exists() and force:
                logger.warning("Force rebuilding project: %s", name)
                shutil.rmtree(project_path)

            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)

            # Get project structure definition
            structure = self.template.get_structure()

            # Build directory structure
            self._build_directories(project_path, structure)

            # Build configuration file
            self._build_config_file(project_path, name, user_config)

            # Build template files
            self._build_template_files(project_path, name, user_config)

            # Initialize git repository if requested
            if git_init:
                self._init_git_repository(project_path, name)

            # Output success messages
            self._print_build_success_messages(name, project_path)

            logger.info("Project '%s' built successfully at %s", name, project_path)
            return str(project_path)

        except ValidationError as e:
            error_msg = ERROR_VALIDATION_FAILED.format(name, str(e))
            logger.error(error_msg)
            raise ProjectBuildError(error_msg) from e
        except Exception as e:
            error_msg = ERROR_BUILD_FAILED.format(name, str(e))
            logger.error(error_msg)
            raise ProjectBuildError(error_msg) from e

    def ensure_structure(self, project_path: str) -> None:
        """Ensure project has complete directory structure

        Args:
            project_path: Project path
        """
        path = self._validate_project_path(project_path)
        structure = self.template.get_structure()
        self._build_directories(path, structure)

    # ========================================================================
    # Public Interface - Project Maintenance Features
    # ========================================================================

    def update_all_template_files(
        self, project_path: str, name: str, description: str, preserve_custom_code: bool = True
    ) -> None:
        """Update all template files (server.py, pyproject.toml, README.md, .env)

        Args:
            project_path: Project path
            name: Project name
            description: Project description
            preserve_custom_code: Whether to preserve user custom code (default True)
        """
        self.update_server_file(project_path)
        self.update_pyproject_file(project_path, name, description)
        self.update_readme_file(project_path, name, description)
        self.update_env_file(project_path)  # Regenerate .env template
        self.update_changelog_file(project_path)
        self.update_gitignore_file(project_path)

    def update_config_file(
        self, project_path: str, user_config: dict[str, Any], rescan_components: bool = False
    ) -> None:
        """Update project configuration file

        Args:
            project_path: Project path
            user_config: User configuration updates
            rescan_components: Whether to rescan component directories (default False, auto-discover when missing)
        """
        logger.info("Updating config file for project: %s", project_path)
        path = self._validate_project_path(project_path)
        config_path = path / "config.yaml"

        # Read existing configuration
        existing_config = self._load_existing_config(config_path)

        # Use configuration module's merge functionality
        merged_config = merge_configs(existing_config, user_config)

        # Handle component configuration
        self._handle_component_config(path, merged_config, user_config, rescan_components)

        # Normalize and validate configuration
        merged_config = normalize_config(merged_config)
        is_valid, errors = validate_config(merged_config)
        if not is_valid:
            error_message = ERROR_CONFIG_VALIDATION.format("; ".join(errors))
            raise ProjectBuildError(error_message)

        # Write back normalized file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(merged_config, f, default_flow_style=False, allow_unicode=True)

        logger.debug("Config file updated successfully")

    def update_server_file(self, project_path: str) -> None:
        """Fully overwrite and update server.py file

        Args:
            project_path: Project path
        """
        logger.info("Updating server.py for project: %s", project_path)
        path = self._validate_project_path(project_path)
        server_path = path / "server.py"

        # Read configuration to get description information
        config_path = path / "config.yaml"
        description = "MCP Server"
        if config_path.exists():
            try:
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    server_config = config.get("server", {})
                    description = (
                        server_config.get("instructions", "") or f"MCP server: {server_config.get('name', 'unnamed')}"
                    )
            except Exception as e:
                logger.warning("Failed to read config for description: %s", e)

        server_content = self.template.get_server_template().format(description=description)
        server_path.write_text(server_content, encoding="utf-8")
        logger.debug("server.py updated successfully")

    def update_pyproject_file(self, project_path: str, name: str, description: str) -> None:
        """Fully overwrite and update pyproject.toml file

        Args:
            project_path: Project path
            name: Project name
            description: Project description
        """
        path = self._validate_project_path(project_path)
        pyproject_path = path / "pyproject.toml"
        pyproject_content = self.template.get_pyproject_template().format(name=name, description=description)
        pyproject_path.write_text(pyproject_content, encoding="utf-8")
        logger.debug("pyproject.toml updated successfully")

    def update_readme_file(self, project_path: str, name: str, description: str) -> None:
        """Fully overwrite and update README.md file

        Args:
            project_path: Project path
            name: Project name
            description: Project description
        """
        path = self._validate_project_path(project_path)
        readme_path = path / "README.md"
        readme_content = self.template.get_readme_template().format(name=name, description=description)
        readme_path.write_text(readme_content, encoding="utf-8")
        logger.debug("README.md updated successfully")

    def update_env_file(
        self, project_path: str, env_vars: dict[str, str] | None = None, jwt_auth: dict[str, str] | None = None
    ) -> None:
        """Update .env file

        Args:
            project_path: Project path
            env_vars: Environment variables dictionary to update (optional, regenerate template if not provided)
            jwt_auth: JWT authentication configuration (optional), containing issuer, audience, public_key or jwks_uri
        """
        logger.info("Updating .env file for project: %s", project_path)
        path = self._validate_project_path(project_path)
        env_path = path / ".env"

        # Handle JWT authentication configuration
        if jwt_auth:
            jwt_vars = self._validate_and_build_jwt_config(jwt_auth)
            if env_vars:
                env_vars.update(jwt_vars)
            else:
                env_vars = jwt_vars

        if env_vars:
            self._update_env_variables(env_path, env_vars)
        else:
            # Regenerate template
            env_content = self.template.get_env_template()
            env_path.write_text(env_content, encoding="utf-8")

        logger.debug(".env file updated successfully")

    def update_changelog_file(self, project_path: str) -> None:
        """Update CHANGELOG.md file

        Args:
            project_path: Project path
        """
        logger.info("Updating CHANGELOG.md for project: %s", project_path)
        path = self._validate_project_path(project_path)

        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        changelog_content = self.template.get_changelog_template().format(date=current_date)

        changelog_path = path / "CHANGELOG.md"
        changelog_path.write_text(changelog_content, encoding="utf-8")
        logger.debug("CHANGELOG.md updated successfully")

    def update_gitignore_file(self, project_path: str) -> None:
        """Update .gitignore file

        Args:
            project_path: Project path
        """
        logger.info("Updating .gitignore for project: %s", project_path)
        path = self._validate_project_path(project_path)

        gitignore_content = self.template.get_gitignore_template()
        gitignore_path = path / ".gitignore"
        gitignore_path.write_text(gitignore_content, encoding="utf-8")
        logger.debug(".gitignore updated successfully")

    # ========================================================================
    # Public Interface - Feature Extension Methods
    # ========================================================================

    def add_tool_function(
        self,
        project_path: str,
        tool_name: str,
        description: str,
        parameters: dict[str, str] | None = None,
        return_type: str = "str",
    ) -> None:
        """Add tool function to tools module

        Args:
            project_path: Project path
            tool_name: Tool name
            description: Tool description
            parameters: Parameter definitions (optional)
            return_type: Return type (default str)
        """
        template_data = {
            "parameters": parameters or {},
            "return_type": return_type,
        }
        self._inject_function_to_module(project_path, "tools", tool_name, description, template_data)

    def add_resource_function(
        self,
        project_path: str,
        resource_name: str,
        description: str,
        return_type: str = "Dict[str, Any]",
    ) -> None:
        """Add resource function to resources module

        Args:
            project_path: Project path
            resource_name: Resource name
            description: Resource description
            return_type: Return type (default Dict[str, Any])
        """
        template_data = {"return_type": return_type}
        self._inject_function_to_module(project_path, "resources", resource_name, description, template_data)

    def add_prompt_function(
        self,
        project_path: str,
        prompt_name: str,
        description: str,
        arguments: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add prompt function

        Args:
            project_path: Project path
            prompt_name: Prompt name
            description: Prompt description
            arguments: Prompt arguments
        """
        # Convert arguments list to parameters dict for compatibility with _generate_function_code
        parameters = {}
        if arguments:
            for arg in arguments:
                if "name" in arg and "type" in arg:
                    parameters[arg["name"]] = arg["type"]

        template_data = {
            "parameters": parameters,  # Use parameters instead of arguments
            "return_type": "str",
        }
        self._inject_function_to_module(project_path, "prompts", prompt_name, description, template_data)

    def add_multiple_functions(self, project_path: str, functions: list[dict[str, Any]]) -> None:
        """Add multiple functions in batch

        Args:
            project_path: Project path
            functions: List of function definitions
        """
        logger.info("Adding %s functions in batch", len(functions))

        for i, func_def in enumerate(functions):
            try:
                module_type = func_def.get("type", "tools")
                function_name = func_def["name"]
                description = func_def["description"]

                if module_type == "tools":
                    self.add_tool_function(
                        project_path,
                        function_name,
                        description,
                        func_def.get("parameters"),
                        func_def.get("return_type", "str"),
                    )
                elif module_type == "resources":
                    self.add_resource_function(
                        project_path, function_name, description, func_def.get("return_type", "Dict[str, Any]")
                    )
                elif module_type == "prompts":
                    self.add_prompt_function(project_path, function_name, description, func_def.get("parameters"))
                else:
                    raise ProjectError(f"Unknown module type: {module_type}", project_path=project_path)

            except Exception as e:
                logger.error("Failed to add function %s: %s", i + 1, e)
                raise

        logger.info("Batch function addition completed successfully")

    def remove_function(
        self,
        project_path: str,
        module_type: str,
        function_name: str,
    ) -> None:
        """Remove function from specified module

        Args:
            project_path: Project path
            module_type: Module type (tools, resources, prompts)
            function_name: Function name
        """
        logger.info("Removing function '%s' from %s module", function_name, module_type)
        path = self._validate_project_path(project_path)

        if module_type not in ALLOWED_MODULE_TYPES:
            raise ProjectBuildError(f"Invalid module type: {module_type}")

        module_path = path / module_type / "__init__.py"
        if not module_path.exists():
            raise ProjectBuildError(f"Module file not found: {module_path}")

        # Read file content
        with open(module_path, encoding="utf-8") as f:
            content = f.read()

        # Use simpler method: find and remove function line by line
        lines = content.split("\n")
        result_lines = []
        i = 0
        found_function = False

        while i < len(lines):
            line = lines[i]
            # Check if this is the target function definition line
            if re.match(rf"^def {re.escape(function_name)}\(", line):
                found_function = True
                # Skip all lines of this function until next function or end of file
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    # If encounter next function definition or non-indented line, stop
                    if (
                        next_line.strip()
                        and not next_line.startswith("    ")
                        and not next_line.startswith("\t")
                        and next_line != ""
                    ):
                        break
                    i += 1
                # Go back one line because outer loop will auto-increment
                i -= 1
            else:
                result_lines.append(line)
            i += 1

        if not found_function:
            logger.warning("Function '%s' not found in %s module", function_name, module_type)
            return

        # Rebuild content and clean up excessive empty lines
        content = "\n".join(result_lines)
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Write back to file
        with open(module_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Function '%s' removed successfully", function_name)

    # ========================================================================
    # Public Interface - Information Query
    # ========================================================================

    def list_functions(self, project_path: str, module_type: str) -> list[str]:
        """List all functions in specified module

        Args:
            project_path: Project path
            module_type: Module type (tools, resources, prompts)

        Returns:
            List of function names
        """
        logger.debug("Listing functions in %s module", module_type)
        path = self._validate_project_path(project_path)

        if module_type not in ALLOWED_MODULE_TYPES:
            raise ProjectBuildError(f"Invalid module type: {module_type}")

        module_path = path / module_type / "__init__.py"
        if not module_path.exists():
            return []

        # Read file content
        with open(module_path, encoding="utf-8") as f:
            content = f.read()

        # Use regex to match function definitions
        function_pattern = r"^def (\w+)\("
        matches = re.findall(function_pattern, content, re.MULTILINE)

        logger.debug("Found %s functions in %s module", len(matches), module_type)
        return matches

    def get_project_stats(self, project_path: str) -> dict[str, Any]:
        """Get project statistics

        Args:
            project_path: Project path

        Returns:
            Project statistics dictionary
        """
        path = self._validate_project_path(project_path)

        stats = {
            "project_path": str(path),
            "functions": {},
            "total_functions": 0,
            "has_config": (path / "config.yaml").exists(),
            "has_server": (path / "server.py").exists(),
            "has_env": (path / ".env").exists(),
        }

        # Count functions in each module
        for module_type in ALLOWED_MODULE_TYPES:
            functions = self.list_functions(project_path, module_type)
            stats["functions"][module_type] = len(functions)  # type: ignore
            stats["total_functions"] += len(functions)  # type: ignore

        return stats

    def get_build_info(self) -> dict[str, Any]:
        """Get builder information

        Returns:
            Builder information dictionary
        """
        return {
            "workspace_root": str(self.workspace_root),
            "template_version": getattr(self.template, "version", "unknown"),
            "validator_version": getattr(self.validator, "version", "unknown"),
        }

    # ========================================================================
    # Private Methods - Core Build Helpers
    # ========================================================================

    def _build_directories(self, project_path: Path, structure: dict[str, str]) -> None:
        """Build project directory structure

        Args:
            project_path: Project path
            structure: Directory structure definition
        """
        for dir_name in structure:
            # Items ending with '/' are directories
            if dir_name.endswith("/"):
                actual_dir_name = dir_name.rstrip("/")
                dir_path = project_path / actual_dir_name
                dir_path.mkdir(parents=True, exist_ok=True)

                # Create __init__.py files for module directories
                if actual_dir_name in ALLOWED_MODULE_TYPES:
                    init_file = dir_path / "__init__.py"
                    if not init_file.exists():
                        init_file.write_text("# " + actual_dir_name.title() + " module\n", encoding="utf-8")

    def _build_config_file(self, project_path: Path, name: str, user_config: dict[str, Any] | None) -> None:
        """Build project configuration file

        Args:
            project_path: Project path
            name: Project name
            user_config: User configuration
        """
        logger.info("Building config file")
        config_path = project_path / "config.yaml"

        # Get default configuration
        default_config = get_default_config()
        default_config["server"]["name"] = name

        # Merge user configuration
        merged_config = merge_configs(default_config, user_config) if user_config else default_config

        # Auto-discover components (only when not manually configured)
        if "components" not in merged_config:
            components_config = ComponentManager.discover_project_components(project_path)
            if components_config:
                merged_config["components"] = components_config
                logger.info("Auto-discovered components: %s", components_config)

        # Normalize and validate configuration
        merged_config = normalize_config(merged_config)
        is_valid, errors = validate_config(merged_config)
        if not is_valid:
            error_message = ERROR_CONFIG_VALIDATION.format("; ".join(errors))
            raise ProjectBuildError(error_message)

        # Write normalized configuration file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(merged_config, f, default_flow_style=False, allow_unicode=True)

        logger.debug("Config file written to: %s", config_path)

    def _build_template_files(self, project_path: Path, name: str, user_config: dict[str, Any] | None) -> None:
        """Build template files

        Args:
            project_path: Project path
            name: Project name
            user_config: User configuration
        """
        logger.info("Building template files")

        # Prepare description information
        description = user_config.get("description", f"MCP server: {name}") if user_config else f"MCP server: {name}"

        # Create server.py
        server_content = self.template.get_server_template().format(description=description)
        (project_path / "server.py").write_text(server_content, encoding="utf-8")

        # Create pyproject.toml
        pyproject_content = self.template.get_pyproject_template().format(name=name, description=description)
        (project_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

        # Create README.md
        readme_content = self.template.get_readme_template().format(name=name, description=description)
        (project_path / "README.md").write_text(readme_content, encoding="utf-8")

        # Create AGENTS.md
        agents_content = self.template.get_agents_template().format(name=name, description=description)
        (project_path / "AGENTS.md").write_text(agents_content, encoding="utf-8")

        # Create .env template
        env_content = self.template.get_env_template()
        (project_path / ".env").write_text(env_content, encoding="utf-8")

        # Create CHANGELOG.md
        from datetime import datetime

        current_date = datetime.now().strftime("%Y-%m-%d")
        changelog_content = self.template.get_changelog_template().format(date=current_date)
        (project_path / "CHANGELOG.md").write_text(changelog_content, encoding="utf-8")

        # Create .gitignore
        gitignore_content = self.template.get_gitignore_template()
        (project_path / ".gitignore").write_text(gitignore_content, encoding="utf-8")

        logger.debug("Template files created successfully")

    # ========================================================================
    # Private Methods - Configuration and Authentication Handling
    # ========================================================================

    def _validate_and_build_jwt_config(self, jwt_auth: dict[str, str]) -> dict[str, str]:
        """Validate and build JWT authentication configuration

        Args:
            jwt_auth: JWT authentication configuration

        Returns:
            Validated JWT environment variables dictionary

        Raises:
            ProjectBuildError: Raised when JWT configuration validation fails
        """
        logger.info("Validating JWT authentication configuration")

        jwt_vars = {}

        # Validate required fields
        if "issuer" not in jwt_auth:
            msg = "JWT issuer is required"
            raise ProjectBuildError(msg)

        if "audience" not in jwt_auth:
            msg = "JWT audience is required"
            raise ProjectBuildError(msg)

        # Validate authentication method: must provide either public_key or jwks_uri
        has_public_key = "public_key" in jwt_auth
        has_jwks_uri = "jwks_uri" in jwt_auth

        if not has_public_key and not has_jwks_uri:
            msg = "JWT configuration must include either 'public_key' or 'jwks_uri'"
            raise ProjectBuildError(msg)

        if has_public_key and has_jwks_uri:
            msg = "JWT configuration should include either 'public_key' or 'jwks_uri', not both"
            raise ProjectBuildError(msg)

        # Build environment variables
        jwt_vars["MCP_JWT_ISSUER"] = jwt_auth["issuer"]
        jwt_vars["MCP_JWT_AUDIENCE"] = jwt_auth["audience"]

        if has_public_key:
            jwt_vars["MCP_JWT_PUBLIC_KEY"] = jwt_auth["public_key"]
        else:
            jwt_vars["MCP_JWT_JWKS_URI"] = jwt_auth["jwks_uri"]

        # Optional fields
        if "algorithm" in jwt_auth:
            jwt_vars["MCP_JWT_ALGORITHM"] = jwt_auth["algorithm"]

        if "leeway" in jwt_auth:
            try:
                jwt_vars["MCP_JWT_LEEWAY"] = jwt_auth["leeway"]
            except ValueError:
                msg = "JWT leeway must be a number"
                raise ProjectBuildError(msg) from None

        logger.debug("JWT authentication configuration validated successfully")
        return jwt_vars

    # ========================================================================
    # Private Methods - Function Injection
    # ========================================================================

    def _inject_function_to_module(
        self,
        project_path: str,
        module_type: str,
        function_name: str,
        description: str,
        template_data: dict[str, Any],
    ) -> None:
        """Inject function to specified module as separate file

        Args:
            project_path: Project path
            module_type: Module type
            function_name: Function name
            description: Function description
            template_data: Template data
        """
        logger.info("Creating separate file for function '%s' in %s module", function_name, module_type)
        path = self._validate_project_path(project_path)

        if module_type not in ALLOWED_MODULE_TYPES:
            raise ProjectBuildError(f"Invalid module type: {module_type}")

        module_dir = path / module_type
        if not module_dir.exists():
            raise ProjectBuildError(f"Module directory not found: {module_dir}")

        # Create separate file for the function
        function_file = module_dir / f"{function_name}.py"

        # Check if function file already exists
        if function_file.exists():
            logger.warning("Function file '%s' already exists in %s module", function_name, module_type)
            return

        # Generate function code
        function_code = self._generate_function_code(module_type, function_name, description, template_data)

        # Detect required type imports
        type_imports = self._detect_type_imports(function_code, template_data)

        # Create the function file with imports
        import_section = ""
        if type_imports:
            import_section = f"from typing import {', '.join(sorted(type_imports))}\n\n"

        file_content = (
            textwrap.dedent(f'''
        """
        {function_name} - {module_type.title()} module
        Generated by MCP Factory
        """

        __all__ = ["{function_name}"]

        ''').strip()
            + "\n\n"
            + import_section
            + function_code
            + "\n"
        )

        with open(function_file, "w", encoding="utf-8") as f:
            f.write(file_content)

        # Update __init__.py to import the new function
        self._update_module_init(module_dir, function_name)

        logger.info("Function '%s' created successfully in separate file", function_name)

    def _update_module_init(self, module_dir: Path, function_name: str) -> None:
        """Update __init__.py to import the new function

        Args:
            module_dir: Module directory path
            function_name: Function name to import
        """
        init_file = module_dir / "__init__.py"

        # Collect all existing function files
        function_files = []
        for py_file in module_dir.glob("*.py"):
            if py_file.name != "__init__.py" and not py_file.name.startswith("_"):
                function_files.append(py_file.stem)

        # Sort function names alphabetically
        function_files.sort()

        # Generate new __init__.py content
        lines = [
            f"__all__ = {function_files}",
            "",
        ]

        # Add imports in alphabetical order
        for func_name in function_files:
            lines.append(f"from .{func_name} import {func_name}")

        lines.extend(["", "# Auto-generated imports", ""])

        content = "\n".join(lines)

        # Write the complete file
        with open(init_file, "w", encoding="utf-8") as f:
            f.write(content)

        logger.debug("Regenerated __init__.py with sorted imports for '%s'", function_name)

    def _detect_type_imports(self, function_code: str, template_data: dict[str, Any]) -> set[str]:
        """Detect required type imports from function code and template data

        Args:
            function_code: Generated function code
            template_data: Template data containing type information

        Returns:
            Set of type names that need to be imported from typing
        """
        import re

        typing_types = {"Dict", "List", "Tuple", "Set", "Union", "Optional", "Any", "Callable"}
        required_imports = set()

        # Check return type
        return_type = template_data.get("return_type", "")
        for type_name in typing_types:
            if type_name in return_type:
                required_imports.add(type_name)

        # Check parameter types
        parameters = template_data.get("parameters", {})
        for param_type in parameters.values():
            for type_name in typing_types:
                if type_name in param_type:
                    required_imports.add(type_name)

        # Check function code for any remaining type usage
        for type_name in typing_types:
            if re.search(rf"\b{type_name}\b", function_code):
                required_imports.add(type_name)

        return required_imports

    def _generate_function_code(
        self,
        module_type: str,
        function_name: str,
        description: str,
        template_data: dict[str, Any],
    ) -> str:
        """Generate function code

        Args:
            module_type: Module type
            function_name: Function name
            description: Function description
            template_data: Template data

        Returns:
            Generated function code
        """
        # Build parameter list
        parameters = template_data.get("parameters", {})
        return_type = template_data.get("return_type", "str")

        param_list = ", ".join([f"{name}: {ptype}" for name, ptype in parameters.items()])

        # Build function signature
        function_signature = f"def {function_name}({param_list}) -> {return_type}:"

        # Generate function body
        function_body = self._generate_function_body(module_type, function_name, description, template_data)

        # Combine complete function
        return f'''{function_signature}
    """{description}"""
{function_body}
'''

    def _generate_function_body(
        self, module_type: str, function_name: str, description: str, template_data: dict[str, Any]
    ) -> str:
        """Generate function body

        Args:
            module_type: Module type
            function_name: Function name
            description: Function description
            template_data: Template data

        Returns:
            Generated function body code
        """
        return_type = template_data.get("return_type", "str")

        if module_type == "tools":
            body = f'''    # TODO: Implement tool functionality
    # Use generate_todo_template tool for detailed implementation guidance
    return {{"status": "success", "method": "{function_name}", "result": "TODO"}}'''
        elif module_type == "resources":
            if "Dict" in return_type:
                body = """    # TODO: Implement resource retrieval logic
    return {"status": "success", "data": {}}"""
            else:
                body = '''    # TODO: Implement resource retrieval logic
    return "Resource data"'''
        elif module_type == "prompts":
            body = f'''    # TODO: Implement prompt logic
    return "Generated prompt for {function_name}"'''
        else:
            body = """    # TODO: Implement functionality logic
    pass"""

        return textwrap.indent(body, "")

    # ========================================================================
    # Private Methods - Utility Functions
    # ========================================================================

    def _validate_project_path(self, project_path: str) -> Path:
        """Validate if project path exists

        Args:
            project_path: Project path string

        Returns:
            Path object

        Raises:
            ProjectBuildError: Raised when project does not exist
        """
        path = Path(project_path)
        if not path.exists():
            raise ProjectBuildError(ERROR_PROJECT_NOT_FOUND.format(project_path))
        return path

    def _load_existing_config(self, config_path: Path) -> dict[str, Any]:
        """Load existing configuration file

        Args:
            config_path: Configuration file path

        Returns:
            Configuration dictionary
        """
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        else:
            return get_default_config()

    def _handle_component_config(
        self, path: Path, merged_config: dict[str, Any], user_config: dict[str, Any], rescan_components: bool
    ) -> None:
        """Handle component configuration

        Args:
            path: Project path
            merged_config: Merged configuration
            user_config: User configuration
            rescan_components: Whether to rescan components
        """
        if rescan_components or ("components" not in user_config and "components" not in merged_config):
            components_config = ComponentManager.discover_project_components(path)
            if components_config:
                merged_config["components"] = components_config
                if rescan_components:
                    logger.info("Rescanned and updated components during config update")
                else:
                    logger.info("Auto-discovered components during config update")

    def _update_env_variables(self, env_path: Path, env_vars: dict[str, str]) -> None:
        """Update environment variables file

        Args:
            env_path: .env file path
            env_vars: Environment variables to update
        """
        if env_path.exists():
            # Read existing content
            existing_lines = []
            with open(env_path, encoding="utf-8") as f:
                existing_lines = f.readlines()

            # Update specified variables
            updated_lines = []
            updated_vars = set()

            for line in existing_lines:
                line = line.rstrip()
                if "=" in line and not line.strip().startswith("# "):
                    var_name = line.split("=", 1)[0].strip()
                    if var_name in env_vars:
                        updated_lines.append(f"{var_name}={env_vars[var_name]}\n")
                        updated_vars.add(var_name)
                    else:
                        updated_lines.append(line + "\n")
                else:
                    updated_lines.append(line + "\n")

            # Add new variables
            for var_name, var_value in env_vars.items():
                if var_name not in updated_vars:
                    updated_lines.append(f"{var_name}={var_value}\n")

            # Write back to file
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(updated_lines)
        else:
            # If file doesn't exist, create new file
            env_content = self.template.get_env_template()
            env_path.write_text(env_content, encoding="utf-8")

            # Then update variables
            self._update_env_variables(env_path, env_vars)

    def _print_build_success_messages(self, name: str, project_path: Path) -> None:
        """Print build success messages

        Args:
            name: Project name
            project_path: Project path
        """
        print(SUCCESS_MESSAGES["project_created"].format(name))
        print(SUCCESS_MESSAGES["project_path"].format(project_path))
        print(SUCCESS_MESSAGES["jwt_config"])
        print(SUCCESS_MESSAGES["jwt_warning"])
        print(SUCCESS_MESSAGES["usage_hint"])

        for example in USAGE_EXAMPLES:
            print(example.format(project_path))

    def _init_git_repository(self, project_path: Path, project_name: str) -> None:
        """Initialize a new git repository in the project directory.

        Args:
            project_path: The path to the project directory.
            project_name: The name of the project.
        """
        logger.info("Initializing git repository for project: %s", project_name)
        try:
            # Check if .git directory already exists
            if (project_path / ".git").exists():
                logger.warning("Git repository already exists for project: %s", project_name)
                return

            # Initialize git repository
            subprocess.run(["git", "init"], cwd=project_path, check=True)
            logger.info("Git repository initialized successfully for project: %s", project_name)

            # Ensure git user configuration exists (required for commits)
            self._ensure_git_user_config(project_path)

            # Add all files to git
            subprocess.run(["git", "add", "."], cwd=project_path, check=True)
            logger.info("All files added to git for project: %s", project_name)

            # Commit initial changes
            commit_message = f"Initial commit for project: {project_name}"
            subprocess.run(["git", "commit", "-m", commit_message], cwd=project_path, check=True)
            logger.info("Git repository committed successfully for project: %s", project_name)

        except subprocess.CalledProcessError as e:
            logger.error("Failed to initialize git repository for project '%s': %s", project_name, e)
            raise ProjectBuildError(f"Failed to initialize git repository for project '{project_name}': {e}") from e
        except Exception as e:
            logger.error("An unexpected error occurred during git initialization for project '%s': %s", project_name, e)
            raise ProjectBuildError(
                f"An unexpected error occurred during git initialization for project '{project_name}': {e}"
            ) from e

    def _ensure_git_user_config(self, project_path: Path) -> None:
        """Ensure git user configuration exists for commits.

        Args:
            project_path: The path to the project directory.
        """
        try:
            # Check if global git user is configured
            result = subprocess.run(
                ["git", "config", "--global", "user.name"], cwd=project_path, capture_output=True, text=True
            )

            if result.returncode != 0 or not result.stdout.strip():
                # Set default user configuration for this repository
                subprocess.run(["git", "config", "user.name", "MCP Factory"], cwd=project_path, check=True)
                logger.info("Set default git user.name for project")

            # Check git user email
            result = subprocess.run(
                ["git", "config", "--global", "user.email"], cwd=project_path, capture_output=True, text=True
            )

            if result.returncode != 0 or not result.stdout.strip():
                # Set default email configuration for this repository
                subprocess.run(["git", "config", "user.email", "mcpfactory@example.com"], cwd=project_path, check=True)
                logger.info("Set default git user.email for project")

        except subprocess.CalledProcessError as e:
            logger.warning("Failed to configure git user settings: %s", e)
            # This is not a fatal error, just log it
