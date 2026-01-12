"""
Bash command execution tool.
Provides safe shell command execution with timeout and output limits.
"""

import asyncio
import os
import shlex
from typing import Optional

from ..base_tool import BaseTool
from ..tool_schemas import (
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolCategory,
)


# Commands that are blocked for safety
BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    ":(){ :|:& };:",  # Fork bomb
    "> /dev/sda",
    "chmod -R 777 /",
}

# Dangerous patterns that require extra caution
DANGEROUS_PATTERNS = [
    "rm -rf",
    "sudo rm",
    "chmod 777",
    "> /dev/",
    "mkfs.",
    "fdisk",
    "parted",
    "dd if=",
]


class BashTool(BaseTool):
    """Execute bash commands."""

    name = "bash"
    description = """Executes bash commands in a shell.
    Use for terminal operations like git, npm, docker, etc.
    Has timeout and output limits for safety."""
    category = ToolCategory.SYSTEM
    version = "1.0.0"
    is_dangerous = True
    timeout_seconds = 120  # 2 minutes default

    parameters = [
        ToolParameter(
            name="command",
            type=ParameterType.STRING,
            description="The bash command to execute",
            required=True,
        ),
        ToolParameter(
            name="timeout",
            type=ParameterType.INTEGER,
            description="Timeout in seconds (max 600)",
            required=False,
            default=120,
            min_value=1,
            max_value=600,
        ),
        ToolParameter(
            name="cwd",
            type=ParameterType.STRING,
            description="Working directory for the command",
            required=False,
        ),
        ToolParameter(
            name="env",
            type=ParameterType.OBJECT,
            description="Additional environment variables",
            required=False,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._output_limit = 30000  # Characters

    async def execute(
        self,
        command: str,
        timeout: int = 120,
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> ToolResult:
        """Execute the bash command."""
        # Safety checks
        safety_result = self._check_safety(command)
        if safety_result:
            return safety_result

        try:
            # Prepare environment
            process_env = os.environ.copy()
            if env:
                process_env.update(env)

            # Validate working directory
            if cwd and not os.path.isdir(cwd):
                return ToolResult.error_result(
                    f"Working directory not found: {cwd}",
                    "DirectoryNotFoundError"
                )

            # Create the process
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=process_env,
            )

            try:
                # Wait for completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult.error_result(
                    f"Command timed out after {timeout} seconds",
                    "TimeoutError"
                )

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            # Truncate if too long
            if len(stdout_str) > self._output_limit:
                stdout_str = stdout_str[:self._output_limit] + "\n... (output truncated)"

            if len(stderr_str) > self._output_limit:
                stderr_str = stderr_str[:self._output_limit] + "\n... (output truncated)"

            # Combine output
            output_parts = []
            if stdout_str.strip():
                output_parts.append(stdout_str.strip())
            if stderr_str.strip():
                output_parts.append(f"STDERR:\n{stderr_str.strip()}")

            output = "\n\n".join(output_parts) if output_parts else "(no output)"

            # Check return code
            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    output=output,
                    error=f"Command exited with code {process.returncode}",
                    error_type="NonZeroExitCode",
                    metadata={
                        "exit_code": process.returncode,
                        "command": command,
                    }
                )

            return ToolResult.success_result(
                output,
                exit_code=process.returncode,
                command=command,
            )

        except Exception as e:
            return ToolResult.error_result(str(e), type(e).__name__)

    def _check_safety(self, command: str) -> Optional[ToolResult]:
        """Check if command is safe to execute."""
        # Check blocked commands
        normalized = command.strip().lower()

        for blocked in BLOCKED_COMMANDS:
            if blocked.lower() in normalized:
                return ToolResult.error_result(
                    f"Command blocked for safety: {blocked}",
                    "BlockedCommandError"
                )

        # Check dangerous patterns (warning, not blocking)
        for pattern in DANGEROUS_PATTERNS:
            if pattern.lower() in normalized:
                # Log warning but don't block (requires_approval will handle)
                import logging
                logging.getLogger(__name__).warning(
                    f"Potentially dangerous command: {command}"
                )
                break

        return None
