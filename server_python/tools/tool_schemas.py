"""
Tool schema definitions for the tool system.
Provides metadata and validation for tools.
"""

from typing import Any, Dict, List, Optional, Literal, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json


class ToolCategory(str, Enum):
    """Categories of tools."""
    FILE = "file"
    SEARCH = "search"
    WEB = "web"
    CODE = "code"
    SYSTEM = "system"
    MCP = "mcp"
    CUSTOM = "custom"


class ParameterType(str, Enum):
    """Supported parameter types."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern for strings
    items_type: Optional[ParameterType] = None  # For array types

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema: Dict[str, Any] = {
            "type": self.type.value,
            "description": self.description,
        }

        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        if self.min_value is not None:
            schema["minimum"] = self.min_value
        if self.max_value is not None:
            schema["maximum"] = self.max_value
        if self.min_length is not None:
            schema["minLength"] = self.min_length
        if self.max_length is not None:
            schema["maxLength"] = self.max_length
        if self.pattern:
            schema["pattern"] = self.pattern
        if self.items_type and self.type == ParameterType.ARRAY:
            schema["items"] = {"type": self.items_type.value}

        return schema


@dataclass
class ToolSchema:
    """Schema definition for a tool."""
    name: str
    description: str
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: Optional[Dict[str, Any]] = None
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format for LLM tool calling."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_format(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.to_json_schema(),
            }
        }

    def to_anthropic_format(self) -> Dict[str, Any]:
        """Convert to Anthropic tool use format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.to_json_schema(),
        }


@dataclass
class ToolMetadata:
    """Metadata about a tool."""
    name: str
    description: str
    category: ToolCategory
    version: str = "1.0.0"
    author: str = "system"
    requires_approval: bool = False
    is_dangerous: bool = False
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit: Optional[int] = None  # calls per minute
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "version": self.version,
            "author": self.author,
            "requires_approval": self.requires_approval,
            "is_dangerous": self.is_dangerous,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "rate_limit": self.rate_limit,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }

    def to_context_string(self) -> str:
        """Convert to string for context injection."""
        if self.success:
            if isinstance(self.output, str):
                return self.output
            return json.dumps(self.output, indent=2, ensure_ascii=False)
        else:
            return f"Error ({self.error_type}): {self.error}"

    @classmethod
    def success_result(cls, output: Any, **metadata) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, output=output, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, error_type: str = "ExecutionError") -> "ToolResult":
        """Create an error result."""
        return cls(success=False, output=None, error=error, error_type=error_type)


@dataclass
class ToolCall:
    """Represents a tool call request."""
    id: str
    tool_name: str
    arguments: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ToolCallResult:
    """Result of a tool call with full context."""
    call: ToolCall
    result: ToolResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "call": self.call.to_dict(),
            "result": self.result.to_dict(),
        }
