#!/usr/bin/env python3
"""Script to run all FastMCP-Factory tests.

Usage:
python -m tests.run_all_tests [optional pytest arguments]
"""

import argparse
import os
import subprocess
import sys
from typing import List

# Add project root path to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def run_tests(args: List[str]) -> None:
    """Run tests and display results.

    Args:
        args: Command line argument list, to be passed to pytest.
    """
    test_modules = [
        "tests/unit",  # Unit tests
        "tests/integration",  # Integration tests
        "tests/examples",  # Example tests
        "tests/performance",  # Performance tests (if any)
    ]

    # Filter existing test modules
    existing_modules = [m for m in test_modules if os.path.isdir(os.path.join(project_root, m))]

    # If no specific test directory is specified, run all tests
    if not any(arg for arg in args if not arg.startswith("-") and "test" in arg):
        test_paths = existing_modules
    else:
        # Keep user-specified test paths
        test_paths = []

    # Build complete command line
    cmd = ["pytest"] + test_paths + args

    # Display command to be run
    print(f"Running test command: {' '.join(cmd)}")

    # Execute tests
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run FastMCP-Factory test suite")

    # Any unspecified arguments will be passed to pytest
    args, unknown = parser.parse_known_args()

    # Run tests
    run_tests(unknown)
