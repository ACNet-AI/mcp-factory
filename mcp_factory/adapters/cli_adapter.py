"""CLI Command Adapter - Convert CLI commands to MCP tools.

This adapter wraps command-line tools and utilities as MCP tools,
supporting parameter mapping and output parsing.
"""

import shlex
import subprocess
from typing import Any

from .base import (
    BaseAdapter,
    CapabilityInfo,
    ConnectivityResult,
    DiscoveryError,
    GenerationError,
    SourceInfo,
    generate_tool_template,
)
from .cache import cached_method


class CliAdapter(BaseAdapter):
    """Adapter for CLI commands"""

    def __init__(self, source_info: SourceInfo):
        super().__init__(source_info)

        self.command = source_info.source_path
        self.shell = self.config.get("shell", False)
        self.timeout = self.config.get("timeout", 30)
        self.working_dir = self.config.get("working_dir")
        self.env_vars = self.config.get("env_vars", {})

        # Command variants and parameters
        self.variants = self.config.get("variants", [])
        self.global_params = self.config.get("parameters", [])

    @cached_method("cli_discover", ttl=3600)  # Cache for 1 hour
    def discover_capabilities(self) -> list[CapabilityInfo]:
        """Discover CLI command capabilities"""
        try:
            capabilities = []

            # If variants are defined, create capabilities for each variant
            if self.variants:
                for variant in self.variants:
                    capability = self._create_variant_capability(variant)
                    capabilities.append(capability)
            else:
                # Create a single capability for the base command
                capability = self._create_base_capability()
                capabilities.append(capability)

            return capabilities

        except Exception as e:
            raise DiscoveryError(f"Failed to discover CLI capabilities: {e}") from e

    def _create_variant_capability(self, variant: dict[str, Any]) -> CapabilityInfo:
        """Create capability for a command variant"""
        name = variant.get("name", self.command.replace(" ", "_"))
        description = variant.get("description", f"CLI command: {self.command} {variant.get('args', '')}")

        # Combine global parameters with variant-specific parameters
        parameters = self.global_params.copy()
        parameters.extend(variant.get("parameters", []))

        return CapabilityInfo(
            name=name,
            description=description,
            parameters=parameters,
            capability_type="cli_command",
            metadata={
                "command": self.command,
                "args": variant.get("args", ""),
                "shell": self.shell,
                "timeout": self.timeout,
                "working_dir": self.working_dir,
                "env_vars": self.env_vars,
                "output_format": variant.get("output_format", "text"),
            },
        )

    def _create_base_capability(self) -> CapabilityInfo:
        """Create capability for the base command"""
        name = self.command.replace(" ", "_").replace("-", "_")
        description = f"CLI command: {self.command}"

        return CapabilityInfo(
            name=name,
            description=description,
            parameters=self.global_params,
            capability_type="cli_command",
            metadata={
                "command": self.command,
                "args": "",
                "shell": self.shell,
                "timeout": self.timeout,
                "working_dir": self.working_dir,
                "env_vars": self.env_vars,
                "output_format": "text",
            },
        )

    @cached_method("cli_generate", ttl=7200)  # Cache for 2 hours
    def generate_tool_code(self, capability: CapabilityInfo) -> str:
        """Generate MCP tool code for CLI command"""
        try:
            command = capability.metadata["command"]
            args = capability.metadata.get("args", "")
            shell = capability.metadata.get("shell", False)
            timeout = capability.metadata.get("timeout", 30)
            working_dir = capability.metadata.get("working_dir")
            env_vars = capability.metadata.get("env_vars", {})
            output_format = capability.metadata.get("output_format", "text")

            # Generate parameter handling code
            param_handling = self._generate_parameter_handling(capability.parameters)

            # Generate command execution code
            exec_code = self._generate_execution_code(
                command, args, shell, timeout, working_dir, env_vars, output_format
            )

            impl_code = f"""
        # CLI command implementation
        import subprocess
        import shlex
        import json
        import os
        from pathlib import Path

        {param_handling}

        {exec_code}"""

            return generate_tool_template(
                tool_name=capability.name,
                parameters=capability.parameters,
                description=capability.description,
                implementation_code=impl_code,
            )

        except Exception as e:
            raise GenerationError(f"Failed to generate tool code for {capability.name}: {e}") from e

    def _generate_parameter_handling(self, parameters: list[dict[str, Any]]) -> str:
        """Generate parameter handling code"""
        if not parameters:
            return "# No parameters to handle\ncommand_args = []"

        code_lines = ["# Handle command parameters", "command_args = []", ""]

        for param in parameters:
            param_name = param["name"]
            param_type = param.get("type", "string")
            required = param.get("required", True)
            flag = param.get("flag", f"--{param_name}")

            if required:
                if param_type == "boolean":
                    code_lines.append(f"if {param_name}:")
                    code_lines.append(f'    command_args.append("{flag}")')
                else:
                    code_lines.append(f'command_args.extend(["{flag}", str({param_name})])')
            else:
                code_lines.append(f"if {param_name} is not None:")
                if param_type == "boolean":
                    code_lines.append(f"    if {param_name}:")
                    code_lines.append(f'        command_args.append("{flag}")')
                else:
                    code_lines.append(f'    command_args.extend(["{flag}", str({param_name})])')

        return "\n        ".join(code_lines)

    def _generate_execution_code(
        self,
        command: str,
        args: str,
        shell: bool,
        timeout: int,
        working_dir: str | None,
        env_vars: dict[str, str],
        output_format: str,
    ) -> str:
        """Generate command execution code"""

        # Prepare command
        if shell:
            cmd_prep = f'''
        # Prepare shell command
        full_command = "{command} {args}" + " " + " ".join(command_args)
        cmd = full_command'''
        else:
            cmd_prep = f'''
        # Prepare command list
        cmd = ["{command}"]
        if "{args}".strip():
            cmd.extend(shlex.split("{args}"))
        cmd.extend(command_args)'''

        # Prepare environment
        env_prep = ""
        if env_vars:
            env_prep = f"""
        # Prepare environment
        env = os.environ.copy()
        env.update({env_vars})"""
        else:
            env_prep = """
        # Use current environment
        env = None"""

        # Prepare working directory
        cwd_prep = ""
        if working_dir:
            cwd_prep = f'''
        # Set working directory
        cwd = Path("{working_dir}")'''
        else:
            cwd_prep = """
        # Use current directory
        cwd = None"""

        # Generate execution code
        exec_code = f'''
        {cmd_prep}
        {env_prep}
        {cwd_prep}

        # Execute command
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout={timeout},
                shell={shell},
                env=env,
                cwd=cwd
            )

            # Parse output based on format
            output = result.stdout
            if "{output_format}" == "json" and output.strip():
                try:
                    parsed_output = json.loads(output)
                except json.JSONDecodeError:
                    parsed_output = output
            else:
                parsed_output = output

            return {{
                "success": result.returncode == 0,
                "result": parsed_output,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode,
                "command": str(cmd) if not {shell} else cmd
            }}

        except subprocess.TimeoutExpired:
            return {{
                "success": False,
                "error": f"Command timed out after {timeout} seconds",
                "command": str(cmd) if not {shell} else cmd
            }}
        except FileNotFoundError:
            return {{
                "success": False,
                "error": f"Command not found: {command}",
                "command": str(cmd) if not {shell} else cmd
            }}'''

        return exec_code

    def test_connectivity(self) -> ConnectivityResult:
        """Test connectivity to CLI command"""
        try:
            # Try to run the command with --help or --version
            test_commands = [
                f"{self.command} --help",
                f"{self.command} --version",
                f"{self.command} -h",
                f"{self.command} -v",
            ]

            for test_cmd in test_commands:
                try:
                    if self.shell:
                        cmd: str | list[str] = test_cmd
                    else:
                        cmd = shlex.split(test_cmd)

                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=10, shell=self.shell, cwd=self.working_dir
                    )

                    # Many commands return 1 for --help, so we check if we got output
                    if result.stdout or result.stderr:
                        return ConnectivityResult(
                            success=True,
                            message=f"Successfully connected to command: {self.command}",
                            details={
                                "command": self.command,
                                "test_command": test_cmd,
                                "return_code": result.returncode,
                                "has_output": bool(result.stdout or result.stderr),
                            },
                        )

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    continue

            # If all test commands failed, try just the base command
            try:
                if self.shell:
                    cmd_final: str | list[str] = self.command
                else:
                    cmd_final = shlex.split(self.command)

                result = subprocess.run(
                    cmd_final, capture_output=True, text=True, timeout=5, shell=self.shell, cwd=self.working_dir
                )

                return ConnectivityResult(
                    success=True,
                    message=f"Command exists: {self.command}",
                    details={"command": self.command, "return_code": result.returncode},
                )

            except FileNotFoundError:
                return ConnectivityResult(
                    success=False, message=f"Command not found: {self.command}", details={"command": self.command}
                )
            except subprocess.TimeoutExpired:
                return ConnectivityResult(
                    success=True,
                    message=f"Command exists but timed out: {self.command}",
                    details={"command": self.command, "note": "Command may require input"},
                )

        except Exception as e:
            return ConnectivityResult(
                success=False, message=f"Failed to test command {self.command}: {e}", details={"error": str(e)}
            )


# Convenience functions


def create_cli_adapter(
    command: str,
    shell: bool = False,
    timeout: int = 30,
    working_dir: str | None = None,
    env_vars: dict[str, str] | None = None,
    parameters: list[dict[str, Any]] | None = None,
    variants: list[dict[str, Any]] | None = None,
) -> CliAdapter:
    """Create CLI adapter with simplified configuration"""

    config: dict[str, Any] = {"shell": shell, "timeout": timeout}

    if working_dir:
        config["working_dir"] = working_dir

    if env_vars:
        config["env_vars"] = env_vars

    if parameters:
        config["parameters"] = parameters

    if variants:
        config["variants"] = variants

    from .base import AdapterType

    source_info = SourceInfo(adapter_type=AdapterType.CLI_COMMAND, source_path=command, config=config)

    return CliAdapter(source_info)
