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
from treeline.commands.chart_wizard import ChartWizardConfig, create_chart_from_config
from treeline.commands.saved_queries import save_query
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


def _run_chart_wizard(session: AnalysisSession) -> bool:
    """Run interactive chart wizard (outside TUI).

    Returns True if chart was created, False otherwise.
    """
    if not session.has_results():
        return False

    console.print(f"\n[{theme.ui_header}]Chart Wizard[/{theme.ui_header}]")
    console.print(f"[{theme.muted}]Available columns: {', '.join(session.columns)}[/{theme.muted}]\n")

    # Chart type
    console.print(f"[{theme.info}]Chart types:[/{theme.info}]")
    console.print("  1. Bar chart")
    console.print("  2. Line chart")
    console.print("  3. Scatter plot")
    console.print("  4. Histogram (single column)")
    chart_type_choice = console.input(f"\n[{theme.info}]Select chart type (1-4):[/{theme.info}] ").strip()

    chart_type_map = {"1": "bar", "2": "line", "3": "scatter", "4": "histogram"}
    if chart_type_choice not in chart_type_map:
        console.print(f"[{theme.error}]Invalid choice[/{theme.error}]")
        return False

    chart_type = chart_type_map[chart_type_choice]

    # X column
    console.print(f"\n[{theme.info}]Available columns:[/{theme.info}]")
    for i, col in enumerate(session.columns, 1):
        console.print(f"  {i}. {col}")

    x_choice = console.input(f"\n[{theme.info}]X-axis column (number):[/{theme.info}] ").strip()
    try:
        x_idx = int(x_choice) - 1
        if x_idx < 0 or x_idx >= len(session.columns):
            console.print(f"[{theme.error}]Invalid column number[/{theme.error}]")
            return False
        x_column = session.columns[x_idx]
    except ValueError:
        console.print(f"[{theme.error}]Invalid input[/{theme.error}]")
        return False

    # Y column (optional for histogram)
    y_column = ""
    if chart_type != "histogram":
        y_choice = console.input(f"[{theme.info}]Y-axis column (number):[/{theme.info}] ").strip()
        try:
            y_idx = int(y_choice) - 1
            if y_idx < 0 or y_idx >= len(session.columns):
                console.print(f"[{theme.error}]Invalid column number[/{theme.error}]")
                return False
            y_column = session.columns[y_idx]
        except ValueError:
            console.print(f"[{theme.error}]Invalid input[/{theme.error}]")
            return False

    # Create chart
    config = ChartWizardConfig(
        chart_type=chart_type,
        x_column=x_column,
        y_column=y_column,
        title=f"{y_column} by {x_column}" if y_column else x_column,
        width=100,
        height=20,
    )

    result = create_chart_from_config(config, session.columns, session.results)

    if result.success:
        session.chart = result.data
        session.view_mode = "chart"
        console.print(f"\n[{theme.success}]Chart created![/{theme.success}]")
        import time
        time.sleep(1)
        return True
    else:
        console.print(f"\n[{theme.error}]Error: {result.error}[/{theme.error}]")
        return False


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


def format_chart_or_wizard(session: AnalysisSession) -> list:
    """Format chart, wizard, or save UI for display.

    Args:
        session: AnalysisSession with chart or wizard state

    Returns:
        List of (style, text) tuples for FormattedTextControl
    """
    # Show wizard if in wizard mode
    if session.view_mode == "wizard":
        return _format_wizard_ui(session)

    # Show save UI if in save mode
    if session.view_mode in ["save_query", "save_chart"]:
        return _format_save_ui(session)

    # Otherwise show chart
    if not session.has_chart():
        return [("", "No chart yet.\n\nPress 'g' to create a chart from results.")]

    # Chart is already a rendered string, split into lines and apply scrolling
    lines = session.chart.split('\n')

    # Apply vertical scrolling with pagination
    page_size = 30  # Lines to show at once
    start_line = session.chart_scroll_offset
    end_line = min(start_line + page_size, len(lines))

    result = []
    for line in lines[start_line:end_line]:
        result.append(("", line))
        result.append(("", "\n"))

    # Add scroll indicator if there are more lines
    if end_line < len(lines):
        result.append(("class:muted", f"\n[↓ {len(lines) - end_line} more lines]"))

    return result


