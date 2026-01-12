"""
Think tool for reasoning and reflection.
Allows agents to externalize their thinking process.
"""

from datetime import datetime
from typing import Optional

from ..base_tool import BaseTool
from ..tool_schemas import (
    ToolResult,
    ToolParameter,
    ParameterType,
    ToolCategory,
)


class ThinkTool(BaseTool):
    """Record thinking and reasoning process."""

    name = "think"
    description = """Allows the agent to externalize its thinking process.
    Use this to record reasoning steps, analyze problems, or reflect on results.
    This helps with Chain-of-Thought and self-critique workflows."""
    category = ToolCategory.CUSTOM
    version = "1.0.0"
    timeout_seconds = 5

    parameters = [
        ToolParameter(
            name="thought",
            type=ParameterType.STRING,
            description="The thought or reasoning to record",
            required=True,
        ),
        ToolParameter(
            name="thought_type",
            type=ParameterType.STRING,
            description="Type of thought: 'observation', 'analysis', 'plan', 'reflection', 'critique'",
            required=False,
            default="observation",
            enum=["observation", "analysis", "plan", "reflection", "critique"],
        ),
        ToolParameter(
            name="context",
            type=ParameterType.STRING,
            description="Additional context about what triggered this thought",
            required=False,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._thoughts = []

    async def execute(
        self,
        thought: str,
        thought_type: str = "observation",
        context: Optional[str] = None,
    ) -> ToolResult:
        """Execute the think operation."""
        # Record the thought
        thought_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": thought_type,
            "thought": thought,
            "context": context,
        }

        self._thoughts.append(thought_record)

        # Format output
        output_lines = [
            f"[{thought_type.upper()}]",
            thought,
        ]

        if context:
            output_lines.append(f"\nContext: {context}")

        return ToolResult.success_result(
            "\n".join(output_lines),
            thought_type=thought_type,
            recorded_at=thought_record["timestamp"],
        )

    def get_thought_history(self) -> list:
        """Get all recorded thoughts."""
        return self._thoughts.copy()

    def clear_thoughts(self) -> None:
        """Clear thought history."""
        self._thoughts.clear()
