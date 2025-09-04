"""
Authorization system configuration utilities
"""

import os
from pathlib import Path


def get_default_data_dir() -> Path:
    """
    Get default data directory

    Priority:
    1. Environment variable MCP_FACTORY_DATA_DIR
    2. System user data directory

    Returns:
        Path: Data directory path
    """
    # 1. Use environment variable first
    if data_dir_env := os.getenv("MCP_FACTORY_DATA_DIR"):
        path = Path(data_dir_env)
        path.mkdir(parents=True, exist_ok=True)
        return path

    # 2. Use user data directory
    if os.name == "nt":  # Windows
        appdata = os.getenv("APPDATA")
        if appdata:
            base_dir = Path(appdata)
        else:
            base_dir = Path.home()
        data_dir = base_dir / "mcp-factory"
    else:  # Unix/Linux/macOS
        data_dir = Path.home() / ".mcp-factory"

    # Ensure directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_default_authz_policy_path() -> str:
    """Get default authorization policy file path"""
    return str(get_default_data_dir() / "authz_policy.csv")


def get_default_authz_db_path() -> str:
    """Get default authorization database path"""
    return str(get_default_data_dir() / "authz_extended.db")


def get_default_audit_db_path() -> str:
    """Get default audit database path"""
    return str(get_default_data_dir() / "audit.db")


def get_default_audit_log_path() -> str:
    """Get default audit log path"""
    return str(get_default_data_dir() / "audit.log")
