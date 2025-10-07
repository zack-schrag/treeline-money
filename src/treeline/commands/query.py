"""Query and clear commands."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel
from treeline.theme import get_theme

console = Console()
theme = get_theme()

# Global conversation history for chat mode
conversation_history = []


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


def handle_clear_command() -> None:
    """Handle /clear command - reset conversation session."""
    container = get_container()
    agent_service = container.agent_service()

    result = asyncio.run(agent_service.clear_session())

    if result.success:
        console.print(f"[{theme.success}]✓[/{theme.success}] Conversation cleared. Starting fresh!\n")
    else:
        console.print(f"[{theme.warning}]Note: {result.error}[/{theme.warning}]\n")


def handle_query_command(sql: str) -> None:
    """Handle /query command - execute SQL directly."""
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
    console.print(f"\n[{theme.muted}]{len(rows)} row{'s' if len(rows) != 1 else ''} returned[/{theme.muted}]\n")


