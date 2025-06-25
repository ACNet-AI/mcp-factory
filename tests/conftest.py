"""FastMCP-Factory test configuration and shared fixtures."""

import asyncio
import os
import shutil
import tempfile
import tracemalloc
from collections.abc import Generator
from typing import Any

import pytest
import yaml

from mcp_factory import MCPFactory


# Set up pytest session
def pytest_configure(config: Any) -> None:
    """Configure pytest session."""
    # Ensure asyncio warnings are handled
    asyncio.get_event_loop_policy().new_event_loop()
    # Enable tracemalloc for memory allocation tracking
    tracemalloc.start()

    # Add filter to ignore expected warnings
    config.addinivalue_line(
        "filterwarnings",
        "ignore:Exposing FastMCP native methods as management tools without authentication.*:UserWarning",
    )


# Provide temporary configuration file
@pytest.fixture
def temp_config_file() -> Generator[str, None, None]:
    """Create a temporary test configuration file and clean up after the test."""
    # Create temporary configuration file
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
        config = {
            "server": {
                "name": "test-server",
                "instructions": "Test server configuration",
                "host": "localhost",
                "port": 8080,
            }
        }
        yaml_content = yaml.dump(config)
        temp_file.write(yaml_content.encode("utf-8"))
        config_path = temp_file.name

    # Provide file path
    yield config_path

    # Clean up temporary file
    if os.path.exists(config_path):
        os.unlink(config_path)


# Create temporary directory for testing
@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing, automatically cleaned up after the test."""
    # Create temporary directory
    temp_dir_path = tempfile.mkdtemp()

    # Provide directory path
    yield temp_dir_path

    # Clean up directory after test
    shutil.rmtree(temp_dir_path, ignore_errors=True)


# Provide configured MCPFactory instance
@pytest.fixture
def factory(temp_dir: str) -> MCPFactory:
    """Return a configured MCPFactory instance with temporary workspace."""
    return MCPFactory(workspace_root=temp_dir)


# Provide factory with workspace
@pytest.fixture
def factory_with_workspace(temp_dir: str) -> MCPFactory:
    """Return a MCPFactory instance with temporary workspace."""
    return MCPFactory(workspace_root=temp_dir)
