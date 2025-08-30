#!/usr/bin/env python3
"""MCP Factory Simplified Audit Tool

Streamlined audit system with reduced complexity and improved maintainability
"""

import argparse
import contextlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Add current directory to path and import local module
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Local import - placed after path setup
from dependency_checker import DependencyChecker  # type: ignore[import-untyped]


class AuditRunner:
    """Simplified audit runner with unified configuration"""

    def __init__(self, config_path: str, project_root: str, output_dir: str | None = None):
        """Initialize audit runner

        Args:
            config_path: Path to audit configuration file
            project_root: Project root directory
            output_dir: Optional output directory override
        """
        self.project_root = Path(project_root).resolve()
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.start_time = datetime.now()

        # Setup output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_root / self.config["reporting"]["output_dir"]

        self.output_dir.mkdir(exist_ok=True)

        # Initialize dependency checker
        self.dep_checker = DependencyChecker(str(self.project_root))

        # Results storage
        self.results = {
            "metadata": {
                "start_time": self.start_time.isoformat(),
                "config_file": str(self.config_path),
                "project_root": str(self.project_root),
                "output_dir": str(self.output_dir),
            },
            "phases": {},
        }

    def _load_config(self) -> dict[str, Any]:
        """Load and validate audit configuration"""
        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Validate required sections
            required_sections = ["metadata", "standards", "modules", "tools", "scoring"]
            for section in required_sections:
                if section not in config:
                    raise ValueError(f"Missing required section: {section}")

            return config

        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            sys.exit(1)

    def _run_command(self, cmd: list[str], timeout: int = 60) -> dict[str, Any]:
        """Generic command runner to eliminate code duplication"""
        try:
            result = subprocess.run(
                cmd, check=False, cwd=self.project_root, capture_output=True, text=True, timeout=timeout
            )
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "cmd": " ".join(cmd)}
        except Exception as e:
            return {"error": str(e), "cmd": " ".join(cmd)}

    def run_audit(self, mode: str = "full") -> dict[str, Any]:
        """Run audit based on specified mode

        Args:
            mode: Audit mode - 'full', 'quick', or 'static'
        """
        print(f"🚀 Starting {mode} audit...")
        print(f"📁 Project: {self.project_root}")
        print(f"⚙️  Config: {self.config_path}")
        print(f"📊 Output: {self.output_dir}")
        print("-" * 60)

        # Phase 1: Environment check
        self._run_phase("environment", self._check_environment)

        # Phase 2: Static analysis
        self._run_phase("static_analysis", self._run_static_analysis)

        # Phase 3: Testing (skip in static mode)
        if mode != "static":
            timeout = 60 if mode == "quick" else 300
            self._run_phase("testing", lambda: self._run_testing(timeout))

        # Phase 4: Generate reports
        self._run_phase("reporting", self._generate_reports)

        # Calculate final score
        self._calculate_score()

        duration = datetime.now() - self.start_time
        print(f"\n✅ Audit completed in {duration}")
        print(f"📄 Reports available at: {self.output_dir}")

        return self.results

    def _run_phase(self, phase_name: str, phase_func):
        """Execute a single audit phase"""
        print(f"\n🔄 [{phase_name.title()}] Starting...")
        phase_start = time.time()

        try:
            result = phase_func()
            duration = time.time() - phase_start

            self.results["phases"][phase_name] = {"status": "success", "duration": f"{duration:.2f}s", "result": result}

            print(f"✅ [{phase_name.title()}] Completed ({duration:.2f}s)")

        except Exception as e:
            duration = time.time() - phase_start

            self.results["phases"][phase_name] = {"status": "failed", "duration": f"{duration:.2f}s", "error": str(e)}

            print(f"❌ [{phase_name.title()}] Failed: {e}")

    def _check_environment(self) -> dict[str, Any]:
        """Check environment and dependencies"""
        env_results = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "project_structure": self._analyze_project_structure(),
            "dependencies": self.dep_checker.check_all_dependencies(),
        }

        # Print dependency report
        self.dep_checker.print_dependency_report(env_results["dependencies"])

        return env_results

    def _analyze_project_structure(self) -> dict[str, Any]:
        """Analyze project structure based on configuration"""
        structure = {}

        for module_name, module_config in self.config["modules"].items():
            module_info = {
                "priority": module_config["priority"],
                "description": module_config["description"],
                "weight": module_config["weight"],
                "files": [],
            }

            for path_pattern in module_config["paths"]:
                path = self.project_root / path_pattern

                if path.is_file():
                    module_info["files"].append(
                        {
                            "path": str(path.relative_to(self.project_root)),
                            "size": path.stat().st_size,
                            "type": "file",
                            "exists": True,
                        }
                    )
                elif path.is_dir():
                    # Count Python files in directory
                    py_files = list(path.rglob("*.py"))
                    module_info["files"].append(
                        {
                            "path": str(path.relative_to(self.project_root)),
                            "type": "directory",
                            "py_files": len(py_files),
                            "exists": True,
                        }
                    )
                else:
                    module_info["files"].append({"path": path_pattern, "exists": False})

            structure[module_name] = module_info

        return structure

    def _run_static_analysis(self) -> dict[str, Any]:
        """Run static analysis tools"""
        analysis_results = {}
        tools_config = self.config["tools"]["static_analysis"]

        # Run Ruff
        if tools_config.get("ruff", {}).get("enabled", False):
            analysis_results["ruff"] = self._run_ruff()

        # Run MyPy
        if tools_config.get("mypy", {}).get("enabled", False):
            analysis_results["mypy"] = self._run_mypy()

        # Run Bandit
        if tools_config.get("bandit", {}).get("enabled", False):
            analysis_results["bandit"] = self._run_bandit()

        return analysis_results

    def _run_ruff(self) -> dict[str, Any]:
        """Run Ruff linting and formatting check"""
        # Check linting
        lint_result = self._run_command(["ruff", "check", "mcp_factory/", "--output-format=json"])
        if "error" in lint_result:
            return lint_result

        # Check formatting
        format_result = self._run_command(["ruff", "format", "--check", "mcp_factory/"])
        if "error" in format_result:
            return format_result

        # Parse issues
        issues = []
        if lint_result["stdout"]:
            with contextlib.suppress(json.JSONDecodeError):
                issues = json.loads(lint_result["stdout"])

        return {
            "issues_count": len(issues),
            "issues": issues[:10],  # Limit to first 10 issues
            "format_ok": format_result["success"],
            "lint_returncode": lint_result["returncode"],
            "format_returncode": format_result["returncode"],
        }

    def _run_mypy(self) -> dict[str, Any]:
        """Run MyPy type checking"""
        result = self._run_command(["mypy", "mcp_factory/", "--show-error-codes", "--no-error-summary"], timeout=120)
        if "error" in result:
            return result

        # Parse output for error and warning counts
        output_lines = result["stdout"].split("\n") if result["stdout"] else []
        errors = [line for line in output_lines if ": error:" in line]
        warnings = [line for line in output_lines if ": warning:" in line]

        return {
            "returncode": result["returncode"],
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors[:5],  # Limit to first 5 errors
            "warnings": warnings[:5],
        }

    def _run_bandit(self) -> dict[str, Any]:
        """Run Bandit security analysis"""
        bandit_args = self.config["tools"]["static_analysis"]["bandit"]["args"]
        result = self._run_command(["bandit", *bandit_args])
        if "error" in result:
            return result

        if result["stdout"]:
            try:
                bandit_data = json.loads(result["stdout"])
                issues = bandit_data.get("results", [])

                return {
                    "total_issues": len(issues),
                    "high_severity": len([i for i in issues if i.get("issue_severity") == "HIGH"]),
                    "medium_severity": len([i for i in issues if i.get("issue_severity") == "MEDIUM"]),
                    "low_severity": len([i for i in issues if i.get("issue_severity") == "LOW"]),
                    "returncode": result["returncode"],
                }
            except json.JSONDecodeError:
                pass

        return {
            "returncode": result["returncode"],
            "total_issues": 0,
            "output": result["stdout"][:200] if result["stdout"] else "",
        }

    def _run_testing(self, timeout: int = 300) -> dict[str, Any]:
        """Run testing with coverage"""
        testing_config = self.config["tools"]["testing"]

        if not testing_config.get("pytest", {}).get("enabled", False):
            return {"skipped": True, "reason": "Testing disabled in configuration"}

        # Run pytest with coverage
        cmd = ["python", "-m", "pytest", "tests/", "--cov=mcp_factory", "--cov-report=json", "--cov-report=html", "-v"]

        result = self._run_command(cmd, timeout=timeout)
        if "error" in result:
            return result

        # Parse coverage data
        coverage_file = self.project_root / "coverage.json"
        coverage_data = {}

        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
            except Exception:
                pass

        return {
            "returncode": result["returncode"],
            "coverage_percent": coverage_data.get("totals", {}).get("percent_covered", 0),
            "tests_passed": "failed" not in result["stdout"].lower(),
            "coverage_data": coverage_data.get("totals", {}),
            "output_summary": result["stdout"].split("\n")[-10:] if result["stdout"] else [],
        }

    def _calculate_score(self):
        """Calculate overall audit score"""
        weights = self.config["scoring"]["weights"]
        thresholds = self.config["scoring"]["thresholds"]

        scores = {}

        # Calculate component scores
        if (
            "static_analysis" in self.results["phases"]
            and self.results["phases"]["static_analysis"]["status"] == "success"
        ):
            static_result = self.results["phases"]["static_analysis"]["result"]

            # Functionality score (based on Ruff issues)
            ruff_issues = static_result.get("ruff", {}).get("issues_count", 0)
            scores["functionality"] = max(0, 100 - ruff_issues * 3)

            # Reliability score (based on MyPy errors)
            mypy_errors = static_result.get("mypy", {}).get("error_count", 0)
            scores["reliability"] = max(0, 100 - mypy_errors * 5)

            # Security score (based on Bandit issues)
            bandit_high = static_result.get("bandit", {}).get("high_severity", 0)
            bandit_total = static_result.get("bandit", {}).get("total_issues", 0)
            scores["security"] = max(0, 100 - bandit_high * 20 - bandit_total * 2)

        # Testing score
        if "testing" in self.results["phases"] and self.results["phases"]["testing"]["status"] == "success":
            test_result = self.results["phases"]["testing"]["result"]
            if not test_result.get("error") and not test_result.get("skipped"):
                coverage = test_result.get("coverage_percent", 0)
                tests_passed = test_result.get("tests_passed", False)
                scores["maintainability"] = coverage if tests_passed else coverage * 0.5

        # Performance score (basic implementation)
        scores["performance"] = 85  # Default score

        # Calculate weighted total
        total_score = 0
        total_weight = 0

        for component, score in scores.items():
            if component in weights:
                weight = float(weights[component].rstrip("%")) / 100
                total_score += score * weight
                total_weight += weight

        final_score = total_score / total_weight if total_weight > 0 else 0

        # Determine grade
        grade = "F"
        if final_score >= thresholds["excellent"]:
            grade = "A"
        elif final_score >= thresholds["good"]:
            grade = "B"
        elif final_score >= thresholds["pass"]:
            grade = "C"
        else:
            grade = "F"

        self.results["score"] = {
            "components": scores,
            "total": round(final_score, 1),
            "grade": grade,
            "passed": final_score >= thresholds["pass"],
        }

    def _generate_reports(self) -> dict[str, Any]:
        """Generate audit reports"""
        reports_generated = []

        # Generate JSON report
        json_file = self.output_dir / "audit_results.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        reports_generated.append(str(json_file))

        # Generate Markdown report
        if "markdown" in self.config["reporting"]["formats"]:
            md_file = self.output_dir / "audit_summary.md"
            with open(md_file, "w", encoding="utf-8") as f:
                f.write(self._generate_markdown_report())
            reports_generated.append(str(md_file))

        return {"reports": reports_generated}

    def _generate_markdown_report(self) -> str:
        """Generate Markdown audit report"""
        config_meta = self.config["metadata"]

        report = f"""# MCP Factory Audit Report

## Overview
- **Project**: {config_meta["project_name"]} v{config_meta["version"]}
- **Audit Time**: {self.start_time.strftime("%Y-%m-%d %H:%M:%S")}
- **Configuration**: {config_meta["description"]}

## Results Summary
"""

        # Overall score
        if "score" in self.results:
            score_info = self.results["score"]
            status_emoji = "✅" if score_info["passed"] else "❌"

            report += f"""
### Overall Score: {score_info["total"]}/100 (Grade {score_info["grade"]}) {status_emoji}

**Component Scores:**
"""
            for component, score in score_info["components"].items():
                report += f"- {component.title()}: {score:.1f}/100\n"

        # Phase results
        report += "\n## Execution Phases\n\n"
        for phase_name, phase_result in self.results["phases"].items():
            status_emoji = "✅" if phase_result["status"] == "success" else "❌"
            report += (
                f"- {status_emoji} **{phase_name.title()}**: {phase_result['status']} ({phase_result['duration']})\n"
            )

        # Static analysis details
        if (
            "static_analysis" in self.results["phases"]
            and self.results["phases"]["static_analysis"]["status"] == "success"
        ):
            static_result = self.results["phases"]["static_analysis"]["result"]
            report += "\n## Static Analysis Details\n\n"

            if "ruff" in static_result:
                ruff = static_result["ruff"]
                report += "**Ruff (Code Quality)**\n"
                report += f"- Issues: {ruff.get('issues_count', 'N/A')}\n"
                report += f"- Format OK: {'✅' if ruff.get('format_ok') else '❌'}\n\n"

            if "mypy" in static_result:
                mypy = static_result["mypy"]
                report += "**MyPy (Type Checking)**\n"
                report += f"- Errors: {mypy.get('error_count', 'N/A')}\n"
                report += f"- Warnings: {mypy.get('warning_count', 'N/A')}\n\n"

            if "bandit" in static_result:
                bandit = static_result["bandit"]
                report += "**Bandit (Security)**\n"
                report += f"- Total Issues: {bandit.get('total_issues', 'N/A')}\n"
                report += f"- High Severity: {bandit.get('high_severity', 'N/A')}\n\n"

        # Testing details
        if "testing" in self.results["phases"] and self.results["phases"]["testing"]["status"] == "success":
            test_result = self.results["phases"]["testing"]["result"]
            report += "## Testing Results\n\n"

            if not test_result.get("error") and not test_result.get("skipped"):
                report += f"- Coverage: {test_result.get('coverage_percent', 'N/A')}%\n"
                report += f"- Tests Passed: {'✅' if test_result.get('tests_passed') else '❌'}\n"
            else:
                report += f"- Status: {test_result.get('error', 'Skipped')}\n"

        report += f"\n---\n*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

        return report


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="MCP Factory Simplified Audit Tool")
    parser.add_argument("--config", default="scripts/audit_config.yaml", help="Audit configuration file")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--output", help="Output directory (overrides config)")
    parser.add_argument("--mode", choices=["full", "quick", "static"], default="full", help="Audit mode")

    args = parser.parse_args()

    # Validate config file
    if not Path(args.config).exists():
        print(f"❌ Configuration file not found: {args.config}")
        sys.exit(1)

    # Run audit
    auditor = AuditRunner(args.config, args.project_root, args.output)
    results = auditor.run_audit(args.mode)

    # Exit with appropriate code
    if "score" in results:
        sys.exit(0 if results["score"]["passed"] else 1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
