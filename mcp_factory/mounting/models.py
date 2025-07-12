"""
MCP Factory Mounting - Data Models

Define data structures related to external server mounting:
- DiscoveredServer: Discovered server information (for Agent-discovered servers)
- ServerConfig: Server configuration information (for mounting)
- MountedServerInfo: Mounted server runtime information

These models focus on configuration management and mount status tracking for external servers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import subprocess

    from fastmcp import Client

logger = logging.getLogger(__name__)


# Note: Client is imported from fastmcp for actual MCP client connections


@dataclass
class DiscoveredServer:
    """Discovered server information"""

    name: str
    description: str
    source: str  # "builtin", "registry", "local", "config", "smithery", "mcp-market", etc.
    config_template: dict[str, Any]
    requirements: list[str]
    tags: list[str]
    # New fields for external registries
    registry_url: str | None = None  # Source registry URL
    author: str | None = None  # Author information
    version: str | None = None  # Version information
    license: str | None = None  # License
    documentation_url: str | None = None  # Documentation link
    repository_url: str | None = None  # Code repository link
    install_instructions: str | None = None  # Installation instructions
    popularity_score: int = 0  # Popularity score

    @property
    def is_local(self) -> bool:
        """Whether it's a local script server"""
        return "command" in self.config_template

    @property
    def is_remote(self) -> bool:
        """Whether it's a remote HTTP server"""
        return "url" in self.config_template

    def to_server_config(self) -> ServerConfig:
        """Convert to ServerConfig object"""
        return ServerConfig.from_discovered_server(self)

    def matches_tags(self, tags: list[str]) -> bool:
        """Check if matches specified tags"""
        return any(tag in self.tags for tag in tags)

    def matches_query(self, query: str) -> bool:
        """Check if matches search query"""
        query_lower = query.lower()
        return (
            query_lower in self.name.lower()
            or query_lower in self.description.lower()
            or any(query_lower in tag.lower() for tag in self.tags)
        )


@dataclass
class ServerConfig:
    """Server configuration information"""

    name: str
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    transport: str | None = None
    headers: dict[str, str] | None = None
    timeout: float = 30.0

    def __post_init__(self) -> None:
        if self.args is None:
            self.args = []
        if self.env is None:
            self.env = {}
        if self.headers is None:
            self.headers = {}

    @classmethod
    def from_discovered_server(cls, discovered: DiscoveredServer) -> ServerConfig:
        """Create configuration from discovered server"""
        template = discovered.config_template
        return cls(
            name=discovered.name,
            command=template.get("command"),
            args=template.get("args", []),
            env=template.get("env", {}),
            url=template.get("url"),
            transport=template.get("transport"),
            headers=template.get("headers", {}),
            timeout=template.get("timeout", 30.0),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ServerConfig:
        """Create configuration from dictionary (Agent-friendly interface)"""
        return cls(
            name=data["name"],
            command=data.get("command"),
            args=data.get("args", []),
            env=data.get("env", {}),
            url=data.get("url"),
            transport=data.get("transport"),
            headers=data.get("headers", {}),
            timeout=data.get("timeout", 30.0),
        )

    @property
    def is_local(self) -> bool:
        """Whether it's a local script server"""
        return self.command is not None

    @property
    def is_remote(self) -> bool:
        """Whether it's a remote HTTP server"""
        return self.url is not None

    @property
    def inferred_transport(self) -> str:
        """Inferred transport protocol"""
        if self.transport:
            return self.transport
        return "stdio" if self.is_local else "streamable-http"


class MountedServerInfo:
    """Mounted server runtime information"""

    def __init__(self, name: str, config: ServerConfig, prefix: str = ""):
        self.name = name
        self.config = config
        self.prefix = prefix
        self.client: Client[Any] | None = None
        self.process: subprocess.Popen[str] | None = None
        self.status = "stopped"  # stopped, starting, running, failed
        self.last_health_check = 0.0
        self.restart_attempts = 0
        self.error_message = ""

    @property
    def is_local(self) -> bool:
        """Whether it's a local script server"""
        return self.config.is_local

    @property
    def is_remote(self) -> bool:
        """Whether it's a remote HTTP server"""
        return self.config.is_remote

    @property
    def transport(self) -> str:
        """Get transport protocol"""
        return self.config.inferred_transport
