"""Tool for getting transaction date range information."""

from typing import Any, Dict
from uuid import UUID

from treeline.abstractions import Repository
from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool


class DateRangeInfoTool(Tool):
    """
    Get information about the date ranges in the database.

    Returns earliest/latest transaction dates and total transaction count
    to help the AI understand the data coverage period.
    """

    def __init__(self, repository: Repository):
        """
        Initialize date range info tool.

        Args:
            repository: Repository instance for database access
        """
        self._repository = repository

    @property
    def name(self) -> str:
        return "get_date_range_info"

    @property
    def description(self) -> str:
        return (
            "Get information about the date ranges in the database "
            "(earliest/latest transaction dates, total transactions)."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Get date range information and return formatted output."""
        result = await self._repository.get_date_range_info(user_id)

        if not result.success:
            return Fail(f"Error getting date range info: {result.error}")

        date_info = result.data

        if not date_info.get("earliest_date") or not date_info.get("latest_date"):
            return Ok("No transactions found in database")

        earliest = date_info["earliest_date"]
        latest = date_info["latest_date"]
        total = date_info.get("total_transactions", 0)
        days_range = date_info.get("days_range")

        info_text = "Date Range Information:\n\n"
        info_text += f"Earliest transaction: {earliest}\n"
        info_text += f"Latest transaction: {latest}\n"
        info_text += f"Total transactions: {total}\n"
        if days_range is not None:
            info_text += f"Date range: {days_range} days\n"

        return Ok(info_text)
