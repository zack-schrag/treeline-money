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
    # Clear previous error
    session.error_message = ""

    if not session.sql.strip():
        return

    # Validate SELECT only
    sql_upper = session.sql.strip().upper()
    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        # Store error in session
        session.results = None
        session.columns = None
        session.error_message = "Only SELECT and WITH queries are allowed in analysis mode"
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
        session.error_message = ""  # Clear any previous errors
    else:
        # Store error message
        session.results = None
        session.columns = None
        session.error_message = f"Query failed: {result.error}"


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
    # Show error message if there is one
    if session.error_message:
        return [
            ("fg:red bold", "Error\n\n"),
            ("fg:red", session.error_message),
            ("", "\n\nFix the SQL below and press Ctrl+Enter to execute again.")
        ]

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
    """Format chart, wizard, save, or browser UI for display.

    Args:
        session: AnalysisSession with chart or wizard state

    Returns:
        List of (style, text) tuples for FormattedTextControl
    """
    # Show help overlay if in help mode
    if session.view_mode == "help":
        return _format_help_overlay()

    # Show load menu
    if session.view_mode == "load_menu":
        return _format_load_menu()

    # Show browser UIs
    if session.view_mode == "browse_query":
        return _format_browser_ui(session, "query")
    if session.view_mode == "browse_chart":
        return _format_browser_ui(session, "chart")

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


def _format_load_menu() -> list:
    """Format the load menu showing options to load query or chart.

    Returns:
        List of (style, text) tuples for load menu
    """
    result = []
    result.append(("bold #44755a", "Load Saved Item"))
    result.append(("", "\n\n"))
    result.append(("", "What would you like to load?\n\n"))
    result.append(("", "  [q] Query\n"))
    result.append(("", "  [c] Chart\n\n"))
    result.append(("class:muted", "Press q or c to select, Esc to cancel"))
    return result


def _format_browser_ui(session: AnalysisSession, browser_type: str) -> list:
    """Format the browser UI for saved queries or charts.

    Args:
        session: AnalysisSession with browser state
        browser_type: "query" or "chart"

    Returns:
        List of (style, text) tuples for browser UI
    """
    result = []
    result.append(("bold #44755a", f"Load {browser_type.title()}"))
    result.append(("", "\n\n"))

    if not session.browse_items:
        result.append(("class:muted", f"No saved {browser_type}s found"))
        result.append(("", "\n\n"))
        result.append(("class:muted", "Press Esc to cancel"))
        return result

    # Show list with selection indicator
    for i, item in enumerate(session.browse_items):
        if i == session.browse_selected_index:
            # Highlight selected item with green background
            result.append(("bg:#44755a fg:white", f"→ {item}"))
        else:
            result.append(("", f"  {item}"))
        result.append(("", "\n"))

    result.append(("", "\n"))
    result.append(("class:muted", "↑↓ to navigate, Enter to load, Esc to cancel"))
    return result


