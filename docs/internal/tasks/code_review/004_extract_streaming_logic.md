# Task 004: Extract Streaming Response Logic

## Status
🔴 Not Started

## Priority
**LOW-MEDIUM** - Further reduces CLI file size, optional refinement

## Problem
The `cli.py` file contains streaming response handling logic that could be extracted:

### Code to Extract:
- `_handle_streaming_response()` - Handles streaming AI responses
- `_display_stream_chunk()` - Displays individual chunks
- Related streaming utilities

### Current State:
- Streaming logic mixed with command definitions
- Could be more reusable if extracted
- Not a violation, but could be cleaner

## Architectural Principle
**Separation of Concerns** - Streaming logic is a distinct concern that could be isolated for reusability and testing.

## Solution
1. Create new file: `src/treeline/cli_streaming.py`
2. Move streaming-related helper functions
3. Update `cli.py` to import and use streaming utilities
4. Maintain all existing functionality

## Implementation Steps
1. Identify all streaming-related helper functions in `cli.py`
2. Create `src/treeline/cli_streaming.py`
3. Move streaming functions to new file
4. Update `cli.py` imports
5. Update function calls in `cli.py`
6. Test streaming commands (e.g., chat, analysis)
7. Run unit tests: `uv run pytest tests/unit`
8. Run smoke tests: `uv run pytest tests/smoke`

## Acceptance Criteria
- [ ] Streaming helpers extracted to `cli_streaming.py`
- [ ] `cli.py` imports from streaming module
- [ ] CLI file size reduced by ~50-100 lines
- [ ] Streaming commands work correctly
- [ ] All tests pass
- [ ] Code follows project style (ruff formatted)

## Expected Outcome
- **After Task 003**: `cli.py` = ~1350 lines
- **After Task 004**: `cli.py` = ~1250 lines, `cli_streaming.py` = ~100 lines
- Total reduction: ~290 lines from original 1540

## Estimated Impact
- **Files Modified**: 2 (1 new, 1 updated)
- **Lines Moved**: ~50-100 lines
- **Test Risk**: Medium (need to verify streaming functionality)

## Notes
- This task is optional but recommended
- Consider doing this after Tasks 001-003
- May discover additional streaming utilities that can be consolidated
