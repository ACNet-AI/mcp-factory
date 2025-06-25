# MCP Factory Development Scripts Collection

This directory contains simplified development and operation scripts for the MCP Factory project, focused on essential quality assurance and environment management.

## 📁 File Structure

```
scripts/
├── audit_config.yaml           # Simplified audit configuration
├── audit.py                    # Main audit execution script
├── audit.sh                    # Convenient shell wrapper
├── dependency_checker.py       # Unified dependency management
└── README.md                   # This document
```

## 🚀 Quick Start

### 🔍 Dependency Check

```bash
# Check all dependencies
python3 scripts/dependency_checker.py

# Install missing dependencies
python3 scripts/dependency_checker.py --install

# Or use shell wrapper
./scripts/audit.sh --deps-check
./scripts/audit.sh --deps-install
```

### 🔐 JWT Environment Check

```bash
# Check JWT environment variables (using main CLI)
mcp-factory auth check
# or
mcp-factory health --check-env
```

### 📊 Code Quality Audit

```bash
# Run complete audit
./scripts/audit.sh

# Run quick audit (faster, reduced timeout)
./scripts/audit.sh --quick

# Run static analysis only
./scripts/audit.sh --static

# Custom configuration
./scripts/audit.sh --config my_config.yaml

# Custom output directory
./scripts/audit.sh --output /tmp/audit_results
```

### 🐍 Direct Python Usage

```bash
# Full control with Python script
python3 scripts/audit.py \
    --mode full \
    --config scripts/audit_config.yaml \
    --project-root . \
    --output audit_results
```

## 📊 Audit Content

### 🔍 Static Analysis
- **Ruff**: Code quality and style checking
- **MyPy**: Type annotation validation  
- **Bandit**: Security vulnerability scanning

### 🧪 Testing
- **Pytest**: Complete test suite execution
- **Coverage**: Test coverage analysis (target: 95%)

### 📚 Documentation
- **README**: Documentation completeness check
- **Docstrings**: API documentation validation

## ⚙️ Configuration

### Simplified Configuration Structure

The new `audit_config.yaml` uses a streamlined structure:

```yaml
# Global quality standards
standards:
  code_quality:
    min_coverage: 95%
    max_complexity: 10
    linting_score: 8.5

# Module definitions with priorities and weights
modules:
  core:
    priority: critical
    weight: 40%
    paths: ["mcp_factory/factory.py", "mcp_factory/server.py"]
    
  config:
    priority: high
    weight: 25%
    paths: ["mcp_factory/config/"]

# Tool configuration
tools:
  static_analysis:
    ruff:
      enabled: true
    mypy:
      enabled: true
    bandit:
      enabled: true
      
  testing:
    pytest:
      enabled: true
      coverage_target: 95%
```

### Audit Modes

- **Full Mode** (`--full`): Complete audit with all checks
- **Quick Mode** (`--quick`): Reduced timeouts for faster feedback
- **Static Mode** (`--static`): Static analysis only, no testing

## 📈 Scoring System

### Component Weights
- **Functionality** (30%): Code correctness and completeness
- **Reliability** (25%): Error handling and stability
- **Security** (20%): Security vulnerabilities and protection
- **Maintainability** (15%): Code quality and test coverage
- **Performance** (10%): Execution efficiency

### Grade Thresholds
- **Grade A**: 95+ points (Excellent)
- **Grade B**: 85+ points (Good) 
- **Grade C**: 75+ points (Pass)
- **Grade F**: <75 points (Fail)

## 📄 Output Reports

After audit completion, the following reports are generated:

### 1. `audit_results.json`
- Complete audit data in JSON format
- Detailed results for each phase
- Component scores and overall grade

### 2. `audit_summary.md`
- Human-readable audit summary
- Key findings and recommendations
- Visual status indicators

### 3. `coverage.html/` (if testing enabled)
- Interactive test coverage report
- File-by-file coverage details

### 4. Quick Quality Check

For quick development checks during development:

```bash
# Use the quick audit mode for faster feedback
./scripts/audit.sh --quick
```

## 🛠️ Key Improvements

### ✅ Simplified Configuration
- **50% reduction** in configuration complexity
- Unified tool settings
- Clear module prioritization

### ✅ Eliminated Code Duplication
- Unified dependency checking in `dependency_checker.py`
- Consistent error handling across scripts
- Shared utility functions

### ✅ Removed Hard-coding
- Configuration-driven approach
- No embedded YAML generation
- Flexible parameter handling

### ✅ Better Maintainability
- Modular script design
- Clear separation of concerns
- Comprehensive error reporting

## 🔧 Development Workflow Integration

### Daily Development
```bash
# Quick check before commits
./scripts/audit.sh --quick
# Quick audit mode for faster feedback
./scripts/audit.sh --quick
```

### Pre-Release
```bash
# Complete audit before releases
./scripts/audit.sh --full
```

## 🔗 Integration with Main CLI

The scripts system integrates with the main MCP Factory CLI:

- **JWT/Auth checking**: Use `mcp-factory auth check` instead of separate JWT scripts
- **Health monitoring**: Use `mcp-factory health --check-env` for environment validation
- **Dependency management**: Scripts provide unified dependency checking that complements the main CLI

This approach reduces duplication and provides a consistent user experience across all project tools.

## 🔍 Troubleshooting

### Common Issues

#### 1. Missing Dependencies
```bash
# Check what's missing
./scripts/audit.sh --deps-check

# Install automatically
./scripts/audit.sh --deps-install
```

#### 2. Configuration Errors
```bash
# Validate configuration
python3 -c "import yaml; yaml.safe_load(open('scripts/audit_config.yaml'))"
```

#### 3. Permission Issues
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py
```

### Environment Requirements

- **Python**: 3.11 or higher
- **Tools**: ruff, mypy, bandit, pytest, pytest-cov
- **System**: Unix-like environment (Linux, macOS)

## 📞 Getting Help

For issues and support:
- Check the main project documentation
- Review configuration examples
- Run dependency checker for environment issues
- Use `--help` flag for command options

---

🚀 **Simplified, efficient, and maintainable audit system!** 