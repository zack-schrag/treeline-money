# Task 006: Extract Commands from cli.py to commands/ Folder

## Status
🔴 Not Started

## Priority
**HIGH** - Critical architectural issue, cli.py should be thin routing layer

## Problem
The `cli.py` file contains **13 command implementations** totaling 1540 lines. According to architecture guidelines, cli.py should be a **thin presentation layer** that primarily routes to implementations in `commands/` folder.

### Current State Analysis:

| Command | Lines | Current Location | Action Needed |
|---------|-------|------------------|---------------|
| `login` | ~67 | cli.py | ❌ Keep (auth setup) |
| `setup` | ~226 | cli.py | ❌ Keep (initial config) |
| `analysis` | ~10 | cli.py (routes to TUI) | ✅ Already correct |
| `queries` | ~14 | cli.py (routes to TUI) | ✅ Already correct |
| `charts` | ~14 | cli.py (routes to TUI) | ✅ Already correct |
| **`chat`** | **~168** | **cli.py** | 🔴 **MOVE to commands/** |
| **`ask`** | **~147** | **cli.py** | 🔴 **MOVE to commands/** |
| **`clear`** | **~22** | **cli.py** | 🟡 **CONSIDER moving** |
| **`status`** | **~44** | **cli.py** | 🟡 **CONSIDER moving** |
| **`query`** | **~90** | **cli.py** | 🔴 **MOVE to commands/** |
| **`schema`** | **~133** | **cli.py** | 🔴 **MOVE to commands/** |
| **`sync`** | **~42** | **cli.py** | 🟡 **CONSIDER moving** |
| `import` | ~98 | cli.py (routes correctly) | ✅ Already correct pattern |

### Commands to Extract (Priority Order):

1. **`chat`** (~168 lines) → `commands/chat.py`
   - Interactive AI chat with streaming
   - Complex logic that belongs in commands/

2. **`ask`** (~147 lines) → `commands/ask.py`
   - One-shot AI queries
   - Similar to chat, should be extracted

3. **`schema`** (~133 lines) → `commands/schema.py`
   - Database schema display
   - Significant formatting logic

4. **`query`** (~90 lines) → `commands/query.py`
   - Execute SQL queries
   - Should follow same pattern as import command

5. **`status`** (~44 lines) → `commands/status.py`
   - System status display
   - Could be extracted for consistency

6. **`sync`** (~42 lines) → `commands/sync.py`
   - Sync with SimpleFIN
   - Could be extracted for consistency

7. **`clear`** (~22 lines) → `commands/clear.py`
   - Clear local data
   - Small but could be extracted

## Architectural Principle

**Separation of Concerns** - The CLI file should be a **thin routing layer** that:
1. Defines command signatures (arguments, options)
2. Handles basic validation
3. Routes to appropriate handler in `commands/` folder
4. Should NOT contain complex business presentation logic

**Target**: cli.py should be ~500-700 lines (routing only), with implementations in `commands/`

## Solution Pattern

Follow the **import command pattern** (lines 1332-1375):

```python
@app.command(name="chat")
def chat_command(
    message: str = typer.Argument(None, help="Message to send"),
    # ... other options
) -> None:
    """Chat with AI about your finances."""
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

    # Route to command implementation
    from treeline.commands.chat import handle_chat_command
    handle_chat_command(message=message, ...)
```

Then create `commands/chat.py`:
```python
def handle_chat_command(message: str, ...) -> None:
    """Handle chat command implementation."""
    # All the actual logic here
```

## Implementation Steps

### Phase 1: High Priority Commands
1. Create `commands/chat.py` and extract chat logic
2. Update `cli.py` chat command to route to new handler
3. Test: `uv run tl chat "test message"`
4. Create `commands/ask.py` and extract ask logic
5. Update `cli.py` ask command to route to new handler
6. Test: `uv run tl ask "test query"`

### Phase 2: Medium Priority Commands
7. Create `commands/schema.py` and extract schema logic
8. Update `cli.py` schema command to route to new handler
9. Test: `uv run tl schema`
10. Create `commands/query.py` and extract query logic
11. Update `cli.py` query command to route to new handler
12. Test: `uv run tl query "SELECT 1"`

### Phase 3: Low Priority Commands (Optional)
13. Create `commands/status.py` and extract status logic
14. Create `commands/sync.py` and extract sync logic
15. Create `commands/clear.py` and extract clear logic

### Phase 4: Validation
16. Run unit tests: `uv run pytest tests/unit`
17. Run smoke tests: `uv run pytest tests/smoke`
18. Verify all commands work correctly
19. Check cli.py line count (should be ~700-800 lines after Phase 1+2)

## Acceptance Criteria
- [ ] Chat command extracted to `commands/chat.py`
- [ ] Ask command extracted to `commands/ask.py`
- [ ] Schema command extracted to `commands/schema.py`
- [ ] Query command extracted to `commands/query.py`
- [ ] All commands route through cli.py (thin layer)
- [ ] cli.py reduced from 1540 → ~700-900 lines
- [ ] All tests pass
- [ ] All commands work correctly
- [ ] Code follows project style (ruff formatted)

## Expected Outcome

**Before**:
- `cli.py`: 1540 lines (routing + implementation)
- `commands/`: 8 files (TUIs + import)

**After**:
- `cli.py`: ~700-900 lines (routing only)
- `commands/`: 12+ files (organized implementations)
- Lines moved: ~600-700 lines to appropriate modules

## Dependencies
- Should be done **AFTER** Task 001 (extract CLI helpers)
- Requires shared `cli_helpers.py` to be in place first

## Estimated Impact
- **Files Created**: 4-7 new command files
- **Files Modified**: 1 (cli.py)
- **Lines Moved**: ~600-700 lines
- **Test Risk**: Medium (need to verify all commands still work)
- **Complexity**: Medium-High (lots of refactoring)

## Notes
- This is the **biggest architectural cleanup** needed
- Follow the import command pattern consistently
- Each command should support both interactive and scriptable modes where appropriate
- Commands can still use helpers from `cli_helpers.py` (after Task 001)
