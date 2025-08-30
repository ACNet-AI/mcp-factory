#!/usr/bin/env python3
"""
FastMCP-Factory Examples - Shared Utilities Module

Provides common tool classes and functions for all examples in the examples directory
"""

import logging
from pathlib import Path
from typing import Any

import yaml


class ConfigHelper:
    """Configuration management helper tool"""

    @staticmethod
    def load_config(config_path: str) -> dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config if isinstance(config, dict) else {}
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Configuration file not found: {config_path}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"Configuration file format error: {e}") from e

    @staticmethod
    def get_example_config_path(config_name: str) -> str:
        """Get the full path of example configuration file"""
        current_dir = Path(__file__).parent
        return str(current_dir / "configs" / f"{config_name}.yaml")

    @staticmethod
    def validate_server_config(config: dict[str, Any]) -> bool:
        """Validate basic structure of server configuration"""
        required_fields = ["server"]
        for field in required_fields:
            if field not in config:
                return False

        return "name" in config["server"]


class LoggerSetup:
    """Logging setup tool"""

    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """Set up standardized logger"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))

        # Avoid duplicate handler addition
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger


class ToolUtils:
    """Tool-related helper functions"""

    @staticmethod
    def get_basic_tools() -> dict[str, Any]:
        """Get basic tool definitions"""
        return {
            "echo": {
                "description": "Echo the input text",
                "parameters": {"text": {"type": "string", "description": "Text to echo"}},
            },
            "get_timestamp": {"description": "Get current timestamp", "parameters": {}},
        }

    @staticmethod
    def create_echo_tool() -> Any:
        """Create simple echo tool"""

        def echo(text: str) -> str:
            return f"Echo: {text}"

        return echo

    @staticmethod
    def create_timestamp_tool() -> Any:
        """Create timestamp tool"""
        import datetime

        def get_timestamp() -> str:
            return datetime.datetime.now().isoformat()

        return get_timestamp


class ServerTestHelper:
    """Server testing helper tool"""

    @staticmethod
    def create_test_config() -> dict[str, Any]:
        """Create test configuration"""
        return {
            "server": {
                "name": "test-server",
                "instructions": "Test server",
                "host": "localhost",
                "port": 8999,  # Use non-standard port to avoid conflicts
            },
            "tools": {"expose_management_tools": True},
            "advanced": {"log_level": "DEBUG"},
        }

    @staticmethod
    def create_mock_auth_config() -> dict[str, Any]:
        """Create mock authentication configuration"""
        return {
            "auth": {
                "enabled": False,  # Disable real authentication in test environment
                "provider": "mock",
                "config": {"test_mode": True, "mock_users": ["test@example.com", "admin@example.com"]},
            }
        }

    @staticmethod
    def create_mounting_test_config() -> dict[str, Any]:
        """Create mounting test configuration"""
        return {
            "mcpServers": {
                "test-local": {"command": "python", "args": ["-c", "print('Test server')"], "env": {"TEST": "true"}},
                "test-remote": {
                    "url": "https://httpbin.org/json",  # Use public test API
                    "timeout": 10,
                },
            },
            "mount_options": {
                "auto_start": False,  # Don't auto-start during testing
                "prefix_tools": True,
                "health_check": False,
            },
        }


def validate_example_environment() -> dict[str, bool]:
    """Validate example runtime environment"""
    results = {}

    # Check necessary Python packages
    try:
        import importlib.util

        spec = importlib.util.find_spec("mcp_factory")
        results["mcp_factory_available"] = spec is not None
    except ImportError:
        results["mcp_factory_available"] = False

    try:
        import importlib.util

        spec = importlib.util.find_spec("yaml")
        results["yaml_available"] = spec is not None
    except ImportError:
        results["yaml_available"] = False

    # Check configuration files
    config_dir = Path(__file__).parent / "configs"
    results["configs_directory_exists"] = config_dir.exists()

    if config_dir.exists():
        config_files = ["basic.yaml", "factory.yaml", "mounting.yaml", "production.yaml"]
        for config_file in config_files:
            config_path = config_dir / config_file
            results[f"{config_file}_exists"] = config_path.exists()

    return results


def print_example_status() -> bool:
    """Print example environment status"""
    status = validate_example_environment()

    print("📋 FastMCP-Factory Examples Environment Status Check:")
    print("=" * 50)

    for key, value in status.items():
        emoji = "✅" if value else "❌"
        print(f"{emoji} {key}: {value}")

    all_good = all(status.values())
    if all_good:
        print("\n🎉 All checks passed! Examples can be run.")
    else:
        print("\n⚠️ Issues found, please check the failed items above.")

    return all_good


if __name__ == "__main__":
    print_example_status()
