# FastMCP-Factory Tests

## Test Structure

The tests for this project are divided into four main categories:

1. **unit**: Unit tests that test the independent functionality of each component
2. **integration**: Integration tests that test how multiple components work together
3. **examples**: Example usage tests that verify API usage patterns
4. **performance**: Performance tests that verify the performance characteristics of key operations

## Running Tests

To run all tests:

```bash
python -m pytest
```

To run tests in a specific category:

```bash
python -m pytest tests/unit/  # Run only unit tests
```

To generate a test coverage report:

```bash
python -m pytest --cov=mcp_factory
```

To generate a detailed HTML coverage report:

```bash
python -m pytest --cov=mcp_factory --cov-report=html
```

## Current Coverage

The current test coverage for the project is approximately 96%. For detailed coverage analysis and improvement plans, please see the `tests/coverage_report.md` file.

## Test Refactoring and Coverage Improvement Record

### 2023-10-01: Completed Test Refactoring

Restructured the test directory, dividing tests into four main categories:
- **unit**: Unit tests
- **integration**: Integration tests
- **examples**: Example usage tests
- **performance**: Performance tests

### 2023-10-15: Improved Test Coverage (Phase 1)

Significantly improved test coverage for the following modules:
- param_utils.py: 25% → 90% (+65%)
- auth/registry.py: 34% → 97% (+63%)
- auth/auth0.py: 62% → 88% (+26%)

Total test coverage increased from 62% to 81%, a 19% improvement.

### 2023-11-01: Improved Test Coverage (Phase 2)

Further improved test coverage for the following modules:
- auth/auth0.py: 88% → 100% (+12%)
- config_validator.py: 86% → 95% (+9%)
- factory.py: 68% → 98% (+30%)
- server.py: 77% → 94% (+17%)

Total test coverage increased from 81% to 96%, a 15% improvement.

## Writing New Tests

When adding new tests, please follow these best practices:

1. **Choose the right test category**: Select the appropriate test directory based on the purpose of the test
2. **Keep tests independent**: Each test should run independently, not relying on the state of other tests
3. **Use descriptive names**: Test names should clearly describe the functionality being tested
4. **Use appropriate assertions**: Use the most specific assertions to verify results
5. **Document test purpose**: Each test class and method should have clear documentation comments

## Mocking External Services

For tests that need to connect to external services, please use the unittest.mock module to create mock objects. For example:

```python
from unittest.mock import patch, MagicMock

# Mock external HTTP requests
with patch('httpx.AsyncClient.post') as mock_post:
    mock_post.return_value = MagicMock(status_code=200, json=lambda: {"success": True})
    # Test code...
``` 