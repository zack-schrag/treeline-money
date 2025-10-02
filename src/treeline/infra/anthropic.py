"""Anthropic AI provider using Anthropic SDK."""

import os
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List
from uuid import UUID

from anthropic import AsyncAnthropic

from treeline.abstractions import AIProvider
from treeline.domain import Result, Ok, Fail
from treeline.infra.mcp import ToolRegistry


class AnthropicProvider(AIProvider):
    """
    AI provider implementation using Anthropic SDK.

    Handles:
    - Conversation context management with message history
    - Streaming message delivery
    - Session lifecycle management

    Delegates tool execution to ToolRegistry for provider-independence.
    """

    def __init__(self, tool_registry: ToolRegistry):
        """
        Initialize the Anthropic provider.

        Args:
            tool_registry: Registry of available tools
        """
        self.tool_registry = tool_registry
        self.client: AsyncAnthropic | None = None
        self.user_id: UUID | None = None
        self.session_started: datetime | None = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.MAX_TOOL_USE_ROUNDS = 10
        self.MAX_TOKENS = 4096
        self.MODEL = "claude-sonnet-4-20250514"

    async def start_session(self, user_id: UUID, db_path: str) -> Result[None]:
        """Initialize a new conversation session."""
        try:
            self.user_id = user_id

            # Verify API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY must be set in environment")

            # Create Anthropic client
            self.client = AsyncAnthropic(api_key=api_key)
            self.conversation_history = []
            self.session_started = datetime.now()

            return Ok()

        except Exception as e:
            return Fail(f"Failed to start session: {str(e)}")

    async def send_message(self, message: str) -> Result[Dict[str, Any]]:
        """Send a message and get response with tool execution and streaming."""
        if not self.client:
            return Fail("No active session. Call start_session() first.")

        try:
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": message
            })

            # Create async generator for streaming response
            async def response_stream() -> AsyncIterator[str]:
                tool_use_round = 0

                while tool_use_round < self.MAX_TOOL_USE_ROUNDS:
                    # Get tool definitions from registry
                    tools = self.tool_registry.to_anthropic_format()

                    # Call Claude
                    response = await self.client.messages.create(
                        model=self.MODEL,
                        max_tokens=self.MAX_TOKENS,
                        system=self._build_system_prompt(),
                        messages=self.conversation_history,
                        tools=tools
                    )

                    # Add assistant response to history
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })

                    # Check for tool uses
                    tool_uses = [block for block in response.content if block.type == "tool_use"]

                    if not tool_uses:
                        # No tool uses, yield text and break
                        for block in response.content:
                            if block.type == "text":
                                yield block.text
                        break

                    # Execute tools using registry
                    tool_results = []
                    for tool_use in tool_uses:
                        yield f"__TOOL_USE__:{tool_use.name}\n"

                        # Delegate to tool registry
                        result = await self.tool_registry.execute_tool(
                            tool_use.name,
                            self.user_id,
                            tool_use.input
                        )

                        # For visualizations, yield output to user
                        if tool_use.name.startswith("create_"):
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
        """End the current conversation session."""
        try:
            self.client = None
            self.user_id = None
            self.session_started = None
            self.conversation_history = []
            return Ok()
        except Exception as e:
            return Fail(f"Failed to end session: {str(e)}")

    def has_active_session(self) -> bool:
        """Check if there is an active conversation session."""
        return self.client is not None

    def is_session_expired(self) -> bool:
        """Check if session has been idle for more than 30 minutes."""
        if not self.session_started:
            return False
        return (datetime.now() - self.session_started) > timedelta(minutes=30)

    def _build_system_prompt(self) -> str:
        """Build the system prompt for Claude."""
        return """You are a financial analysis assistant for Treeline, a CLI-based personal finance tool.

## Your Capabilities
You have access to the user's financial data stored in a DuckDB database. You can:
1. Execute SQL queries to analyze transactions, accounts, and balances
2. Create beautiful terminal-based visualizations (bar charts, line charts, histograms, scatter plots, box plots)
3. Provide insights and answer questions about spending patterns, trends, and anomalies

## Available Tools

### Data Analysis Tools
- **execute_sql_query**: Run SELECT queries against the database
- **get_schema_info**: View complete database schema with sample data
- **get_date_range_info**: Get transaction date range information

### Visualization Tools
- **create_barplot**: Horizontal bar charts for comparing categories (e.g., spending by tag)
- **create_lineplot**: Line charts for time-series trends (e.g., balance over time)
- **create_histogram**: Distribution charts (e.g., transaction amount distribution)
- **create_scatterplot**: Correlation plots (e.g., amount vs. day of week)
- **create_boxplot**: Statistical comparison charts

## Database Schema
The database contains these tables:
- **accounts**: User's financial accounts
- **transactions**: All financial transactions with amounts, dates, descriptions, tags
- **balance_snapshots**: Historical account balance records
- **integrations**: Connected data providers

Use `get_schema_info()` to see complete schema with column names and sample data.

## Important Rules
1. **ALWAYS show SQL queries** in readable code blocks
2. **Use visualization tools for charts** - provide data arrays directly to tools
3. **Never try to execute Python code** - use the specific visualization tools instead
4. **Format responses clearly** - this is a CLI interface
5. **Only read-only queries** - SELECT and WITH statements only
6. **Look for insights** - proactively identify patterns and anomalies

## Workflow for Creating Charts

1. Use `execute_sql_query` to get the data
2. Extract the relevant values from query results
3. Call the appropriate visualization tool with data arrays

Example for bar chart of spending by category:
```
# Step 1: Query the data
execute_sql_query({
  "sql": "SELECT category, SUM(amount) as total FROM transactions GROUP BY category",
  "description": "Get spending by category"
})

# Step 2: Create visualization with the data
create_barplot({
  "labels": ["Groceries", "Dining", "Transport"],
  "values": [450.25, 320.10, 180.50],
  "title": "Spending by Category",
  "xlabel": "Amount ($)"
})
```

## Response Format
**Analysis:** [Summary]
**Query Used:**
```sql
[SQL query]
```
**Results:** [Description of findings]
**Insights:**
- [Key finding 1]
- [Key finding 2]

Be conversational, concise, and proactive. This is a CLI tool for technical users.
"""
