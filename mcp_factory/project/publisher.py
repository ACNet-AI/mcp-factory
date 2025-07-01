"""MCP Project Publisher Module - Based on GitHub App Registry Pattern"""

import base64
import json
import subprocess
import textwrap
import time
import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import toml

from .validator import ProjectValidator, ValidationError


class PublishError(Exception):
    """Publishing error"""

    pass


class GitError(Exception):
    """Git operation error"""

    pass


class ProjectPublisher:
    """MCP Project Publisher - Based on GitHub App and Registry Pattern"""

    def __init__(self, github_app_url: str = "https://mcp-project-manager.vercel.app"):
        """Initialize publisher"""
        self.validator = ProjectValidator()
        self.github_app_name = "mcp-project-manager"
        self.hub_repo = "ACNet-AI/mcp-servers-hub"
        self.github_app_url = github_app_url.rstrip("/")

    # ============================================================================
    # Main Publishing Workflow
    # ============================================================================

    def publish(self, project_path: str) -> bool:
        """
        🚀 One-click publish project to GitHub and register to MCP Servers Hub

        The system will automatically select the best publishing method,
        users don't need to understand technical details.

        Args:
            project_path: Project path

        Returns:
            Whether publishing was successful
        """
        project_path = Path(project_path).resolve()
        print(f"🔍 Validating project: {project_path}")

        try:
            # 1. Validate project
            if not self.validate_project(project_path):
                return False
            print("✅ Project validation passed")

            # 2. Extract project metadata
            metadata = self.extract_project_metadata(project_path)
            print(f"📋 Project name: {metadata['name']}")

            # 3. Smart publishing (internal logic invisible to users)
            return self._smart_publish(project_path, metadata)

        except (PublishError, GitError) as e:
            print(f"❌ Publishing failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unknown error occurred during publishing: {e}")
            return False

    def _smart_publish(self, project_path: Path, metadata: dict[str, Any]) -> bool:
        """
        🧠 Smart publishing logic - internal implementation invisible to users

        Try the best experience API publishing, automatically fallback to traditional mode on failure
        """
        # 1. Try API publishing (silent attempt)
        if self._try_api_publish(project_path, metadata):
            return True

        # 2. API publishing failed, automatically switch to traditional mode
        print("🔄 Trying alternative publishing method...")
        return self._fallback_manual_publish(project_path, metadata)

    # ============================================================================
    # 🆕 GitHub App API Methods
    # ============================================================================

    def _check_github_app_status(self) -> bool:
        """Check GitHub App service status"""
        try:
            response = requests.get(f"{self.github_app_url}/api/status", timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def _prepare_api_payload(self, project_path: Path, metadata: dict[str, Any]) -> dict[str, Any]:
        """Prepare API payload for GitHub App"""

        # Collect project files
        files = self._collect_project_files(project_path)

        # Detect language
        language = self._detect_language(project_path)

        # Detect GitHub username
        owner = self._detect_github_username()

        return {
            "projectName": metadata["name"],
            "description": metadata["description"],
            "version": metadata.get("version", "1.0.0"),
            "language": language,
            "category": metadata.get("category", "utilities"),
            "tags": metadata.get("tags", ["mcp", "server"]),
            "owner": owner,
            "repoName": metadata["name"],
            "files": files,
            "packageJson": self._get_package_json(project_path),
        }

    def _collect_project_files(self, project_path: Path) -> list[dict[str, str]]:
        """Collect project files for API upload"""
        files = []

        # File patterns to include
        include_patterns = [
            "*.py",
            "*.js",
            "*.ts",
            "*.json",
            "*.toml",
            "*.yaml",
            "*.yml",
            "README*",
            "LICENSE*",
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Dockerfile",
            ".gitignore",
        ]

        # Directories to exclude
        exclude_dirs = {
            "__pycache__",
            ".git",
            "node_modules",
            ".venv",
            "venv",
            ".env",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
        }

        def should_include_file(file_path: Path) -> bool:
            # Check if in excluded directory
            for part in file_path.parts:
                if part in exclude_dirs:
                    return False

            # Check file size (limit 100KB)
            try:
                if file_path.stat().st_size > 100 * 1024:
                    return False
            except OSError:
                return False

            # Check if matches include patterns
            for pattern in include_patterns:
                if file_path.match(pattern):
                    return True

            return False

        # Collect files recursively
        for file_path in project_path.rglob("*"):
            if file_path.is_file() and should_include_file(file_path):
                try:
                    relative_path = file_path.relative_to(project_path)
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    files.append({"path": str(relative_path), "content": content})
                except (UnicodeDecodeError, OSError):
                    # Skip binary files
                    continue

        return files

    def _detect_language(self, project_path: Path) -> str:
        """Detect project language"""
        if (project_path / "package.json").exists():
            return "javascript"
        elif (project_path / "pyproject.toml").exists() or (project_path / "requirements.txt").exists():
            return "python"
        elif any(project_path.glob("*.py")):
            return "python"
        elif any(project_path.glob("*.js")) or any(project_path.glob("*.ts")):
            return "javascript"
        else:
            return "python"  # default

    def _detect_github_username(self) -> str:
        """Detect GitHub username"""
        try:
            # Try GitHub CLI
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, check=True)
            for line in result.stderr.split("\n"):
                if "Logged in to github.com as" in line:
                    username = line.split("as")[-1].strip().split()[0]
                    return username
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        try:
            # Try git config
            result = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, check=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            pass

        # Ask user input
        username = input("Please enter your GitHub username: ").strip()
        if not username:
            raise ValueError("GitHub username cannot be empty")
        return username

    def _get_package_json(self, project_path: Path) -> dict | None:
        """Get package.json content if exists"""
        package_json_path = project_path / "package.json"
        if package_json_path.exists():
            try:
                with open(package_json_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    def _send_publish_request(self, project_info: dict[str, Any]) -> dict[str, Any]:
        """Send publish request to GitHub App API"""
        api_url = f"{self.github_app_url}/api/publish"

        response = requests.post(
            api_url,
            json=project_info,
            headers={"Content-Type": "application/json", "User-Agent": "mcp-factory/1.0.0"},
            timeout=120,  # Extended timeout for file upload
        )

        if response.status_code == 200:
            return response.json()
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", f"HTTP {response.status_code}")
            except ValueError:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"

            return {"success": False, "error": error_msg}

    # ============================================================================
    # Project Validation and Metadata Processing
    # ============================================================================

    def validate_project(self, project_path: Path) -> bool:
        """
        Validate project structure and configuration

        Args:
            project_path: Project path

        Returns:
            Whether validation passed
        """
        try:
            result = self.validator.validate_project(str(project_path))
            if not result["valid"]:
                for error in result["errors"]:
                    print(f"❌ {error}")
                return False

            for warning in result["warnings"]:
                print(f"⚠️ {warning}")

            return True
        except ValidationError as e:
            print(f"❌ Project validation failed: {e}")
            return False

    def extract_project_metadata(self, project_path: Path) -> dict[str, Any]:
        """
        Extract project metadata

        Args:
            project_path: Project path

        Returns:
            Project metadata
        """
        pyproject_path = project_path / "pyproject.toml"

        if not pyproject_path.exists():
            raise PublishError("Missing pyproject.toml file")

        try:
            config = toml.load(pyproject_path)
        except Exception as e:
            raise PublishError(f"Failed to parse pyproject.toml: {e}") from e

        # Check if hub configuration exists
        hub_config = config.get("tool", {}).get("mcp-servers-hub", {})
        if not hub_config:
            print("❌ Missing publishing configuration")
            print("🔧 Starting configuration wizard...")

            if not self.setup_hub_configuration(project_path):
                raise PublishError("Configuration wizard cancelled")

            # Reload configuration
            config = toml.load(pyproject_path)
            hub_config = config.get("tool", {}).get("mcp-servers-hub", {})

        # Validate required fields
        required_fields = ["name", "description", "author", "github_username"]
        for field in required_fields:
            if not hub_config.get(field):
                raise PublishError(f"Missing required configuration field: {field}")

        return hub_config

    # ============================================================================
    # Configuration Wizard
    # ============================================================================

    def setup_hub_configuration(self, project_path: Path) -> bool:
        """
        Interactive Hub configuration setup

        Args:
            project_path: Project path

        Returns:
            Whether configuration was successfully set up
        """
        pyproject_path = project_path / "pyproject.toml"

        print(
            textwrap.dedent("""
            🚀 MCP Servers Hub Publishing Configuration Wizard

            To publish your project to GitHub and register to MCP Servers Hub, some basic information is needed.
        """).strip()
        )

        # Infer default values from existing project information
        existing_info = self._extract_existing_project_info(project_path)

        try:
            # Collect configuration information
            print("📝 Please provide the following information:")

            name = input(f"Project name [{existing_info.get('name', '')}]: ").strip() or existing_info.get("name", "")
            description = input(
                f"Project description [{existing_info.get('description', '')}]: "
            ).strip() or existing_info.get("description", "")
            author = input("Author name: ").strip()
            github_username = input("GitHub username: ").strip()

            print("\n📂 Project categories (comma-separated, e.g.: tools,productivity):")
            categories_input = input("Categories: ").strip()
            categories = (
                [cat.strip() for cat in categories_input.split(",") if cat.strip()] if categories_input else ["tools"]
            )

            print("\n🏷️ Project tags (comma-separated, e.g.: mcp,server,automation):")
            tags_input = input("Tags: ").strip()
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else ["mcp", "server"]

            license_name = input("License [MIT]: ").strip() or "MIT"

            # Validate required fields
            if not all([name, description, author, github_username]):
                print("❌ All required fields must be filled")
                return False

            # Generate configuration
            hub_config = {
                "name": name,
                "description": description,
                "author": author,
                "github_username": github_username,
                "categories": categories,
                "tags": tags,
                "license": license_name,
            }

            # Add to pyproject.toml
            self._add_hub_config_to_pyproject(pyproject_path, hub_config)

            print(f"✅ Configuration added to {pyproject_path}")
            return True

        except KeyboardInterrupt:
            print("\n❌ Configuration cancelled")
            return False
        except Exception as e:
            print(f"❌ Error occurred during configuration: {e}")
            return False

    def _extract_existing_project_info(self, project_path: Path) -> dict[str, str]:
        """Extract information from existing project files"""
        info = {}

        # Extract basic information from pyproject.toml
        pyproject_path = project_path / "pyproject.toml"
        if pyproject_path.exists():
            try:
                config = toml.load(pyproject_path)
                project_config = config.get("project", {})
                info["name"] = project_config.get("name", "")
                info["description"] = project_config.get("description", "")
            except Exception:
                pass

        # Infer project name from directory name
        if not info.get("name"):
            info["name"] = project_path.name

        return info

    def _add_hub_config_to_pyproject(self, pyproject_path: Path, hub_config: dict[str, Any]) -> None:
        """Add hub configuration to pyproject.toml file"""
        try:
            # Read existing configuration
            config = toml.load(pyproject_path)

            # Add hub configuration
            if "tool" not in config:
                config["tool"] = {}
            config["tool"]["mcp-servers-hub"] = hub_config

            # Write back to file
            with open(pyproject_path, "w", encoding="utf-8") as f:
                toml.dump(config, f)

        except Exception as e:
            raise PublishError(f"Unable to update pyproject.toml file: {e}") from e

    # ============================================================================
    # Git Repository Handling
    # ============================================================================

    def detect_git_info(self, project_path: Path) -> dict[str, str]:
        """
        Detect Git repository information

        Args:
            project_path: Project path

        Returns:
            Git repository information
        """
        try:
            # Check if it's a Git repository
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=project_path,
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip() != "true":
                raise GitError("Current directory is not a Git repository")

            # Get remote repository URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"], cwd=project_path, capture_output=True, text=True, check=True
            )

            remote_url = result.stdout.strip()
            if not remote_url:
                raise GitError("Origin remote repository not found")

            # Parse GitHub repository information
            repo_info = self._parse_github_url(remote_url)

            # Check working directory status
            result = subprocess.run(
                ["git", "status", "--porcelain"], cwd=project_path, capture_output=True, text=True, check=True
            )
            has_changes = bool(result.stdout.strip())

            # Check if there are unpushed commits
            result = subprocess.run(
                ["git", "log", "origin/main..HEAD", "--oneline"], cwd=project_path, capture_output=True, text=True
            )
            has_unpushed = bool(result.stdout.strip())

            return {
                "remote_url": remote_url,
                "owner": repo_info["owner"],
                "repo": repo_info["repo"],
                "full_name": f"{repo_info['owner']}/{repo_info['repo']}",
                "has_changes": has_changes,
                "has_unpushed": has_unpushed,
            }

        except subprocess.CalledProcessError as e:
            raise GitError(f"Git command execution failed: {e}") from e
        except Exception as e:
            raise GitError(f"Failed to detect Git information: {e}") from e

    def _parse_github_url(self, url: str) -> dict[str, str]:
        """Parse GitHub repository URL"""
        # Handle SSH format: git@github.com:owner/repo.git
        if url.startswith("git@github.com:"):
            path = url.replace("git@github.com:", "").replace(".git", "")
            owner, repo = path.split("/", 1)
            return {"owner": owner, "repo": repo}

        # Handle HTTPS format: https://github.com/owner/repo.git
        if "github.com" in url:
            parsed = urlparse(url)
            path = parsed.path.strip("/").replace(".git", "")
            parts = path.split("/")
            if len(parts) >= 2:
                return {"owner": parts[0], "repo": parts[1]}

        raise GitError(f"Unable to parse GitHub repository URL: {url}")

    def ensure_git_ready(self, project_path: Path, git_info: dict[str, str]) -> bool:
        """
        Ensure Git repository is ready for publishing

        Args:
            project_path: Project path
            git_info: Git repository information

        Returns:
            Whether ready
        """
        if git_info["has_changes"]:
            print("⚠️ Detected uncommitted changes")
            response = input("Automatically commit changes? (y/N): ").strip().lower()

            if response == "y":
                try:
                    # Add all changes
                    subprocess.run(["git", "add", "."], cwd=project_path, check=True)

                    # Commit changes
                    subprocess.run(
                        ["git", "commit", "-m", "chore: prepare for MCP Servers Hub publication"],
                        cwd=project_path,
                        check=True,
                    )

                    print("✅ Changes committed")
                    git_info["has_unpushed"] = True

                except subprocess.CalledProcessError as e:
                    print(f"❌ Commit failed: {e}")
                    return False
            else:
                print("❌ Please commit or stage your changes first")
                return False

        if git_info["has_unpushed"]:
            print("⚠️ Detected unpushed commits")
            response = input("Automatically push to GitHub? (y/N): ").strip().lower()

            if response == "y":
                try:
                    subprocess.run(["git", "push", "origin", "main"], cwd=project_path, check=True)
                    print("✅ Pushed to GitHub")

                except subprocess.CalledProcessError as e:
                    print(f"❌ Push failed: {e}")
                    return False
            else:
                print("❌ Please push your changes to GitHub first")
                return False

        return True

    # ============================================================================
    # GitHub App Integration
    # ============================================================================

    def create_github_app_install_url(self, repo_full_name: str, metadata: dict[str, Any]) -> str:
        """Create GitHub App installation URL"""
        # Create state parameter with context information
        context = {
            "action": "publish_project",
            "repo": repo_full_name,
            "project_name": metadata["name"],
            "timestamp": int(time.time()),
        }

        state = base64.b64encode(json.dumps(context).encode()).decode()
        return f"https://github.com/apps/{self.github_app_name}/installations/new?state={state}"

    def guide_github_app_installation(self, repo_full_name: str, metadata: dict[str, Any]) -> bool:
        """
        Guide user through GitHub App installation

        Args:
            repo_full_name: Repository full name
            metadata: Project metadata

        Returns:
            Whether installation succeeded
        """
        install_url = self.create_github_app_install_url(repo_full_name, metadata)

        print(
            textwrap.dedent(f"""
            🚀 Publish project to GitHub and register to MCP Servers Hub

            📍 Project: {metadata["name"]}
            📍 Repository: {repo_full_name}

            🔗 GitHub App installation required to enable automatic publishing

            📋 Installation steps:
            1. GitHub App installation page will open shortly
            2. Select your account or organization
            3. ⭐ Important: Select "Only select repositories"
            4. ⭐ Important: Select repository "{repo_full_name}"
            5. Click "Install" to complete installation

            💡 Notes:
            - GitHub App will monitor your repository changes
            - Registry automatically updates when you push code
            - You can manage permissions in GitHub settings anytime

            Press Enter to open installation page...
        """).strip()
        )

        input()

        print("🌐 Opening GitHub App installation page...")
        webbrowser.open(install_url)

        print(
            textwrap.dedent("""
            ⏳ Please complete GitHub App installation in your browser

            After installation is complete, return to terminal and press Enter to continue...
        """).strip()
        )

        input()
        return True

    def trigger_initial_registration(self, repo_full_name: str, metadata: dict[str, Any]) -> bool:
        """
        Trigger initial registration (by pushing empty commit to trigger webhook)

        Args:
            repo_full_name: Repository full name
            metadata: Project metadata

        Returns:
            Whether trigger succeeded
        """
        print("🔄 Triggering initial registration...")

        try:
            # Create empty commit to trigger webhook
            subprocess.run(
                [
                    "git",
                    "commit",
                    "--allow-empty",
                    "-m",
                    f"feat: register {metadata['name']} with MCP Servers Hub\n\nThis commit triggers the initial registration of this MCP server project.",
                ],
                check=True,
            )

            # Push to trigger webhook
            subprocess.run(["git", "push", "origin", "main"], check=True)

            print("✅ Registration process triggered")
            print(f"📋 Your project will appear at https://github.com/{self.hub_repo} within a few minutes")

            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to trigger registration: {e}")
            return False

    def _try_api_publish(self, project_path: Path, metadata: dict[str, Any]) -> bool:
        """
        🤫 Silent API publishing attempt - no technical details shown, no user interaction required

        Returns:
            True if successful, False if should fallback to manual
        """
        try:
            # Silent check GitHub App service status
            if not self._check_github_app_status():
                return False

            # Collect project information
            project_info = self._prepare_api_payload(project_path, metadata)

            # Silent send publish request
            result = self._send_publish_request(project_info)

            if result["success"]:
                print("\n🎉 Project published successfully!")
                print(f"🔗 Repository URL: {result['repoUrl']}")
                if result.get("registrationUrl"):
                    print(f"📋 Registration URL: {result['registrationUrl']}")
                print("\n✅ Your MCP project has been successfully published and registered to the server hub!")
                return True
            else:
                # Silent failure, let system automatically fallback
                return False

        except Exception:
            # All exceptions are handled silently, let system automatically fallback
            return False

    def _fallback_manual_publish(self, project_path: Path, metadata: dict[str, Any]) -> bool:
        """
        🔧 Fallback to traditional publishing mode - simplified manual process

        Used when API publishing fails, but tries to simplify user operations
        """
        try:
            print("📝 Using traditional publishing process...")

            # Detect Git repository information
            print("🔍 Detecting Git repository information...")
            git_info = self.detect_git_info(project_path)
            print(f"📍 GitHub repository: {git_info['full_name']}")

            # Ensure Git status is ready
            if not self.ensure_git_ready(project_path, git_info):
                return False

            # Guide GitHub App installation
            if not self.guide_github_app_installation(git_info["full_name"], metadata):
                return False

            # Trigger initial registration
            if not self.trigger_initial_registration(git_info["full_name"], metadata):
                return False

            print("\n🎉 Publishing process completed!")
            print("✅ Your project has been successfully registered to the MCP Servers Hub")
            return True

        except (PublishError, GitError) as e:
            print(f"❌ Publishing failed: {e}")
            return False
