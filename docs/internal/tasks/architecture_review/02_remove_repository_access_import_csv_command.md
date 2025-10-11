# Remove Direct Repository Access from CSV Import Command

## Priority
**CRITICAL** - Breaks hexagonal architecture core principle

## Violation
The import CSV command (`src/treeline/commands/import_csv.py`) directly accesses the Repository abstraction, bypassing the Service layer.

**Location:** `src/treeline/commands/import_csv.py:52, 79`

**Current Code:**
```python
# Line 52
repository = container.repository()

# Line 79
accounts_result = asyncio.run(repository.get_accounts(UUID(user_id)))
```

## Why It's Wrong
According to `CLAUDE.md`:
> "The CLI MUST ONLY interact with services from `src/treeline/app/service.py`"
> "The CLI MUST NEVER directly call repositories, providers, or any other abstractions"

The CLI is directly calling `repository.get_accounts()` which bypasses the service layer.

## Fix Approach

1. **Use the AccountService created in task 01:**
   - Assumes task 01 has created an `AccountService` or added `get_accounts()` to an existing service

2. **Update import_csv command:**
   - Remove line 52: `repository = container.repository()`
   - Replace with: `account_service = container.account_service()`
   - Replace `repository.get_accounts(UUID(user_id))` with `account_service.get_accounts(UUID(user_id))`

3. **Update tests:**
   - Update test mocks to mock service layer instead of repository

## Dependencies
- **Depends on:** Task 01 (creating AccountService.get_accounts method)

## Files to Modify
- `src/treeline/commands/import_csv.py` - Remove repository access
- `tests/unit/commands/test_import_csv.py` - Update test mocks if needed

## Success Criteria
- [ ] Import CSV command no longer imports or uses `container.repository()`
- [ ] All account access goes through service layer
- [ ] Unit tests pass
- [ ] Command functionality unchanged
