"""
Core Publisher - Pure business logic without CLI dependencies
Handles core business logic for project publishing without user interaction
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import toml

from ..exceptions import ErrorHandler, ProjectError, ValidationError
from .validator import ProjectValidator


class PublishError(Exception):
    """Publishing-related errors"""

    pass


class GitError(Exception):
    """Git operation-related errors"""

    pass


class PublishResult:
    """Publishing result data class"""

    def __init__(self, success: bool, message: str = "", data: dict[str, Any] | None = None):
        self.success = success
        self.message = message
        self.data = data or {}


class ProjectPublisher:
    """
    Core project publisher - Pure business logic

    Responsibilities:
    - Project validation
    - Metadata extraction
    - Git status checking
    - API publishing
    - GitHub App integration
    """

    def __init__(self, github_app_url: str = "https://mcp-project-manager.vercel.app"):
        """Initialize publisher"""
        self.validator = ProjectValidator()
        self.github_app_name = "mcp-project-manager"
        self.hub_repo = "ACNet-AI/mcp-servers-hub"
        self.github_app_url = github_app_url.rstrip("/")

        # Error handling
        self.error_handler = ErrorHandler("ProjectPublisher", enable_metrics=True)

    # ============================================================================
    # Core publishing logic
    # ============================================================================

    def publish_project(self, project_path: str, config: dict[str, Any]) -> PublishResult:
        """Publish project - Pure business logic"""
        try:
            project_path_obj = Path(project_path).resolve()

            # 1. Validate project
            validation_result = self.validate_project(project_path_obj)
            if not validation_result.success:
                return validation_result

            # 2. Extract project metadata
            try:
                metadata = self.extract_project_metadata(project_path_obj)
                metadata.update(config)
            except Exception as e:
                return PublishResult(False, f"Metadata extraction failed: {e}")

            # 3. Smart publishing (API first, fallback on failure)
            return self._smart_publish(project_path_obj, metadata)

        except (ProjectError, ValidationError) as e:
            return PublishResult(False, f"Project publishing failed: {e}")
        except Exception as e:
            self.error_handler.handle_error("publish_project", e, {"project_path": project_path}, reraise=False)
            return PublishResult(False, f"Unknown error: {e}")

    def _smart_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Smart publishing logic - Internal fallback handling"""
        # 1. Try API publishing
        api_result = self._try_api_publish(project_path, metadata)
        if api_result.success:
            return api_result

        # 2. Fallback to manual publishing
        return self._prepare_manual_publish(project_path, metadata)

    def _try_api_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Try API publishing"""
        try:
            # Check GitHub App service status
            if not self._check_github_app_status():
                return PublishResult(False, "GitHub App service unavailable")

            # Prepare API payload
            project_info = self._prepare_api_payload(project_path, metadata)

            # Send publish request
            result = self._send_publish_request(project_info)

            if result["success"]:
                return PublishResult(
                    True,
                    "API publishing successful",
                    {
                        "method": "api",
                        "repo_url": result["repoUrl"],
                        "registration_url": result.get("registrationUrl", ""),
                    },
                )
            else:
                return PublishResult(False, "API publishing failed")

        except (ConnectionError, requests.RequestException, TimeoutError) as e:
            return PublishResult(False, f"API publishing failed: {e}")
        except Exception as e:
            self.error_handler.handle_error("try_api_publish", e, {"project_path": str(project_path)}, reraise=False)
            return PublishResult(False, "API publishing exception")

    def _prepare_manual_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Prepare manual publishing workflow"""
        try:
            # Detect Git information
            git_info = self.detect_git_info(project_path)

            # Return information needed for manual publishing
            return PublishResult(
                True,
                "Manual publishing required",
                {
                    "method": "manual",
                    "git_info": git_info,
                    "install_url": self.create_github_app_install_url(git_info["full_name"], metadata),
                    "repo_name": git_info["full_name"],
                    "project_name": metadata["name"],
                },
            )

        except (GitError, OSError) as e:
            return PublishResult(False, f"Failed to prepare manual publishing: {e}")
        except Exception as e:
            self.error_handler.handle_error(
                "prepare_manual_publish", e, {"project_path": str(project_path)}, reraise=False
            )
            return PublishResult(False, f"Failed to prepare manual publishing: {e}")

    # ============================================================================
    # Git operations
    # ============================================================================

    def check_git_status(self, project_path: Path) -> dict[str, Any]:
        """Check Git status"""
        try:
            git_info = self.detect_git_info(project_path)
            return {
                "valid": True,
                "git_info": git_info,
                "needs_commit": git_info.get("has_changes", False),
                "needs_push": git_info.get("has_unpushed", False),
            }
        except GitError as e:
            return {"valid": False, "error": str(e)}

    def commit_changes(self, project_path: Path, message: str | None = None) -> bool:
        """Commit uncommitted changes"""
        if message is None:
            message = "feat: prepare for MCP Servers Hub publishing"

        try:
            subprocess.run(["git", "add", "."], cwd=project_path, check=True)
            subprocess.run(["git", "commit", "-m", message], cwd=project_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_error(
                "commit_changes",
                GitError(f"Git commit failed: {e}"),
                {"project_path": str(project_path)},
                reraise=False,
            )
            return False

    def push_changes(self, project_path: Path) -> bool:
        """Push changes to remote repository"""
        try:
            subprocess.run(["git", "push"], cwd=project_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_error(
                "push_changes", GitError(f"Git push failed: {e}"), {"project_path": str(project_path)}, reraise=False
            )
            return False

    def trigger_initial_registration(self, project_path: Path, metadata: dict[str, Any]) -> bool:
        """Trigger initial registration"""
        try:
            # Create empty commit to trigger webhook
            subprocess.run(
                [
                    "git",
                    "commit",
                    "--allow-empty",
                    "-m",
                    f"feat: register {metadata['name']} with MCP Servers Hub",
                ],
                cwd=project_path,
                check=True,
            )
            subprocess.run(["git", "push"], cwd=project_path, check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.error_handler.handle_error(
                "trigger_initial_registration",
                GitError(f"Git registration failed: {e}"),
                {"project_path": str(project_path)},
                reraise=False,
            )
            return False

    # ============================================================================
    # Hub configuration management
    # ============================================================================

    def add_hub_configuration(self, project_path: Path, hub_config: dict[str, Any]) -> bool:
        """Add Hub configuration to pyproject.toml"""
        try:
            pyproject_path = project_path / "pyproject.toml"
            self._add_hub_config_to_pyproject(pyproject_path, hub_config)
            return True
        except (OSError, toml.TomlDecodeError) as e:
            self.error_handler.handle_error(
                "add_hub_configuration", e, {"project_path": str(project_path)}, reraise=False
            )
            return False

    def check_hub_configuration(self, project_path: Path) -> tuple[bool, dict[str, Any]]:
        """Check Hub configuration"""
        try:
            pyproject_path = project_path / "pyproject.toml"
            if not pyproject_path.exists():
                return False, {}

            config = toml.load(pyproject_path)
            hub_config = config.get("tool", {}).get("mcp-servers-hub", {})

            return bool(hub_config), hub_config
        except (OSError, toml.TomlDecodeError) as e:
            self.error_handler.handle_error(
                "check_hub_configuration", e, {"project_path": str(project_path)}, reraise=False
            )
            return False, {}

    # ============================================================================
    # Project validation and metadata extraction
    # ============================================================================

    def validate_project(self, project_path: Path) -> PublishResult:
        """Validate project"""
        try:
            result = self.validator.validate_project(str(project_path))
            if not result["valid"]:
                return PublishResult(False, "Project validation failed", {"errors": result["errors"]})

            return PublishResult(True, "Project validation passed", {"warnings": result["warnings"]})
        except ValidationError as e:
            return PublishResult(False, f"Project validation exception: {e}")

    def extract_project_metadata(self, project_path: Path) -> dict[str, Any]:
        """Extract project metadata"""
        pyproject_path = project_path / "pyproject.toml"
        if not pyproject_path.exists():
            raise PublishError("pyproject.toml not found")

        config = toml.load(pyproject_path)

        # Extract basic project information
        project_info = config.get("project", {})

        # Extract tool-specific configuration
        tool_config = config.get("tool", {})
        build_config = tool_config.get("mcp-factory", {})

        return {
            "name": project_info.get("name", ""),
            "description": project_info.get("description", ""),
            "version": project_info.get("version", "0.1.0"),
            "author": self._extract_author_name(project_info),
            "license": project_info.get("license", {}).get("text", "MIT"),
            "python_requires": project_info.get("requires-python", ">=3.8"),
            "dependencies": project_info.get("dependencies", []),
            "entry_points": build_config.get("entry_points", {}),
            "build_config": build_config,
        }

    # ============================================================================
    # GitHub App integration
    # ============================================================================

    def create_github_app_install_url(self, repo_full_name: str, metadata: dict[str, Any]) -> str:
        """Create GitHub App installation URL"""
        context = {
            "action": "publish_project",
            "repo": repo_full_name,
            "project_name": metadata["name"],
            "timestamp": int(time.time()),
        }
        state = json.dumps(context)
        return f"https://github.com/apps/{self.github_app_name}/installations/new?state={state}"

    # ============================================================================
    # Private methods
    # ============================================================================

    def _check_github_app_status(self) -> bool:
        """Check GitHub App service status"""
        try:
            response = requests.get(f"{self.github_app_url}/api/health", timeout=10)
            return response.status_code == 200
        except (ConnectionError, requests.RequestException, TimeoutError):
            return False

    def _prepare_api_payload(self, project_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
        """Prepare API payload"""
        return {
            "projectName": metadata["name"],
            "description": metadata["description"],
            "author": metadata["author"],
            "githubUsername": metadata["github_username"],
            "categories": metadata.get("categories", ["tools"]),
            "language": self._detect_language(project_path),
            "files": self._collect_key_files(project_path),
        }

    def _send_publish_request(self, project_info: dict[str, Any]) -> dict[str, Any]:
        """Send publish request"""
        try:
            response = requests.post(f"{self.github_app_url}/api/publish", json=project_info, timeout=30)
            result = response.json()
            if isinstance(result, dict):
                return result
            return {"success": False}
        except (ConnectionError, requests.RequestException, TimeoutError):
            return {"success": False}

    def detect_git_info(self, project_path: Path) -> dict[str, Any]:
        """Detect Git repository information"""
        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            current_branch = branch_result.stdout.strip()

            # Get remote URL
            remote_result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            remote_url = remote_result.stdout.strip()

            # Parse GitHub repository information
            repo_info = self._parse_github_url(remote_url)

            # Check uncommitted changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )
            has_changes = bool(status_result.stdout.strip())

            # Check unpushed commits
            try:
                unpushed_result = subprocess.run(
                    ["git", "log", f"origin/{current_branch}..HEAD", "--oneline"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                has_unpushed = bool(unpushed_result.stdout.strip())
            except subprocess.CalledProcessError:
                has_unpushed = True

            return {
                "owner": repo_info["owner"],
                "repo": repo_info["repo"],
                "full_name": repo_info["full_name"],
                "branch": current_branch,
                "remote_url": remote_url,
                "has_changes": has_changes,
                "has_unpushed": has_unpushed,
            }

        except subprocess.CalledProcessError as e:
            raise GitError(f"Failed to detect Git information: {e}") from e

    def _parse_github_url(self, url: str) -> dict[str, str]:
        """Parse GitHub URL and extract owner/repo information"""
        if url.startswith("git@github.com:"):
            # SSH format: git@github.com:owner/repo.git
            parts = url.replace("git@github.com:", "").replace(".git", "").split("/")
        elif "github.com" in url:
            # HTTPS format: https://github.com/owner/repo.git
            parsed = urlparse(url)
            parts = parsed.path.strip("/").replace(".git", "").split("/")
        else:
            raise GitError(f"Not a GitHub repository URL: {url}")

        if len(parts) < 2:
            raise GitError(f"Invalid GitHub repository URL: {url}")

        owner, repo = parts[0], parts[1]
        return {
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
        }

    def _extract_author_name(self, project_info: dict[str, Any]) -> str:
        """Extract author name from project information"""
        authors = project_info.get("authors", [])
        if authors and isinstance(authors[0], dict):
            name = authors[0].get("name", "")
            return str(name) if name else ""
        return ""

    def _detect_language(self, project_path: Path) -> str:
        """Validate project language - ensure it's a Python project created by mcp-factory"""
        # Check necessary Python project files
        if not (project_path / "pyproject.toml").exists():
            raise PublishError("Not a valid mcp-factory project: missing pyproject.toml")

        # Check if misused on non-Python projects
        if (project_path / "package.json").exists():
            raise PublishError("Cannot publish JavaScript project - mcp-factory only supports Python MCP servers")
        elif (project_path / "Cargo.toml").exists():
            raise PublishError("Cannot publish Rust project - mcp-factory only supports Python MCP servers")
        elif (project_path / "go.mod").exists():
            raise PublishError("Cannot publish Go project - mcp-factory only supports Python MCP servers")

        return "python"

    def _collect_key_files(self, project_path: Path) -> list[dict[str, str]]:
        """Collect key files from MCP project (based on mcp-factory project template)"""
        # File structure based on mcp-factory project template
        template_files = [
            "server.py",  # Main MCP server file
            "config.yaml",  # Project configuration file
            "pyproject.toml",  # Python project configuration
            "README.md",  # Project documentation
            "CHANGELOG.md",  # Version changelog
            ".env",  # Environment variables configuration
            ".gitignore",  # Git ignore file
        ]

        # Key files in module directories
        module_patterns = [
            "tools/__init__.py",  # Tools module initialization
            "resources/__init__.py",  # Resources module initialization
            "prompts/__init__.py",  # Prompts module initialization
        ]

        files = []
        all_files = template_files + module_patterns

        for filename in all_files:
            file_path = project_path / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding="utf-8")
                    files.append({"path": filename, "content": content})
                except Exception:
                    continue

        # Collect actual implementation files in tools/resources/prompts directories
        for module_dir in ["tools", "resources", "prompts"]:
            module_path = project_path / module_dir
            if module_path.is_dir():
                for py_file in module_path.glob("*.py"):
                    if py_file.name != "__init__.py":  # Skip already included __init__.py
                        try:
                            content = py_file.read_text(encoding="utf-8")
                            relative_path = py_file.relative_to(project_path)
                            files.append({"path": str(relative_path), "content": content})
                        except Exception:
                            continue

        return files

    def _add_hub_config_to_pyproject(self, pyproject_path: Path, hub_config: dict[str, Any]) -> None:
        """Add Hub configuration to pyproject.toml"""
        if not pyproject_path.exists():
            raise PublishError("pyproject.toml not found")

        config = toml.load(pyproject_path)

        # Ensure tool section exists
        if "tool" not in config:
            config["tool"] = {}

        # Add mcp-servers-hub configuration
        config["tool"]["mcp-servers-hub"] = hub_config

        # Write back to file
        with open(pyproject_path, "w") as f:
            toml.dump(config, f)
