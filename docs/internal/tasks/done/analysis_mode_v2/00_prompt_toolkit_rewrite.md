# Task 00: Rewrite with prompt_toolkit Split-Panel Architecture

**Status:** ✅ Complete
**Priority:** CRITICAL - Blocks all other tasks
**Estimated Time:** 3-4 hours

## Problem

Current implementation uses two incompatible input systems:
- `readchar.readkey()` for navigation
- `PromptSession` for SQL editing

These cannot coexist, causing:
- SQL editor appears below modal view (not replacing it)
- Results accumulate instead of replacing in-place
- No way to have SQL editor and results visible simultaneously

## Solution

Rewrite `/analysis` mode using `prompt_toolkit.Application` with split-panel layout:
- **Top panel:** Results table (read-only, updates in-place)
- **Bottom panel:** SQL editor (editable buffer, always visible)
- Both panels visible at all times
- Ctrl+Enter executes query and updates top panel

## Architecture

### Key Components

**1. prompt_toolkit.Application**
- Main application container
- Runs event loop
- Manages key bindings globally

**2. prompt_toolkit.layout.Layout**
- HSplit for top/bottom panels
- Window for results (read-only)
- Window for SQL buffer (editable)

**3. prompt_toolkit.buffer.Buffer**
- Multiline SQL editing
- Syntax highlighting (PygmentsLexer)
- Custom accept handler for Ctrl+Enter

**4. FormattedTextControl**
- Renders results table as formatted text
- Updates when query executes

## Implementation Steps

### Step 1: Create Application Shell
```python
from prompt_toolkit import Application
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.key_binding import KeyBindings

def create_analysis_app(session: AnalysisSession) -> Application:
    # Create SQL buffer
    sql_buffer = Buffer(
        multiline=True,
        on_text_changed=lambda _: update_session(session)
    )

    # Create layout
    layout = Layout(
        HSplit([
            Window(content=ResultsControl(session), height=20),  # Results
            Window(content=BufferControl(buffer=sql_buffer)),    # SQL
        ])
    )

    # Create key bindings
    kb = KeyBindings()

    @kb.add('c-j')  # Ctrl+Enter
    def execute_query(event):
        _execute_query(session, sql_buffer.text)
        event.app.invalidate()  # Trigger re-render

    @kb.add('c-c')  # Ctrl+C to quit
    def quit(event):
        event.app.exit()

    return Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
    )
```

### Step 2: Create Results Control
```python
from prompt_toolkit.layout import FormattedTextControl
from rich.console import Console
from rich.table import Table
from io import StringIO

class ResultsControl(FormattedTextControl):
    def __init__(self, session: AnalysisSession):
        self.session = session
        super().__init__(self._get_text)

    def _get_text(self):
        if not self.session.has_results():
            return "No results yet. Type SQL below and press Ctrl+Enter to execute."

        # Render Rich table to string
        buffer = StringIO()
        console = Console(file=buffer, width=80)
        table = Table(...)
        # ... add rows ...
        console.print(table)
        return buffer.getvalue()
```

### Step 3: Wire Query Execution
```python
def _execute_query(session: AnalysisSession, sql: str) -> None:
    session.sql = sql

    # Execute (same async call as before)
    result = asyncio.run(db_service.execute_query(user_id, sql))

    if result.success:
        session.results = result.data['rows']
        session.columns = result.data['columns']
    # Errors: TODO - display in results panel
```

### Step 4: Update Main Entry Point
```python
def handle_analysis_command() -> None:
    if not is_authenticated():
        console.print(f"[{theme.error}]Error: You must be logged in[/{theme.error}]")
        return

    session = AnalysisSession()
    app = create_analysis_app(session)

    # Run the application (blocks until quit)
    app.run()

    console.print(f"\n[{theme.muted}]Exiting analysis mode[/{theme.muted}]\n")
```

## What Changes

**Remove:**
- `_edit_sql()` function (replaced by Buffer)
- `_render_analysis_view()` (replaced by Layout)
- `readchar.readkey()` loop (replaced by Application)
- All `console.clear()` and `console.print()` calls for UI

**Keep:**
- `_execute_query()` logic (query execution)
- `AnalysisSession` domain model
- `_create_chart()` (for later - charts will be added back)
- All service layer calls (db_service, etc.)

**Add:**
- `create_analysis_app()` - Application factory
- `ResultsControl` - Custom control for results display
- Key bindings for Ctrl+Enter, q, etc.

## Testing Strategy

Unit tests will need updates:
- Mock `Application.run()` instead of `readchar.readkey()`
- Test buffer updates instead of prompt session
- Test ResultsControl rendering

Keep existing tests for:
- `_execute_query()` logic (unchanged)
- `AnalysisSession` domain model (unchanged)

## Success Criteria

- [ ] SQL editor visible at bottom
- [ ] Results table visible at top
- [ ] Ctrl+Enter executes query
- [ ] Results update in-place (no stacking)
- [ ] Both panels visible simultaneously
- [ ] 'q' or Ctrl+C exits cleanly
- [ ] All unit tests passing

## References

- [prompt_toolkit docs - Application](https://python-prompt-toolkit.readthedocs.io/en/master/pages/full_screen_apps.html)
- [prompt_toolkit docs - Layout](https://python-prompt-toolkit.readthedocs.io/en/master/pages/advanced_topics/layout.html)
- [prompt_toolkit examples - Split panel editor](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/master/examples/full-screen/split-screen.py)
