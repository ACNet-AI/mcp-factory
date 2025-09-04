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

    def __init__(self) -> None:
        """Initialize the publisher with enhanced error handling and configuration management"""
        self.error_handler = ErrorHandler()
        # OAuth fix is deployed to stable production URL
        self.github_app_url = "https://mcp-project-manager.vercel.app"
        self.validator = ProjectValidator()
        self.github_app_name = "mcp-project-manager"
        self.hub_repo = "ACNet-AI/mcp-servers-hub"

        # Simple auth cache management
        self.auth_cache_dir = Path.home() / ".mcp-factory"
        self.auth_cache_file = self.auth_cache_dir / "auth_cache.json"
        self.auth_cache_dir.mkdir(exist_ok=True)

    # ============================================================================
    # Authentication cache management
    # ============================================================================

    def _load_auth_cache(self) -> dict[str, Any]:
        """Load authentication cache from disk"""
        if not self.auth_cache_file.exists():
            return {}

        try:
            with open(self.auth_cache_file) as f:
                cache_data: dict[str, Any] = json.load(f)
                return cache_data
        except Exception:
            return {}

    def _save_auth_cache(self, cache: dict[str, Any]) -> None:
        """Save authentication cache to disk"""
        try:
            with open(self.auth_cache_file, "w") as f:
                json.dump(cache, f, indent=2)
            # Set restrictive permissions (contains sensitive data)
            self.auth_cache_file.chmod(0o600)
        except Exception:
            pass  # Fail silently, not critical

    def _get_installation_id(self, github_username: str) -> str | None:
        """Get installation_id from cache for a GitHub username"""
        cache = self._load_auth_cache()
        installations: dict[str, str] = cache.get("installations", {})
        return installations.get(github_username)

    def _save_installation_id(self, github_username: str, installation_id: str) -> None:
        """Save installation_id to cache"""
        cache = self._load_auth_cache()
        if "installations" not in cache:
            cache["installations"] = {}
        cache["installations"][github_username] = installation_id
        self._save_auth_cache(cache)

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

        # 2. Check if API failure might be due to existing repository or creation issues
        if api_result.data and api_result.data.get("method") == "api_failed":
            error_type = api_result.data.get("error_type")
            if error_type in ["repository_already_exists", "repository_creation_failed"]:
                # Don't fallback to manual - let CLI handle these cases
                return api_result

        # 3. Fallback to manual publishing for other types of failures
        return self._prepare_manual_publish(project_path, metadata)

    def _try_api_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Try API publishing with GitHub App Installation API"""
        try:
            # 1. Service status check
            if not self._check_github_app_status():
                return PublishResult(False, "GitHub App service unavailable. Falling back to manual workflow.")

            # 2. Get installation_id from auth cache
            github_username = metadata.get("github_username")
            if not github_username or not isinstance(github_username, str):
                return PublishResult(
                    False, "GitHub username not found in metadata. Please configure GitHub authentication."
                )
            installation_id = self._get_installation_id(github_username)

            if not installation_id:
                return PublishResult(
                    False, f"No installation found for user {github_username}. GitHub App installation required."
                )

            # 3. Add installation_id to metadata for the API call (but don't save to project)
            api_metadata = metadata.copy()
            api_metadata["installation_id"] = installation_id

            # 4. Use Installation API directly
            return self._try_installation_api_publish(project_path, api_metadata)

        except Exception as e:
            return PublishResult(False, f"API publishing failed: {e!s}")

    def _prepare_manual_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Prepare manual publishing workflow with enhanced guidance"""
        try:
            # Detect Git information
            git_info = self.detect_git_info(project_path)

            # Return information needed for manual publishing
            return PublishResult(
                True,
                "Manual publishing workflow prepared. GitHub App installation required.",
                {
                    "method": "manual",
                    "git_info": git_info,
                    "install_url": self.create_github_app_install_url(git_info["full_name"], metadata),
                    "repo_name": git_info["full_name"],
                    "project_name": metadata["name"],
                },
            )

        except GitError as e:
            error_msg = str(e)

            # Provide specific guidance based on git error type
            if "No git repository found" in error_msg:
                return PublishResult(
                    False,
                    "Git repository not initialized. Please run 'git init && git add . && git commit -m \"Initial commit\"' "
                    "in your project directory first.",
                )
            if "No remote origin configured" in error_msg:
                return PublishResult(
                    False,
                    "Git repository exists but no GitHub remote configured. Please either:\n"
                    "1. Create a repository on GitHub first, then add remote: 'git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git'\n"
                    "2. Or use the manual publishing wizard to create repository automatically",
                )
            return PublishResult(False, f"Git configuration issue: {error_msg}")

        except OSError as e:
            return PublishResult(False, f"File system error: {e}")
        except Exception as e:
            self.error_handler.handle_error(
                "prepare_manual_publish", e, {"project_path": str(project_path)}, reraise=False
            )
            return PublishResult(
                False,
                f"Failed to prepare manual publishing due to unexpected error: {e}. "
                "Please check your project configuration and try again.",
            )

    # ============================================================================
    # Git operations
    # ============================================================================

    def check_git_status(self, project_path: Path, allow_no_remote: bool = False) -> dict[str, Any]:
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
            if allow_no_remote and "no remote" in str(e).lower():
                # Allow projects without remote when explicitly requested
                return {
                    "valid": True,
                    "git_info": {"has_changes": False, "has_unpushed": False},
                    "needs_commit": False,
                    "needs_push": False,
                }
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
        """Trigger initial registration with improved Git handling"""
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

            # Advanced push handling for existing repositories
            try:
                # Try regular push first
                subprocess.run(["git", "push"], cwd=project_path, check=True)
            except subprocess.CalledProcessError:
                try:
                    # If regular push fails, try with upstream setup
                    subprocess.run(["git", "push", "--set-upstream", "origin", "main"], cwd=project_path, check=True)
                except subprocess.CalledProcessError:
                    # If upstream push fails due to divergent histories, try pull first
                    try:
                        # Fetch and merge remote changes
                        subprocess.run(["git", "fetch", "origin"], cwd=project_path, check=True)
                        subprocess.run(
                            ["git", "merge", "origin/main", "--allow-unrelated-histories"], cwd=project_path, check=True
                        )
                        # Now try push again
                        subprocess.run(
                            ["git", "push", "--set-upstream", "origin", "main"], cwd=project_path, check=True
                        )
                    except subprocess.CalledProcessError:
                        # Last resort: force push (warn user)
                        print("[WARNING] Forcing push due to divergent histories. This may overwrite remote changes.")
                        subprocess.run(
                            ["git", "push", "--set-upstream", "origin", "main", "--force"], cwd=project_path, check=True
                        )

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
            "license": self._extract_license(project_info),
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
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status") if isinstance(health_data, dict) else None
                return status == "healthy"
            return False
        except (ConnectionError, requests.RequestException, TimeoutError, ValueError):
            return False

    def check_github_app_installation(self, github_username: str) -> dict[str, Any]:
        """Check GitHub App installation status for a specific user"""
        try:
            response = requests.get(
                f"{self.github_app_url}/api/installation-status", params={"username": github_username}, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "installed": data.get("installed", False),
                    "installation_id": data.get(
                        "installationId"
                    ),  # Note: Backend returns installationId instead of installation_id
                    "permissions": data.get("permissions", {}),
                    "account": data.get("account", {}),
                }
            # If status check fails, assume not installed
            return {"installed": False}

        except (ConnectionError, requests.RequestException, TimeoutError, ValueError):
            # If we can't check status, assume not installed to be safe
            return {"installed": False}

    def start_session_based_installation(self, project_name: str) -> dict[str, Any]:
        """Start session-based GitHub App installation process - using existing API"""
        try:
            # Temporarily use standard GitHub App installation URL, not dependent on backend session API
            # This allows implementing improved user experience first, with optimization later
            app_name = "mcp-project-manager"
            install_url = f"https://github.com/apps/{app_name}/installations/new"

            # Generate a temporary session_id for tracking (not actually used for now)
            import uuid

            session_id = str(uuid.uuid4())

            return {
                "success": True,
                "install_url": install_url,
                "session_id": session_id,
                "message": "Using standard GitHub App installation URL",
            }

        except Exception as e:
            return {"success": False, "error": f"Failed to start session-based installation: {e!s}"}

    def check_installation_status_by_session(self, session_id: str) -> dict[str, Any]:
        """Check session-based GitHub App installation status - using existing configuration and API"""
        try:
            # Read local github_username configuration
            project_path = Path.cwd()
            pyproject_path = project_path / "pyproject.toml"

            if pyproject_path.exists():
                try:
                    config = toml.load(pyproject_path)
                    hub_config = config.get("tool", {}).get("mcp-servers-hub", {})
                    github_username = hub_config.get("github_username")

                    if github_username:
                        # Use existing API to check installation status
                        install_status = self.check_user_installation_status(github_username)

                        if install_status.get("installed"):
                            installations = install_status.get("installations", [])
                            if installations:
                                latest_installation_id = installations[0].get("id")
                                return {
                                    "completed": True,
                                    "status": "success",
                                    "data": {
                                        "github_username": github_username,
                                        "installation_id": latest_installation_id,
                                        "installations": installations,
                                    },
                                }

                except Exception:
                    # Configuration reading failed, continue waiting
                    pass

            # If no configuration found or not installed, return pending status to continue waiting
            return {
                "completed": False,
                "status": "pending",
                "message": "Waiting for GitHub App installation to complete...",
            }

        except Exception as e:
            return {"completed": False, "status": "error", "error": str(e)}

    def check_user_installation_status(self, github_username: str) -> dict[str, Any]:
        """Check specified user's GitHub App installation status - using existing API"""
        try:
            response = requests.get(
                f"{self.github_app_url}/api/github/installation-status", params={"user": github_username}, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "installed": data.get("installed", False),
                    "installations": data.get("installations", []),
                    "user_info": {"username": github_username},
                }
            return {"installed": False, "error": f"HTTP {response.status_code}"}

        except Exception as e:
            return {"installed": False, "error": str(e)}

    def create_installation_url_for_user(self, github_username: str, project_name: str) -> str:
        """Create GitHub App installation URL for a specific user and project"""
        # GitHub App installation URL follows standard GitHub format
        # For MCP Project Manager app, we'll use the direct GitHub app installation URL

        # Standard GitHub App installation URL format
        # We can include suggested_target_id parameter to suggest repository
        base_url = "https://github.com/apps/mcp-project-manager/installations/new"

        # Add suggested target (repository) if we know the username
        if github_username and project_name:
            return f"{base_url}?suggested_target_id={github_username}&suggested_repository_name={project_name}"

        return base_url

    def _prepare_api_payload(self, project_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
        """Prepare API payload"""
        payload = {
            "projectName": metadata["name"],
            "description": metadata["description"],
            "author": metadata["author"],
            "githubUsername": metadata["github_username"],
            "categories": metadata.get("categories", ["tools"]),
            "language": self._detect_language(project_path),
            "files": self._collect_key_files(project_path),
        }

        return payload

    def _try_installation_api_publish(self, project_path: Path, metadata: dict[str, Any]) -> PublishResult:
        """Try publishing using GitHub App Installation API with installation_id"""
        try:
            # Prepare payload following Backend team's integration example
            payload = {
                "name": metadata["name"],
                "description": metadata["description"],
                "author": metadata.get("author", ""),
                "categories": metadata.get("categories", ["tools"]),
                "private": metadata.get("private", False),  # Added private field support
                "owner": metadata.get(
                    "github_username"
                ),  # Always pass owner, let backend handle account type detection
            }

            # Use installation-id header for authentication
            headers = {"Content-Type": "application/json", "installation-id": str(metadata["installation_id"])}

            response = requests.post(
                f"{self.github_app_url}/api/publish",
                json=payload,
                headers=headers,
                timeout=45,  # Increased timeout for Backend's improved processing
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success", False):
                    repository_info = result.get("repository", {})
                    return PublishResult(
                        True,
                        "Repository created via GitHub App Installation",
                        {
                            "method": "api",
                            "repo_url": repository_info.get("html_url", ""),
                            "clone_url": repository_info.get("clone_url", ""),
                            "repository": repository_info,  # Pass full repository info
                            "registration_url": "https://github.com/mcp-factory/mcp-servers-hub",
                        },
                    )
                error_msg = result.get("error", "Unknown error")
                details = result.get("details", "")
                full_error = f"{error_msg}. {details}" if details else error_msg
                return PublishResult(False, f"GitHub App API failed: {full_error}")
            # Improved error handling following Backend team's example
            try:
                error_result = response.json()
                error_msg = error_result.get("error", "Unknown error")
                details = error_result.get("details", "")
                solutions = error_result.get("solutions", [])

                full_error = f"{error_msg}"
                if details:
                    full_error += f". {details}"
                if solutions:
                    full_error += f". Suggestions: {'; '.join(solutions)}"

                # Enhanced error type detection following Backend example
                error_type = "other"
                if details and "already exists" in details.lower():
                    error_type = "repository_already_exists"
                elif "Repository creation failed" in error_msg:
                    error_type = "repository_creation_failed"

                result_data = {"method": "api_failed", "error_type": error_type, "original_error": error_result}

                return PublishResult(False, f"GitHub App API failed: {full_error}", result_data)
            except Exception:
                error_text = response.text[:200] if response.text else "No response"
                return PublishResult(False, f"GitHub App API call failed (HTTP {response.status_code}): {error_text}")

        except (ConnectionError, requests.RequestException, TimeoutError) as e:
            return PublishResult(False, f"GitHub App connection failed: {e}")
        except Exception as e:
            return PublishResult(False, f"Installation API publishing failed: {e!s}")

    def _send_publish_request(self, project_info: dict[str, Any]) -> dict[str, Any]:
        """Send publish request with unified installation-id authentication"""
        try:
            # Unified use of installation-id authentication - working with backend simplified solution
            headers = {"Content-Type": "application/json"}
            installation_id = project_info.get("installation_id")
            if installation_id:
                headers["installation-id"] = str(installation_id)

            response = requests.post(
                f"{self.github_app_url}/api/publish", json=project_info, headers=headers, timeout=30
            )

            # Success response
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, dict):
                    return result

            # Handle error responses with detailed information
            try:
                error_data = response.json()
                if isinstance(error_data, dict) and "error" in error_data:
                    error_detail = error_data["error"]

                    # Check for session-related errors
                    if "Missing session ID" in error_detail or "Invalid or expired session" in error_detail:
                        return {"success": False, "error": error_detail, "needs_reauth": True}

                    # Add HTTP status context to error message
                    if response.status_code == 400:
                        return {"success": False, "error": f"Bad request: {error_detail}"}
                    if response.status_code == 401:
                        return {"success": False, "error": f"Authentication failed: {error_detail}"}
                    if response.status_code == 403:
                        return {"success": False, "error": f"Permission denied: {error_detail}"}
                    if response.status_code == 404:
                        return {"success": False, "error": f"Service not found: {error_detail}"}
                    if response.status_code == 429:
                        return {"success": False, "error": f"Rate limit exceeded: {error_detail}"}
                    if response.status_code >= 500:
                        return {"success": False, "error": f"Server error: {error_detail}"}
                    return {"success": False, "error": error_detail}
                return {"success": False, "error": f"Invalid error response format (HTTP {response.status_code})"}

            except ValueError:
                # Non-JSON error response
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text[:200]}"}

        except requests.Timeout:
            return {"success": False, "error": "Request timeout - GitHub App did not respond within 30 seconds"}
        except requests.ConnectionError:
            return {"success": False, "error": "Connection failed - Unable to reach GitHub App service"}
        except requests.RequestException as e:
            return {"success": False, "error": f"Request failed: {e!s}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error during API call: {e!s}"}

    def detect_git_info(self, project_path: Path) -> dict[str, Any]:
        """Detect Git repository information"""
        # First check if .git directory exists
        git_dir = project_path / ".git"
        if not git_dir.exists():
            raise GitError(
                f"No git repository found in {project_path}. "
                f"Initialize a git repository with: cd {project_path} && git init && git add . && git commit -m 'Initial commit'"
            )

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

            # Get remote URL (might not exist for new repos)
            try:
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
            except subprocess.CalledProcessError:
                # No remote origin configured
                raise GitError(
                    f"No remote origin configured for git repository in {project_path}. "
                    f"Please add a GitHub remote with: cd {project_path} && git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git"
                ) from None

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

    def init_git_repository(self, project_path: Path, project_name: str) -> bool:
        """Initialize git repository for the project"""
        try:
            git_dir = project_path / ".git"
            if git_dir.exists():
                return True  # Already initialized

            # Initialize git repository
            subprocess.run(["git", "init"], cwd=project_path, check=True)

            # Add all files
            subprocess.run(["git", "add", "."], cwd=project_path, check=True)

            # Create initial commit
            commit_message = f"Initial commit for {project_name}"
            subprocess.run(["git", "commit", "-m", commit_message], cwd=project_path, check=True)

            return True

        except subprocess.CalledProcessError as e:
            self.error_handler.handle_error(
                "init_git_repository",
                GitError(f"Failed to initialize git repository: {e}"),
                {"project_path": str(project_path)},
                reraise=False,
            )
            return False

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

    def _extract_license(self, project_info: dict[str, Any]) -> str:
        """Extract license information from project information"""
        license_info = project_info.get("license", "MIT")

        # Handle both string and dict formats
        if isinstance(license_info, dict):
            # New format: license = { text = "MIT" }
            text_value = license_info.get("text", "MIT")
            return str(text_value) if text_value is not None else "MIT"
        if isinstance(license_info, str):
            # Simple format: license = "MIT"
            return license_info
        return "MIT"

    def _detect_language(self, project_path: Path) -> str:
        """Validate project language - ensure it's a Python project created by mcp-factory"""
        # Check necessary Python project files
        if not (project_path / "pyproject.toml").exists():
            raise PublishError("Not a valid mcp-factory project: missing pyproject.toml")

        # Check if misused on non-Python projects
        if (project_path / "package.json").exists():
            raise PublishError("Cannot publish JavaScript project - mcp-factory only supports Python MCP servers")
        if (project_path / "Cargo.toml").exists():
            raise PublishError("Cannot publish Rust project - mcp-factory only supports Python MCP servers")
        if (project_path / "go.mod").exists():
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
            "AGENTS.md",  # AI agent development guidelines
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
