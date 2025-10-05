# AI Agent Design - Financial Analysis Assistant

## Overview
The Treeline AI agent is a conversational financial analysis assistant that helps users understand and explore their financial data through natural language. It combines the power of Claude's reasoning with direct access to the user's DuckDB database and terminal-based visualizations via YouPlot.

## Key Implementation Decisions

### Using Claude Agent SDK (ClaudeSDKClient)
We leverage the Claude Agent SDK which **significantly simplifies** our implementation:
- ✅ **Automatic context management** - No manual conversation history tracking needed
- ✅ **Built-in tool execution** - Tools are registered via `@tool` decorator, SDK handles calling them
- ✅ **Streaming responses** - Native async streaming support for responsive UX
- ✅ **Session lifecycle** - Context manager pattern handles connection/disconnection
- ✅ **Multi-turn conversations** - Follow-up questions "just work" with full context

### Read-Only DuckDB Access
All agent tools use **read-only DuckDB connections** (`read_only=True`):
- 🔒 **Security**: Agent CANNOT modify user data (no INSERT/UPDATE/DELETE/DROP)
- 🔒 **Safety**: Even if agent is compromised or makes mistakes, data is protected
- 🔒 **Implementation**: Simple flag on `duckdb.connect()`, no complex SQL validation needed

### Implementation in `src/treeline/infra/anthropic.py`
- Use existing `anthropic.py` file (currently empty)
- Implement `AnthropicProvider` class using `ClaudeSDKClient`
- Define tools with `@tool` decorator
- Each tool opens fresh read-only connection to DuckDB

## Core Principles

### 1. Show Your Work
Every AI response that involves data analysis MUST display the SQL queries used. This serves multiple purposes:
- **Trust**: Users can verify the agent's reasoning
- **Learning**: Users learn SQL by seeing examples
- **Iteration**: Users can copy/modify SQL for further analysis
- **Debugging**: When results seem wrong, users can inspect the query

### 2. Conversational Context
The agent maintains conversation history to enable iterative analysis:
- User: "Can you provide an overview of my last week?"
- Agent: *runs queries, shows results*
- User: "Whoa, my spending was more than expected. Can you identify why?"
- Agent: *uses context from previous analysis to dive deeper*

### 3. Multi-Modal Output
The agent can present information in multiple formats:
- **Text summaries**: Natural language explanations
- **Tables**: Structured data display using Rich tables
- **Charts**: Terminal visualizations using YouPlot
- **Raw SQL**: Always shown for transparency

## Architecture

### High-Level Flow
```
User Input (natural language)
    ↓
AI Agent (Claude Agent SDK)
    ↓
Tool Execution (DuckDB queries, YouPlot charts)
    ↓
Result Presentation (Rich formatting)
    ↓
Context Retained for Next Turn
```

### Key Components

#### 1. Agent Service (`src/treeline/app/service.py`)
```python
class AgentService:
    """Service for AI-powered financial analysis."""

    def __init__(
        self,
        ai_provider: AIProvider,
        repository: Repository,
        config_service: ConfigService
    ):
        self.ai_provider = ai_provider
        self.repository = repository
        self.config_service = config_service
        self.conversation_history: List[Message] = []

    async def chat(
        self,
        user_id: UUID,
        message: str
    ) -> Result[AgentResponse]:
        """
        Process a conversational message and return analysis.

        Maintains conversation history for context across turns.
        """
        pass

    async def start_new_session(self) -> None:
        """Clear conversation history to start fresh."""
        pass
```

#### 2. AI Provider Abstraction (`src/treeline/abstractions.py`)
```python
class AIProvider(ABC):
    """Abstraction for AI/LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: List[Tool],
        system_prompt: str
    ) -> Result[AIResponse]:
        """Execute a chat completion with tools."""
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: List[Message],
        tools: List[Tool],
        system_prompt: str
    ) -> AsyncIterator[StreamChunk]:
        """Stream a chat completion with tools."""
        pass
```

