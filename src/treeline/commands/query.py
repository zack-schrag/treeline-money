"""Query and clear commands."""

import asyncio
from uuid import UUID

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.sql import SqlLexer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from treeline.theme import get_theme
from treeline.commands.saved_queries import (
    get_queries_dir,
    list_queries,
    load_query,
    save_query,
    validate_query_name,
)
from treeline.commands.chart_config import (
    ChartConfig,
    ChartConfigStore,
    get_charts_dir,
)
from treeline.commands.chart_wizard import (
    ChartWizardConfig,
    create_chart_from_config,
    validate_chart_data,
)

console = Console()
theme = get_theme()

# Global conversation history for chat mode
conversation_history = []


class SavedQueryCompleter(Completer):
    """Completer that suggests saved query names when typing in SQL editor."""

    def get_completions(self, document, complete_event):
        """Generate completions for saved queries.

        Triggers when user types '/load ' or just starts typing a query name.
        """
        text = document.text_before_cursor

        # Get all saved queries
        queries = list_queries()

        if not queries:
            return

        # Check if user is trying to load a query (typed "/load ")
        if text.lower().startswith("/load "):
            query_prefix = text[6:]  # Remove "/load "
            for query_name in queries:
                if query_name.lower().startswith(query_prefix.lower()):
                    # Load the actual SQL content
                    sql_content = load_query(query_name)
                    if sql_content:
                        yield Completion(
                            sql_content,
                            start_position=-len(query_prefix),
                            display=f"📄 {query_name}",
                        )
        # Also suggest at the beginning if buffer is empty or just whitespace
        elif len(text.strip()) == 0 or text.strip().startswith("/"):
            for query_name in queries:
                # Load the actual SQL content
                sql_content = load_query(query_name)
                if sql_content:
                    yield Completion(
                        sql_content,
                        start_position=-len(text),
                        display=f"📄 {query_name}",
                        display_meta="(saved query)",
                    )


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


def _prompt_to_save_query_with_loopback(sql: str, loop_back_handler) -> None:
    """Prompt user to save a query and optionally return to editor.

    Args:
        sql: The SQL query that was executed
        loop_back_handler: Callback to invoke to return to editor
    """
    try:
        # Ask if user wants to save
        save = Confirm.ask(f"[{theme.info}]Save this query?[/{theme.info}]", default=False)

        if save:
            # Get query name
            while True:
                name = Prompt.ask(f"[{theme.info}]Query name[/{theme.info}]")

                if not name:
                    console.print(f"[{theme.warning}]Cancelled[/{theme.warning}]\n")
                    break

                # Validate name
                if not validate_query_name(name):
                    console.print(f"[{theme.error}]Invalid name. Use only letters, numbers, and underscores.[/{theme.error}]")
                    continue

                # Check if file already exists
                queries_dir = get_queries_dir()
                query_file = queries_dir / f"{name}.sql"

                if query_file.exists():
                    overwrite = Confirm.ask(
                        f"[{theme.warning}]Query '{name}' already exists. Overwrite?[/{theme.warning}]",
                        default=False
                    )
                    if not overwrite:
                        continue

                # Save the query
                if save_query(name, sql):
                    console.print(f"[{theme.success}]✓[/{theme.success}] Saved as [{theme.emphasis}]{query_file}[/{theme.emphasis}]\n")
                else:
                    console.print(f"[{theme.error}]Failed to save query[/{theme.error}]\n")
                break

        # Ask if they want to continue editing
        console.print()
        continue_editing = Confirm.ask(f"[{theme.info}]Continue editing?[/{theme.info}]", default=True)
        if continue_editing:
            loop_back_handler()

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]\n")


def _prompt_to_save_query(sql: str) -> None:
    """Prompt user to save a query after execution.

    Args:
        sql: The SQL query that was executed
    """
    try:
        # Ask if user wants to save
        save = Confirm.ask(f"[{theme.info}]Save this query?[/{theme.info}]", default=False)

        if not save:
            return

        # Get query name
        while True:
            name = Prompt.ask(f"[{theme.info}]Query name[/{theme.info}]")

            if not name:
                console.print(f"[{theme.warning}]Cancelled[/{theme.warning}]\n")
                return

            # Validate name
            if not validate_query_name(name):
                console.print(f"[{theme.error}]Invalid name. Use only letters, numbers, and underscores.[/{theme.error}]")
                continue

            # Check if file already exists
            queries_dir = get_queries_dir()
            query_file = queries_dir / f"{name}.sql"

            if query_file.exists():
                overwrite = Confirm.ask(
                    f"[{theme.warning}]Query '{name}' already exists. Overwrite?[/{theme.warning}]",
                    default=False
                )
                if not overwrite:
                    continue

            # Save the query
            if save_query(name, sql):
                console.print(f"[{theme.success}]✓[/{theme.success}] Saved as [{theme.emphasis}]{query_file}[/{theme.emphasis}]\n")
            else:
                console.print(f"[{theme.error}]Failed to save query[/{theme.error}]\n")
            break

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]\n")


