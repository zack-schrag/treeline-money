"""Tool for creating box plot visualizations."""

from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool
from treeline.pyplot import boxplot


class BoxplotTool(Tool):
    """
    Create box-and-whisker plot visualizations for terminal display.

    Best for comparing distributions across multiple groups (e.g., spending
    distribution by month, transaction amounts by category).
    """

    @property
    def name(self) -> str:
        return "create_boxplot"

    @property
    def description(self) -> str:
        return (
            "Create a box-and-whisker plot for terminal display. "
            "Use this to compare distributions across groups (e.g., monthly spending "
            "distribution, amounts by category). Provide a list of data series."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"}
                    },
                    "description": "List of data series - each series is an array of numbers representing one group"
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels for each data series (e.g., month names, categories). Optional."
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
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
                    "description": "Box color",
                    "default": "blue"
                }
            },
            "required": ["data"]
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Create box plot and return rendered output."""
        try:
            # Extract parameters
            data: List[List[float]] = tool_input.get("data", [])
            labels: List[str] | None = tool_input.get("labels")
            title: str = tool_input.get("title", "")
            ylabel: str = tool_input.get("ylabel", "")
            width: int = tool_input.get("width", 60)
            height: int = tool_input.get("height", 20)
            color: str = tool_input.get("color", "blue")

            # Validation
            if len(data) == 0:
                return Fail("Must provide at least one data series.")

            for i, series in enumerate(data):
                if len(series) == 0:
                    return Fail(f"Data series {i} is empty.")

            if labels is not None and len(labels) != len(data):
                return Fail(
                    f"Number of labels must match number of data series. "
                    f"Got {len(labels)} labels and {len(data)} series."
                )

            # Create chart
            chart = boxplot(
                data=data,
                labels=labels,
                title=title,
                ylabel=ylabel,
                width=width,
                height=height,
                color=color
            )

            # Render and return
            rendered = chart.render()
            return Ok(f"\n{rendered}\n")

        except Exception as e:
            return Fail(f"Error creating box plot: {str(e)}")
