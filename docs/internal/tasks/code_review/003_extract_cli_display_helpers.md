# Task 003: Extract CLI Display Helper Functions

## Status
🔴 Not Started

## Priority
**MEDIUM** - Reduces CLI file size, improves organization

## Problem
The `cli.py` file is 1540 lines long. While much of this is appropriate (command definitions), there are display helper functions that could be extracted:

### Functions to Extract:
1. `_format_transaction_table()` - Lines ~470-500 (approx)
2. `_format_account_table()` - Lines ~550-580 (approx)
3. `_format_balance_display()` - Related formatting logic
4. `_print_sync_summary()` - Sync result formatting
5. Other `_format_*` and `_print_*` helper methods

### Current State:
- CLI file: 1540 lines
- Multiple private helper methods for formatting/display
- These are presentation-layer helpers (appropriate for CLI)
- But could be organized separately for clarity

## Architectural Principle
**Single Responsibility & Organization** - While these helpers are appropriate for the presentation layer, extracting them to a separate module improves readability and maintainability.

## Solution
1. Create new file: `src/treeline/cli_display.py`
2. Move all `_format_*` and `_print_*` helper methods
3. Update `cli.py` to import and use these functions
4. Maintain all existing functionality

## Implementation Steps
1. Identify all display/formatting helper functions in `cli.py`
2. Create `src/treeline/cli_display.py`
3. Move helper functions to new file
4. Update function visibility (remove leading underscore if appropriate)
5. Update `cli.py` imports
6. Update function calls in `cli.py`
7. Run unit tests: `uv run pytest tests/unit`
8. Run smoke tests: `uv run pytest tests/smoke`
9. Verify CLI commands work correctly

## Acceptance Criteria
- [ ] Display helpers extracted to `cli_display.py`
- [ ] `cli.py` imports from display module
- [ ] CLI file size reduced by ~150-200 lines
- [ ] All CLI commands work correctly
- [ ] All tests pass
- [ ] Code follows project style (ruff formatted)

## Expected Outcome
- **Before**: `cli.py` = 1540 lines
- **After**: `cli.py` = ~1350 lines, `cli_display.py` = ~200 lines
- Better organization without changing architecture

## Estimated Impact
- **Files Modified**: 2 (1 new, 1 updated)
- **Lines Moved**: ~150-200 lines
- **Test Risk**: Low-Medium (need to verify all commands still display correctly)
