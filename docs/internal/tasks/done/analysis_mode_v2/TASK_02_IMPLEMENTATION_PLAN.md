# Task 02 Implementation Plan: SQL Editor Panel

## Status
**In Progress** - Task 01 Complete, Starting Task 02

## What's Done (Task 01)
- ✅ AnalysisSession domain model in [domain.py:283-322](../../src/treeline/domain.py#L283)
- ✅ Analysis command with modal layout in [commands/analysis.py](../../src/treeline/commands/analysis.py)
- ✅ CLI registration and `/help` integration
- ✅ 11 unit tests + 2 smoke tests (all passing)
- ✅ 201 unit tests total, 10 smoke tests total (all passing)

## Task 02 Approach

### Key Insight from Tag Mode
Tag mode uses `readchar` for simple keyboard navigation, not full `prompt_toolkit` integration. For analysis mode:

1. **Main loop**: Use `readchar` for navigation keys (q, c, Tab, etc.)
2. **SQL editing**: Launch `PromptSession` temporarily when user presses a key (like 'e' or when view starts)
3. **F5 binding**: Within PromptSession, F5 executes and returns

### Implementation Pattern (from `/sql` command)

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer

# Create key bindings
bindings = KeyBindings()

@bindings.add('f5')
def _(event):
    """Execute query on F5."""
    event.current_buffer.validate_and_handle()

# Create SQL editor session
session = PromptSession(
    lexer=PygmentsLexer(SqlLexer),
    multiline=True,
    key_bindings=bindings,
)

# Get SQL input
sql = session.prompt(">: ", default=existing_sql)
```

### Analysis Mode Flow

```
1. Render modal view (data panel + SQL panel preview)
2. User presses key:
   - 'e' → Launch SQL editor (PromptSession)
     - F5 in editor → Execute query, update session, return to modal
     - Esc in editor → Cancel, return to modal
   - 'c' → Create chart (if results exist)
   - Tab → Toggle results/chart view
   - 'q' → Quit
3. Loop back to step 1
```

### Files to Modify

1. **src/treeline/commands/analysis.py**
   - Add imports: `readchar`, `PromptSession`, `KeyBindings`, etc.
   - Add `_edit_sql(session: AnalysisSession) -> None` function
   - Add `_execute_query(session: AnalysisSession) -> None` function
   - Update main loop to use `readchar` for navigation

2. **Update tests** to mock SQL editing and query execution

### Execution Flow Detail

```python
def _edit_sql(session: AnalysisSession) -> None:
    """Launch SQL editor and handle F5 execution."""
    bindings = KeyBindings()

    @bindings.add('f5')
    def _(event):
        """Execute query on F5."""
        # This will exit prompt and return the SQL
        event.current_buffer.validate_and_handle()

    sql_session = PromptSession(
        lexer=PygmentsLexer(SqlLexer),
        multiline=True,
        key_bindings=bindings,
    )

    try:
        # Edit SQL
        sql = sql_session.prompt(">: ", default=session.sql)
        session.sql = sql

        # Execute immediately (F5 was pressed)
        _execute_query(session)

    except (KeyboardInterrupt, EOFError):
        # User cancelled (Ctrl+C or Ctrl+D)
        pass


def _execute_query(session: AnalysisSession) -> None:
    """Execute SQL and update session with results."""
    if not session.sql.strip():
        return

    # Get container and execute
    container = get_container()
    db_service = container.db_service()

    result = db_service.execute_query(session.sql)

    if result.success:
        session.results = result.data['rows']
        session.columns = result.data['columns']
        session.view_mode = "results"  # Show results after execution
    else:
        console.print(f"[{theme.error}]Error: {result.error}[/{theme.error}]")


def handle_analysis_command() -> None:
    """Main analysis mode entry point."""
    import readchar

    session = AnalysisSession()

    # Auto-launch SQL editor on start
    _edit_sql(session)

    while True:
        console.clear()
        console.print(_render_analysis_view(session))

        key = readchar.readkey()

        if key == 'e':
            _edit_sql(session)
        elif key == 'c' and session.has_results():
            _create_chart(session)  # Task 04
        elif key == '\t' and session.has_chart():
            session.toggle_view()
        elif key == 'q':
            break
```

## Next Steps

1. Implement `_edit_sql()` function
2. Implement `_execute_query()` function
3. Update main loop with `readchar` navigation
4. Import needed modules from `treeline.cli` (get_container, is_authenticated)
5. Write tests
6. Manual testing

## Architecture Notes

- ✅ SQL editing is CLI presentation layer
- ✅ Query execution delegates to `db_service.execute_query()`
- ✅ No business logic in command handler
- ✅ AnalysisSession remains pure domain model

## Testing Strategy

**Unit tests:**
- Mock PromptSession and verify SQL is captured
- Mock db_service and verify execute_query is called
- Verify session state updates correctly

**Smoke tests:**
- Will test in Task 05 when full navigation is wired

## Estimated Completion

Task 02: ~1 hour (matches original estimate)
