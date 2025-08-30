"""MCP-Factory Test Runner"""

import logging
import subprocess
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def get_test_stats() -> list[tuple[str, str]]:
    """Get test statistics"""
    test_files = []

    unit_dir = Path("tests/unit")
    integration_dir = Path("tests/integration")

    if unit_dir.exists():
        test_files.extend([("Unit Tests", test_file.name) for test_file in unit_dir.glob("test_*.py")])

    if integration_dir.exists():
        test_files.extend([("Integration Tests", test_file.name) for test_file in integration_dir.glob("test_*.py")])

    return test_files


def main() -> None:
    """Run tests"""
    logger.info("🧪 FastMCP-Factory Test Suite")
    logger.info("=" * 40)

    # Display test file statistics
    test_files = get_test_stats()
    logger.info("📊 Test File Statistics:")
    unit_count = sum(1 for t in test_files if t[0] == "Unit Tests")
    integration_count = sum(1 for t in test_files if t[0] == "Integration Tests")
    logger.info("   • Unit Test Files: %s", unit_count)
    logger.info("   • Integration Test Files: %s", integration_count)
    logger.info("   • Total Test Files: %s", len(test_files))
    logger.info("")

    # List test files
    for test_type, filename in test_files:
        logger.info("   📄 %s: %s", test_type, filename)
    logger.info("")

    # Check if there are server module tests
    servers_tests = [f for f in test_files if "servers" in f[1]]
    if servers_tests:
        logger.info("🔧 Server Module Tests:")
        for test_type, filename in servers_tests:
            logger.info("   📄 %s: %s", test_type, filename)
        logger.info("")

    # Run all tests
    cmd = ["pytest", "tests/unit/", "tests/integration/", "-v", "--tb=short"]

    logger.info("Executing command: %s", " ".join(cmd))
    logger.info("")

    try:
        result = subprocess.run(cmd, check=False, timeout=300)

        if result.returncode == 0:
            logger.info("\n✅ All tests passed!")
        else:
            logger.error("\n❌ Tests failed (exit code: %s)", result.returncode)

        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        logger.exception("❌ Test execution timed out")
        sys.exit(1)
    except FileNotFoundError:
        logger.exception("❌ pytest not found. Please install pytest.")
        sys.exit(1)


if __name__ == "__main__":
    main()
