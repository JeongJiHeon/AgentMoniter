"""
Built-in tools for the tool system.
Provides core functionality like file operations, search, bash, and web fetch.
"""

from .file_tools import (
    ReadFileTool,
    WriteFileTool,
    GlobTool,
    GrepTool,
    EditFileTool,
)
from .bash_tool import BashTool
from .web_tools import WebFetchTool, WebSearchTool
from .think_tool import ThinkTool

__all__ = [
    # File tools
    "ReadFileTool",
    "WriteFileTool",
    "GlobTool",
    "GrepTool",
    "EditFileTool",
    # Bash
    "BashTool",
    # Web tools
    "WebFetchTool",
    "WebSearchTool",
    # Reasoning
    "ThinkTool",
]


def register_all_builtin_tools(registry) -> None:
    """Register all built-in tools with the registry."""
    builtin_tools = [
        ReadFileTool,
        WriteFileTool,
        GlobTool,
        GrepTool,
        EditFileTool,
        BashTool,
        WebFetchTool,
        WebSearchTool,
        ThinkTool,
    ]

    for tool_class in builtin_tools:
        try:
            registry.register(tool_class)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to register built-in tool {tool_class.__name__}: {e}"
            )