#### 3. Anthropic Provider (`src/treeline/infra/anthropic.py`)
```python
class AnthropicProvider(AIProvider):
    """
    Implementation using Claude Agent SDK (ClaudeSDKClient).

    The ClaudeSDKClient handles:
    - Automatic conversation state management (context retention)
    - Tool registration and execution
    - Streaming message delivery
    - Session lifecycle (connect, query, receive, disconnect)
    - Permission controls via can_use_tool callback

    Our implementation focuses on:
    - Configuring tools with read-only DuckDB access
    - Managing session lifecycle
    - Formatting responses for terminal display
    """

    def __init__(self, api_key: str, db_path: str, user_id: UUID):
        self.api_key = api_key
        self.db_path = db_path
        self.user_id = user_id
        self.client: ClaudeSDKClient | None = None

    async def start_session(self):
        """
        Initialize ClaudeSDKClient with tools and system prompt.

        ClaudeSDKClient maintains conversation state automatically,
        so each session = one client instance.
        """
        pass

    async def chat(self, message: str) -> AsyncIterator[StreamChunk]:
        """
        Send message and stream response.

        ClaudeSDKClient handles:
        - Appending message to conversation history
        - Invoking Claude with full context
        - Tool execution when Claude requests it
        - Streaming the response back
        """
        pass

    async def end_session(self):
        """Disconnect ClaudeSDKClient and clear state."""
        pass
```

### Tools Available to Agent

The agent will have access to these tools via the Claude Agent SDK:

#### 1. `execute_sql_query`
```python
@tool
async def execute_sql_query(
    sql: str,
    description: str
) -> Dict[str, Any]:
    """
    Execute a SQL query against the user's DuckDB database.

    Args:
        sql: The SQL query to execute
        description: Human-readable description of what this query does

    Returns:
        Dict with 'rows', 'columns', and 'row_count'
    """
    # Open read-only connection to prevent any data modification
    conn = duckdb.connect(db_path, read_only=True)

    try:
        # Execute query
        result = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description]

        return {
            "success": True,
            "rows": result,
            "columns": columns,
            "row_count": len(result),
            "description": description
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "description": description
        }
    finally:
        conn.close()
```

**Key Features:**
- **Read-only connection** (`read_only=True`) - Agent CANNOT modify data
- Always requires a description (for transparency)
- Returns structured data that can be formatted
- Connection is closed after each query (stateless, safe)
- Includes execution metadata (timing, row counts)
- No SQL validation needed - DuckDB read-only mode prevents writes

#### 2. `create_terminal_chart`
```python
@tool
def create_terminal_chart(
    sql: str,
    chart_type: Literal["line", "bar", "scatter", "hist"],
    x_column: str,
    y_column: str,
    title: str
) -> str:
    """
    Create a terminal-based chart using YouPlot from SQL results.

    Args:
        sql: Query that returns data to visualize
        chart_type: Type of chart to create
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title

    Returns:
        ASCII art chart ready to display in terminal
    """
```

**Key Features:**
- Pipes DuckDB output directly to YouPlot
- Supports common chart types
- Returns ASCII art for terminal display
- Validates column names exist in query results

#### 3. `get_schema_info`
```python
@tool
def get_schema_info() -> Dict[str, Any]:
    """
    Get complete schema information about available tables.

    Returns detailed schema including:
    - Table names
    - Column names and types
    - Sample data (3 rows per table)
    - Index information
    """
```

**Why This Matters:**
- Agent knows what data is available
- Can suggest appropriate queries
- Understands data types for proper filtering

#### 4. `get_date_range_info`
```python
@tool
def get_date_range_info() -> Dict[str, Any]:
    """
    Get information about the date ranges in the database.

    Returns:
        - Earliest transaction date
        - Latest transaction date
        - Account creation dates
        - Data gaps (if any)
    """
```

