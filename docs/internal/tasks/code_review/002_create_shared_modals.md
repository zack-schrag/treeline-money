# Task 002: Create Shared Modal Components

## Status
🔴 Not Started

## Priority
**MEDIUM** - Code duplication affecting 2 files, but isolated impact

## Problem
The `RenameModal` class is duplicated identically in two browser implementations:

### Affected Files:
1. `src/treeline/commands/queries_browser_textual.py` - Lines 34-77
2. `src/treeline/commands/charts_browser_textual.py` - Lines 34-77

### Duplicated Code:
```python
class RenameModal(Screen):
    """Modal dialog for renaming items."""
    # ~40 lines of identical code
```

## Architectural Principle
**DRY (Don't Repeat Yourself)** - Shared UI components should be centralized for consistency and maintainability.

## Solution
1. Create new file: `src/treeline/commands/shared_components.py`
2. Move `RenameModal` class to this shared module
3. Update both browser files to import from shared module
4. Consider extracting other common components in future

## Implementation Steps
1. Create `src/treeline/commands/shared_components.py`
2. Move `RenameModal` class definition to shared file
3. Add appropriate docstring and type hints
4. Update `queries_browser_textual.py` to import `RenameModal`
5. Update `charts_browser_textual.py` to import `RenameModal`
6. Test both browsers to ensure modal works correctly
7. Run unit tests: `uv run pytest tests/unit`
8. Run smoke tests: `uv run pytest tests/smoke`

## Acceptance Criteria
- [ ] `RenameModal` extracted to `shared_components.py`
- [ ] Both browser files import from shared module
- [ ] No duplicated modal code remains
- [ ] Queries browser rename functionality works
- [ ] Charts browser rename functionality works
- [ ] All tests pass
- [ ] Code follows project style (ruff formatted)

## Future Considerations
Other potential shared components to extract later:
- Common dialog patterns
- Shared key bindings
- Reusable widgets

## Estimated Impact
- **Files Modified**: 3 (1 new, 2 updated)
- **Lines Reduced**: ~40 lines of duplication removed
- **Test Risk**: Low (simple refactoring, no logic changes)
