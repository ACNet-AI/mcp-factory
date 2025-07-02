"""FastMCP-Factory test configuration and shared fixtures."""

import asyncio
import shutil
import tempfile
import tracemalloc
import warnings
from collections.abc import Generator, Iterator
from pathlib import Path

import pytest
import yaml

from mcp_factory import MCPFactory


# Set up pytest session
def pytest_configure(config: pytest.Config) -> None:
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

    # Ensure asyncio warnings are handled
    warnings.filterwarnings("ignore", category=DeprecationWarning)


# Provide temporary configuration file
@pytest.fixture
def temp_config_file() -> Iterator[str]:
    """Create a temporary configuration file for testing."""
    config = {
        "server": {
            "name": "test-server",
            "instructions": "Test server for unit tests",
            "expose_management_tools": True,
        },
        "transport": {
            "host": "localhost",
            "port": 8080,
        },
    }
    yaml_content = yaml.dump(config)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
        temp_file.write(yaml_content)
        config_path = temp_file.name

    yield config_path

    # Clean up temporary file
    config_path_obj = Path(config_path)
    if config_path_obj.exists():
        config_path_obj.unlink()


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