**Why This Matters:**
- Helps agent understand temporal context
- Prevents queries for data that doesn't exist
- Enables smart date range suggestions

## System Prompt Design

The system prompt is critical for agent behavior. Here's the structure:

```markdown
You are a financial analysis assistant for Treeline, a CLI-based personal finance tool.

## Your Capabilities
You have access to the user's financial data stored in a DuckDB database. You can:
1. Execute SQL queries to analyze transactions, accounts, and balances
2. Create terminal-based visualizations using YouPlot
3. Provide insights and answer questions about spending patterns, trends, and anomalies

## Database Schema
[Dynamically injected from get_schema_info tool]

## Important Rules
1. ALWAYS show the SQL queries you use - users want to see your work
2. Format SQL in readable code blocks with syntax highlighting
3. When showing query results, use tables for clarity
4. For trends and comparisons, prefer visualizations over raw numbers
5. Be conversational but concise - this is a CLI, not an essay
6. If data seems incomplete or unusual, mention it
7. Only use read-only SQL operations (SELECT, WITH, etc.)
8. When analyzing spending, consider both amount and frequency
9. Look for outliers and unusual patterns proactively

## Response Format
When analyzing data, structure responses like this:

**Analysis:** [Brief natural language summary]

**Query Used:**
```sql
[The SQL query]
```

**Results:**
[Table or chart visualization]

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
GROUP BY 1
ORDER BY 1;
```

[Chart showing daily spending trend]

**Insights:**
- Total spending: $X
- Highest spending day: Monday with $Y
- Average daily spending: $Z
```

## How ClaudeSDKClient Simplifies Implementation

The Claude Agent SDK's `ClaudeSDKClient` class handles many complex aspects automatically:

### What ClaudeSDKClient Does For Us

1. **Automatic Context Management**
   - Maintains full conversation history internally
   - No need to manually track messages or build context windows
   - Each `query()` call automatically includes all previous context
   - Context persists for the lifetime of the client instance

2. **Tool Registration & Execution**
   - Tools defined with `@tool` decorator are automatically registered
   - Claude decides when to call tools based on user query
   - Tool results are automatically fed back to Claude
   - Multi-step tool usage (Claude can call multiple tools in sequence)

3. **Streaming Built-In**
   - `receive_response()` returns async iterator for streaming
   - Handles both text streaming and tool execution events
   - We just iterate and display - SDK handles all the protocol details

4. **Session Management**
   - Context manager pattern (`async with ClaudeSDKClient()`) handles connection lifecycle
   - Automatic cleanup on session end
   - Can interrupt long-running operations with `interrupt()`

### What We Need to Implement

1. **Tool Functions**
   - Define `@tool` decorated functions for DuckDB queries and YouPlot charts
   - Ensure tools use read-only DuckDB connections
   - Return structured data that Claude can work with

2. **Response Formatting**
   - Receive streamed chunks from SDK
   - Format for terminal display (Rich tables, syntax highlighting)
   - Handle different message types (text, tool_use, tool_result)

3. **Session Lifecycle in CLI**
   - When to create new client (start of conversation)
   - When to reuse client (follow-up questions)
   - When to end session (`/clear` command or inactivity)

4. **System Prompt**
   - Define the agent's behavior and constraints
   - Inject schema information dynamically
   - Provide response format templates

### Implementation Pattern

```python
# Creating a session
async with ClaudeSDKClient(
    api_key=api_key,
    system_prompt=build_system_prompt(schema_info),
    allowed_tools=[execute_sql_query, create_terminal_chart, get_schema_info]
) as client:

    # First query
    await client.query("Show my spending last week")

    # Stream response
    async for chunk in client.receive_response():
        if chunk.type == "text":
            console.print(chunk.content)
        elif chunk.type == "tool_use":
            console.print(f"[dim]Executing {chunk.tool_name}...[/dim]")
        elif chunk.type == "tool_result":
            display_result(chunk.result)

    # Follow-up question - SDK automatically includes context
    await client.query("Why was it so high?")

    async for chunk in client.receive_response():
        # Display response (same as above)
        ...

