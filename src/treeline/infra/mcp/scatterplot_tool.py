"""Tool for creating scatter plot visualizations."""

from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool
from treeline.pyplot import scatterplot


class ScatterplotTool(Tool):
    """
    Create scatter plot visualizations for terminal display.

    Best for showing relationships between two variables (e.g., amount vs day of week,
    spending correlation analysis).
    """

    @property
    def name(self) -> str:
        return "create_scatterplot"

    @property
    def description(self) -> str:
        return (
            "Create a scatter plot for terminal display. "
            "Use this to show relationships between two variables (e.g., amount vs day, "
            "correlation analysis). Provide x and y coordinate arrays."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "x": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "X values (independent variable)"
                },
                "y": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Y values (dependent variable)"
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
                "ylabel": {
                    "type": "string",
                    "description": "Y-axis label",
                    "default": ""
                },
                "width": {
                    "type": "integer",
                    "description": "Chart width in characters",
                    "default": 60
                },
                "height": {
                    "type": "integer",
                    "description": "Chart height in characters",
                    "default": 20
                },
                "color": {
                    "type": "string",
                    "enum": ["green", "blue", "red", "yellow", "cyan", "magenta"],
                    "description": "Point color",
                    "default": "magenta"
                }
            },
            "required": ["x", "y"]
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Create scatter plot and return rendered output."""
        try:
            # Extract parameters
            x: List[float] = tool_input.get("x", [])
            y: List[float] = tool_input.get("y", [])
            title: str = tool_input.get("title", "")
            xlabel: str = tool_input.get("xlabel", "")
            ylabel: str = tool_input.get("ylabel", "")
            width: int = tool_input.get("width", 60)
            height: int = tool_input.get("height", 20)
            color: str = tool_input.get("color", "magenta")

            # Validation
            if len(x) == 0 or len(y) == 0:
                return Fail("Must provide at least one data point.")

            if len(x) != len(y):
                return Fail(
                    f"X and Y arrays must have same length. "
                    f"Got {len(x)} x values and {len(y)} y values."
                )

            # Create chart
            chart = scatterplot(
                x=x,
                y=y,
                title=title,
                xlabel=xlabel,
                ylabel=ylabel,
                width=width,
                height=height,
                color=color
            )

            # Render and return
            rendered = chart.render()
            return Ok(f"\n{rendered}\n")

        except Exception as e:
            return Fail(f"Error creating scatter plot: {str(e)}")
