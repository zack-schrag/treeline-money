"""Schema browser command."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


# Example queries for each table
EXAMPLE_QUERIES = {
    "transactions": """SELECT *
FROM transactions
WHERE amount < 0
  AND transaction_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY transaction_date DESC
LIMIT 10;""",
    "accounts": """SELECT
  account_name,
  institution_name,
  account_type,
  currency
FROM accounts
ORDER BY account_name;""",
    "balance_snapshots": """SELECT
  account_name,
  snapshot_time,
  balance
FROM balance_snapshots
WHERE account_id = 'your-account-id'
ORDER BY snapshot_time DESC
LIMIT 30;""",
    "sys_transactions": """SELECT *
FROM sys_transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY transaction_date DESC
LIMIT 20;""",
    "sys_accounts": """SELECT
  account_id,
  name,
  nickname,
  account_type,
  balance
FROM sys_accounts;""",
    "sys_balance_snapshots": """SELECT
  account_id,
  snapshot_time,
  balance
FROM sys_balance_snapshots
ORDER BY snapshot_time DESC
LIMIT 50;""",
    "sys_integrations": """SELECT
  integration_name,
  created_at,
  updated_at
FROM sys_integrations;""",
}


def handle_schema_command(table_name: str | None = None) -> None:
    """Handle /schema command - browse database schema.

    Args:
        table_name: Optional table name to show details for. If None, lists all tables.
    """
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    if table_name is None:
        # List all tables
        _list_tables(db_service, user_id)
    else:
        # Show table schema
        _show_table_schema(db_service, user_id, table_name)


def _list_tables(db_service, user_id: UUID) -> None:
    """List all tables in the database."""
    # Query to get all tables (both regular tables and views)
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'main'
    ORDER BY table_name;
    """

    result = asyncio.run(db_service.execute_query(user_id, sql))

    if not result.success:
        console.print(f"[{theme.error}]Error: {result.error}[/{theme.error}]\n")
        return

    rows = result.data.get("rows", [])

    console.print()
    console.print(f"[{theme.ui_header}]Available Tables and Views[/{theme.ui_header}]\n")

    if not rows:
        console.print(f"[{theme.muted}]No tables found. Have you synced your data yet?[/{theme.muted}]\n")
        return

    # Group into system tables and views
    system_tables = []
    user_views = []

    for row in rows:
        table = row[0]
        if table.startswith("sys_"):
            system_tables.append(table)
        else:
            user_views.append(table)

    if user_views:
        console.print(f"[{theme.info}]User Views (recommended):[/{theme.info}]")
        for table in user_views:
            console.print(f"  • [{theme.emphasis}]{table}[/{theme.emphasis}]")
        console.print()

    if system_tables:
        console.print(f"[{theme.muted}]System Tables:[/{theme.muted}]")
        for table in system_tables:
            console.print(f"  • [{theme.muted}]{table}[/{theme.muted}]")
        console.print()

    console.print(f"[{theme.muted}]Use [{theme.emphasis}]/schema <table_name>[/{theme.emphasis}] to see column details[/{theme.muted}]\n")


def _show_table_schema(db_service, user_id: UUID, table_name: str) -> None:
    """Show schema details for a specific table."""
    # Query to get columns for the table
    sql = f"""
    SELECT
        column_name,
        data_type,
        is_nullable
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
    ORDER BY ordinal_position;
    """

    result = asyncio.run(db_service.execute_query(user_id, sql))

    if not result.success:
        console.print(f"[{theme.error}]Error: {result.error}[/{theme.error}]\n")
        return

    rows = result.data.get("rows", [])

    if not rows:
        console.print(f"\n[{theme.error}]Table '{table_name}' not found.[/{theme.error}]")
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/schema[/{theme.emphasis}] to see available tables.[/{theme.muted}]\n")
        return

    # Display table info
    console.print()
    console.print(f"[{theme.ui_header}]Table: {table_name}[/{theme.ui_header}]\n")

    # Create Rich table
    table = Table(show_header=True, header_style=theme.ui_header, border_style=theme.separator)
    table.add_column("Column", style=theme.emphasis)
    table.add_column("Type", style=theme.info)
    table.add_column("Nullable", style=theme.neutral)

    for row in rows:
        column_name, data_type, is_nullable = row
        nullable_display = "YES" if is_nullable == "YES" else "NO"
        table.add_row(column_name, data_type, nullable_display)

    console.print(table)
    console.print()

    # Show example query if available
    if table_name in EXAMPLE_QUERIES:
        example_sql = EXAMPLE_QUERIES[table_name]
        syntax = Syntax(example_sql, "sql", theme="monokai", line_numbers=False)
        console.print(Panel(
            syntax,
            title=f"[{theme.ui_header}]Example Query[/{theme.ui_header}]",
            border_style=theme.primary,
            padding=(0, 1),
        ))
        console.print()
