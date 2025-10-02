"""Tool for creating bar chart visualizations."""

from typing import Any, Dict, List
from uuid import UUID

from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool
from treeline.pyplot import barplot


class BarplotTool(Tool):
    """
    Create horizontal bar chart visualizations for terminal display.

    This tool allows AI agents to create bar charts from data they've
    analyzed via SQL queries. The AI must provide the data directly
    (labels and values) rather than executing arbitrary Python code.
    """

    @property
    def name(self) -> str:
        return "create_barplot"

    @property
    def description(self) -> str:
        return (
            "Create a horizontal bar chart for terminal display. "
            "Use this for comparing categorical values (e.g., spending by category, "
            "monthly totals). You must provide the data (labels and values) directly."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Labels for each bar (e.g., category names, month names)"
                },
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Numeric values for each bar (must be non-negative)"
                },
                "title": {
                    "type": "string",
                    "description": "Chart title",
                    "default": ""
                },
                "xlabel": {
                    "type": "string",
                    "description": "X-axis label (e.g., 'Amount ($)')",
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
                    "default": "green"
                }
            },
            "required": ["labels", "values"]
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Create bar chart and return rendered output."""
        try:
            # Extract parameters
            labels: List[str] = tool_input.get("labels", [])
            values: List[float] = tool_input.get("values", [])
            title: str = tool_input.get("title", "")
            xlabel: str = tool_input.get("xlabel", "")
            width: int = tool_input.get("width", 60)
            color: str = tool_input.get("color", "green")

            # Validation
            if len(labels) != len(values):
                return Fail(
                    f"Labels and values must have same length. "
                    f"Got {len(labels)} labels and {len(values)} values."
                )

            if len(labels) == 0:
                return Fail("Must provide at least one data point.")

            if any(v < 0 for v in values):
                return Fail("All values must be non-negative for bar charts.")

            # Create chart
            chart = barplot(
                labels=labels,
                values=values,
                title=title,
                xlabel=xlabel,
                width=width,
                color=color
            )

            # Render and return
            rendered = chart.render()
            return Ok(f"\n{rendered}\n")

        except Exception as e:
            return Fail(f"Error creating bar chart: {str(e)}")
