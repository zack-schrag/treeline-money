"""Tool for executing SQL queries against user's database."""

from typing import Any, Dict
from uuid import UUID

from treeline.abstractions import Repository
from treeline.domain import Result, Fail, Ok
from treeline.infra.mcp.base import Tool


class SqlQueryTool(Tool):
    """
    Execute read-only SQL queries against the user's DuckDB database.

    This tool provides AI agents with the ability to analyze financial data
    using SQL. All queries are executed in read-only mode for safety.
    """

    def __init__(self, repository: Repository):
        """
        Initialize SQL query tool.

        Args:
            repository: Repository instance for database access
        """
        self._repository = repository

    @property
    def name(self) -> str:
        return "execute_sql_query"

    @property
    def description(self) -> str:
        return (
            "Execute a SQL query against the user's DuckDB database. "
            "Always use this to analyze financial data. "
            "Only SELECT queries are supported."
        )

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SQL query to execute (SELECT only)"
                },
                "description": {
                    "type": "string",
                    "description": "A brief description of what this query does"
                }
            },
            "required": ["sql", "description"]
        }

    async def execute(self, user_id: UUID, tool_input: Dict[str, Any]) -> Result[str]:
        """Execute SQL query and return formatted results."""
        sql = tool_input.get("sql", "")
        description = tool_input.get("description", "")

        # Security: Basic validation to prevent non-SELECT queries
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            return Fail(
                f"Only SELECT and WITH queries are allowed. "
                f"Query starts with: {sql_upper[:20]}"
            )

        # Execute query using repository abstraction
        result = await self._repository.execute_query(user_id, sql)

        if not result.success:
            return Fail(f"Error executing SQL: {result.error}\nQuery: {sql}")

        # Format results
        query_result = result.data
        rows = query_result.get("rows", [])
        columns = query_result.get("columns", [])

        result_text = f"Query: {description}\n\n"
        result_text += f"SQL:\n{sql}\n\n"
        result_text += f"Results ({len(rows)} rows):\n"
        result_text += f"Columns: {', '.join(columns)}\n"
        result_text += f"Data: {rows}\n"

        return Ok(result_text)
