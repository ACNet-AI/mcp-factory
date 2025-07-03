"""Project Validator - Specialized for project structure and content validation

Separate validation responsibilities from Builder, providing professional project validation functionality
"""

from __future__ import annotations

import keyword
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from .constants import ALLOWED_MODULE_TYPES, REQUIRED_PROJECT_FILES
from .template import BasicTemplate

# Configure logging
logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Validation exception"""


class ProjectValidator:
    """Project Validator

    Design Philosophy:
    - Dedicated to project validation, not mixed with build functionality
    - Can be used independently, does not depend on Builder
    - Supports multiple validation levels and scenarios
    """

    def __init__(self) -> None:
        """Initialize validator"""
        self.template = BasicTemplate()

    # =================== Name validation methods ===================

    def validate_project_name(self, name: str) -> None:
        """Validate if project name is legal

        Args:
            name: Project name

        Raises:
            ValidationError: Raised when project name is invalid
        """
        if not name or not name.strip():
            msg = "Project name cannot be empty"
            raise ValidationError(msg)

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
            raise ValidationError(
                f"Invalid project name: {name}. "
                "Project name must start with letter or underscore, "
                "contain only letters, numbers, underscores, and hyphens"
            )

        if keyword.iskeyword(name):
            raise ValidationError(f"Project name cannot be a Python keyword: {name}")

    def validate_function_name(self, function_name: str) -> None:
        """Validate if function name is legal

        Args:
            function_name: Function name

        Raises:
            ValidationError: Raised when function name is invalid
        """
        if not function_name or not function_name.strip():
            msg = "Function name cannot be empty"
            raise ValidationError(msg)

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", function_name):
            raise ValidationError(f"Invalid function name: {function_name}. Must be a valid Python identifier")

        if keyword.iskeyword(function_name):
            raise ValidationError(f"Function name cannot be a Python keyword: {function_name}")

    def validate_module_type(self, module_type: str) -> None:
        """Validate if module type is supported

        Args:
            module_type: Module type

        Raises:
            ValidationError: Raised when module type is not supported
        """
        if module_type not in ALLOWED_MODULE_TYPES:
            raise ValidationError(
                f"Unsupported module type: {module_type}. Allowed types: {', '.join(ALLOWED_MODULE_TYPES)}"
            )

    # =================== Project structure validation methods ===================

    def validate_project(self, project_path: str) -> dict[str, Any]:
        """Validate project structure integrity

        Args:
            project_path: Project path

        Returns:
            Validation result dictionary containing:
            - valid: Whether it's valid
            - errors: Error list
            - warnings: Warning list
            - structure: File and directory status
            - missing_files: List of missing files
            - missing_dirs: List of missing directories

        Raises:
            ValidationError: Raised when project path does not exist
        """
        logger.info("Validating project: %s", project_path)

        path = Path(project_path)
        if not path.exists():
            raise ValidationError(f"Project not found: {project_path}")

        result: dict[str, Any] = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "structure": {},
            "missing_files": [],
            "missing_dirs": [],
        }

        # Check required files
        required_files = REQUIRED_PROJECT_FILES
        for file_name in required_files:
            file_path = path / file_name
            if file_path.exists():
                result["structure"][file_name] = "exists"
            else:
                result["structure"][file_name] = "missing"
                result["missing_files"].append(file_name)
                result["errors"].append(f"Missing required file: {file_name}")
                result["valid"] = False

        # Check module directories
        for module_type in ALLOWED_MODULE_TYPES:
            module_dir = path / module_type
            dir_key = f"{module_type}/"
            if module_dir.exists():
                result["structure"][dir_key] = "exists"
            else:
                result["structure"][dir_key] = "missing"
                result["missing_dirs"].append(dir_key)
                result["warnings"].append(f"Module directory missing: {dir_key}")

        # Check configuration file format (simple syntax check)
        try:
            config_path = path / "config.yaml"
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    yaml.safe_load(f)  # Only check YAML syntax
        except Exception as e:
            result["errors"].append(f"Invalid config file format: {e}")
            result["valid"] = False

        logger.info("Project validation completed. Valid: %s", result["valid"])
        return result

    def validate_project_structure_only(self, project_path: str) -> bool:
        """Quick project structure validation (returns only true/false)

        Args:
            project_path: Project path

        Returns:
            Whether the project is valid
        """
        try:
            result = self.validate_project(project_path)
            return bool(result["valid"])
        except ValidationError:
            return False
