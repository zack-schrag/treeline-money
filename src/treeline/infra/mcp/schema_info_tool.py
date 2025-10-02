"""Tool for getting database schema information."""

from typing import Any, Dict
from uuid import UUID

from treeline.abstractions import Repository
from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool


class SchemaInfoTool(Tool):
    """
    Get complete schema information about available database tables.

    Returns table names, column definitions, and sample data to help
    the AI understand the database structure.
    """

    def __init__(self, repository: Repository):
        """
        Initialize schema info tool.

        Args:
            repository: Repository instance for database access
        """
        self._repository = repository

    @property
    def name(self) -> str:
        return "get_schema_info"

    @property
    def description(self) -> str:
        return (
            "Get complete schema information about all database tables including "
            "column names, types, and sample data."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Get schema information and return formatted output."""
        result = await self._repository.get_schema_info(user_id)

        if not result.success:
            return Fail(f"Error getting schema: {result.error}")

        schema_info = result.data

        # Format schema as text
        schema_text = "Database Schema:\n\n"
        for table_name, table_info in schema_info.items():
            schema_text += f"Table: {table_name}\n"
            schema_text += "Columns:\n"
            for col in table_info["columns"]:
                schema_text += f"  - {col['name']}: {col['type']}\n"
            schema_text += f"\nSample data ({len(table_info['sample_data']['rows'])} rows):\n"
            schema_text += f"Columns: {', '.join(table_info['sample_data']['columns'])}\n"
            for row in table_info['sample_data']['rows']:
                schema_text += f"  {row}\n"
            schema_text += "\n"

        return Ok(schema_text)
