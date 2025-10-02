"""
MCP-style tool infrastructure for AI agents.

This module provides a registry of tools that AI providers can use
to analyze data and create visualizations. Tools are provider-agnostic
and can be registered with any AI provider (Anthropic, OpenAI, etc.).
"""

from typing import Dict, List
from uuid import UUID

from treeline.abstractions import Repository
from treeline.infra.mcp.base import Tool
from treeline.infra.mcp.sql_query_tool import SqlQueryTool
from treeline.infra.mcp.schema_info_tool import SchemaInfoTool
from treeline.infra.mcp.date_range_info_tool import DateRangeInfoTool
from treeline.infra.mcp.barplot_tool import BarplotTool
from treeline.infra.mcp.lineplot_tool import LineplotTool
from treeline.infra.mcp.histogram_tool import HistogramTool
from treeline.infra.mcp.scatterplot_tool import ScatterplotTool
from treeline.infra.mcp.boxplot_tool import BoxplotTool


class ToolRegistry:
    """
    Central registry of all available tools for AI agents.

    Handles tool instantiation, dependency injection, and provides
    tools in format required by different AI providers.
    """

    def __init__(self, repository: Repository):
        """
        Initialize tool registry with dependencies.

        Args:
            repository: Repository instance for tools that need database access
        """
        self._repository = repository
        self._tools: Dict[str, Tool] = {}
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register all standard tools."""
        # Database query tools
        self.register(SqlQueryTool(self._repository))
        self.register(SchemaInfoTool(self._repository))
        self.register(DateRangeInfoTool(self._repository))

        # Visualization tools
        self.register(BarplotTool())
        self.register(LineplotTool())
        self.register(HistogramTool())
        self.register(ScatterplotTool())
        self.register(BoxplotTool())

    def register(self, tool: Tool) -> None:
        """
        Register a tool in the registry.

        Args:
            tool: Tool instance to register
        """
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Tool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get list of all registered tools."""
        return list(self._tools.values())

    def to_anthropic_format(self) -> List[Dict]:
        """Get all tools in Anthropic API format."""
        return [tool.to_anthropic_format() for tool in self._tools.values()]

    def to_openai_format(self) -> List[Dict]:
        """Get all tools in OpenAI API format."""
        return [tool.to_openai_format() for tool in self._tools.values()]

    async def execute_tool(self, name: str, user_id: UUID, tool_input: Dict) -> str:
        """
        Execute a tool by name.

        Args:
            name: Tool name
            user_id: User context
            tool_input: Tool parameters

        Returns:
            Tool output string (or error message)
        """
        tool = self.get_tool(name)
        if not tool:
            return f"Unknown tool: {name}"

        result = await tool.execute(user_id, tool_input)
        if not result.success:
            return result.error
        return result.data


__all__ = [
    "Tool",
    "ToolRegistry",
    "SqlQueryTool",
    "SchemaInfoTool",
    "DateRangeInfoTool",
    "BarplotTool",
    "LineplotTool",
    "HistogramTool",
    "ScatterplotTool",
    "BoxplotTool"
]
