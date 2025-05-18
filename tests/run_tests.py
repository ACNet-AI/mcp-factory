#!/usr/bin/env python
"""Run all FastMCP-Factory tests.

Usage: python -m tests.run_tests
"""

import os
import sys

import pytest


def main() -> int:
    """Main function to run tests."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    print("Running FastMCP-Factory tests...")

    # Run all tests using pytest
    args = ["--verbose", "tests/"]

    # Add additional command-line arguments if provided
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])

    result = pytest.main(args)
    return result


if __name__ == "__main__":
    sys.exit(main())
