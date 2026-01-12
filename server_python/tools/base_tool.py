"""
Base tool class for the tool system.
All tools should inherit from BaseTool.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar
import asyncio
import time
import logging
from dataclasses import dataclass, field

from .tool_schemas import (
    ToolSchema,
    ToolMetadata,
    ToolResult,
    ToolParameter,
    ToolCategory,
    ParameterType,
)

logger = logging.getLogger(__name__)

# Re-export for convenience
__all__ = [
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolCategory",
    "ParameterType",
    "tool",
]

T = TypeVar("T", bound="BaseTool")


class ToolValidationError(Exception):
    """Raised when tool parameter validation fails."""
    pass


class ToolExecutionError(Exception):
    """Raised when tool execution fails."""
    pass


class BaseTool(ABC):
    """
    Base class for all tools.

    Tools are the fundamental building blocks for agent capabilities.
    Each tool should:
    - Define its schema (parameters, returns)
    - Define its metadata (category, permissions)
    - Implement the execute method

    Example:
        class ReadFileTool(BaseTool):
            name = "read_file"
            description = "Read the contents of a file"
            category = ToolCategory.FILE

            parameters = [
                ToolParameter(
                    name="file_path",
                    type=ParameterType.STRING,
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="limit",
                    type=ParameterType.INTEGER,
                    description="Maximum lines to read",
                    required=False,
                    default=1000
                )
            ]

            async def execute(self, file_path: str, limit: int = 1000) -> ToolResult:
                content = await self.read_file(file_path, limit)
                return ToolResult.success_result(content)
    """

    # Class-level attributes to be overridden
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.CUSTOM
    version: str = "1.0.0"

    # Tool parameters
    parameters: List[ToolParameter] = []

    # Permissions and limits
    requires_approval: bool = False
    is_dangerous: bool = False
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit: Optional[int] = None

    def __init__(self):
        """Initialize the tool."""
        if not self.name:
            raise ValueError(f"Tool {self.__class__.__name__} must define a 'name'")
        if not self.description:
            raise ValueError(f"Tool {self.__class__.__name__} must define a 'description'")

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with the given arguments.

        This method must be implemented by all tools.

        Args:
            **kwargs: Tool-specific arguments as defined in parameters

        Returns:
            ToolResult: The result of the tool execution
        """
        pass

    async def validate_and_execute(self, **kwargs) -> ToolResult:
        """
        Validate parameters and execute the tool.

        This is the main entry point for tool execution.
        It handles validation, timeout, retries, and error handling.
        """
        start_time = time.time()

        try:
            # Validate parameters
            validated_args = self.validate_parameters(**kwargs)

            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(**validated_args),
                timeout=self.timeout_seconds
            )

            # Add execution time
            result.execution_time_ms = (time.time() - start_time) * 1000

            return result

        except asyncio.TimeoutError:
            return ToolResult.error_result(
                f"Tool execution timed out after {self.timeout_seconds} seconds",
                "TimeoutError"
            )
        except ToolValidationError as e:
            return ToolResult.error_result(str(e), "ValidationError")
        except ToolExecutionError as e:
            return ToolResult.error_result(str(e), "ExecutionError")
        except Exception as e:
            logger.exception(f"Unexpected error in tool {self.name}")
            return ToolResult.error_result(str(e), type(e).__name__)

    def validate_parameters(self, **kwargs) -> Dict[str, Any]:
        """
        Validate and normalize input parameters.

        Args:
            **kwargs: Input parameters

        Returns:
            Dict with validated and normalized parameters

        Raises:
            ToolValidationError: If validation fails
        """
        validated = {}

        for param in self.parameters:
            value = kwargs.get(param.name)

            # Check required
            if param.required and value is None:
                raise ToolValidationError(
                    f"Required parameter '{param.name}' is missing"
                )

            # Use default if not provided
            if value is None:
                value = param.default

            if value is not None:
                # Type validation
                value = self._validate_type(param, value)

                # Enum validation
                if param.enum and value not in param.enum:
                    raise ToolValidationError(
                        f"Parameter '{param.name}' must be one of {param.enum}"
                    )

                # Range validation for numbers
                if param.type in (ParameterType.INTEGER, ParameterType.NUMBER):
                    if param.min_value is not None and value < param.min_value:
                        raise ToolValidationError(
                            f"Parameter '{param.name}' must be >= {param.min_value}"
                        )
                    if param.max_value is not None and value > param.max_value:
                        raise ToolValidationError(
                            f"Parameter '{param.name}' must be <= {param.max_value}"
                        )

                # Length validation for strings
                if param.type == ParameterType.STRING:
                    if param.min_length is not None and len(value) < param.min_length:
                        raise ToolValidationError(
                            f"Parameter '{param.name}' must have length >= {param.min_length}"
                        )
                    if param.max_length is not None and len(value) > param.max_length:
                        raise ToolValidationError(
                            f"Parameter '{param.name}' must have length <= {param.max_length}"
                        )

            validated[param.name] = value

        return validated

    def _validate_type(self, param: ToolParameter, value: Any) -> Any:
        """Validate and convert parameter type."""
        try:
            if param.type == ParameterType.STRING:
                return str(value)
            elif param.type == ParameterType.INTEGER:
                return int(value)
            elif param.type == ParameterType.NUMBER:
                return float(value)
            elif param.type == ParameterType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes")
                return bool(value)
            elif param.type == ParameterType.ARRAY:
                if not isinstance(value, list):
                    raise ToolValidationError(
                        f"Parameter '{param.name}' must be an array"
                    )
                return value
            elif param.type == ParameterType.OBJECT:
                if not isinstance(value, dict):
                    raise ToolValidationError(
                        f"Parameter '{param.name}' must be an object"
                    )
                return value
            else:
                return value
        except (ValueError, TypeError) as e:
            raise ToolValidationError(
                f"Parameter '{param.name}' has invalid type: expected {param.type.value}"
            )

    def get_schema(self) -> ToolSchema:
        """Get the tool schema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def get_metadata(self) -> ToolMetadata:
        """Get the tool metadata."""
        return ToolMetadata(
            name=self.name,
            description=self.description,
            category=self.category,
            version=self.version,
            requires_approval=self.requires_approval,
            is_dangerous=self.is_dangerous,
            timeout_seconds=self.timeout_seconds,
            max_retries=self.max_retries,
            rate_limit=self.rate_limit,
        )

    def to_llm_format(self, format: str = "anthropic") -> Dict[str, Any]:
        """
        Convert tool to LLM-compatible format.

        Args:
            format: "anthropic" or "openai"

        Returns:
            Tool definition in the specified format
        """
        schema = self.get_schema()
        if format == "openai":
            return schema.to_openai_format()
        return schema.to_anthropic_format()

    def __repr__(self) -> str:
        return f"<Tool: {self.name} ({self.category.value})>"


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.CUSTOM,
    requires_approval: bool = False,
    is_dangerous: bool = False,
    timeout_seconds: int = 30,
):
    """
    Decorator to create a tool from a function.

    Example:
        @tool(name="read_file", description="Read file contents")
        async def read_file(file_path: str, limit: int = 1000) -> ToolResult:
            content = open(file_path).read()
            return ToolResult.success_result(content)
    """
    def decorator(func):
        # Create a dynamic tool class
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Execute {func.__name__}"

        class DynamicTool(BaseTool):
            pass

        DynamicTool.name = tool_name
        DynamicTool.description = tool_description
        DynamicTool.category = category
        DynamicTool.requires_approval = requires_approval
        DynamicTool.is_dangerous = is_dangerous
        DynamicTool.timeout_seconds = timeout_seconds

        async def execute(self, **kwargs):
            return await func(**kwargs)

        DynamicTool.execute = execute

        return DynamicTool

    return decorator
