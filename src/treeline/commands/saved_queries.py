"""Saved queries functionality."""

import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_queries_dir() -> Path:
    """Get the directory where saved queries are stored.

    Returns:
        Path to ~/.treeline/queries/
    """
    return Path.home() / ".treeline" / "queries"


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


def save_query(name: str, sql: str, queries_dir: Path | None = None) -> bool:
    """Save a query to a file.

    Args:
        name: The name for the query (without .sql extension)
        sql: The SQL query content
        queries_dir: Directory to save to (defaults to get_queries_dir())

    Returns:
        True if saved successfully, False otherwise
    """
    if queries_dir is None:
        queries_dir = get_queries_dir()

    try:
        # Create directory if it doesn't exist
        queries_dir.mkdir(parents=True, exist_ok=True)

        # Write the query to file
        query_file = queries_dir / f"{name}.sql"
        query_file.write_text(sql)

        return True
    except Exception:
        return False


def load_query(name: str, queries_dir: Path | None = None) -> str | None:
    """Load a query from a file.

    Args:
        name: The name of the query (without .sql extension)
        queries_dir: Directory to load from (defaults to get_queries_dir())

    Returns:
        The SQL query content, or None if file doesn't exist
    """
    if queries_dir is None:
        queries_dir = get_queries_dir()

    query_file = queries_dir / f"{name}.sql"

    if not query_file.exists():
        return None

    try:
        return query_file.read_text()
    except Exception:
        return None


def list_queries(queries_dir: Path | None = None) -> list[str]:
    """List all saved queries.

    Args:
        queries_dir: Directory to list from (defaults to get_queries_dir())

    Returns:
        List of query names (without .sql extension)
    """
    if queries_dir is None:
        queries_dir = get_queries_dir()

    if not queries_dir.exists():
        return []

    try:
        # Get all .sql files and remove the extension
        return sorted([f.stem for f in queries_dir.glob("*.sql")])
    except Exception:
        return []


def delete_query(name: str, queries_dir: Path | None = None) -> bool:
    """Delete a saved query.

    Args:
        name: The name of the query (without .sql extension)
        queries_dir: Directory containing the query (defaults to get_queries_dir())

    Returns:
        True if deleted successfully, False if file doesn't exist or error
    """
    if queries_dir is None:
        queries_dir = get_queries_dir()

    query_file = queries_dir / f"{name}.sql"

    if not query_file.exists():
        return False

    try:
        query_file.unlink()
        return True
    except Exception:
        return False


def show_query(name: str, queries_dir: Path | None = None) -> None:
    """Display a saved query.

    Args:
        name: The name of the query (without .sql extension)
        queries_dir: Directory containing the query (defaults to get_queries_dir())
    """
    sql = load_query(name, queries_dir)

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
