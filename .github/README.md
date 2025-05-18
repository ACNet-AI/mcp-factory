# CI/CD Workflow Configuration

This project uses GitHub Actions to automate testing and deployment processes, ensuring code quality and consistency.

## Workflow Description

The workflow `python-ci.yml` is triggered in the following cases:
- Pushing code to `main` or `master` branches
- Creating pull requests to `main` or `master` branches
- Only triggered when Python files, pyproject.toml, or workflow configuration are modified

## Included Tasks

The workflow includes the following tasks:

### 1. Code Quality Check (lint)
- Uses Ruff to check code style and quality
- Verifies that code formatting meets standards

### 2. Type Checking (typecheck)
- Uses Mypy for static type checking
- Ensures correctness of type annotations

### 3. Testing and Coverage (test)
- Runs unit tests on multiple Python versions (3.10, 3.11, 3.12)
- Generates code coverage reports
- Uploads coverage reports to Codecov

### 4. Build Distribution Package (build)
- Builds Python package
- Stores build artifacts as GitHub Actions artifacts

### 5. Publish to PyPI (publish) - Disabled by default
- Automatically publishes to PyPI when a new tag is created
- Requires setting up the `PYPI_API_TOKEN` secret

## How to Configure

### Codecov Integration
1. Register on [Codecov](https://codecov.io/) and connect your GitHub repository
2. No additional configuration needed, the workflow will automatically upload coverage reports

### PyPI Publishing Configuration
To enable automatic publishing to PyPI:

1. Uncomment the `publish` job in `python-ci.yml`
2. Create a secret named `PYPI_API_TOKEN` in your GitHub repository settings
   - Go to repository -> Settings -> Secrets -> New repository secret
   - Get an API token from PyPI and add it as the value

## Manual Triggering

You can manually trigger the workflow in the Actions tab of your GitHub repository. 