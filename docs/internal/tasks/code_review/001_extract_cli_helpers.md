# Task 001: Extract CLI Helper Functions

## Status
🔴 Not Started

## Priority
**HIGH** - Affects 6+ files, significant code duplication

## Problem
Helper functions (`get_container()`, `is_authenticated()`, `require_auth()`, etc.) are duplicated across multiple files:

### Affected Files:
1. `src/treeline/cli.py` - Lines 88-96, 99-104
2. `src/treeline/commands/analysis_textual.py` - Lines 12-18
3. `src/treeline/commands/queries_browser_textual.py` - Lines 23-27
4. `src/treeline/commands/charts_browser_textual.py` - Lines 23-27
5. `src/treeline/commands/tag_textual.py` - Lines 13-19
6. `src/treeline/commands/tags_browser_textual.py` - Lines 13-19

### Duplicated Code:
```python
def get_container() -> Container:
    """Get the application container."""
    from treeline.app.container import get_container as _get_container
    return _get_container()

def is_authenticated() -> bool:
    """Check if user is authenticated."""
    container = get_container()
    config_service = container.config_service()
    return config_service.is_authenticated()

def require_auth() -> None:
    """Check authentication and exit if not authenticated."""
    if not is_authenticated():
        console.print("[red]Error: Not authenticated[/red]")
        console.print("Run 'treeline login' first")
        raise typer.Exit(1)
```

## Architectural Principle
**DRY (Don't Repeat Yourself)** - Common utilities should be centralized to avoid maintenance burden and inconsistencies.

## Solution
1. Create new file: `src/treeline/cli_helpers.py`
2. Move all shared helper functions to this file:
   - `get_container()`
   - `is_authenticated()`
   - `require_auth()`
3. Update all 6 affected files to import from `cli_helpers.py`
4. Run tests to ensure no regressions

## Implementation Steps
1. Create `src/treeline/cli_helpers.py` with consolidated functions
2. Update imports in `cli.py`
3. Update imports in `commands/analysis_textual.py`
4. Update imports in `commands/queries_browser_textual.py`
5. Update imports in `commands/charts_browser_textual.py`
6. Update imports in `commands/tag_textual.py`
7. Update imports in `commands/tags_browser_textual.py`
8. Run unit tests: `uv run pytest tests/unit`
9. Run smoke tests: `uv run pytest tests/smoke`

## Acceptance Criteria
- [ ] All helper functions consolidated in `cli_helpers.py`
- [ ] All 6 files import from shared module
- [ ] No duplicated helper functions remain
- [ ] All tests pass
- [ ] Code follows project style (ruff formatted)

## Estimated Impact
- **Files Modified**: 7 (1 new, 6 updated)
- **Lines Reduced**: ~60-70 lines of duplication removed
- **Test Risk**: Low (simple refactoring, no logic changes)
