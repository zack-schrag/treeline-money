# Remove Direct Repository Access from Tag Command

## Priority
**CRITICAL** - Breaks hexagonal architecture core principle

## Violation
The tag command (`src/treeline/commands/tag.py`) directly accesses the Repository abstraction, bypassing the Service layer.

**Location:** `src/treeline/commands/tag.py:51, 71`

**Current Code:**
```python
# Line 51
repository = container.repository()

# Line 71
accounts_result = asyncio.run(repository.get_accounts(UUID(user_id)))
```

**Status:** Confirmed present in second review (2025-10-11)

## Why It's Wrong
According to `CLAUDE.md`:
> "The CLI MUST ONLY interact with services from `src/treeline/app/service.py`"
> "The CLI MUST NEVER directly call repositories, providers, or any other abstractions"

The CLI is directly calling `repository.get_accounts()` which bypasses the service layer entirely. This violates dependency flow and creates tight coupling between CLI and data access.

## Fix Approach

1. **Add `get_accounts()` method to Service layer:**
   - Create an `AccountService` or add to existing `StatusService`
   - Method signature: `async def get_accounts(self, user_id: UUID) -> Result[List[Account], Error]`
   - This method internally calls `self.repository.get_accounts(user_id)`

2. **Update Container to provide account service:**
   - Add `account_service()` method to `Container` class

3. **Update tag command to use service:**
   - Replace `repository = container.repository()` with `account_service = container.account_service()`
   - Replace `repository.get_accounts(UUID(user_id))` with `account_service.get_accounts(UUID(user_id))`

4. **Update tests:**
   - Ensure unit tests mock the service layer, not the repository directly

## Files to Modify
- `src/treeline/commands/tag.py` - Remove repository access
- `src/treeline/app/service.py` - Add get_accounts method
- `src/treeline/app/container.py` - Add account_service method
- `tests/unit/commands/test_tag.py` - Update test mocks if needed

## Success Criteria
- [ ] Tag command no longer imports or uses `container.repository()`
- [ ] All account access goes through service layer
- [ ] Unit tests pass
- [ ] Command functionality unchanged
