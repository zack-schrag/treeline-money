"""Analysis mode command - integrated workspace for data exploration.

This module implements a split-panel TUI using prompt_toolkit:
- Top panel: Results table (read-only, updates in-place)
- Bottom panel: SQL editor (multiline, always editable)
"""

import asyncio
from uuid import UUID

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_focus
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    FormattedTextControl,
    HSplit,
    Layout,
    VSplit,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.widgets import Frame
from pygments.lexers.sql import SqlLexer
from rich.console import Console

from treeline.domain import AnalysisSession
from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container

    return _get_container()


def is_authenticated():
    """Check if user is authenticated."""
    from treeline.cli import is_authenticated as _is_authenticated

    return _is_authenticated()


def get_current_user_id():
    """Get current user ID."""
    from treeline.cli import get_current_user_id as _get_current_user_id

    return _get_current_user_id()


async def _execute_query(session: AnalysisSession) -> None:
    """Execute SQL and update session with results."""
    if not session.sql.strip():
        return

    # Validate SELECT only
    sql_upper = session.sql.strip().upper()
    if not sql_upper.startswith("SELECT"):
        # Store error in session
        session.results = None
        session.columns = None
        return

    # Get container and execute
    container = get_container()
    db_service = container.db_service()

    # Get user_id
    user_id_str = get_current_user_id()
    user_id = UUID(user_id_str)

    # Execute query
    result = await db_service.execute_query(user_id, session.sql)

    if result.success:
        session.results = result.data["rows"]
        session.columns = result.data["columns"]
        session.view_mode = "results"
        session.scroll_offset = 0  # Reset vertical scroll on new query
        session.column_offset = 0  # Reset horizontal scroll on new query
        session.selected_row = 0  # Reset selection to first row


def format_results_table(session: AnalysisSession, start_row: int = 0, page_size: int = 20, terminal_width: int = 140) -> list:
    """Format results as prompt_toolkit formatted text with column windowing.

    Args:
        session: AnalysisSession with results to format
        start_row: Index of first row to display (vertical scroll)
        page_size: Number of rows to display per page
        terminal_width: Available width for display

    Returns:
        List of (style, text) tuples for FormattedText
    """
    if not session.has_results():
        return [("", "No results yet.\n\nType SQL below and press Ctrl+Enter to execute.")]

    # Calculate column widths for ALL columns
    all_col_widths = []
    for i, col_name in enumerate(session.columns):
        max_width = len(col_name)
        # Check sample of data
        for row in session.results[:100]:
            val = row[i]
            val_str = str(val) if val is not None else "NULL"
            max_width = max(max_width, len(val_str))
        # Reasonable width: between 8 and 40 chars
        all_col_widths.append(min(max(max_width, 8), 40))

    # Determine which columns to show based on terminal width and column offset
    visible_cols = []
    visible_widths = []
    current_width = 0
    col_spacing = 2  # "  " between columns

    for i in range(session.column_offset, len(session.columns)):
        col_width = all_col_widths[i]
        needed_width = col_width + (col_spacing if visible_cols else 0)

        if current_width + needed_width > terminal_width - 20:  # Leave room for scroll indicators
            break

        visible_cols.append(i)
        visible_widths.append(col_width)
        current_width += needed_width

    if not visible_cols:
        # At least show one column
        visible_cols = [session.column_offset]
        visible_widths = [all_col_widths[session.column_offset]]

    result = []

    # Header row with column indicators
    header_parts = []
    for col_idx, width in zip(visible_cols, visible_widths):
        col_name = session.columns[col_idx]
        header_parts.append(col_name.ljust(width))
    result.append(("bold", "  ".join(header_parts)))

    # Add scroll indicators
    if session.column_offset > 0:
        result.append(("", "  "))
        result.append(("class:muted", "◀"))
    if visible_cols[-1] < len(session.columns) - 1:
        result.append(("", "  "))
        result.append(("class:muted", "▶"))
    result.append(("", "\n"))

    # Separator
    sep_parts = ["─" * width for width in visible_widths]
    result.append(("", "  ".join(sep_parts)))
    result.append(("", "\n"))

    # Data rows (paginated) with highlight for selected row
    end_row = min(start_row + page_size, len(session.results))

    for i in range(start_row, end_row):
        row = session.results[i]
        row_parts = []
        for col_idx, width in zip(visible_cols, visible_widths):
            val = row[col_idx]
            val_str = str(val) if val is not None else "NULL"
            # Truncate if needed
            if len(val_str) > width:
                val_str = val_str[:width-3] + "..."
            row_parts.append(val_str.ljust(width))

        # Highlight selected row with green theme color
        if i == session.selected_row:
            result.append(("bold #44755a", "  ".join(row_parts)))
        else:
            result.append(("", "  ".join(row_parts)))
        result.append(("", "\n"))

    # Pagination info
    result.append(("", "\n"))
    total_rows = len(session.results)
    total_cols = len(session.columns)
    shown_cols = f"{visible_cols[0] + 1}-{visible_cols[-1] + 1}" if len(visible_cols) > 1 else str(visible_cols[0] + 1)

    info_parts = []
    info_parts.append(f"Rows {start_row + 1}-{end_row} of {total_rows}")
    if total_cols > len(visible_cols):
        info_parts.append(f"Cols {shown_cols} of {total_cols}")

    result.append(("class:muted", "  |  ".join(info_parts)))

    return result


