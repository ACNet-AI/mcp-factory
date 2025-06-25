#!/usr/bin/env python3
"""Unified Dependency Checker for MCP Factory

Centralizes dependency checking logic to eliminate code duplication
"""

import subprocess
import sys
from pathlib import Path


class DependencyChecker:
    """Unified dependency checking utility"""

    def __init__(self, project_root: str | None = None):
        """Initialize dependency checker

        Args:
            project_root: Project root directory path
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.required_tools = {
            "ruff": "Code linting and formatting",
            "mypy": "Type checking",
            "bandit": "Security analysis",
            "pytest": "Testing framework",
            "pytest-cov": "Test coverage",
        }

    def check_python_version(self) -> tuple[bool, str]:
        """Check Python version compatibility

        Returns:
            Tuple of (is_compatible, version_info)
        """
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"

        # Require Python 3.11+
        is_compatible = version >= (3, 11)

        return is_compatible, version_str

    def check_tool_availability(self, tool: str) -> tuple[bool, str | None]:
        """Check if a specific tool is available

        Args:
            tool: Tool name to check

        Returns:
            Tuple of (is_available, version_or_error)
        """
        try:
            if tool == "pytest-cov":
                # Special handling for pytest-cov
                result = subprocess.run(
                    [sys.executable, "-c", "import pytest_cov; print(pytest_cov.__version__)"],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            else:
                result = subprocess.run([tool, "--version"], check=False, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                version = result.stdout.strip().split("\n")[0]
                return True, version
            return False, result.stderr.strip()

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            return False, str(e)

    def check_all_dependencies(self) -> dict[str, dict[str, any]]:
        """Check all required dependencies

        Returns:
            Dictionary with dependency check results
        """
        results = {"python": {}, "tools": {}, "summary": {}}

        # Check Python version
        py_compatible, py_version = self.check_python_version()
        results["python"] = {"version": py_version, "compatible": py_compatible, "required": ">=3.11"}

        # Check tools
        available_tools = 0
        for tool, description in self.required_tools.items():
            is_available, version_or_error = self.check_tool_availability(tool)
            results["tools"][tool] = {
                "available": is_available,
                "description": description,
                "version": version_or_error if is_available else None,
                "error": version_or_error if not is_available else None,
            }
            if is_available:
                available_tools += 1

        # Summary
        results["summary"] = {
            "python_compatible": py_compatible,
            "tools_available": available_tools,
            "tools_total": len(self.required_tools),
            "all_ready": py_compatible and available_tools == len(self.required_tools),
        }

        return results

    def print_dependency_report(self, results: dict | None = None) -> bool:
        """Print formatted dependency report

        Args:
            results: Check results, if None will run check

        Returns:
            True if all dependencies are satisfied
        """
        if results is None:
            results = self.check_all_dependencies()

        print("🔍 Dependency Check Report")
        print("=" * 50)

        # Python version
        py_info = results["python"]
        py_status = "✅" if py_info["compatible"] else "❌"
        print("\n🐍 Python Version:")
        print(f"   {py_status} Current: {py_info['version']} (Required: {py_info['required']})")

        # Tools
        print("\n🛠️  Development Tools:")
        for tool, info in results["tools"].items():
            status = "✅" if info["available"] else "❌"
            if info["available"]:
                print(f"   {status} {tool}: {info['version']}")
            else:
                print(f"   {status} {tool}: Not available")
                if info["error"]:
                    print(f"       Error: {info['error']}")

        # Summary
        summary = results["summary"]
        print("\n📊 Summary:")
        print(f"   Python Compatible: {'✅' if summary['python_compatible'] else '❌'}")
        print(f"   Tools Available: {summary['tools_available']}/{summary['tools_total']}")
        print(f"   Overall Status: {'✅ Ready' if summary['all_ready'] else '❌ Not Ready'}")

        return summary["all_ready"]

    def install_missing_dependencies(self) -> bool:
        """Attempt to install missing dependencies

        Returns:
            True if installation was successful
        """
        results = self.check_all_dependencies()

        if results["summary"]["all_ready"]:
            print("✅ All dependencies are already satisfied")
            return True

        missing_tools = [tool for tool, info in results["tools"].items() if not info["available"]]

        if not missing_tools:
            print("✅ All tools are available")
            return True

        print(f"📦 Installing missing tools: {', '.join(missing_tools)}")

        try:
            # Install missing tools
            install_cmd = [sys.executable, "-m", "pip", "install", *missing_tools]
            subprocess.run(install_cmd, check=True, capture_output=True, text=True)

            print("✅ Installation completed successfully")

            # Verify installation
            verification_results = self.check_all_dependencies()
            return verification_results["summary"]["all_ready"]

        except subprocess.CalledProcessError as e:
            print(f"❌ Installation failed: {e}")
            print(f"   Error output: {e.stderr}")
            return False

    def get_installation_guide(self) -> str:
        """Get installation guide for missing dependencies

        Returns:
            Formatted installation guide
        """
        results = self.check_all_dependencies()

        if results["summary"]["all_ready"]:
            return "✅ All dependencies are satisfied"

        guide = "🛠️ Installation Guide\n"
        guide += "=" * 30 + "\n\n"

        if not results["python"]["compatible"]:
            guide += "1. Update Python:\n"
            guide += "   Please install Python 3.11 or higher\n"
            guide += "   Visit: https://python.org/downloads\n\n"

        missing_tools = [tool for tool, info in results["tools"].items() if not info["available"]]

        if missing_tools:
            guide += "2. Install missing tools:\n"
            guide += f"   pip install {' '.join(missing_tools)}\n\n"
            guide += "   Or install development dependencies:\n"
            guide += "   pip install -e .[dev]\n\n"

        return guide


def main():
    """Main function for standalone usage"""
    import argparse

    parser = argparse.ArgumentParser(description="Check MCP Factory dependencies")
    parser.add_argument("--install", action="store_true", help="Attempt to install missing dependencies")
    parser.add_argument("--guide", action="store_true", help="Show installation guide")
    parser.add_argument("--project-root", help="Project root directory")

    args = parser.parse_args()

    checker = DependencyChecker(args.project_root)

    if args.guide:
        print(checker.get_installation_guide())
        return

    if args.install:
        success = checker.install_missing_dependencies()
        sys.exit(0 if success else 1)
    else:
        results = checker.check_all_dependencies()
        all_ready = checker.print_dependency_report(results)
        sys.exit(0 if all_ready else 1)


if __name__ == "__main__":
    main()
