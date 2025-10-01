"""Anthropic AI provider using Claude Agent SDK."""

import os
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict
from uuid import UUID

import duckdb
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, tool

from treeline.abstractions import AIProvider
from treeline.domain import Result, Ok, Fail


class AnthropicProvider(AIProvider):
    """
    AI provider implementation using Claude Agent SDK.

    The ClaudeSDKClient handles:
    - Automatic conversation context management
    - Tool registration and execution
    - Streaming message delivery
    - Session lifecycle management

    We handle:
    - Tool implementations with read-only DuckDB access
    - System prompt generation
    - Session state tracking
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY must be set in environment or passed to constructor")

        self.client: ClaudeSDKClient | None = None
        self.user_id: UUID | None = None
        self.db_path: str | None = None
        self.session_started: datetime | None = None
        self.MAX_TOOL_RETRIES = 3

    async def start_session(self, user_id: UUID, db_path: str) -> Result[None]:
        """
        Initialize a new conversation session.

        Creates ClaudeSDKClient with tools and system prompt.
        """
        try:
            self.user_id = user_id
            self.db_path = db_path

            # Build system prompt with schema info
            system_prompt = self._build_system_prompt()

            # Create tools - these need access to db_path and user_id
            # We'll use closures to capture these values
            @tool(
                name="execute_sql_query",
                description="Execute a SQL query against the user's DuckDB database. Always use this to analyze financial data.",
                input_schema={
                    "sql": str,
                    "description": str
                }
            )
            async def execute_sql_query(args: Dict[str, Any]) -> Dict[str, Any]:
                """Execute a SQL query against the user's DuckDB database."""
                sql = args.get("sql", "")
                description = args.get("description", "")

                try:
                    # Open read-only connection to prevent any data modification
                    conn = duckdb.connect(db_path, read_only=True)

                    try:
                        # Execute query
                        result = conn.execute(sql).fetchall()
                        columns = [desc[0] for desc in conn.description] if conn.description else []

                        # Format result as text content
                        result_text = f"Query: {description}\n\n"
                        result_text += f"SQL:\n{sql}\n\n"
                        result_text += f"Results ({len(result)} rows):\n"
                        result_text += f"Columns: {', '.join(columns)}\n"
                        result_text += f"Data: {result}\n"

                        return {
                            "content": [{
                                "type": "text",
                                "text": result_text
                            }]
                        }
                    finally:
                        conn.close()

                except Exception as e:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Error executing SQL: {str(e)}\nQuery: {sql}"
                        }]
                    }

            @tool(
                name="get_schema_info",
                description="Get complete schema information about all database tables including column names, types, and sample data.",
                input_schema={}
            )
            async def get_schema_info(args: Dict[str, Any]) -> Dict[str, Any]:
                """Get complete schema information about available tables."""
                try:
                    conn = duckdb.connect(db_path, read_only=True)

                    try:
                        # Get all tables
                        tables_result = conn.execute(
                            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                        ).fetchall()

                        schema_info = {}

                        for (table_name,) in tables_result:
                            # Get column information
                            columns_result = conn.execute(f"""
                                SELECT column_name, data_type
                                FROM information_schema.columns
                                WHERE table_name = '{table_name}'
                                ORDER BY ordinal_position
                            """).fetchall()

                            # Get sample data
                            sample_result = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
                            column_names = [desc[0] for desc in conn.description] if conn.description else []

                            schema_info[table_name] = {
                                "columns": [
                                    {"name": col[0], "type": col[1]}
                                    for col in columns_result
                                ],
                                "sample_data": {
                                    "columns": column_names,
                                    "rows": sample_result
                                }
                            }

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

                        return {
                            "content": [{
                                "type": "text",
                                "text": schema_text
                            }]
                        }

                    finally:
                        conn.close()

                except Exception as e:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Error getting schema: {str(e)}"
                        }]
                    }

            @tool(
                name="get_date_range_info",
                description="Get information about the date ranges in the database (earliest/latest transaction dates, total transactions).",
                input_schema={}
            )
            async def get_date_range_info(args: Dict[str, Any]) -> Dict[str, Any]:
                """Get information about the date ranges in the database."""
                try:
                    conn = duckdb.connect(db_path, read_only=True)

                    try:
                        result = conn.execute("""
                            SELECT
                                MIN(transaction_date) as earliest_date,
                                MAX(transaction_date) as latest_date,
                                COUNT(*) as total_transactions
                            FROM transactions
                        """).fetchone()

                        if result and result[0] and result[1]:
                            earliest = result[0]
                            latest = result[1]
                            total = result[2]

                            # Calculate date range in days
                            if isinstance(earliest, datetime) and isinstance(latest, datetime):
                                days_range = (latest - earliest).days
                            else:
                                days_range = None

                            info_text = f"Date Range Information:\n\n"
                            info_text += f"Earliest transaction: {earliest}\n"
                            info_text += f"Latest transaction: {latest}\n"
                            info_text += f"Total transactions: {total}\n"
                            info_text += f"Date range: {days_range} days\n"

                            return {
                                "content": [{
                                    "type": "text",
                                    "text": info_text
                                }]
                            }
                        else:
                            return {
                                "content": [{
                                    "type": "text",
                                    "text": "No transactions found in database"
                                }]
                            }

                    finally:
                        conn.close()

                except Exception as e:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"Error getting date range info: {str(e)}"
                        }]
                    }

            # Set API key in environment for Claude SDK
            os.environ["ANTHROPIC_API_KEY"] = self.api_key

            # Create options for ClaudeSDKClient
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                allowed_tools=[execute_sql_query, get_schema_info, get_date_range_info]
            )

            # Create ClaudeSDKClient with options
            self.client = ClaudeSDKClient(options=options)

            await self.client.connect()
            self.session_started = datetime.now()

            return Ok()

        except Exception as e:
            return Fail(f"Failed to start session: {str(e)}")

    async def send_message(self, message: str) -> Result[Dict[str, Any]]:
        """
        Send a message and get response with streaming chunks.

        Args:
            message: User's natural language query

        Returns:
            Result containing response data with streaming iterator
        """
        if not self.client:
            return Fail("No active session. Call start_session() first.")

        try:
            # Send query to Claude
            await self.client.query(message)

            # Return success with streaming iterator
            return Ok({
                "stream": self.client.receive_response(),
                "message": message
            })

        except Exception as e:
            return Fail(f"Failed to send message: {str(e)}")

    async def end_session(self) -> Result[None]:
        """
        End the current conversation session and cleanup resources.
        """
        try:
            if self.client:
                await self.client.disconnect()
                self.client = None

            self.user_id = None
            self.db_path = None
            self.session_started = None

            return Ok()

        except Exception as e:
            return Fail(f"Failed to end session: {str(e)}")

    def has_active_session(self) -> bool:
        """
        Check if there is an active conversation session.
        """
        return self.client is not None

    def is_session_expired(self) -> bool:
        """
        Check if session has been idle for more than 30 minutes.
        """
        if not self.session_started:
            return False

        return (datetime.now() - self.session_started) > timedelta(minutes=30)

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for Claude.

        Includes:
        - Role definition
        - Available capabilities
        - Important rules
        - Response format guidelines
        """
        return """You are a financial analysis assistant for Treeline, a CLI-based personal finance tool.