def create_analysis_app(session: AnalysisSession) -> Application:
    """Create prompt_toolkit Application for analysis mode.

    Args:
        session: AnalysisSession to manage state

    Returns:
        Application instance ready to run
    """
    # Create SQL buffer
    sql_buffer = Buffer(
        multiline=True,
        document=Document(session.sql, 0),
    )

    # Create key bindings
    kb = KeyBindings()

    @kb.add("c-j")  # Ctrl+J (Ctrl+Enter in terminal)
    @kb.add("escape", "enter")  # Alt+Enter
    def execute_query(event):
        """Execute query on Ctrl+Enter or Alt+Enter."""
        # Update session with current buffer text
        session.sql = sql_buffer.text

        # Run async query execution in the event loop
        async def run_query():
            await _execute_query(session)
            # Switch focus to results panel after query executes
            event.app.layout.focus(results_window)
            # Trigger re-render
            event.app.invalidate()

        # Schedule the coroutine
        asyncio.ensure_future(run_query())

    @kb.add("c-c")
    def quit_app(event):
        """Quit on Ctrl+C."""
        event.app.exit()

    @kb.add("tab")
    def switch_focus(event):
        """Switch focus between SQL editor and results panel."""
        event.app.layout.focus_next()

    # Create a focusable buffer for results (read-only)
    results_buffer = Buffer(read_only=True)

    # Create windows first so we can reference them in filters
    results_window = Window(
        content=FormattedTextControl(
            text=lambda: format_results_table(session, start_row=session.scroll_offset),
            show_cursor=False,
            focusable=True,  # Make it focusable
        ),
        wrap_lines=True,
    )

    sql_window = Window(
        content=BufferControl(
            buffer=sql_buffer,
            lexer=PygmentsLexer(SqlLexer),
        ),
        wrap_lines=True,
    )

    # Results panel navigation (only when results window is focused)
    from prompt_toolkit.filters import has_focus

    results_focused = has_focus(results_window)

    @kb.add("down", filter=results_focused)
    def scroll_down(event):
        """Move selection down (Down arrow when results focused)."""
        if not session.has_results():
            return

        # Move selection down if possible
        if session.selected_row < len(session.results) - 1:
            session.selected_row += 1

            # Scroll viewport if selected row goes off bottom
            page_size = 20
            end_row = min(session.scroll_offset + page_size, len(session.results))
            if session.selected_row >= end_row:
                session.scroll_offset += 1

            event.app.invalidate()

    @kb.add("up", filter=results_focused)
    def scroll_up(event):
        """Move selection up (Up arrow when results focused)."""
        if not session.has_results():
            return

        # Move selection up if possible
        if session.selected_row > 0:
            session.selected_row -= 1

            # Scroll viewport if selected row goes off top
            if session.selected_row < session.scroll_offset:
                session.scroll_offset -= 1

            event.app.invalidate()

    @kb.add("left", filter=results_focused)
    def scroll_left(event):
        """Scroll columns left (Left arrow when results focused)."""
        if session.has_results() and session.column_offset > 0:
            session.column_offset -= 1
            event.app.invalidate()

    @kb.add("right", filter=results_focused)
    def scroll_right(event):
        """Scroll columns right (Right arrow when results focused)."""
        if session.has_results():
            max_col_offset = max(0, len(session.columns) - 1)
            if session.column_offset < max_col_offset:
                session.column_offset += 1
                event.app.invalidate()

    # Status bar with dynamic focus indicator
    def get_status_text():
        base_text = "Analysis Mode  [Ctrl+Enter] execute  [Tab] switch panel  [Ctrl+C] quit"

        # Add focus indicator
        from prompt_toolkit.application import get_app
        app = get_app()
        if app.layout.has_focus(results_window):
            focus_hint = "  [Results: use ←↓↑→ to scroll]"
        else:
            focus_hint = "  [SQL Editor]"

        return [("reverse", f" {base_text}{focus_hint} ")]

    status_bar = Window(
        content=FormattedTextControl(get_status_text),
        height=1,
        align=WindowAlign.LEFT,
    )

    root_container = HSplit(
        [
            status_bar,
            results_window,
            Window(height=1, char="─"),  # Separator
            sql_window,
        ]
    )

    layout = Layout(root_container, focused_element=sql_window)

    return Application(
        layout=layout,
        key_bindings=kb,
        full_screen=True,
        mouse_support=False,
    )


def handle_analysis_command() -> None:
    """Main analysis mode entry point."""
    if not is_authenticated():
        console.print(
            f"[{theme.error}]Error: You must be logged in to use analysis mode.[/{theme.error}]"
        )
        console.print(f"[{theme.muted}]Run /login to authenticate[/{theme.muted}]\n")
        return

    session = AnalysisSession()

    try:
        app = create_analysis_app(session)
        app.run()
    except (KeyboardInterrupt, EOFError):
        pass

    console.print(f"\n[{theme.muted}]Exiting analysis mode[/{theme.muted}]\n")
