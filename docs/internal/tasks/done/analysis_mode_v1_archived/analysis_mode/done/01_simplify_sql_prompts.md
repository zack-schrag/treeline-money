# Task 01: Simplify SQL Prompts ✅

**Status**: COMPLETED

## Objective
Replace sequential prompts in `/sql` command with single action menu to reduce friction.

## What Was Changed

### Modified Files
1. **src/treeline/commands/query.py**
   - Added `_prompt_post_query_actions()` function - single action menu with [c]hart, [s]ave, [e]dit options
   - Modified `handle_query_command()` to use new action menu
   - Simplified `_prompt_chart_wizard()` by removing initial "Create chart?" prompt
   - Removed `_prompt_to_save_query_with_loopback()` (no longer needed)

2. **tests/unit/commands/test_post_query_actions.py** (NEW)
   - 8 comprehensive unit tests covering all action menu flows
   - Tests: chart → exit, save, edit, enter to exit, invalid options, case sensitivity
   - All tests passing

3. **tests/unit/commands/test_sql_command.py**
   - Fixed mock from `Confirm` to `Prompt` to match new action menu
   - Updated return value to simulate pressing enter

### User Experience Changes

**Before** (3 sequential prompts):
```
[Results displayed]
Create a chart? [y/N]
Save this query? [y/N]
Continue editing? [y/N]
```

**After** (1 action menu with looping):
```
[Results displayed]
10 rows returned
Next? [c]hart  [s]ave  [e]dit  [enter] to continue
```

Users can now:
- Press `c` to create chart, then return to action menu
- Press `s` to save query and exit
- Press `e` to edit SQL again
- Press Enter to exit cleanly

## Test Results
- All 190 unit tests passing ✅
- All 6 smoke tests passing ✅
- Test coverage for new functionality: 8/8 tests passing

## Architecture Review
Task 01 is UI-only refactoring with no architecture concerns:
- No new business logic added
- No service layer changes
- CLI layer remains thin (parsing → display)
- Follows hexagonal principles ✅

## Next Steps
Ready to proceed with Task 02: Refine Chart Command
