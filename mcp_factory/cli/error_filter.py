"""Intelligent Error Information Filtering Module

Provides user-friendly error message translation and solution suggestions.
"""

from __future__ import annotations

import re
import traceback
from typing import Any

from ..exceptions import (
    BuildError,
    ConfigurationError,
    MCPFactoryError,
    MountingError,
    ProjectError,
    ServerError,
    ValidationError,
)


class ErrorPattern:
    """Error pattern definition"""

    def __init__(
        self,
        pattern: str,
        user_message: str,
        suggestions: list[str] | None = None,
        docs_link: str | None = None,
    ) -> None:
        self.pattern = pattern
        self.user_message = user_message
        self.suggestions = suggestions or []
        self.docs_link = docs_link

    def matches(self, error_text: str) -> bool:
        """Check if error matches this pattern"""
        return bool(re.search(self.pattern, error_text, re.IGNORECASE))


class UserFriendlyErrorHandler:
    """User-friendly error handler - converts technical errors to user-friendly messages"""

    def __init__(self) -> None:
        self._error_patterns = self._build_error_patterns()

    def _build_error_patterns(self) -> list[ErrorPattern]:
        """Build error pattern database"""
        return [
            # Configuration errors
            ErrorPattern(
                pattern=r"(config.*not found|configuration.*missing)",
                user_message="Configuration file not found",
                suggestions=[
                    "Use 'mcp-factory config template' to generate a configuration template",
                    "Check if the configuration file path is correct",
                    "Ensure the configuration file exists in the workspace",
                ],
                docs_link="docs/configuration.md",
            ),
            ErrorPattern(
                pattern=r"(yaml.*error|invalid.*yaml|malformed.*yaml)",
                user_message="Configuration file format error",
                suggestions=[
                    "Check YAML syntax (proper indentation, colon spacing)",
                    "Use online YAML validator to check syntax",
                    "Ensure no tab characters are used (use spaces only)",
                ],
                docs_link="docs/configuration.md",
            ),
            ErrorPattern(
                pattern=r"(required.*field|missing.*required)",
                user_message="Required configuration field missing",
                suggestions=[
                    "Check if all required fields are present in the configuration",
                    "Reference the configuration template or documentation",
                    "Use 'mcp-factory config template' to generate a complete template",
                ],
                docs_link="docs/configuration.md",
            ),
            # Server errors
            ErrorPattern(
                pattern=r"(server.*not found|no.*server.*found)",
                user_message="Server not found",
                suggestions=[
                    "Use 'mcp-factory server list' to view all servers",
                    "Check if the server name or ID is correct",
                    "Ensure the server has been created",
                ],
            ),
            ErrorPattern(
                pattern=r"(port.*in use|address.*already.*use|port.*occupied)",
                user_message="Port already in use",
                suggestions=[
                    "Use a different port number",
                    "Stop other services using the same port",
                    "Check port usage with 'netstat' or 'lsof' command",
                ],
            ),
            ErrorPattern(
                pattern=r"(permission.*denied|access.*denied)",
                user_message="Permission denied",
                suggestions=[
                    "Check file and directory permissions",
                    "Try running with appropriate permissions",
                    "Ensure you have write access to the workspace directory",
                ],
            ),
            # Project errors
            ErrorPattern(
                pattern=r"(directory.*not.*empty|path.*exists)",
                user_message="Target directory is not empty",
                suggestions=[
                    "Choose a different directory name",
                    "Remove existing files from the directory",
                    "Use '--force' option to overwrite (if available)",
                ],
            ),
            ErrorPattern(
                pattern=r"(git.*not.*found|not.*git.*repository)",
                user_message="Git repository not found",
                suggestions=[
                    "Initialize Git repository: 'git init'",
                    "Ensure Git is installed",
                    "Check if you're in the correct project directory",
                ],
            ),
            # Network errors
            ErrorPattern(
                pattern=r"(connection.*refused|connection.*timeout|network.*unreachable)",
                user_message="Network connection error",
                suggestions=[
                    "Check network connection",
                    "Verify server address and port",
                    "Check firewall settings",
                ],
            ),
            # Dependency errors
            ErrorPattern(
                pattern=r"(module.*not.*found|import.*error|no.*module.*named)",
                user_message="Missing dependency",
                suggestions=[
                    "Install missing dependencies: 'pip install -r requirements.txt'",
                    "Check if virtual environment is activated",
                    "Update dependency packages",
                ],
            ),
            # Workspace errors
            ErrorPattern(
                pattern=r"(workspace.*not.*found|invalid.*workspace)",
                user_message="Workspace directory error",
                suggestions=[
                    "Create workspace directory first",
                    "Check workspace path is correct",
                    "Use absolute path if relative path fails",
                ],
            ),
        ]

    def process_error(self, error: Exception, operation: str | None = None, verbose: bool = False) -> dict[str, Any]:
        """
        Process error and generate user-friendly information

        Args:
            error: Exception object
            operation: Operation description
            verbose: Whether to show technical details

        Returns:
            dict containing processed error information
        """
        error_info: dict[str, Any] = {
            "original_error": str(error),
            "error_type": type(error).__name__,
            "operation": operation,
            "user_message": None,
            "suggestions": [],
            "docs_link": None,
            "technical_details": None,
        }

        # Extract user-friendly message and suggestions
        if isinstance(error, MCPFactoryError):
            error_info.update(self._process_factory_error(error))
        else:
            error_info.update(self._process_generic_error(error))

        # Add technical details if verbose mode
        if verbose:
            error_info["technical_details"] = {
                "exception_type": type(error).__name__,
                "exception_message": str(error),
                "traceback": traceback.format_exc(),
            }

        return error_info

    def _process_factory_error(self, error: MCPFactoryError) -> dict[str, Any]:
        """Process MCP Factory specific errors"""
        result: dict[str, Any] = {
            "user_message": error.message,
            "suggestions": [],
            "docs_link": None,
        }

        # Add type-specific suggestions
        if isinstance(error, ConfigurationError):
            result["suggestions"] = [
                "Check configuration file syntax and format",
                "Use 'mcp-factory config template' to generate a reference template",
                "Verify all required fields are present",
            ]
            result["docs_link"] = "docs/configuration.md"

        elif isinstance(error, ServerError):
            result["suggestions"] = [
                "Use 'mcp-factory server list' to check server status",
                "Verify server configuration",
                "Check server logs for detailed error information",
            ]

        elif isinstance(error, ProjectError):
            result["suggestions"] = [
                "Ensure project directory exists and is accessible",
                "Check project structure and required files",
                "Verify permissions on project directory",
            ]
            result["docs_link"] = "docs/getting-started.md"

        elif isinstance(error, MountingError):
            result["suggestions"] = [
                "Check mounted server configuration",
                "Verify external server is accessible",
                "Review mount point settings",
            ]
            result["docs_link"] = "docs/middleware.md"

        elif isinstance(error, ValidationError):
            result["suggestions"] = [
                "Review validation error details",
                "Check data format and required fields",
                "Reference configuration documentation",
            ]

        elif isinstance(error, BuildError):
            result["suggestions"] = [
                "Check project dependencies",
                "Verify build configuration",
                "Ensure all required files are present",
            ]

        # Try pattern matching for more specific messages
        pattern_result = self._match_error_patterns(str(error))
        if pattern_result:
            result.update(pattern_result)

        return result

    def _process_generic_error(self, error: Exception) -> dict[str, Any]:
        """Process generic Python errors"""
        error_text = str(error)

        # Try pattern matching
        pattern_result = self._match_error_patterns(error_text)
        if pattern_result:
            return pattern_result

        # Default generic error handling
        return {
            "user_message": f"An unexpected error occurred: {error_text}",
            "suggestions": [
                "Try the operation again",
                "Check system resources and permissions",
                "Use --verbose flag for detailed error information",
            ],
        }

    def _match_error_patterns(self, error_text: str) -> dict[str, Any] | None:
        """Match error text against known patterns"""
        for pattern in self._error_patterns:
            if pattern.matches(error_text):
                return {
                    "user_message": pattern.user_message,
                    "suggestions": pattern.suggestions,
                    "docs_link": pattern.docs_link,
                }
        return None

    def format_error_display(self, error_info: dict[str, Any]) -> str:
        """Format error information for display"""
        lines = []

        # Main error message
        if error_info.get("user_message"):
            lines.append(f"❌ {error_info['user_message']}")
        else:
            lines.append(f"❌ {error_info['original_error']}")

        # Operation context
        if error_info.get("operation"):
            lines.append(f"📍 Operation: {error_info['operation']}")

        # Suggestions
        suggestions = error_info.get("suggestions", [])
        if suggestions:
            lines.append("\n💡 Suggested solutions:")
            for i, suggestion in enumerate(suggestions, 1):
                lines.append(f"   {i}. {suggestion}")

        # Documentation link
        if error_info.get("docs_link"):
            lines.append(f"\n📚 See documentation: {error_info['docs_link']}")

        # Technical details (verbose mode)
        if error_info.get("technical_details"):
            lines.append("\n🔧 Technical details:")
            details = error_info["technical_details"]
            lines.append(f"   Type: {details['exception_type']}")
            lines.append(f"   Message: {details['exception_message']}")

        return "\n".join(lines)

    def suggest_common_solutions(self, operation: str) -> list[str]:
        """Suggest common solutions based on operation type"""
        common_solutions = {
            "server_start": [
                "Check if port is available",
                "Verify configuration file",
                "Ensure dependencies are installed",
            ],
            "server_stop": [
                "Check if server is running",
                "Use correct server name or ID",
                "Try force stop if normal stop fails",
            ],
            "config_load": [
                "Verify YAML syntax",
                "Check file permissions",
                "Use absolute file path",
            ],
            "project_create": [
                "Ensure target directory is empty",
                "Check write permissions",
                "Use valid project name",
            ],
        }

        return common_solutions.get(
            operation,
            [
                "Check system logs for details",
                "Verify file permissions and paths",
                "Try with --verbose flag for more information",
            ],
        )
