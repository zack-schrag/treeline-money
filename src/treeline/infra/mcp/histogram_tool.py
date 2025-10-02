"""Tool for creating histogram visualizations."""

from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool
from treeline.pyplot import histogram
from treeline.pyplot.utils.colors import strip_colors


class HistogramTool(Tool):
    """
    Create histogram visualizations for terminal display.

    Best for showing distribution of values (e.g., transaction amount distribution,
    spending patterns across ranges).
    """

    @property
    def name(self) -> str:
        return "create_histogram"

    @property
    def description(self) -> str:
        return (
            "Create a histogram for terminal display. "
            "Use this to show distribution of values (e.g., transaction amounts, "
            "spending ranges). Provide the raw data values."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Data values to bin and display as histogram"
                },
                "bins": {
                    "type": "integer",
                    "description": "Number of bins to group values into",
                    "default": 10
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                    "default": ""
                },
                "xlabel": {
                    "type": "string",
                    "description": "X-axis label",
                    "default": ""
                },
                "width": {
                    "type": "integer",
                    "description": "Chart width in characters",
                    "default": 60
                },
                "color": {
                    "type": "string",
                    "enum": ["green", "blue", "red", "yellow", "cyan", "magenta"],
                    "description": "Bar color",
                    "default": "cyan"
                }
            },
            "required": ["values"]
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Create histogram and return rendered output."""
        try:
            # Extract parameters
            values: List[float] = tool_input.get("values", [])
            bins: int = tool_input.get("bins", 10)
            title: str = tool_input.get("title", "")
            xlabel: str = tool_input.get("xlabel", "")
            width: int = tool_input.get("width", 60)
            color: str = tool_input.get("color", "cyan")

            # Validation
            if len(values) == 0:
                return Fail("Must provide at least one data value.")

            if bins < 1:
                return Fail(f"Number of bins must be at least 1, got {bins}.")

            # Create chart
            chart = histogram(
                values=values,
                bins=bins,
                title=title,
                xlabel=xlabel,
                width=width,
                color=color
            )

            # Render and strip ANSI color codes for clean terminal output
            rendered = chart.render()
            clean_output = strip_colors(rendered)
            return Ok(f"\n{clean_output}\n")

        except Exception as e:
            return Fail(f"Error creating histogram: {str(e)}")
