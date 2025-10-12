# Reorganize Abstractions into Directory Structure

## Priority
**MAJOR** - Organizational inconsistency with documented architecture

## Violation
The abstractions are in a single file (`src/treeline/abstractions.py`) instead of organized in a directory structure as specified in `architecture.md`.

**Status:** Confirmed present in second review (2025-10-11)

**Current Structure:**
```
src/treeline/
    abstractions.py  # Single file with all abstractions
```

**Expected Structure (per architecture.md lines 48-54):**
```
src/treeline/
    abstractions/
        __init__.py
        auth.py       # AuthProvider
        db.py         # Repository, DatabaseConnection
        ai.py         # AIProvider
        data.py       # DataAggregationProvider, IntegrationProvider
        config.py     # CredentialStore
        tagging.py    # TagSuggester
```

## Why It Matters
While this doesn't break hexagonal architecture functionally, it:
1. Violates the documented architecture structure
2. Makes the codebase harder to navigate as it grows
3. Creates inconsistency between docs and implementation
4. Will become unwieldy as more abstractions are added

## Fix Approach

1. **Create abstractions directory structure:**
   ```bash
   mkdir -p src/treeline/abstractions
   ```

2. **Split abstractions.py into separate files:**
   - **auth.py:** Move `AuthProvider` class
   - **db.py:** Move `Repository` and `DatabaseConnection` classes
   - **ai.py:** Move `AIProvider` class
   - **data.py:** Move `DataAggregationProvider` and `IntegrationProvider` classes
   - **config.py:** Move `CredentialStore` class
   - **tagging.py:** Move `TagSuggester` class

3. **Create abstractions/__init__.py:**
   ```python
   from treeline.abstractions.auth import AuthProvider
   from treeline.abstractions.db import Repository, DatabaseConnection
   from treeline.abstractions.ai import AIProvider
   from treeline.abstractions.data import DataAggregationProvider, IntegrationProvider
   from treeline.abstractions.config import CredentialStore
   from treeline.abstractions.tagging import TagSuggester

   __all__ = [
       "AuthProvider",
       "Repository",
       "DatabaseConnection",
       "AIProvider",
       "DataAggregationProvider",
       "IntegrationProvider",
       "CredentialStore",
       "TagSuggester",
   ]
   ```

4. **Update all imports throughout codebase:**
   - All existing `from treeline.abstractions import X` should continue to work
   - Verify imports in: cli.py, commands/, app/, infra/
   - Run tests to ensure nothing breaks

5. **Delete old abstractions.py file**

## Files to Create
- `src/treeline/abstractions/__init__.py`
- `src/treeline/abstractions/auth.py`
- `src/treeline/abstractions/db.py`
- `src/treeline/abstractions/ai.py`
- `src/treeline/abstractions/data.py`
- `src/treeline/abstractions/config.py`
- `src/treeline/abstractions/tagging.py`

## Files to Modify
- All files that import from `treeline.abstractions` (should work without changes due to __init__.py)
- Verify: `src/treeline/app/`, `src/treeline/infra/`, `src/treeline/commands/`, `src/treeline/cli.py`

## Files to Delete
- `src/treeline/abstractions.py`

## Success Criteria
- [ ] Abstractions organized into directory structure matching architecture.md
- [ ] All imports continue to work (backward compatible)
- [ ] All unit tests pass
- [ ] All smoke tests pass
- [ ] No functionality changed, purely organizational

## Notes
- This is the lowest priority task since it's organizational, not functional
- Should be done LAST after all critical architecture fixes
- The `__init__.py` provides backward compatibility so existing imports don't break
- This sets up better structure for future abstraction additions
