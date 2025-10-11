# Fix is_session_expired Leaky Abstraction

## Priority
**MAJOR** - Leaky abstraction, contained to service layer

## Violation
`AgentService.ensure_session_active()` calls `is_session_expired()` method that is NOT defined in the `AIProvider` abstraction.

**Location:** `src/treeline/app/service.py:651`

**Current Code:**
```python
# Line 651 in AgentService.ensure_session_active()
if self.ai_provider.is_session_expired():
    await self.ai_provider.end_session()
    return await self.ai_provider.start_session(user_id, db_path)
```

## Why It's Wrong
The `AIProvider` abstraction (`src/treeline/abstractions.py:271-319`) only defines:
- `start_session()`
- `send_message()`
- `end_session()`
- `has_active_session()`

The method `is_session_expired()` exists only in the Anthropic implementation, leaking through the abstraction boundary. The service layer should only call methods defined in the abstraction.

## Fix Approach

### Option A: Remove is_session_expired usage (RECOMMENDED)
Session expiration should be handled internally by the provider implementation.

1. **Update `ensure_session_active()` logic:**
   ```python
   async def ensure_session_active(self, user_id: UUID, db_path: str):
       if not self.ai_provider.has_active_session():
           return await self.ai_provider.start_session(user_id, db_path)
       return Ok(None)
   ```

2. **Update `AnthropicAIProvider.send_message()`:**
   - Before sending message, check if session is expired
   - If expired, automatically end session and raise appropriate error
   - Let caller handle re-establishing session

3. **Update `AnthropicAIProvider.has_active_session()`:**
   - Return False if session exists but is expired
   - This makes the abstraction method accurate

### Option B: Add to AIProvider abstraction
If session expiration is a general concept all AI providers need:

1. Add `is_session_expired()` to `AIProvider` abstract class
2. Implement in all providers (return False for providers without expiration)

**RECOMMENDATION:** Use Option A. Session expiration is implementation-specific. The abstraction's `has_active_session()` should return False for expired sessions, making `is_session_expired()` unnecessary.

## Files to Modify
- `src/treeline/app/service.py` - Update ensure_session_active()
- `src/treeline/infra/anthropic.py` - Update has_active_session() and send_message()
- `tests/unit/app/test_service.py` - Update AgentService tests
- `tests/unit/infra/test_anthropic.py` - Add tests for expiration handling

## Success Criteria
- [ ] AgentService only calls methods defined in AIProvider abstraction
- [ ] No calls to `is_session_expired()` in service layer
- [ ] Session expiration handled internally by provider
- [ ] Unit tests pass
- [ ] Agent functionality unchanged

## Notes
This is a more minor issue than the CLI violations, but important for maintaining clean abstractions. The fix makes the code more maintainable by keeping implementation details inside the provider.
