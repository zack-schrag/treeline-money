"""Saved queries functionality."""

import re

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def validate_query_name(name: str) -> bool:
    """Validate that a query name contains only alphanumeric characters and underscores.

    Args:
        name: The query name to validate

    Returns:
        True if valid, False otherwise
    """
    if not name:
        return False
    # Only allow alphanumeric and underscores
    return bool(re.match(r'^[a-zA-Z0-9_]+$', name))


# Convenience wrappers for backward compatibility
def save_query(name: str, sql: str) -> bool:
    """Save a query using the storage abstraction."""
    container = get_container()
    return container.query_storage().save(name, sql)


def load_query(name: str) -> str | None:
    """Load a query using the storage abstraction."""
    container = get_container()
    return container.query_storage().load(name)


def list_queries() -> list[str]:
    """List all saved queries using the storage abstraction."""
    container = get_container()
    return container.query_storage().list()


def delete_query(name: str) -> bool:
    """Delete a saved query using the storage abstraction."""
    container = get_container()
    return container.query_storage().delete(name)


def query_exists(name: str) -> bool:
    """Check if a query exists using the storage abstraction."""
    container = get_container()
    return container.query_storage().exists(name)


def show_query(name: str) -> None:
    """Display a saved query.

    Args:
        name: The name of the query (without .sql extension)
    """
    sql = load_query(name)

    if sql is None:
        console.print(f"\n[{theme.error}]Query '{name}' not found.[/{theme.error}]")
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/queries list[/{theme.emphasis}] to see available queries.[/{theme.muted}]\n")
        return

    # Display the query with syntax highlighting
    console.print()
    syntax = Syntax(sql, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(
        syntax,
        title=f"[{theme.ui_header}]{name}[/{theme.ui_header}]",
        border_style=theme.primary,
        padding=(0, 1),
    ))
    console.print()


def handle_queries_command(subcommand: str | None = None, query_name: str | None = None) -> None:
    """Handle /queries command with subcommands.

    Args:
        subcommand: The subcommand (list, show, delete, or None for list)
        query_name: The query name for show/delete commands
    """
    if subcommand is None or subcommand == "list":
        # List all queries
        queries = list_queries()

        console.print()
        if not queries:
            console.print(f"[{theme.muted}]No saved queries yet.[/{theme.muted}]")
            console.print(f"[{theme.muted}]After running a query, you'll be prompted to save it.[/{theme.muted}]\n")
            return

        console.print(f"[{theme.ui_header}]Saved Queries[/{theme.ui_header}]\n")
        for query in queries:
            console.print(f"  • [{theme.emphasis}]{query}[/{theme.emphasis}]")

        console.print()
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/query:{theme.emphasis}query_name[/{theme.emphasis}] to run a saved query[/{theme.muted}]")
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/queries show query_name[/{theme.emphasis}] to view a query[/{theme.muted}]\n")

    elif subcommand == "show":
        if not query_name:
            console.print(f"[{theme.error}]Error: /queries show requires a query name[/{theme.error}]")
            console.print(f"[{theme.muted}]Usage: /queries show query_name[/{theme.muted}]\n")
            return

        show_query(query_name)

    elif subcommand == "delete":
        if not query_name:
            console.print(f"[{theme.error}]Error: /queries delete requires a query name[/{theme.error}]")
            console.print(f"[{theme.muted}]Usage: /queries delete query_name[/{theme.muted}]\n")
            return

        result = delete_query(query_name)
        if result:
            console.print(f"\n[{theme.success}]✓[/{theme.success}] Deleted query '[{theme.emphasis}]{query_name}[/{theme.emphasis}]'\n")
        else:
            console.print(f"\n[{theme.error}]Query '{query_name}' not found.[/{theme.error}]\n")

    else:
        console.print(f"[{theme.error}]Unknown subcommand: {subcommand}[/{theme.error}]")
        console.print(f"[{theme.muted}]Available: /queries list, /queries show <name>, /queries delete <name>[/{theme.muted}]\n")
