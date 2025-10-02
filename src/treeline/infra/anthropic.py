"""Anthropic AI provider using Anthropic SDK."""

import io
import os
import sys
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List
from uuid import UUID

import duckdb
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message, MessageStreamEvent

from treeline.abstractions import AIProvider
from treeline.domain import Result, Ok, Fail
from treeline.pyplot import barplot, lineplot, histogram, scatterplot


class AnthropicProvider(AIProvider):
    """
    AI provider implementation using Anthropic SDK.

    Handles:
    - Conversation context management with message history
    - Tool definitions and execution with read-only DuckDB access
    - Streaming message delivery
    - Session lifecycle management
    """

    def __init__(self):
        """Initialize the Anthropic provider."""
        self.client: AsyncAnthropic | None = None
        self.user_id: UUID | None = None
        self.db_path: str | None = None
        self.session_started: datetime | None = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.MAX_TOOL_USE_ROUNDS = 10  # Max rounds of tool calling
        self.MAX_TOKENS = 4096
        self.MODEL = "claude-sonnet-4-20250514"

    async def start_session(self, user_id: UUID, db_path: str) -> Result[None]:
        """
        Initialize a new conversation session.

        Creates Anthropic client and initializes conversation history.
        """
        try:
            self.user_id = user_id
            self.db_path = db_path

            # Verify API key is set in environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set in environment")

            # Create Anthropic client
            self.client = AsyncAnthropic(api_key=api_key)

            # Clear conversation history
            self.conversation_history = []

            self.session_started = datetime.now()

            return Ok()

        except Exception as e:
            return Fail(f"Failed to start session: {str(e)}")

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get the tool definitions for the Anthropic API."""
        return [
            {
                "name": "execute_sql_query",
                "description": "Execute a SQL query against the user's DuckDB database. Always use this to analyze financial data.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "The SQL query to execute"
                        },
                        "description": {
                            "type": "string",
                            "description": "A brief description of what this query does"
                        }
                    },
                    "required": ["sql", "description"]
                }
            },
            {
                "name": "get_schema_info",
                "description": "Get complete schema information about all database tables including column names, types, and sample data.",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_date_range_info",
                "description": "Get information about the date ranges in the database (earliest/latest transaction dates, total transactions).",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "execute_python",
                "description": "Execute Python code for data analysis and visualization. You have access to: conn (DuckDB connection), barplot(), lineplot(), histogram(), scatterplot() for creating terminal charts. Charts are rendered by calling .render() and printing the result. The code will be executed and any output will be captured.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute. Available: conn (database), barplot(), lineplot(), histogram(), scatterplot(), datetime module."
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of what this code does"
                        }
                    },
                    "required": ["code", "description"]
                }
            }
        ]

    async def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return the result as a string."""
        if tool_name == "execute_sql_query":
            return await self._execute_sql_query(tool_input)
        elif tool_name == "get_schema_info":
            return await self._get_schema_info()
        elif tool_name == "get_date_range_info":
            return await self._get_date_range_info()
        elif tool_name == "execute_python":
            return await self._execute_python(tool_input)
        else:
            return f"Unknown tool: {tool_name}"

    async def _execute_sql_query(self, tool_input: Dict[str, Any]) -> str:
        """Execute a SQL query against the user's DuckDB database."""
        sql = tool_input.get("sql", "")
        description = tool_input.get("description", "")

        try:
            # Open read-only connection to prevent any data modification
            conn = duckdb.connect(self.db_path, read_only=True)

            try:
                # Execute query
                result = conn.execute(sql).fetchall()
                columns = [desc[0] for desc in conn.description] if conn.description else []

                # Format result as text
                result_text = f"Query: {description}\n\n"
                result_text += f"SQL:\n{sql}\n\n"
                result_text += f"Results ({len(result)} rows):\n"
                result_text += f"Columns: {', '.join(columns)}\n"
                result_text += f"Data: {result}\n"

                return result_text
            finally:
                conn.close()

        except Exception as e:
            return f"Error executing SQL: {str(e)}\nQuery: {sql}"

    async def _get_schema_info(self) -> str:
        """Get complete schema information about available tables."""
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

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

                return schema_text

            finally:
                conn.close()

        except Exception as e:
            return f"Error getting schema: {str(e)}"

    async def _get_date_range_info(self) -> str:
        """Get information about the date ranges in the database."""
        try:
            conn = duckdb.connect(self.db_path, read_only=True)

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

                    return info_text
                else:
                    return "No transactions found in database"

            finally:
                conn.close()

        except Exception as e:
            return f"Error getting date range info: {str(e)}"

    async def _execute_python(self, tool_input: Dict[str, Any]) -> str:
        """Execute Python code with access to database and pyplot."""
        code = tool_input.get("code", "")
        description = tool_input.get("description", "")

        try:
            # Create a read-only database connection
            conn = duckdb.connect(self.db_path, read_only=True)

            # Capture stdout for any print statements
            old_stdout = sys.stdout
            sys.stdout = captured_output = io.StringIO()

            try:
                # Create execution context with database connection and pyplot
                exec_globals = {
                    "conn": conn,
                    "barplot": barplot,
                    "lineplot": lineplot,
                    "histogram": histogram,
                    "scatterplot": scatterplot,
                    "duckdb": duckdb,
                    "datetime": datetime,
                }

                # Execute the code
                exec(code, exec_globals)

                # Get any captured output
                output = captured_output.getvalue()

                if output:
                    return f"Visualization: {description}\n\n{output}"
                else:
                    return f"Code executed successfully: {description}\n(No output produced)"

            finally:
                # Restore stdout
                sys.stdout = old_stdout
                conn.close()

        except Exception as e:
            # Restore stdout in case of error
            sys.stdout = old_stdout
            return f"Error executing Python code: {str(e)}\n\nCode:\n{code}"

    async def send_message(self, message: str) -> Result[Dict[str, Any]]:
        """
        Send a message and get response with tool execution and streaming.

        Args:
            message: User's natural language query

        Returns:
            Result containing response data with streaming iterator
        """
        if not self.client:
            return Fail("No active session. Call start_session() first.")

        try:
            # Add user message to conversation history
            self.conversation_history.append({
                "role": "user",
                "content": message
            })

            # Create async generator for streaming response
            async def response_stream() -> AsyncIterator[str]:
                tool_use_round = 0

                while tool_use_round < self.MAX_TOOL_USE_ROUNDS:
                    # Call Claude with conversation history
                    response = await self.client.messages.create(
                        model=self.MODEL,
                        max_tokens=self.MAX_TOKENS,
                        system=self._build_system_prompt(),
                        messages=self.conversation_history,
                        tools=self._get_tool_definitions()
                    )

                    # Add assistant response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Check if there are tool uses in the response
                    tool_uses = [block for block in response.content if block.type == "tool_use"]

                    if not tool_uses:
                        # No tool uses, yield text content and break
                        for block in response.content:
                            if block.type == "text":
                                yield block.text
                        break

                    # Execute tools and add results to conversation
                    tool_results = []
                    for tool_use in tool_uses:
                        # Use special marker for tool use that CLI will render with dim styling
                        yield f"__TOOL_USE__:{tool_use.name}\n"
                        result = await self._execute_tool(tool_use.name, tool_use.input)

                        # For Python execution (including visualizations), yield output directly to user
                        if tool_use.name == "execute_python":
                            yield f"\n{result}\n"

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result
                        })

                    # Add tool results to conversation
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results
                    })

                    tool_use_round += 1

                if tool_use_round >= self.MAX_TOOL_USE_ROUNDS:
                    yield "\n[Max tool use rounds reached]\n"

            return Ok({
                "stream": response_stream(),
                "message": message
            })

        except Exception as e:
            return Fail(f"Failed to send message: {str(e)}")

    async def end_session(self) -> Result[None]:
        """
        End the current conversation session and cleanup resources.
        """
        try:
            # Cleanup
            self.client = None
            self.user_id = None
            self.db_path = None
            self.session_started = None
            self.conversation_history = []

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
2. Create beautiful terminal-based visualizations using pyplot (barplot, lineplot, histogram, scatterplot)
3. Provide insights and answer questions about spending patterns, trends, and anomalies

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
9. **NEVER generate ASCII charts or bar graphs in SQL** - they don't render well in terminals
10. **Use the execute_python tool for visualizations** - when users ask for charts, graphs, trends over time, or visual representations
11. For visualizations, you have access to: `conn` (DuckDB connection), `barplot()`, `lineplot()`, `histogram()`, `scatterplot()`, `datetime`
12. Always call `.render()` on charts and print the result - this displays the chart to the user
13. For time-series data (spending over time, trends, etc.), use lineplot() for smooth curves
14. For comparing categories or discrete values, use barplot() for horizontal bars

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

## Example Interactions

### Example 1: Simple Query
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

### Example 2: Visualization Request
User: "Show me a chart of my weekly spending over the last 90 days"

You:
**Analysis:** I'll create a bar chart showing your weekly spending for the last 90 days.

[Use execute_python tool with code like:]
```python
# Query weekly spending
result = conn.execute('''
    SELECT
        DATE_TRUNC('week', transaction_date) as week,
        SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as spending
    FROM transactions
    WHERE transaction_date >= CURRENT_DATE - INTERVAL '90 days'
      AND amount < 0
    GROUP BY 1
    ORDER BY 1
''').fetchall()

# Format data
weeks = [row[0].strftime('%m/%d') for row in result]
spending = [float(row[1]) for row in result]

# Create and display chart
chart = barplot(labels=weeks, values=spending, title="Weekly Spending - Last 90 Days", xlabel="Week")
print(chart.render())
```

**Insights:**
[Describe trends you observe in the chart]

## Tips
- Use `get_date_range_info()` to understand what time period the data covers
- Negative amounts typically represent spending/outflows
- Positive amounts typically represent income/inflows
- Tags in the transactions table are arrays - use UNNEST(tags) to work with them
- Be helpful and proactive - if you notice something interesting, mention it!
"""
