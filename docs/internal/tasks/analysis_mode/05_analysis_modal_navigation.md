# Analysis Mode: Modal Navigation UI

## Problem

With session state in place (from task 04), we need to build the user-facing modal navigation that allows fluid movement between SQL editing, result viewing, and chart creation.

## Solution

Implement three modal sub-modes within `/analysis`:

1. **SQL Mode**: Edit and execute SQL
2. **Results Mode**: View results, create charts
3. **Chart Mode**: Configure and adjust charts

Each mode has clear visual indicators and navigation options.

## Implementation Details

### Entry Point

```python
def handle_analysis_command() -> None:
    """Handle /analysis command - enter analysis mode."""
    container = get_container()
    config_service = container.config_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    # Create session
    session = AnalysisSession()

    # Show welcome
    _show_analysis_welcome()

    # Main modal loop
    try:
        while True:
            if session.mode == "sql":
                action = _handle_sql_mode(session, user_id)
            elif session.mode == "results":
                action = _handle_results_mode(session, user_id)
            elif session.mode == "chart":
                action = _handle_chart_mode(session, user_id)
            else:
                break

            if action == "quit":
                break

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.muted}]Exiting analysis mode[/{theme.muted}]\n")
```

### SQL Mode

```python
def _handle_sql_mode(session: AnalysisSession, user_id: UUID) -> str:
    """Handle SQL editing mode.

    Returns:
        Action: "quit", "execute", etc.
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.lexers import PygmentsLexer
    from pygments.lexers.sql import SqlLexer

    console.print(f"\n[{theme.ui_header}]──── SQL Mode ────[/{theme.ui_header}]")
    console.print(f"[{theme.muted}]F5 to execute  |  Tab for saved queries  |  q to quit[/{theme.muted}]\n")

    # Create bindings
    bindings = KeyBindings()

    @bindings.add('f5')
    def _(event):
        """Execute on F5."""
        event.current_buffer.validate_and_handle()

    # Create session with SQL highlighting
    prompt_session = PromptSession(
        lexer=PygmentsLexer(SqlLexer),
        multiline=True,
        key_bindings=bindings,
        completer=SavedQueryCompleter(),  # From existing code
    )

    try:
        # Prefill with current SQL if exists
        sql = prompt_session.prompt("SQL> ", default=session.sql)
    except KeyboardInterrupt:
        return "quit"

    if not sql or not sql.strip():
        return "quit"

    # Check for quit command
    if sql.strip().lower() == 'q':
        return "quit"

    # Update session
    session.update_sql(sql.strip())

    # Execute query
    result = _execute_query(user_id, session.sql)

    if not result.success:
        console.print(f"\n[{theme.error}]Error: {result.error}[/{theme.error}]\n")
        return "sql"  # Stay in SQL mode

    # Update results
    query_result = result.data
    session.update_results(
        query_result.get("columns", []),
        query_result.get("rows", [])
    )

    # Transition to results mode
    session.mode = "results"
    return "continue"
```

### Results Mode

```python
def _handle_results_mode(session: AnalysisSession, user_id: UUID) -> str:
    """Handle results viewing mode.

    Returns:
        Action: "quit", "chart", "edit", etc.
    """
    console.print(f"\n[{theme.ui_header}]──── Results ────[/{theme.ui_header}]\n")

    # Display results table
    _display_results_table(session.columns, session.rows)

    console.print(f"\n[{theme.muted}]{len(session.rows)} row{'s' if len(session.rows) != 1 else ''} returned[/{theme.muted}]\n")

    # Action menu
    action = Prompt.ask(
        f"[{theme.info}]Next?[/{theme.info}] [c]hart  [e]dit SQL  [s]ave query  [q]uit",
        default="",
        show_default=False
    )

    if action.lower() == "c":
        session.mode = "chart"
        return "continue"
    elif action.lower() == "e":
        session.mode = "sql"
        return "continue"
    elif action.lower() == "s":
        _save_query_prompt(session.sql)
        return "results"  # Stay in results
    elif action.lower() == "q" or action == "":
        return "quit"
    else:
        console.print(f"[{theme.error}]Invalid option[/{theme.error}]")
        return "results"
```

### Chart Mode