# Session ends when exiting context manager
```

**Key Insight:** We don't need to manage conversation history ourselves! ClaudeSDKClient does it all. Our code is much simpler because we just:
1. Define tools
2. Send queries
3. Display responses

## Conversational Context Management

### Session Lifecycle

```python
# In AgentService
class AgentService:
    def __init__(self, api_key: str, db_path: str):
        self.api_key = api_key
        self.db_path = db_path
        self.active_client: ClaudeSDKClient | None = None
        self.session_started: datetime | None = None

    async def ensure_session_active(self):
        """Start session if needed or check for timeout."""
        if self.active_client is None:
            await self.start_session()
        elif self._is_session_expired():
            await self.end_session()
            await self.start_session()

    async def start_session(self):
        """Create new ClaudeSDKClient - starts fresh conversation."""
        self.active_client = ClaudeSDKClient(
            api_key=self.api_key,
            system_prompt=self._build_system_prompt(),
            allowed_tools=[
                execute_sql_query,
                create_terminal_chart,
                get_schema_info,
                get_date_range_info
            ]
        )
        await self.active_client.connect()
        self.session_started = datetime.now()

    async def chat(self, message: str) -> AsyncIterator[StreamChunk]:
        """Send message and stream response."""
        await self.ensure_session_active()

        # Query - ClaudeSDKClient handles context automatically
        await self.active_client.query(message)

        # Stream response
        async for chunk in self.active_client.receive_response():
            yield chunk

    async def end_session(self):
        """End current session and clear state."""
        if self.active_client:
            await self.active_client.disconnect()
            self.active_client = None
            self.session_started = None

    def _is_session_expired(self) -> bool:
        """Check if session has been idle too long."""
        if not self.session_started:
            return False
        return (datetime.now() - self.session_started) > timedelta(minutes=30)
```

### Context Retention Strategy

**ClaudeSDKClient Handles:**
- ✅ Full conversation history (user messages + assistant responses)
- ✅ Tool calls and their results
- ✅ Multi-turn context (follow-up questions work automatically)
- ✅ Conversation threading (knows what "it" and "that" refer to)

**We Handle:**
- 🔧 Session timeout (30 minute idle timeout)
- 🔧 Explicit session reset (`/clear` command)
- 🔧 Session state in CLI (one session per conversation)

**No Need To:**
- ❌ Manually build message history
- ❌ Truncate context (Claude handles token limits)
- ❌ Track previous queries (SDK does it)
- ❌ Manage tool execution history (SDK does it)

**Session Reset Triggers:**
- User explicitly runs `/clear` or `/new`
- 30 minutes of inactivity
- CLI session ends (user exits)

**Key Simplification:** Because ClaudeSDKClient manages context internally, our code is dramatically simpler. We just create a client, send messages, and the SDK ensures each message has full conversational context.

## Streaming UX

For a CLI tool, streaming is important for perceived responsiveness:

```python
async def display_agent_response_streaming(
    response_stream: AsyncIterator[StreamChunk]
):
    """Display agent response as it streams."""

    with Live(console=console, refresh_per_second=4) as live:
        current_text = ""

        async for chunk in response_stream:
            if chunk.type == "text":
                current_text += chunk.content
                live.update(Markdown(current_text))

            elif chunk.type == "tool_use":
                # Show "Thinking..." indicator
                live.update(f"[dim]Executing: {chunk.tool_name}...[/dim]")

            elif chunk.type == "tool_result":
                # Show result immediately
                display_tool_result(chunk.result)
