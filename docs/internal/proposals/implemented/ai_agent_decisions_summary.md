# AI Agent - Key Decisions Summary

Quick reference for major implementation decisions.

## Architecture

### Claude Agent SDK (ClaudeSDKClient)
- ✅ Handles conversation context automatically
- ✅ Built-in tool execution with `@tool` decorator
- ✅ Native streaming support
- ✅ Session lifecycle management
- **Result:** Much simpler implementation than manual context tracking

### Read-Only DuckDB Access
```python
conn = duckdb.connect(db_path, read_only=True)
```
- 🔒 Agent CANNOT modify user data
- 🔒 Enforced at database level (no SQL parsing needed)
- 🔒 Safe even if agent is compromised

### Implementation Location
- File: `src/treeline/infra/anthropic.py`
- Class: `AnthropicProvider`
- Uses existing empty file

## Cost Optimization

### Prompt Caching - YES ✅
**Savings:** ~90% on prompt tokens after first message

**Math:**
- System prompt: ~2500 tokens (base + schema + examples)
- First message: +25% cost ($0.009375)
- Subsequent: -90% cost ($0.00075)
- **Breakeven:** 2nd message
- **TTL:** 5 minutes (auto-refreshed on use)

**Implementation:**
```python
system_prompt = [
    {"type": "text", "text": base_instructions},
    {
        "type": "text",
        "text": schema_info,
        "cache_control": {"type": "ephemeral"}  # Cache this!
    }
]
```

## Session Management

### Multi-User
- ❌ **NOT AN ISSUE** - Each user has separate DuckDB file
- No session isolation needed
- Each Treeline instance is independent

### Session Timeout
- ⏱️ **30 minutes** of inactivity
- User can reset with `/clear` or `/new`
- ClaudeSDKClient maintains context for session lifetime

## Error Handling

### Retry Logic - Capped at 3 Attempts ✅

**Strategy:**
1. **1st attempt:** Original query
2. **2nd attempt:** Self-correction (fix typo, column name, etc.)
3. **3rd attempt:** Different approach or deeper fix
4. **After 3:** Interrupt and ask user for help

**Why cap it?**
- Prevent agent from "going off the deep end"
- After 3 tries, something is fundamentally wrong
- Better to involve user than waste tokens/time

**Implementation:**
```python
class AgentService:
    MAX_TOOL_RETRIES = 3

    async def chat(self, message: str):
        tool_call_count = 0

        async for chunk in self.active_client.receive_response():
            if chunk.type == "tool_use":
                tool_call_count += 1
                if tool_call_count > self.MAX_TOOL_RETRIES:
                    await self.active_client.interrupt()
                    yield error_message
                    break
```

## Future Considerations (V2)

### Not for MVP
- ❌ Offline mode (ollama support)
- ❌ Proactive insights (unsolicited notifications)
- ❌ Multi-user session isolation (not needed)

### Consider Later
- 💡 Prompt caching with 1-hour TTL (currently using 5-min)
- 💡 Local model support for privacy-conscious users
- 💡 Opt-in proactive insights ("Your spending increased 30%")

## Quick Reference

| Feature | Decision | Rationale |
|---------|----------|-----------|
| Context Management | ClaudeSDKClient handles | Automatic, no manual tracking |
| DuckDB Access | Read-only | Safety & security |
| Prompt Caching | Yes, 5-min TTL | 90% cost savings after msg 2 |
| Multi-user | No special handling | Separate DB files |
| Retry Cap | 3 attempts max | Prevent infinite loops |
| Offline Mode | V2 | Focus on Claude first |
| Proactive Insights | V2 | MVP = user-initiated only |

## Implementation Phases

**Week 1: Foundation**
- [ ] AnthropicProvider with ClaudeSDKClient
- [ ] execute_sql_query tool (read-only)
- [ ] System prompt with schema info
- [ ] Basic chat without charts

**Week 2: Visualization**
- [ ] create_terminal_chart tool
- [ ] YouPlot integration
- [ ] Chart display formatting

**Week 3: Context & Streaming**
- [ ] Session management (30min timeout)
- [ ] Streaming display with Live
- [ ] /clear and /new commands

**Week 4: Polish**
- [ ] Prompt caching implementation
- [ ] Retry cap (3 attempts)
- [ ] Error handling edge cases
- [ ] Comprehensive tests