def _prompt_chart_wizard(sql: str, columns: list[str], rows: list[list]) -> None:
    """Prompt user to create a chart from query results.

    NOTE: This function is called from the action menu, so it doesn't
    ask "Create a chart?" - the user has already chosen that option.

    Args:
        sql: The SQL query that was executed
        columns: Column names from query results
        rows: Query result rows
    """
    try:
        console.print()

        # Get chart type
        chart_type = Prompt.ask(
            f"[{theme.info}]Chart type[/{theme.info}]",
            choices=["bar", "line", "scatter", "histogram"],
            default="line"
        )

        # Show available columns
        console.print(f"\n[{theme.muted}]Available columns: {', '.join(columns)}[/{theme.muted}]\n")

        # Get X column
        while True:
            x_column = Prompt.ask(f"[{theme.info}]X axis column[/{theme.info}]")
            if x_column in columns:
                break
            console.print(f"[{theme.error}]Column '{x_column}' not found. Try again.[/{theme.error}]")

        # Get Y column (not needed for histogram)
        y_column = ""
        if chart_type != "histogram":
            while True:
                y_column = Prompt.ask(f"[{theme.info}]Y axis column[/{theme.info}]")
                if y_column in columns:
                    break
                console.print(f"[{theme.error}]Column '{y_column}' not found. Try again.[/{theme.error}]")

        # Optional: title
        title = Prompt.ask(f"[{theme.info}]Chart title (optional)[/{theme.info}]", default="")

        # Optional: color
        color_choices = ["green", "blue", "red", "yellow", "cyan", "magenta"]
        default_colors = {"bar": "green", "line": "blue", "scatter": "red", "histogram": "cyan"}
        color = Prompt.ask(
            f"[{theme.info}]Color[/{theme.info}]",
            choices=color_choices,
            default=default_colors.get(chart_type, "blue"),
            show_choices=False,
        )

        # Create wizard config
        config = ChartWizardConfig(
            chart_type=chart_type,
            x_column=x_column,
            y_column=y_column,
            title=title if title else None,
            color=color,
        )

        # Generate chart
        console.print()
        with console.status(f"[{theme.muted}]Generating chart...[/{theme.muted}]"):
            result = create_chart_from_config(config, columns, rows)

        if not result.success:
            console.print(f"[{theme.error}]Error: {result.error}[/{theme.error}]\n")
            return

        # Display chart
        console.print(result.data)

        # Ask if user wants to save chart config
        console.print()
        save_chart = Confirm.ask(f"[{theme.info}]Save chart config?[/{theme.info}]", default=False)

        if not save_chart:
            return

        # Get chart name
        store = ChartConfigStore(get_charts_dir())
        while True:
            name = Prompt.ask(f"[{theme.info}]Chart name[/{theme.info}]")

            if not name:
                console.print(f"[{theme.warning}]Cancelled[/{theme.warning}]\n")
                return

            # Validate name
            if not store.validate_name(name):
                console.print(f"[{theme.error}]Invalid name. Use only letters, numbers, and underscores.[/{theme.error}]")
                continue

            # Check if already exists
            if name in store.list():
                overwrite = Confirm.ask(
                    f"[{theme.warning}]Chart '{name}' already exists. Overwrite?[/{theme.warning}]",
                    default=False
                )
                if not overwrite:
                    continue

            # Save the chart
            chart_config = ChartConfig(
                name=name,
                query=sql,
                chart_type=chart_type,
                x_column=x_column,
                y_column=y_column,
                title=title if title else None,
                color=color,
            )

            if store.save(name, chart_config):
                chart_file = get_charts_dir() / f"{name}.tl"
                console.print(f"[{theme.success}]✓[/{theme.success}] Saved as [{theme.emphasis}]{chart_file}[/{theme.emphasis}]\n")
            else:
                console.print(f"[{theme.error}]Failed to save chart[/{theme.error}]\n")
            break

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]\n")


def _prompt_post_query_actions(
    sql: str,
    columns: list[str],
    rows: list[list],
    loop_back_handler=None
) -> None:
    """Prompt user for next action after query execution.

    Single action menu that replaces the old sequential prompts
    (chart? → save? → continue editing?). Users can now choose
    one action at a time from a clear menu.

    Args:
        sql: The SQL query that was executed
        columns: Column names from results
        rows: Query result rows
        loop_back_handler: Optional callback to return to SQL editor
    """
    try:
        while True:
            console.print()
            console.print(f"[{theme.info}][c][/{theme.info}]hart  [{theme.info}][s][/{theme.info}]ave  [{theme.info}][e][/{theme.info}]dit  [white][enter] to continue[/white]")
            action = Prompt.ask(
                "Next",
                default="",
                show_default=False
            )

            if action == "":
                # Enter pressed - exit cleanly
                return
            elif action.lower() == "c":
                # Chart wizard
                _prompt_chart_wizard(sql, columns, rows)
                # After charting, loop back to menu (can save or edit afterward)
            elif action.lower() == "s":
                # Save query
                _prompt_to_save_query(sql)
                return
            elif action.lower() == "e":
                # Edit SQL - loop back
                if loop_back_handler:
                    loop_back_handler()
                return
            else:
                console.print(f"[{theme.error}]Invalid option. Use c/s/e or press enter[/{theme.error}]")

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.muted}]Exiting[/{theme.muted}]\n")