```

## Error Handling

### SQL Errors
```python
# Agent tries invalid SQL
tool_result = {
    "success": False,
    "error": "SQL syntax error: column 'speding' does not exist. Did you mean 'spending'?",
    "suggestion": "Check the schema using get_schema_info()"
}
```

Agent should be able to:
1. Recognize the error
2. Correct the query
3. Retry automatically

### Empty Results
```python
# Query returns no rows
tool_result = {
    "success": True,
    "rows": [],
    "message": "Query executed successfully but returned no results"
}
```

Agent should:
1. Acknowledge no data found
2. Suggest reasons (date range, filters, etc.)
3. Offer to try different query

### YouPlot Failures
```python
# Chart creation fails
tool_result = {
    "success": False,
    "error": "Cannot create chart: x_column 'date' not found in results",
    "available_columns": ["transaction_date", "amount"]
}
```

Agent should:
1. Recognize column name mismatch
2. Retry with correct column name
3. Or explain why chart can't be created

## Example User Journeys

### Journey 1: Weekly Overview
```
User: "Can you provide an overview of my last week?"

Agent: **Weekly Financial Overview**

**Analysis:** Here's a comprehensive look at your finances over the past 7 days.

**Spending Breakdown:**
```sql
SELECT
  UNNEST(tags) as tag,
  SUM(ABS(amount)) as total,
  COUNT(*) as transactions
FROM transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '7 days'
  AND amount < 0
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
```

[Table showing top spending categories]

**Spending Trend:**
[Line chart showing daily spending]

**Key Insights:**
- Total spending: $1,247.32 (up 12% from previous week)
- Largest category: Groceries ($342.18)
- Unusual spike on Thursday ($287.50)

---

User: "Whoa, my spending was more than expected. Can you identify why?"

Agent: **Spending Increase Analysis**

Let me compare this week to your typical spending patterns.

**Anomaly Detection:**
```sql
WITH weekly_avg AS (
  SELECT AVG(weekly_total) as avg_spending
  FROM (
    SELECT
      DATE_TRUNC('week', transaction_date) as week,
      SUM(ABS(amount)) as weekly_total
    FROM transactions
    WHERE amount < 0
      AND transaction_date >= CURRENT_DATE - INTERVAL '12 weeks'
    GROUP BY 1
  )
)
SELECT
  DATE_TRUNC('day', t.transaction_date) as date,
  SUM(ABS(t.amount)) as daily_total,
  w.avg_spending / 7 as typical_daily
FROM transactions t
CROSS JOIN weekly_avg w
WHERE t.transaction_date >= CURRENT_DATE - INTERVAL '7 days'
  AND t.amount < 0
GROUP BY 1, 2
ORDER BY 1;
```

[Chart comparing this week vs typical]

**Unusual Transactions:**
- Thursday: $287.50 at "Electronics Mega Store" (3x your typical purchase)
- Weekend dining: $156.32 total (usually ~$80)

**Root Causes:**
1. One-time large purchase (electronics) = $287.50 extra
2. Increased dining out = $76.32 extra
3. Total excess: ~$363.82 above typical week
```

### Journey 2: Trend Analysis
```
User: "Show me my net worth trend over the last 3 months"

Agent: **Net Worth Analysis - Last 90 Days**

**Query Used:**
```sql
WITH daily_balances AS (
  SELECT
    DATE_TRUNC('day', snapshot_time) as date,
    SUM(balance) as total_balance
  FROM balance_snapshots
  WHERE snapshot_time >= CURRENT_DATE - INTERVAL '90 days'
  GROUP BY 1
)
SELECT
  date,
  total_balance,
  total_balance - LAG(total_balance) OVER (ORDER BY date) as daily_change
FROM daily_balances
ORDER BY date;
```

[Line chart showing net worth over time]

**Summary:**
- Starting balance (90 days ago): $24,532.18
- Current balance: $27,891.45
- Total change: +$3,359.27 (+13.7%)
- Trend: Generally increasing with some volatility

