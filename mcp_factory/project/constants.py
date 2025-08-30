"""Project-related constant definitions

Unified management of constants used in project building and validation processes
"""

# Supported module types
ALLOWED_MODULE_TYPES = {"tools", "resources", "prompts"}

# Required project files
REQUIRED_PROJECT_FILES = [
    "server.py",
    "config.yaml",
    "pyproject.toml",
    "README.md",
    "AGENTS.md",
    "CHANGELOG.md",
    ".env",
    ".gitignore",
]

# Project structure related constants
PROJECT_STRUCTURE = {
    "tools/": "Tools module directory",
    "resources/": "Resources module directory",
    "prompts/": "Prompt template directory",
    "server.py": "MCP server main file",
    "config.yaml": "Project configuration file",
    "pyproject.toml": "Python project configuration",
    "README.md": "Project documentation",
    "AGENTS.md": "AI agent development guidelines",
    "CHANGELOG.md": "Version change log",
    ".env": "Environment variables configuration file",
    ".gitignore": "Git ignore file",
}
