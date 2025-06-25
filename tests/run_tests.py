#!/usr/bin/env python3
"""MCP-Factory Test Runner"""

import subprocess
import sys
from pathlib import Path


def get_test_stats():
    """Get test statistics"""
    test_files = []
    unit_dir = Path("tests/unit")
    integration_dir = Path("tests/integration")

    if unit_dir.exists():
        for test_file in unit_dir.glob("test_*.py"):
            test_files.append(("Unit Tests", test_file.name))

    if integration_dir.exists():
        for test_file in integration_dir.glob("test_*.py"):
            test_files.append(("Integration Tests", test_file.name))

    return test_files


def main():
    """Run tests"""
    print("🧪 FastMCP-Factory Test Suite")
    print("=" * 40)

    # Display test file statistics
    test_files = get_test_stats()
    print("📊 Test File Statistics:")
    unit_count = sum(1 for t in test_files if t[0] == "Unit Tests")
    integration_count = sum(1 for t in test_files if t[0] == "Integration Tests")
    print(f"   • Unit Test Files: {unit_count}")
    print(f"   • Integration Test Files: {integration_count}")
    print(f"   • Total Test Files: {len(test_files)}")
    print()

    # List test files
    for test_type, filename in test_files:
        print(f"   📄 {test_type}: {filename}")
    print()

    # Check if there are server module tests
    servers_tests = [f for f in test_files if "servers" in f[1]]
    if servers_tests:
        print("🔧 Server Module Tests:")
        for test_type, filename in servers_tests:
            print(f"   📄 {test_type}: {filename}")
        print()

    # Run all tests
    cmd = ["pytest", "tests/unit/", "tests/integration/", "-v", "--tb=short"]

    print(f"Executing command: {' '.join(cmd)}")
    print()

    try:
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            print("\n✅ All tests passed!")
        else:
            print(f"\n❌ Tests failed (exit code: {result.returncode})")

        sys.exit(result.returncode)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