## Your Capabilities
You have access to the user's financial data stored in a DuckDB database. You can:
1. Execute SQL queries to analyze transactions, accounts, and balances
2. Provide insights and answer questions about spending patterns, trends, and anomalies

## Database Schema
The database contains these tables:
- **accounts**: User's financial accounts (checking, savings, credit cards, etc.)
- **transactions**: All financial transactions with amounts, dates, descriptions, and tags
- **balance_snapshots**: Historical account balance records
- **integrations**: Connected data providers (SimpleFIN, etc.)

Use the `get_schema_info()` tool to see the complete schema with column names and sample data.

## Important Rules
1. **ALWAYS show the SQL queries you use** - users want to see your work
2. Format SQL in readable code blocks with the `sql` language marker
3. When showing query results, use tables for clarity
4. Be conversational but concise - this is a CLI, not an essay
5. If data seems incomplete or unusual, mention it
6. **Only use read-only SQL operations** (SELECT, WITH, etc.) - you cannot modify data
7. When analyzing spending, consider both amount and frequency
8. Look for outliers and unusual patterns proactively

## Response Format
When analyzing data, structure responses like this:

**Analysis:** [Brief natural language summary]

**Query Used:**
```sql
[The SQL query]
```

**Results:**
[Present the data clearly - use descriptions of what you found]

**Insights:**
- [Key insight 1]
- [Key insight 2]

## Example Interaction
User: "Show me my spending last week"

You:
**Analysis:** Here's your spending breakdown for the last 7 days.

**Query Used:**
```sql
SELECT
  DATE_TRUNC('day', transaction_date) as date,
  SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as spending
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '7 days'
  AND amount < 0
GROUP BY 1
ORDER BY 1;
```

**Results:**
[Describe the daily spending amounts you found]

**Insights:**
- Total spending: $X
- Highest spending day: Monday with $Y
- Average daily spending: $Z

## Tips
- Use `get_date_range_info()` to understand what time period the data covers
- Negative amounts typically represent spending/outflows
- Positive amounts typically represent income/inflows
- Tags in the transactions table are arrays - use UNNEST(tags) to work with them
- Be helpful and proactive - if you notice something interesting, mention it!
"""