def _format_help_overlay() -> list:
    """Format the help overlay showing all keybindings.

    Returns:
        List of (style, text) tuples for help overlay
    """
    result = []
    result.append(("bold #44755a", "╭─ Analysis Mode Shortcuts "))
    result.append(("bold #44755a", "─" * 30))
    result.append(("bold #44755a", "╮\n"))
    result.append(("bold", "│ SQL Execution"))
    result.append(("", " " * 38))
    result.append(("", "│\n"))
    result.append(("", "│   Ctrl+Enter  - Execute query"))
    result.append(("", " " * 24))
    result.append(("", "│\n"))
    result.append(("", "│"))
    result.append(("", " " * 59))
    result.append(("", "│\n"))
    result.append(("bold", "│ Navigation"))
    result.append(("", " " * 42))
    result.append(("", "│\n"))
    result.append(("", "│   Tab         - Switch focus (SQL ↔ Data panel)"))
    result.append(("", " " * 6))
    result.append(("", "│\n"))
    result.append(("", "│   ↑↓←→        - Context-aware (edit SQL or scroll)"))
    result.append(("", " " * 3))
    result.append(("", "│\n"))
    result.append(("", "│"))
    result.append(("", " " * 59))
    result.append(("", "│\n"))
    result.append(("bold", "│ Data Panel (when focused)"))
    result.append(("", " " * 27))
    result.append(("", "│\n"))
    result.append(("", "│   ↑↓          - Scroll results vertically"))
    result.append(("", " " * 12))
    result.append(("", "│\n"))
    result.append(("", "│   Shift+←→    - Scroll columns horizontally"))
    result.append(("", " " * 10))
    result.append(("", "│\n"))
    result.append(("", "│   v           - Toggle results ↔ chart view"))
    result.append(("", " " * 10))
    result.append(("", "│\n"))
    result.append(("", "│"))
    result.append(("", " " * 59))
    result.append(("", "│\n"))
    result.append(("bold", "│ Charts"))
    result.append(("", " " * 46))
    result.append(("", "│\n"))
    result.append(("", "│   g           - Create/edit chart (wizard)"))
    result.append(("", " " * 12))
    result.append(("", "│\n"))
    result.append(("", "│   s           - Save query or chart"))
    result.append(("", " " * 19))
    result.append(("", "│\n"))
    result.append(("", "│   l           - Load saved query or chart"))
    result.append(("", " " * 12))
    result.append(("", "│\n"))
    result.append(("", "│"))
    result.append(("", " " * 59))
    result.append(("", "│\n"))
    result.append(("bold", "│ Actions"))
    result.append(("", " " * 45))
    result.append(("", "│\n"))
    result.append(("", "│   r           - Reset (clear results/chart)"))
    result.append(("", " " * 11))
    result.append(("", "│\n"))
    result.append(("", "│   Ctrl+C      - Exit analysis mode"))
    result.append(("", " " * 19))
    result.append(("", "│\n"))
    result.append(("", "│   ?           - Show this help"))
    result.append(("", " " * 23))
    result.append(("", "│\n"))
    result.append(("bold #44755a", "╰"))
    result.append(("bold #44755a", "─" * 59))
    result.append(("bold #44755a", "╯\n\n"))
    result.append(("class:muted", "Press any key to close"))

    return result


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

    # Create data window that toggles between results, chart, wizard, save, and browser based on view_mode
    def get_data_content():
        """Return formatted text for data panel (results, chart, wizard, save, or browser)."""
        if session.view_mode in ["chart", "wizard", "save_query", "save_chart", "help", "load_menu", "browse_query", "browse_chart"]:
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

    # 's' key to save query or chart (only when data panel focused, not while typing SQL)
    not_wizard_or_save = Condition(lambda: session.view_mode not in ["wizard", "save_query", "save_chart"])
    @kb.add("s", filter=data_focused & not_wizard_or_save)
    def save_handler(event):
        """Save current SQL query or chart ('s' when data panel focused)."""
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
                # Save chart config
                from treeline.commands.chart_config import ChartConfig, ChartConfigStore, get_charts_dir, serialize_chart_config

                # Build chart config from current state
                if session.has_chart() and session.has_results() and session.wizard_chart_type:
                    chart_config = ChartConfig(
                        name=name,
                        query=session.sql,
                        chart_type=session.wizard_chart_type,
                        x_column=session.wizard_x_column,
                        y_column=session.wizard_y_column or "",
                        title=f"{session.wizard_y_column} by {session.wizard_x_column}" if session.wizard_y_column else session.wizard_x_column,
                    )
                    store = ChartConfigStore(get_charts_dir())
                    if store.save(name, chart_config):
                        prev_chart = session.chart
                        session.chart = f"✓ Chart saved as '{name}'"
                        session.view_mode = "chart"
                        event.app.invalidate()
                        # Schedule return to previous view
                        import threading
                        def restore_view():
                            import time
                            time.sleep(1.5)
                            session.chart = prev_chart
                            session.view_mode = "chart"
                            event.app.invalidate()
                        threading.Thread(target=restore_view, daemon=True).start()
                    else:
                        session.chart = "Error: Failed to save chart"
                        session.view_mode = "chart"
                else:
                    session.chart = "Error: No chart to save"
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

    # 'r' key to reset (clear results/chart, keep SQL) - only when data panel focused
    @kb.add("r", filter=data_focused & not_wizard_or_save)
    def reset_handler(event):
        """Reset results and chart, keep SQL ('r' when data panel focused)."""
        session.results = None
        session.columns = None
        session.chart = None
        session.view_mode = "results"
        session.scroll_offset = 0
        session.column_offset = 0
        session.selected_row = 0
        session.chart_scroll_offset = 0
        event.app.invalidate()

    # '?' key to show help overlay - only when data panel focused
    not_help_or_wizard_or_save = Condition(lambda: session.view_mode not in ["help", "wizard", "save_query", "save_chart"])
    @kb.add("?", filter=data_focused & not_help_or_wizard_or_save)
    def show_help(event):
        """Show help overlay ('?' when data panel focused)."""
        session.view_mode = "help"
        event.app.invalidate()

    # Help mode key handler (any key dismisses help)
    help_mode = Condition(lambda: session.view_mode == "help")
    # Use a catch-all handler for any key in help mode
    @kb.add("<any>", filter=help_mode)
    def dismiss_help(event):
        """Dismiss help overlay (any key when in help mode)."""
        # Return to results view
        session.view_mode = "results" if session.has_results() else "results"
        event.app.invalidate()

    # 'l' key to show load menu - only when data panel focused
    not_special_mode = Condition(lambda: session.view_mode not in ["help", "wizard", "save_query", "save_chart", "load_menu", "browse_query", "browse_chart"])
    @kb.add("l", filter=data_focused & not_special_mode)
    def show_load_menu(event):
        """Show load menu ('l' when data panel focused)."""
        session.view_mode = "load_menu"
        event.app.invalidate()

    # Load menu key handlers
    load_menu_mode = Condition(lambda: session.view_mode == "load_menu")

    @kb.add("q", filter=load_menu_mode)
    def browse_queries(event):
        """Browse saved queries ('q' in load menu)."""
        from treeline.commands.saved_queries import list_queries
        session.view_mode = "browse_query"
        session.browse_items = list_queries()
        session.browse_selected_index = 0
        event.app.invalidate()

    @kb.add("c", filter=load_menu_mode)
    def browse_charts(event):
        """Browse saved charts ('c' in load menu)."""
        from treeline.commands.chart_config import ChartConfigStore, get_charts_dir
        store = ChartConfigStore(get_charts_dir())
        session.view_mode = "browse_chart"
        session.browse_items = store.list()
        session.browse_selected_index = 0
        event.app.invalidate()

    @kb.add("escape", filter=load_menu_mode)
    def cancel_load_menu(event):
        """Cancel load menu and return to previous view."""
        session.view_mode = "results"
        event.app.invalidate()

    # Browser key handlers
    browse_query_mode = Condition(lambda: session.view_mode == "browse_query")
    browse_chart_mode = Condition(lambda: session.view_mode == "browse_chart")
    browse_mode = browse_query_mode | browse_chart_mode

    @kb.add("up", filter=browse_mode)
    def browse_up(event):
        """Move selection up in browser."""
        if session.browse_selected_index > 0:
            session.browse_selected_index -= 1
            event.app.invalidate()

    @kb.add("down", filter=browse_mode)
    def browse_down(event):
        """Move selection down in browser."""
        if session.browse_selected_index < len(session.browse_items) - 1:
            session.browse_selected_index += 1
            event.app.invalidate()

    @kb.add("enter", filter=browse_query_mode)
    def load_selected_query(event):
        """Load selected query and execute it."""
        if session.browse_items:
            from treeline.commands.saved_queries import load_query
            query_name = session.browse_items[session.browse_selected_index]
            query_sql = load_query(query_name)
            if query_sql:
                session.sql = query_sql
                # Update the buffer's document to show the loaded SQL
                sql_buffer.document = Document(query_sql, len(query_sql))
                # Clear previous results/chart when loading new query
                session.results = None
                session.columns = None
                session.chart = None
                session.view_mode = "results"
                session.browse_items = []
                # Execute the query immediately
                async def run_query():
                    await _execute_query(session)
                    # Focus data panel to show results
                    event.app.layout.focus(data_window)
                    event.app.invalidate()
                asyncio.ensure_future(run_query())
            event.app.invalidate()

    @kb.add("enter", filter=browse_chart_mode)
    def load_selected_chart(event):
        """Load selected chart, execute query, and display chart."""
        if session.browse_items:
            from treeline.commands.chart_config import ChartConfigStore, get_charts_dir
            from treeline.commands.chart_wizard import create_chart_from_config
            chart_name = session.browse_items[session.browse_selected_index]
            store = ChartConfigStore(get_charts_dir())
            chart_config = store.load(chart_name)
            if chart_config:
                # Load the SQL from chart config
                session.sql = chart_config.query
                # Update the buffer's document to show the loaded SQL
                sql_buffer.document = Document(chart_config.query, len(chart_config.query))
                session.browse_items = []

                # Store chart config in wizard state for later editing/saving
                session.wizard_chart_type = chart_config.chart_type
                session.wizard_x_column = chart_config.x_column
                session.wizard_y_column = chart_config.y_column

                # Execute query and create chart
                async def run_query_and_chart():
                    await _execute_query(session)
                    # After query executes, create the chart
                    if session.has_results():
                        # Convert ChartConfig to ChartWizardConfig
                        from treeline.commands.chart_wizard import ChartWizardConfig
                        wizard_config = ChartWizardConfig(
                            chart_type=chart_config.chart_type,
                            x_column=chart_config.x_column,
                            y_column=chart_config.y_column,
                            title=chart_config.title,
                            xlabel=chart_config.xlabel,
                            ylabel=chart_config.ylabel,
                            color=chart_config.color,
                            width=100,
                            height=20,
                        )
                        result = create_chart_from_config(wizard_config, session.columns, session.results)
                        if result.success:
                            session.chart = result.data
                            session.view_mode = "chart"
                        else:
                            session.error_message = f"Failed to create chart: {result.error}"
                    # Focus data panel to show chart
                    event.app.layout.focus(data_window)
                    event.app.invalidate()

                asyncio.ensure_future(run_query_and_chart())
            event.app.invalidate()

    @kb.add("escape", filter=browse_mode)
    def cancel_browse(event):
        """Cancel browser and return to previous view."""
        session.browse_items = []
        session.view_mode = "results"
        event.app.invalidate()

    # Status bar with dynamic focus and view mode indicators
    def get_status_text():
        from prompt_toolkit.application import get_app
        app = get_app()

        # Base keybindings
        base = "Analysis Mode  [Ctrl+Enter] execute  [s] save  [l] load  [?] help  [Ctrl+C] quit"

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