def _handle_wizard_input(session: AnalysisSession, key: str) -> None:
    """Handle wizard number key input and progress through steps.

    Args:
        session: AnalysisSession with wizard state
        key: Number key pressed (as string)
    """
    choice = int(key)

    if session.wizard_step == "chart_type":
        # Map number to chart type
        chart_types = {1: "bar", 2: "line", 3: "scatter", 4: "histogram"}
        if choice in chart_types:
            session.wizard_chart_type = chart_types[choice]
            session.wizard_step = "x_column"

    elif session.wizard_step == "x_column":
        # Select X column
        if 1 <= choice <= len(session.columns):
            session.wizard_x_column = session.columns[choice - 1]
            # If histogram, create chart immediately (no Y needed)
            if session.wizard_chart_type == "histogram":
                _create_chart_from_wizard(session)
            else:
                session.wizard_step = "y_column"

    elif session.wizard_step == "y_column":
        # Select Y column and create chart
        if 1 <= choice <= len(session.columns):
            session.wizard_y_column = session.columns[choice - 1]
            _create_chart_from_wizard(session)


def _create_chart_from_wizard(session: AnalysisSession) -> None:
    """Create chart from wizard selections.

    Args:
        session: AnalysisSession with wizard selections
    """
    config = ChartWizardConfig(
        chart_type=session.wizard_chart_type,
        x_column=session.wizard_x_column,
        y_column=session.wizard_y_column,
        title=f"{session.wizard_y_column} by {session.wizard_x_column}" if session.wizard_y_column else session.wizard_x_column,
        width=100,
        height=20,
    )

    result = create_chart_from_config(config, session.columns, session.results)

    if result.success:
        session.chart = result.data
        session.view_mode = "chart"
        session.chart_scroll_offset = 0  # Reset scroll for new chart
        # Clear wizard state
        session.wizard_step = ""
    else:
        # Show error in chart view
        session.chart = f"Error creating chart: {result.error}"
        session.view_mode = "chart"
        session.chart_scroll_offset = 0
        session.wizard_step = ""


def _format_save_ui(session: AnalysisSession) -> list:
    """Format the save query/chart UI.

    Args:
        session: AnalysisSession with save state

    Returns:
        List of (style, text) tuples for save UI
    """
    result = []
    result.append(("bold #44755a", "Save " + ("Query" if session.view_mode == "save_query" else "Chart")))
    result.append(("", "\n\n"))

    result.append(("", "Enter name: "))
    result.append(("bold", session.save_input_buffer))
    result.append(("", "█"))  # Cursor
    result.append(("", "\n\n"))

    result.append(("class:muted", "Type name and press Enter to save, Esc to cancel"))

    return result


