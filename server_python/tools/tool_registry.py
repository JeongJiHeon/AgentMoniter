"""
Tool Registry for the tool system.
Central registry for tool registration, discovery, and retrieval.
"""

from typing import Any, Dict, List, Optional, Type, Set
import logging
from dataclasses import dataclass, field

from .base_tool import BaseTool
from .tool_schemas import ToolCategory, ToolMetadata, ToolSchema

logger = logging.getLogger(__name__)


@dataclass
class ToolRegistration:
    """Registration record for a tool."""
    tool_class: Type[BaseTool]
    instance: Optional[BaseTool] = None
    enabled: bool = True
    tags: Set[str] = field(default_factory=set)


class ToolRegistry:
    """
    Central registry for all tools.

    Provides:
    - Tool registration and discovery
    - Category-based filtering
    - Permission checking
    - Tool instantiation and caching

    Example:
        registry = ToolRegistry()
        registry.register(ReadFileTool)
        registry.register(WriteFileTool)

        # Get all file tools
        file_tools = registry.get_by_category(ToolCategory.FILE)

        # Get specific tool
        read_tool = registry.get("read_file")

        # Get all tools for LLM
        llm_tools = registry.get_llm_tools()
    """

    _instance: Optional["ToolRegistry"] = None

    def __init__(self):
        """Initialize the registry."""
        self._tools: Dict[str, ToolRegistration] = {}
        self._categories: Dict[ToolCategory, Set[str]] = {
            category: set() for category in ToolCategory
        }
        self._dangerous_tools: Set[str] = set()
        self._approval_required_tools: Set[str] = set()

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        tool_class: Type[BaseTool],
        enabled: bool = True,
        tags: Optional[Set[str]] = None,
    ) -> None:
        """
        Register a tool class.

        Args:
            tool_class: The tool class to register
            enabled: Whether the tool is enabled by default
            tags: Optional tags for filtering
        """
        # Create a temporary instance to get metadata
        try:
            instance = tool_class()
        except Exception as e:
            logger.error(f"Failed to instantiate tool {tool_class.__name__}: {e}")
            raise

        name = instance.name

        if name in self._tools:
            logger.warning(f"Tool '{name}' is already registered, overwriting")

        # Create registration
        registration = ToolRegistration(
            tool_class=tool_class,
            instance=instance,
            enabled=enabled,
            tags=tags or set(),
        )

        self._tools[name] = registration

        # Index by category
        self._categories[instance.category].add(name)

        # Track dangerous and approval-required tools
        if instance.is_dangerous:
            self._dangerous_tools.add(name)
        if instance.requires_approval:
            self._approval_required_tools.add(name)

        logger.info(f"Registered tool: {name} ({instance.category.value})")

    def unregister(self, name: str) -> bool:
        """
        Unregister a tool.

        Args:
            name: Name of the tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if name not in self._tools:
            return False

        registration = self._tools[name]
        instance = registration.instance

        # Remove from category index
        if instance:
            self._categories[instance.category].discard(name)

        # Remove from special sets
        self._dangerous_tools.discard(name)
        self._approval_required_tools.discard(name)

        # Remove registration
        del self._tools[name]

        logger.info(f"Unregistered tool: {name}")
        return True

    def get(self, name: str) -> Optional[BaseTool]:
        """
        Get a tool instance by name.

        Args:
            name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        registration = self._tools.get(name)
        if not registration or not registration.enabled:
            return None
        return registration.instance

    def get_class(self, name: str) -> Optional[Type[BaseTool]]:
        """Get the tool class by name."""
        registration = self._tools.get(name)
        if not registration:
            return None
        return registration.tool_class

    def get_all(self, include_disabled: bool = False) -> List[BaseTool]:
        """
        Get all registered tools.

        Args:
            include_disabled: Whether to include disabled tools

        Returns:
            List of tool instances
        """
        tools = []
        for registration in self._tools.values():
            if include_disabled or registration.enabled:
                if registration.instance:
                    tools.append(registration.instance)
        return tools

    def get_by_category(
        self,
        category: ToolCategory,
        include_disabled: bool = False,
    ) -> List[BaseTool]:
        """
        Get all tools in a category.

        Args:
            category: The category to filter by
            include_disabled: Whether to include disabled tools

        Returns:
            List of tool instances in the category
        """
        tools = []
        for name in self._categories.get(category, set()):
            registration = self._tools.get(name)
            if registration and (include_disabled or registration.enabled):
                if registration.instance:
                    tools.append(registration.instance)
        return tools

    def get_by_tags(
        self,
        tags: Set[str],
        match_all: bool = False,
    ) -> List[BaseTool]:
        """
        Get tools by tags.

        Args:
            tags: Tags to filter by
            match_all: If True, tool must have all tags; if False, any tag

        Returns:
            List of matching tool instances
        """
        tools = []
        for registration in self._tools.values():
            if not registration.enabled or not registration.instance:
                continue

            if match_all:
                if tags.issubset(registration.tags):
                    tools.append(registration.instance)
            else:
                if tags & registration.tags:  # Intersection
                    tools.append(registration.instance)

        return tools

    def get_dangerous_tools(self) -> List[BaseTool]:
        """Get all dangerous tools."""
        return [
            self._tools[name].instance
            for name in self._dangerous_tools
            if self._tools[name].enabled and self._tools[name].instance
        ]

    def get_approval_required_tools(self) -> List[BaseTool]:
        """Get all tools that require approval."""
        return [
            self._tools[name].instance
            for name in self._approval_required_tools
            if self._tools[name].enabled and self._tools[name].instance
        ]

    def is_dangerous(self, name: str) -> bool:
        """Check if a tool is marked as dangerous."""
        return name in self._dangerous_tools

    def requires_approval(self, name: str) -> bool:
        """Check if a tool requires approval."""
        return name in self._approval_required_tools

    def enable(self, name: str) -> bool:
        """Enable a tool."""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool."""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def get_names(self, include_disabled: bool = False) -> List[str]:
        """Get all registered tool names."""
        if include_disabled:
            return list(self._tools.keys())
        return [
            name for name, reg in self._tools.items()
            if reg.enabled
        ]

    def get_schemas(self, include_disabled: bool = False) -> List[ToolSchema]:
        """Get schemas for all tools."""
        schemas = []
        for tool in self.get_all(include_disabled):
            schemas.append(tool.get_schema())
        return schemas

    def get_metadata(self, include_disabled: bool = False) -> List[ToolMetadata]:
        """Get metadata for all tools."""
        metadata = []
        for tool in self.get_all(include_disabled):
            metadata.append(tool.get_metadata())
        return metadata

    def get_llm_tools(
        self,
        format: str = "anthropic",
        categories: Optional[List[ToolCategory]] = None,
        exclude_dangerous: bool = False,
        exclude_approval_required: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get tools formatted for LLM consumption.

        Args:
            format: "anthropic" or "openai"
            categories: Optional list of categories to include
            exclude_dangerous: Whether to exclude dangerous tools
            exclude_approval_required: Whether to exclude approval-required tools

        Returns:
            List of tool definitions in LLM format
        """
        llm_tools = []

        for tool in self.get_all():
            # Filter by category
            if categories and tool.category not in categories:
                continue

            # Filter dangerous tools
            if exclude_dangerous and tool.is_dangerous:
                continue

            # Filter approval-required tools
            if exclude_approval_required and tool.requires_approval:
                continue

            llm_tools.append(tool.to_llm_format(format))

        return llm_tools

    def filter_tools(
        self,
        allowed_tools: Optional[List[str]] = None,
        denied_tools: Optional[List[str]] = None,
        allowed_categories: Optional[List[ToolCategory]] = None,
    ) -> List[BaseTool]:
        """
        Get filtered tools based on allowlist/denylist.

        Args:
            allowed_tools: If provided, only these tools are returned
            denied_tools: These tools are excluded
            allowed_categories: If provided, only tools in these categories

        Returns:
            List of filtered tool instances
        """
        tools = []

        for tool in self.get_all():
            # Check allowlist
            if allowed_tools and tool.name not in allowed_tools:
                continue

            # Check denylist
            if denied_tools and tool.name in denied_tools:
                continue

            # Check category
            if allowed_categories and tool.category not in allowed_categories:
                continue

            tools.append(tool)

        return tools

    def get_tool_info(self) -> Dict[str, Any]:
        """Get summary information about registered tools."""
        category_counts = {
            category.value: len(names)
            for category, names in self._categories.items()
        }

        return {
            "total_tools": len(self._tools),
            "enabled_tools": len([r for r in self._tools.values() if r.enabled]),
            "disabled_tools": len([r for r in self._tools.values() if not r.enabled]),
            "dangerous_tools": len(self._dangerous_tools),
            "approval_required_tools": len(self._approval_required_tools),
            "categories": category_counts,
            "tool_names": self.get_names(),
        }

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
        for category in self._categories:
            self._categories[category].clear()
        self._dangerous_tools.clear()
        self._approval_required_tools.clear()
        logger.info("Cleared all tools from registry")


# Singleton accessor
def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry instance."""
    return ToolRegistry.get_instance()