**Notable Events:**
- Sharp drop on July 15th (-$2,100) - large transaction?
- Steady climb since August 1st
- Best single day: Aug 23rd (+$1,847.32)
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create AIProvider abstraction
- [ ] Implement ClaudeAgentProvider using Agent SDK
- [ ] Create AgentService in app layer
- [ ] Build basic tool: execute_sql_query
- [ ] Design and implement system prompt
- [ ] Add /chat command to CLI (or just handle non-slash input)

**Goal:** Get basic Q&A working without charts

### Phase 2: Visualization (Week 2)
- [ ] Integrate YouPlot with DuckDB
- [ ] Create create_terminal_chart tool
- [ ] Test various chart types (line, bar, histogram)
- [ ] Add chart display formatting in CLI
- [ ] Handle YouPlot errors gracefully

**Goal:** Agent can create visualizations

### Phase 3: Context & Streaming (Week 3)
- [ ] Implement conversation history management
- [ ] Add streaming response display
- [ ] Create session management (/clear, /new commands)
- [ ] Optimize context truncation strategy
- [ ] Add "thinking" indicators for tool execution

**Goal:** Smooth conversational experience

### Phase 4: Polish & Intelligence (Week 4)
- [ ] Add get_schema_info tool
- [ ] Add get_date_range_info tool
- [ ] Refine system prompt based on testing
- [ ] Add common analysis templates to prompt
- [ ] Handle edge cases and errors elegantly
- [ ] Write comprehensive tests

**Goal:** Production-ready agent

## Testing Strategy

### Unit Tests
```python
# Test tool execution in isolation
async def test_execute_sql_query_valid():
    result = await execute_sql_query(
        "SELECT COUNT(*) FROM transactions",
        "Count total transactions"
    )
    assert result["success"] is True
    assert "rows" in result

# Test agent service with mock AI provider
async def test_agent_service_maintains_context():
    mock_ai = MockAIProvider()
    service = AgentService(mock_ai, mock_repo, mock_config)

    await service.chat(user_id, "Show my spending")
    await service.chat(user_id, "Why is it so high?")

    # Second message should have context from first
    assert len(mock_ai.messages_sent) == 2
    assert "spending" in mock_ai.messages_sent[1].context
```

### Integration Tests
```python
# Test full flow with real Claude API (using test account)
async def test_agent_end_to_end():
    agent_service = container.agent_service()

    # Seed test database with known data
    await seed_test_transactions()

    # Ask question
    result = await agent_service.chat(
        test_user_id,
        "What was my total spending last week?"
    )

    # Verify response contains expected elements
    assert "SELECT" in result.sql_shown
    assert result.insights is not None
```

### Manual Testing Scenarios
1. **New User Journey**: Empty database, agent handles gracefully
2. **Complex Analysis**: Multi-turn conversation about spending patterns
3. **Error Recovery**: Invalid SQL, agent corrects and retries
4. **Visualization**: Charts render correctly in terminal
5. **Context Limits**: Very long conversation, context pruning works

## Security & Safety

### SQL Injection Prevention
```python
# Tool validates SQL is read-only
def validate_sql_readonly(sql: str) -> bool:
    """Ensure SQL only contains SELECT/WITH statements."""
    # Parse SQL AST
    # Reject any DML (INSERT, UPDATE, DELETE)
    # Reject any DDL (CREATE, ALTER, DROP)
    # Allow only SELECT, WITH, UNION, etc.
```

### Rate Limiting
```python
# Prevent abuse of AI API
class AgentService:
    async def chat(self, user_id, message):
        # Check rate limit
        if not await self.rate_limiter.check(user_id):
            return Result(
                success=False,
                error="Rate limit exceeded. Please wait before next query."
            )
```

### Cost Control
```python
# Track token usage per user
class AgentService:
    async def chat(self, user_id, message):
        # Log token usage
        await self.usage_tracker.record(
            user_id=user_id,
            input_tokens=tokens_in,
            output_tokens=tokens_out,
            cost=estimated_cost
        )
```

