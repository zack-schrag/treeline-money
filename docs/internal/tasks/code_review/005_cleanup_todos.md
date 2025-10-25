# Task 005: Clean Up Incomplete TODOs and Error Handling

## Status
🔴 Not Started

## Priority
**LOW** - Minor issues, no architectural impact

## Problem
Several files have incomplete TODO comments or questionable error handling:

### Issues Found:

#### 1. tui_theme.py - Incomplete Exception Handling
**File**: `src/treeline/commands/tui_theme.py` (Lines ~30-35)
```python
try:
    theme = BUILTIN_THEMES[theme_name]
except KeyError:
    pass  # TODO: what should happen here?
```
**Issue**: Exception caught but no fallback behavior

#### 2. Potential Other TODOs
Need to search codebase for:
- `TODO` comments that are incomplete
- `FIXME` comments
- `HACK` comments
- Empty `except` blocks

## Architectural Principle
**Robustness & Error Handling** - All error conditions should be handled appropriately with clear behavior.

## Solution

### For tui_theme.py:
Either:
1. **Option A**: Provide a default theme fallback
2. **Option B**: Raise a clear error message
3. **Option C**: Log the error and continue with default

**Recommended**: Option A - fallback to a default theme

### For Other TODOs:
1. Search for all TODO/FIXME/HACK comments
2. Categorize by severity
3. Either fix or document why they're acceptable

## Implementation Steps
1. Fix tui_theme.py exception handling
2. Search for all TODO comments: `grep -r "TODO" src/`
3. Search for FIXME comments: `grep -r "FIXME" src/`
4. Search for HACK comments: `grep -r "HACK" src/`
5. Review each finding:
   - Fix if trivial
   - Create separate task if complex
   - Document if acceptable as-is
6. Run unit tests: `uv run pytest tests/unit`
7. Run smoke tests: `uv run pytest tests/smoke`

## Acceptance Criteria
- [ ] tui_theme.py has proper error handling
- [ ] All TODO comments reviewed and categorized
- [ ] Trivial TODOs resolved
- [ ] Complex TODOs converted to proper issues/tasks
- [ ] All tests pass
- [ ] Code follows project style (ruff formatted)

## Example Fix for tui_theme.py:
```python
try:
    theme = BUILTIN_THEMES[theme_name]
except KeyError:
    # Fallback to default monokai theme if requested theme not found
    theme = BUILTIN_THEMES["monokai"]
    logger.warning(f"Theme '{theme_name}' not found, using default 'monokai'")
```

## Estimated Impact
- **Files Modified**: 1-3 files (depending on TODO findings)
- **Lines Changed**: ~5-20 lines
- **Test Risk**: Very Low (minor fixes only)

## Notes
- This is a cleanup task, not urgent
- Good candidate for end of power session
- May discover other minor issues to address