def handle_clear_command() -> None:
    """Handle /clear command - reset conversation session."""
    container = get_container()
    agent_service = container.agent_service()

    result = asyncio.run(agent_service.clear_session())

    if result.success:
        console.print(f"[{theme.success}]✓[/{theme.success}] Conversation cleared. Starting fresh!\n")
    else:
        console.print(f"[{theme.warning}]Note: {result.error}[/{theme.warning}]\n")


def handle_query_command(sql: str, loop_back_handler=None) -> None:
    """Handle /query command - execute SQL directly.

    Args:
        sql: The SQL query to execute
        loop_back_handler: Optional callback to invoke after saving query (for looping back to editor)
    """
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax

    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    # Validate SQL - only allow SELECT and WITH queries
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        console.print(f"[{theme.error}]Error: Only SELECT and WITH queries are allowed.[/{theme.error}]")
        console.print(f"[{theme.muted}]For data modifications, use the AI agent.[/{theme.muted}]\n")
        return

    # Display the SQL query
    console.print()
    syntax = Syntax(sql_stripped, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(
        syntax,
        title=f"[{theme.ui_header}]Executing Query[/{theme.ui_header}]",
        border_style=theme.primary,
        padding=(0, 1),
    ))

    # Execute query
    with console.status(f"[{theme.muted}]Running query...[/{theme.muted}]"):
        result = asyncio.run(db_service.execute_query(user_id, sql_stripped))

    if not result.success:
        console.print(f"\n[{theme.error}]Error: {result.error}[/{theme.error}]\n")
        return

    # Format and display results
    query_result = result.data
    rows = query_result.get("rows", [])
    columns = query_result.get("columns", [])

    console.print()

    if len(rows) == 0:
        console.print(f"[{theme.muted}]No results returned.[/{theme.muted}]\n")
        return

    # Create Rich table
    table = Table(show_header=True, header_style=theme.ui_header, border_style=theme.separator)

    # Add columns
    for col in columns:
        table.add_column(col)

    # Add rows
    for row in rows:
        # Convert row values to strings
        str_row = [str(val) if val is not None else f"[{theme.muted}]NULL[/{theme.muted}]" for val in row]
        table.add_row(*str_row)

    console.print(table)
    console.print(f"\n[{theme.muted}]{len(rows)} row{'s' if len(rows) != 1 else ''} returned[/{theme.muted}]")

    # Single action menu replaces old sequential prompts
    _prompt_post_query_actions(sql_stripped, columns, rows, loop_back_handler)


def handle_sql_command(prefill_sql: str = "") -> None:
    """Handle /sql command - open multi-line SQL editor.

    Args:
        prefill_sql: Optional SQL to prefill the editor with (for looping after save)
    """
    container = get_container()
    config_service = container.config_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    # Show instructions with platform-specific key names
    import platform
    meta_key = "Option+Enter" if platform.system() == "Darwin" else "Alt+Enter"

    # Show instructions and saved queries count
    saved_queries = list_queries()
    console.print(f"\n[{theme.ui_header}]Multi-line SQL Editor[/{theme.ui_header}]")
    console.print(f"[{theme.muted}]Press [{meta_key}] or [F5] to execute query[/{theme.muted}]")
    if saved_queries:
        console.print(f"[{theme.muted}]Press [Tab] to load a saved query ({len(saved_queries)} available)[/{theme.muted}]")
    console.print(f"[{theme.muted}]Press [Ctrl+C] to cancel[/{theme.muted}]\n")

    # Create custom key bindings for Meta+Enter and F5 to execute
    bindings = KeyBindings()

    @bindings.add('escape', 'enter')
    def _(event):
        """Execute query on Meta+Enter (Alt/Option+Enter)."""
        event.current_buffer.validate_and_handle()

    @bindings.add('f5')
    def _(event):
        """Execute query on F5."""
        event.current_buffer.validate_and_handle()

    # Create prompt session with syntax highlighting, completer, and custom key bindings
    session = PromptSession(
        lexer=PygmentsLexer(SqlLexer),
        multiline=True,
        key_bindings=bindings,
        completer=SavedQueryCompleter(),
        complete_while_typing=False,  # Only show completions when Tab is pressed
    )

    try:
        # Get SQL input (with optional prefill)
        sql = session.prompt(">: ", default=prefill_sql)
    except KeyboardInterrupt:
        console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]\n")
        return
    except EOFError:
        # Ctrl+D pressed - get the current buffer content
        sql = session.default_buffer.text if hasattr(session, 'default_buffer') else ""
        if not sql or not sql.strip():
            console.print(f"\n[{theme.warning}]Cancelled[/{theme.warning}]\n")
            return

    # Handle empty input
    if not sql or not sql.strip():
        console.print(f"[{theme.muted}]No query entered[/{theme.muted}]\n")
        return

    # Execute using the existing query handler, passing the sql for potential loop-back
    handle_query_command(sql, loop_back_handler=lambda: handle_sql_command(prefill_sql=sql))