## Decisions Made

### 1. ~~Context Window Management~~
✅ **RESOLVED** - ClaudeSDKClient handles this automatically. We just manage session lifecycle (30 min timeout).

### 2. Prompt Caching
✅ **YES - Enable from Day 1**

**What is it?** Claude can cache portions of the system prompt to save costs:
- Cache writes: 25% more expensive than regular tokens
- Cache reads: 90% cheaper than regular tokens
- TTL: 5 minutes (auto-refreshed on use)
- Minimum: 1024-2048 tokens (our system prompt will exceed this)

**Our System Prompt:**
```
Base prompt: ~500 tokens
+ Schema info: ~1500 tokens
+ Examples: ~500 tokens
= ~2500 tokens total
```

**Cost Analysis:**
```
Without caching (per request):
- System prompt: 2500 tokens × $0.003/1k = $0.0075

With caching (after first request):
- First request: 2500 tokens × $0.00375/1k = $0.009375 (25% more)
- Subsequent requests: 2500 tokens × $0.0003/1k = $0.00075 (90% savings)

Breakeven: After 2nd message
Savings: ~90% on prompt tokens for active conversations
```

**Implementation:**
```python
# Mark schema portion of system prompt as cacheable
system_prompt = [
    {
        "type": "text",
        "text": base_instructions,
    },
    {
        "type": "text",
        "text": schema_info,
        "cache_control": {"type": "ephemeral"}  # Cache this!
    }
]
```

**Decision:** This is a no-brainer. Use prompt caching with 5-minute TTL.

### 3. ~~Multi-User Sessions~~
✅ **NOT AN ISSUE** - Each user has separate DuckDB file, so no session isolation needed.

Each user's Treeline instance is independent:
- User A: `/Users/alice/projects/finances/treeline/treeline.db`
- User B: `/Users/bob/money/treeline/treeline.db`

No shared state, no isolation needed.

### 4. Error Retry Logic
✅ **ALLOW SELF-CORRECTION WITH CAPS**

Agent can see SQL errors and retry, but we'll cap it:

**Strategy:**
```python
class AgentService:
    MAX_TOOL_RETRIES = 3  # Prevent infinite loops

    async def chat(self, message: str):
        tool_call_count = 0

        async for chunk in self.active_client.receive_response():
            if chunk.type == "tool_use":
                tool_call_count += 1

                if tool_call_count > self.MAX_TOOL_RETRIES:
                    # Force stop and explain
                    await self.active_client.interrupt()
                    yield ErrorChunk(
                        "I'm having trouble with this query. "
                        "The error was: [last error]. "
                        "Would you like to try a different question?"
                    )
                    break

            yield chunk
```

**Behavior:**
1. Agent tries query → fails with SQL error
2. Agent sees error, corrects SQL, tries again → fails again
3. Agent tries one more time → fails
4. We interrupt and ask user for help

**Why 3 attempts?**
- 1st attempt: Original try
- 2nd attempt: Self-correction (typo fix, column name correction)
- 3rd attempt: Different approach or deeper fix
- After 3: Something is fundamentally wrong, involve user

### 5. Offline Mode (V2)
**Decision:** Not for MVP. Focus on Claude first, add ollama support later.

### 6. Proactive Insights (V2)
**Decision:** Not for MVP. Could be added as opt-in feature later.

## Success Metrics

**Technical:**
- Average response time < 3 seconds for simple queries
- SQL query success rate > 95%
- Chart generation success rate > 90%
- Context retention accuracy (follow-up questions work)

**User Experience:**
- Users can get insights without writing SQL
- Iterative analysis feels natural (multi-turn works)
- Visualizations add value beyond text
- "Show your work" builds trust

**Business:**
- AI feature drives conversion from free to paid
- Users engage with AI regularly (measure usage)
- Low support burden from AI errors
