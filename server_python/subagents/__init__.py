"""
Sub-agent management system.
Allows agents to spawn and manage child agents for specialized tasks.
"""

from .subagent_manager import SubagentManager, SubagentSpec, SubagentStatus
from .mcp_discovery import MCPToolDiscovery, MCPServerInfo

__all__ = [
    "SubagentManager",
    "SubagentSpec",
    "SubagentStatus",
    "MCPToolDiscovery",
    "MCPServerInfo",
]