def _format_wizard_ui(session: AnalysisSession) -> list:
    """Format the chart wizard UI.

    Args:
        session: AnalysisSession with wizard state

    Returns:
        List of (style, text) tuples for wizard UI
    """
    result = []
    result.append(("bold #44755a", "Chart Wizard"))
    result.append(("", "\n\n"))

    if session.wizard_step == "chart_type":
        result.append(("", "Select chart type:\n\n"))
        result.append(("", "  [1] Bar chart (positive values only)\n"))
        result.append(("", "  [2] Line chart (supports negative values)\n"))
        result.append(("", "  [3] Scatter plot\n"))
        result.append(("", "  [4] Histogram\n\n"))
        result.append(("class:muted", "Press 1-4 to select, Esc to cancel\n"))
        result.append(("class:muted", "Tip: Use Line chart for negative values"))

    elif session.wizard_step == "x_column":
        result.append(("", f"Chart type: {session.wizard_chart_type}\n\n"))
        result.append(("", "Select X-axis column:\n\n"))
        for i, col in enumerate(session.columns, 1):
            result.append(("", f"  [{i}] {col}\n"))
        result.append(("", "\n"))
        result.append(("class:muted", f"Press 1-{len(session.columns)} to select, Esc to cancel"))

    elif session.wizard_step == "y_column":
        result.append(("", f"Chart type: {session.wizard_chart_type}\n"))
        result.append(("", f"X-axis: {session.wizard_x_column}\n\n"))
        result.append(("", "Select Y-axis column:\n\n"))
        for i, col in enumerate(session.columns, 1):
            result.append(("", f"  [{i}] {col}\n"))
        result.append(("", "\n"))
        result.append(("class:muted", f"Press 1-{len(session.columns)} to select, Esc to cancel"))

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
            event.app.layout.focus(data_window)
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
        """Tab key: switch focus between SQL editor and data panel."""
        event.app.layout.focus_next()

    # Create a focusable buffer for results (read-only)
    results_buffer = Buffer(read_only=True)

    # Create data window that toggles between results, chart, wizard, and save based on view_mode
    def get_data_content():
        """Return formatted text for data panel (results, chart, wizard, or save)."""
        if session.view_mode in ["chart", "wizard", "save_query", "save_chart"]:
            return format_chart_or_wizard(session)
        else:
            return format_results_table(session, start_row=session.scroll_offset)

    data_window = Window(
        content=FormattedTextControl(
            text=get_data_content,
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

    # Data panel navigation (only when data window is focused)
    from prompt_toolkit.filters import has_focus

    data_focused = has_focus(data_window)

    # 'v' key to toggle between results and chart view (when data panel focused and have chart)
    has_chart = Condition(lambda: session.has_chart())
    @kb.add("v", filter=data_focused & has_chart)
    def toggle_view(event):
        """Toggle between results and chart view ('v' when data panel focused)."""
        session.toggle_view()
        event.app.invalidate()

    # Only allow scrolling when in results view
    results_view = Condition(lambda: session.view_mode == "results")
    data_focused_results = data_focused & results_view

    @kb.add("down", filter=data_focused_results)
    def scroll_down(event):
        """Move selection down (Down arrow when data panel focused in results view)."""
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

    @kb.add("up", filter=data_focused_results)
    def scroll_up(event):
        """Move selection up (Up arrow when data panel focused in results view)."""
        if not session.has_results():
            return

        # Move selection up if possible
        if session.selected_row > 0:
            session.selected_row -= 1

            # Scroll viewport if selected row goes off top
            if session.selected_row < session.scroll_offset:
                session.scroll_offset -= 1

            event.app.invalidate()

    @kb.add("left", filter=data_focused_results)
    def scroll_left(event):
        """Scroll columns left (Left arrow when data panel focused in results view)."""
        if session.has_results() and session.column_offset > 0:
            session.column_offset -= 1
            event.app.invalidate()

    @kb.add("right", filter=data_focused_results)
    def scroll_right(event):
        """Scroll columns right (Right arrow when data panel focused in results view)."""
        if session.has_results():
            max_col_offset = max(0, len(session.columns) - 1)
            if session.column_offset < max_col_offset:
                session.column_offset += 1
                event.app.invalidate()

    # Chart view scrolling (up/down when viewing chart)
    chart_view = Condition(lambda: session.view_mode == "chart")
    data_focused_chart = data_focused & chart_view

    @kb.add("down", filter=data_focused_chart)
    def scroll_chart_down(event):
        """Scroll chart down (Down arrow when viewing chart)."""
        if session.has_chart():
            lines = session.chart.split('\n')
            page_size = 30
            max_offset = max(0, len(lines) - page_size)
            if session.chart_scroll_offset < max_offset:
                session.chart_scroll_offset += 1
                event.app.invalidate()

    @kb.add("up", filter=data_focused_chart)
    def scroll_chart_up(event):
        """Scroll chart up (Up arrow when viewing chart)."""
        if session.chart_scroll_offset > 0:
            session.chart_scroll_offset -= 1
            event.app.invalidate()

    # 'g' key to start/restart chart wizard
    # Works when: (1) viewing results OR (2) viewing chart
    # 'g' for "graph" - only works when data panel has focus, not while typing SQL
    @kb.add("g", filter=data_focused_results | data_focused_chart)
    def start_chart_wizard(event):
        """Start/restart chart wizard ('g' when data panel focused)."""
        # Start wizard (or restart if editing existing chart)
        session.view_mode = "wizard"
        session.wizard_step = "chart_type"
        session.wizard_chart_type = ""
        session.wizard_x_column = ""
        session.wizard_y_column = ""
        event.app.invalidate()

    # Wizard key handlers (only when in wizard mode)
    wizard_mode = Condition(lambda: session.view_mode == "wizard")

    # Handle number keys 1-9 for wizard selections
    for num in "123456789":
        @kb.add(num, filter=wizard_mode)
        def handle_wizard_choice(event, n=num):
            """Handle wizard number selection."""
            _handle_wizard_input(session, n)
            event.app.invalidate()

    # Escape key to cancel wizard
    @kb.add("escape", filter=wizard_mode)
    def cancel_wizard(event):
        """Cancel wizard and return to results."""
        session.view_mode = "results"
        session.wizard_step = ""
        event.app.invalidate()

    # 's' key to save query or chart (works globally except in wizard/save mode)
    not_wizard_or_save = Condition(lambda: session.view_mode not in ["wizard", "save_query", "save_chart"])
    @kb.add("s", filter=not_wizard_or_save)
    def save_handler(event):
        """Save current SQL query or chart ('s' key)."""
        if session.view_mode == "chart" and session.has_chart():
            # Save chart
            session.view_mode = "save_chart"
            session.save_input_buffer = ""
        elif session.sql.strip():
            # Save query
            session.view_mode = "save_query"
            session.save_input_buffer = ""
        event.app.invalidate()

    # Save mode key handlers (only when in save mode)
    save_mode = Condition(lambda: session.view_mode in ["save_query", "save_chart"])

    # Handle letter/number keys for save input
    for char in "abcdefghijklmnopqrstuvwxyz0123456789_-":
        @kb.add(char, filter=save_mode)
        def handle_save_char(event, c=char):
            """Handle character input in save mode."""
            session.save_input_buffer += c
            event.app.invalidate()

    # Backspace in save mode
    @kb.add("backspace", filter=save_mode)
    def handle_save_backspace(event):
        """Handle backspace in save mode."""
        if session.save_input_buffer:
            session.save_input_buffer = session.save_input_buffer[:-1]
            event.app.invalidate()

    # Enter to confirm save
    @kb.add("enter", filter=save_mode)
    def confirm_save(event):
        """Confirm save and write file."""
        if session.save_input_buffer.strip():
            name = session.save_input_buffer.strip()
            if session.view_mode == "save_query":
                # Save query
                if save_query(name, session.sql):
                    # Show success message briefly by storing in chart field
                    prev_chart = session.chart
                    session.chart = f"✓ Query saved as '{name}'"
                    session.view_mode = "chart"
                    event.app.invalidate()
                    # Schedule return to previous view
                    import threading
                    def restore_view():
                        import time
                        time.sleep(1.5)
                        session.chart = prev_chart
                        session.view_mode = "results" if not prev_chart else "chart"
                        event.app.invalidate()
                    threading.Thread(target=restore_view, daemon=True).start()
                else:
                    session.chart = "Error: Failed to save query"
                    session.view_mode = "chart"
            else:  # save_chart
                # TODO: Implement chart saving
                session.chart = "Chart saving not yet implemented"
                session.view_mode = "chart"
            session.save_input_buffer = ""
        event.app.invalidate()

    # Escape to cancel save
    @kb.add("escape", filter=save_mode)
    def cancel_save(event):
        """Cancel save and return to previous view."""
        prev_mode = "chart" if session.view_mode == "save_chart" else "results"
        session.view_mode = prev_mode
        session.save_input_buffer = ""
        event.app.invalidate()

    # 'r' key to reset (clear results/chart, keep SQL)
    @kb.add("r", filter=not_wizard_or_save)
    def reset_handler(event):
        """Reset results and chart, keep SQL ('r' key)."""
        session.results = None
        session.columns = None
        session.chart = None
        session.view_mode = "results"
        session.scroll_offset = 0
        session.column_offset = 0
        session.selected_row = 0
        session.chart_scroll_offset = 0
        event.app.invalidate()

    # Status bar with dynamic focus and view mode indicators
    def get_status_text():
        from prompt_toolkit.application import get_app
        app = get_app()

        # Base keybindings
        base = "Analysis Mode  [Ctrl+Enter] execute  [s] save  [r] reset  [Ctrl+C] quit"

        # Add context-aware hints
        hints = []
        if app.layout.has_focus(data_window):
            if session.view_mode == "results":
                hints.append("[←↓↑→] scroll")
                if session.has_results():
                    hints.append("[g] chart")
                if session.has_chart():
                    hints.append("[v] view chart")
            elif session.view_mode == "chart":
                hints.append("[↓↑] scroll")
                hints.append("[v] view results")
                hints.append("[g] edit chart")
            elif session.view_mode == "wizard":
                hints.append("[1-9] select")
                hints.append("[Esc] cancel")
        else:  # SQL editor focused
            hints.append("[Tab] to data")

        hint_text = "  " + "  ".join(hints) if hints else ""
        return [("reverse", f" {base}{hint_text} ")]

    status_bar = Window(
        content=FormattedTextControl(get_status_text),
        height=1,
        align=WindowAlign.LEFT,
    )

    root_container = HSplit(
        [
            status_bar,
            data_window,
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