```python
def _handle_chart_mode(session: AnalysisSession, user_id: UUID) -> str:
    """Handle chart creation/editing mode.

    Returns:
        Action: "quit", "back", etc.
    """
    console.print(f"\n[{theme.ui_header}]──── Chart Builder ────[/{theme.ui_header}]\n")

    if not session.can_create_chart():
        console.print(f"[{theme.error}]No results to chart. Run a query first.[/{theme.error}]\n")
        session.mode = "sql"
        return "continue"

    # If we already have a chart config, offer to adjust
    if session.chart_config:
        console.print("[Existing chart configuration]\n")
        action = Prompt.ask(
            f"[{theme.info}]Options:[/{theme.info}] [a]djust  [r]egenerate  [b]ack to results",
            default="a"
        )

        if action == "b":
            session.mode = "results"
            return "continue"
        elif action == "r":
            session.clear_chart()
            # Fall through to create new chart

    # Chart wizard (simplified, integrated version)
    chart_config = _prompt_chart_configuration(session.columns, session.rows, session.sql)

    if not chart_config:
        # User cancelled
        session.mode = "results"
        return "continue"

    # Generate chart
    result = create_chart_from_config(chart_config, session.columns, session.rows)

    if not result.success:
        console.print(f"\n[{theme.error}]{result.error}[/{theme.error}]\n")
        session.mode = "results"
        return "continue"

    # Update session
    session.update_chart(chart_config, result.data)

    # Display chart
    console.print(result.data)

    # Post-chart menu
    action = Prompt.ask(
        f"[{theme.info}]Next?[/{theme.info}] [a]djust  [s]ave  [e]dit SQL  [b]ack  [q]uit",
        default=""
    )

    if action.lower() == "a":
        # Stay in chart mode, loop back to adjust
        return "chart"
    elif action.lower() == "s":
        _save_chart_prompt(session.sql, chart_config)
        return "chart"  # Stay in chart mode
    elif action.lower() == "e":
        session.mode = "sql"
        return "continue"
    elif action.lower() == "b":
        session.mode = "results"
        return "continue"
    else:
        return "quit"
```

### Visual State Indicators

Each mode should have clear visual feedback:

```
SQL Mode:
┌──── SQL Mode ────┐
│ F5 to execute    │
└──────────────────┘
SQL> _

Results Mode:
┌──── Results ────┐
│ 100 rows        │
└─────────────────┘
[Table displayed]
Next? [c]hart [e]dit [q]uit

Chart Mode:
┌──── Chart Builder ────┐
│ Configure chart       │
└───────────────────────┘
Type: histogram
Column: amount
```

## Testing

### Unit Tests

Create `tests/unit/commands/test_analysis_navigation.py`:

```python
def test_analysis_mode_entry():
    """Test entering analysis mode starts in SQL mode."""

def test_sql_mode_execute_transitions_to_results():
    """Test executing query moves to results mode."""

def test_results_mode_chart_transitions_to_chart():
    """Test creating chart moves to chart mode."""

def test_chart_mode_edit_returns_to_sql():
    """Test edit SQL from chart returns to SQL mode."""

def test_quit_from_any_mode():
    """Test quitting works from any mode."""
```

### Manual Testing

```bash
> /analysis

──── SQL Mode ────
SQL> SELECT amount FROM transactions LIMIT 100
[F5]

──── Results ────
[Table with 100 rows]

Next? [c]hart [e]dit [q]uit
> c

──── Chart Builder ────
Type: histogram
...
[Chart displayed]

Next? [a]djust [s]ave [e]dit SQL [q]uit
> e

──── SQL Mode ────
SQL> [previous query prefilled]
```

## Acceptance Criteria

- [ ] `/analysis` command enters analysis mode
- [ ] SQL mode allows editing and execution
- [ ] Results mode displays results and offers actions
- [ ] Chart mode guides chart creation
- [ ] Clear visual indicators for each mode
- [ ] Fluid transitions between modes
- [ ] State preserved across mode changes
- [ ] Keyboard shortcuts work (F5, Tab, etc.)
- [ ] Quit works from any mode
- [ ] Unit tests for mode transitions
- [ ] Manual testing confirms smooth UX

## Notes

- This is the core UX of analysis mode
- Depends on session state (task 04)
- Should feel like an integrated workspace, not separate commands
- Visual clarity is key - users should always know where they are
