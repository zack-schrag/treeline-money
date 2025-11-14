"""Treeline CLI - Interactive financial data management."""

import asyncio
import os
import sys
from pathlib import Path
from typing import List
from uuid import UUID
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

import json
from pydantic import BaseModel
from treeline.app.container import Container
from treeline.commands.import_csv import handle_import_command
from treeline.theme import get_theme
from treeline.utils import get_treeline_dir

# Load environment variables from .env file
load_dotenv()


def get_version() -> str:
    """Get the version from package metadata."""
    try:
        from importlib.metadata import version

        return version("treeline-money")
    except Exception:
        return "0.1.0"  # Fallback version


def version_callback(value: bool):
    """Show version information."""
    if value:
        console.print(get_version())
        raise typer.Exit()


app = typer.Typer(
    help="Treeline - personal finance in your terminal",
    add_completion=False,
    no_args_is_help=True,  # Show help by default
)
console = Console()
theme = get_theme()


@app.callback()
def main(
    _version: bool = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version information",
        callback=version_callback,
        is_eager=True,
    ),
):
    _ = _version  # Used by callback, suppress linter warning


# Global container instance
_container: Container | None = None


def get_container() -> Container:
    """Get or create the dependency injection container."""
    global _container
    if _container is None:
        treeline_dir = get_treeline_dir()
        # Use demo.duckdb in demo mode, otherwise treeline.duckdb
        demo_mode = os.getenv("TREELINE_DEMO_MODE", "").lower() in ("true", "1", "yes")
        db_filename = "demo.duckdb" if demo_mode else "treeline.duckdb"
        _container = Container(str(treeline_dir), db_filename)
    return _container


def display_error(error: str) -> None:
    """Display error message in consistent format.

    Args:
        error: Error message to display
    """
    console.print(f"[{theme.error}]Error: {error}[/{theme.error}]")


def output_json(data: dict) -> None:
    """Output data as JSON.

    Args:
        data: Data to output as JSON
    """

    def json_serializer(obj):
        """Custom JSON serializer for Pydantic models and other objects."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        return str(obj)

    print(json.dumps(data, indent=2, default=json_serializer))


def display_status(status: dict) -> None:
    """Display status using Rich formatting.

    Args:
        status: Status data from StatusService
    """
    console.print(
        f"\n[{theme.ui_header}]📊 Financial Data Status[/{theme.ui_header}]\n"
    )

    # Display summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style=theme.info)
    summary_table.add_column("Value", style=theme.ui_value)

    summary_table.add_row("Accounts", str(len(status["accounts"])))
    summary_table.add_row("Transactions", str(status["total_transactions"]))
    summary_table.add_row("Balance Snapshots", str(status["total_snapshots"]))
    summary_table.add_row("Integrations", str(len(status["integrations"])))

    console.print(summary_table)

    # Date range
    if status["earliest_date"] and status["latest_date"]:
        console.print(
            f"\n[{theme.muted}]Date range: {status['earliest_date']} to {status['latest_date']}[/{theme.muted}]"
        )

    # Show integrations
    if status["integrations"]:
        console.print(f"\n[{theme.emphasis}]Connected Integrations:[/{theme.emphasis}]")
        for integration in status["integrations"]:
            console.print(f"  • {integration['integrationName']}")

    console.print()


def display_sync_result(
    data: dict, dry_run: bool = False, verbose: bool = False
) -> None:
    """Display sync results using Rich formatting.

    Args:
        data: Sync result data from SyncService
        dry_run: Whether this was a dry-run sync
        verbose: Whether to show verbose output
    """
    header = (
        "Synchronizing Financial Data (DRY RUN)"
        if dry_run
        else "Synchronizing Financial Data"
    )
    console.print(f"\n[{theme.ui_header}]{header}[/{theme.ui_header}]\n")

    for sync_result in data["results"]:
        integration_name = sync_result["integration"]
        console.print(
            f"[{theme.emphasis}]Syncing {integration_name}...[/{theme.emphasis}]"
        )

        if "error" in sync_result:
            console.print(f"[{theme.error}]  ✗ {sync_result['error']}[/{theme.error}]")
            continue

        console.print(
            f"[{theme.success}]  ✓[/{theme.success}] Synced {sync_result['accounts_synced']} account(s)"
        )

        if sync_result["sync_type"] == "incremental":
            console.print(
                f"[{theme.muted}]  Syncing transactions since {sync_result['start_date'].date()} (with 7-day overlap)[/{theme.muted}]"
            )
        else:
            console.print(
                f"[{theme.muted}]  Initial sync: fetching last 90 days of transactions[/{theme.muted}]"
            )

        # Display transaction breakdown if stats are available
        tx_stats = sync_result.get("transaction_stats", {})
        if tx_stats:
            discovered = tx_stats.get("discovered", 0)
            new = tx_stats.get("new", 0)
            skipped = tx_stats.get("skipped", 0)

            console.print(
                f"[{theme.success}]  ✓[/{theme.success}] Transaction breakdown:"
            )
            console.print(
                f"[{theme.muted}]    Discovered: {discovered}[/{theme.muted}]"
            )
            console.print(f"[{theme.muted}]    New: {new}[/{theme.muted}]")
            console.print(
                f"[{theme.muted}]    Skipped: {skipped} (already exists)[/{theme.muted}]"
            )

            # Display tagger stats if available
            tagger_stats = sync_result.get("tagger_stats", {})
            verbose_logs = sync_result.get("tagger_verbose_logs", [])

            if tagger_stats:
                console.print(
                    f"[{theme.success}]  ✓[/{theme.success}] Auto-tagging applied:"
                )
                for tagger_name, tag_count in tagger_stats.items():
                    console.print(
                        f"[{theme.muted}]    {tagger_name}: {tag_count} tag(s)[/{theme.muted}]"
                    )

            # Show verbose tagging details if requested
            if verbose and verbose_logs:
                console.print(f"\n[{theme.info}]  Tagging details:[/{theme.info}]")
                for log in verbose_logs:
                    console.print(f"[{theme.muted}]    {log}[/{theme.muted}]")

            # Always show errors even if not verbose
            error_logs = [log for log in verbose_logs if log.startswith("ERROR:")]
            if error_logs and not verbose:
                console.print(f"\n[{theme.error}]  Tagger errors:[/{theme.error}]")
                for log in error_logs:
                    console.print(f"[{theme.error}]    {log}[/{theme.error}]")
        else:
            # Fallback to old display if stats not available
            console.print(
                f"[{theme.success}]  ✓[/{theme.success}] Synced {sync_result['transactions_synced']} transaction(s)"
            )

        console.print(
            f"[{theme.muted}]  Balance snapshots created automatically from account data[/{theme.muted}]"
        )

    if dry_run:
        console.print(
            f"\n[{theme.warning}]⚠[/{theme.warning}] Dry run completed - no changes were made\n"
        )
        console.print(
            f"[{theme.muted}]Run without --dry-run to apply these changes[/{theme.muted}]\n"
        )
    else:
        console.print(f"\n[{theme.success}]✓[/{theme.success}] Sync completed!\n")
        console.print(
            f"[{theme.muted}]Use 'treeline status' to see your updated data[/{theme.muted}]\n"
        )


def display_query_result(columns: list[str], rows: list[list]) -> None:
    """Display query results as a Rich table.

    Args:
        columns: Column names
        rows: Result rows
    """
    console.print()

    # Create Rich table
    table = Table(
        show_header=True, header_style=theme.ui_header, border_style=theme.separator
    )

    # Add columns
    for col in columns:
        table.add_column(col)

    # Add rows
    for row in rows:
        # Convert row values to strings
        str_row = [
            str(val) if val is not None else f"[{theme.muted}]NULL[/{theme.muted}]"
            for val in row
        ]
        table.add_row(*str_row)

    console.print(table)
    console.print(
        f"\n[{theme.muted}]{len(rows)} row{'s' if len(rows) != 1 else ''} returned[/{theme.muted}]\n"
    )


def ensure_treeline_initialized() -> bool:
    """Ensure treeline directory and database exist. Returns True if initialization was needed."""
    treeline_dir = get_treeline_dir()
    needs_init = not treeline_dir.exists()

    # Create directory if it doesn't exist
    treeline_dir.mkdir(exist_ok=True)

    # Initialize database using DbService
    container = get_container()
    db_service = container.db_service()

    result = asyncio.run(db_service.initialize_db())
    if not result.success:
        console.print(
            f"[{theme.error}]Error initializing database: {result.error}[/{theme.error}]"
        )
        sys.exit(1)

    return needs_init


@app.command(name="setup")
def setup_command(
    integration: str = typer.Argument(
        None, help="Integration name (e.g., 'simplefin'). Omit for interactive wizard."
    ),
    token: str = typer.Option(
        None, "--token", help="Setup token (optional, will prompt if not provided)"
    ),
) -> None:
    """Set up financial data integrations.

    Examples:
      # Interactive wizard
      treeline setup

      # Direct SimpleFIN setup
      treeline setup simplefin

      # Non-interactive setup with token
      treeline setup simplefin --token YOUR_TOKEN
    """
    ensure_treeline_initialized()

    if integration is None:
        # Interactive wizard
        console.print(f"\n[{theme.ui_header}]Integration Setup[/{theme.ui_header}]\n")
        console.print(f"[{theme.info}]Available integrations:[/{theme.info}]")
        console.print(f"  [{theme.emphasis}]1[/{theme.emphasis}] - SimpleFIN")
        console.print(f"  [{theme.emphasis}]2[/{theme.emphasis}] - Cancel\n")

        try:
            choice = Prompt.ask("Select integration", choices=["1", "2"], default="1")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{theme.warning}]Setup cancelled[/{theme.warning}]\n")
            raise typer.Exit(0)

        if choice == "1":
            integration = "simplefin"
        else:
            console.print(f"[{theme.muted}]Setup cancelled[/{theme.muted}]\n")
            raise typer.Exit(0)

    # Handle specific integrations
    if integration.lower() == "simplefin":
        setup_simplefin(token)
    else:
        display_error(f"Unknown integration: {integration}")
        console.print(
            f"[{theme.muted}]Supported integrations: simplefin[/{theme.muted}]"
        )
        raise typer.Exit(1)


def setup_simplefin(token: str | None = None) -> None:
    """Set up SimpleFIN integration (helper function).

    Args:
        token: Optional setup token. If not provided, will prompt interactively.
    """
    container = get_container()
    integration_service = container.integration_service("simplefin")

    console.print(f"\n[{theme.ui_header}]SimpleFIN Setup[/{theme.ui_header}]\n")

    # Use provided token or prompt for it
    if token:
        setup_token = token.strip()
    else:
        console.print(
            f"[{theme.muted}]If you don't have a SimpleFIN account, create one at: https://beta-bridge.simplefin.org/[/{theme.muted}]\n"
        )

        # Prompt for setup token
        console.print(f"[{theme.info}]Enter your SimpleFIN setup token[/{theme.info}]")
        console.print(f"[{theme.muted}](Press Ctrl+C to cancel)[/{theme.muted}]\n")

        try:
            setup_token = Prompt.ask("Token")
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n[{theme.warning}]Setup cancelled[/{theme.warning}]\n")
            raise typer.Exit(0)

        if not setup_token or not setup_token.strip():
            console.print(f"[{theme.warning}]Setup cancelled[/{theme.warning}]\n")
            raise typer.Exit(0)

        setup_token = setup_token.strip()

    # Setup integration
    console.print()
    with console.status(
        f"[{theme.status_loading}]Verifying token and setting up integration..."
    ):
        # Create integration
        result = asyncio.run(
            integration_service.create_integration(
                "simplefin", {"setupToken": setup_token}
            )
        )

    if not result.success:
        display_error(f"Setup failed: {result.error}")
        raise typer.Exit(1)

    console.print(
        f"[{theme.success}]✓[/{theme.success}] SimpleFIN integration setup successfully!\n"
    )
    console.print(
        f"[{theme.muted}]Use 'treeline sync' to import your transactions[/{theme.muted}]\n"
    )


# Tag command group
tag_app = typer.Typer(help="Transaction tagging commands")
app.add_typer(tag_app, name="tag")


@tag_app.callback(invoke_without_command=True)
def tag_callback(
    ctx: typer.Context,
    untagged_only: bool = typer.Option(
        False, "--untagged", help="Show only untagged transactions"
    ),
) -> None:
    """Launch interactive transaction tagging interface.

    Examples:
      # Tag all transactions interactively
      treeline tag

      # Show only untagged transactions
      treeline tag --untagged
    """
    # If a subcommand is being invoked, don't run the TUI
    if ctx.invoked_subcommand is not None:
        return

    ensure_treeline_initialized()

    from treeline.commands.tag_rich import run_tagging_interface

    run_tagging_interface(untagged_only=untagged_only)


@tag_app.command(name="apply")
def tag_apply_command(
    ids: str = typer.Option(
        None, "--ids", help="Comma-separated transaction IDs (or read from stdin)"
    ),
    tags: str = typer.Argument(..., help="Comma-separated tags to apply"),
    replace: bool = typer.Option(
        False, "--replace", help="Replace all tags (default: append/merge)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Apply tags to specific transactions (scriptable).

    By default, tags are merged with existing tags. Use --replace to replace all tags.

    Examples:
      # Append tags to transactions (default)
      treeline tag apply --ids abc123,def456 groceries,food

      # Replace all tags
      treeline tag apply --ids abc123 dining --replace

      # Output result as JSON
      treeline tag apply --ids abc123 dining --json

      # Pipe IDs from query (one ID per line)
      treeline query "SELECT transaction_id FROM transactions WHERE description ILIKE '%QFC%'" --json | \\
        jq -r '.rows[][] | @text' | treeline tag apply groceries

      # Pipe comma-separated IDs
      echo "abc123,def456" | treeline tag apply groceries
    """
    ensure_treeline_initialized()

    # Parse IDs from --ids option or stdin
    if ids:
        transaction_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]
    else:
        # Read from stdin
        stdin_input = sys.stdin.read().strip()
        if not stdin_input:
            display_error("No transaction IDs provided via --ids or stdin")
            raise typer.Exit(1)

        # Support both newline-separated and comma-separated IDs
        if "\n" in stdin_input:
            transaction_ids = [
                tid.strip() for tid in stdin_input.split("\n") if tid.strip()
            ]
        else:
            transaction_ids = [
                tid.strip() for tid in stdin_input.split(",") if tid.strip()
            ]

    if not transaction_ids:
        display_error("No transaction IDs provided")
        raise typer.Exit(1)

    # Parse tags
    tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
    if not tag_list:
        display_error("No tags provided")
        raise typer.Exit(1)

    container = get_container()
    tagging_service = container.tagging_service()
    db_service = container.db_service()

    # Apply tags to each transaction
    results = []
    errors = []

    for transaction_id_str in transaction_ids:
        try:
            transaction_id = UUID(transaction_id_str)
        except ValueError:
            errors.append(
                {
                    "transaction_id": transaction_id_str,
                    "error": f"Invalid UUID: {transaction_id_str}",
                    "success": False,
                }
            )
            continue

        # Determine final tag list (merge or replace)
        final_tags = tag_list
        if not replace:
            # Fetch current tags and merge
            query = f"SELECT tags FROM transactions WHERE transaction_id = '{transaction_id}'"
            tags_result = asyncio.run(db_service.execute_query(query))

            if (
                tags_result.success
                and tags_result.data
                and tags_result.data.get("rows")
            ):
                current_tags = tags_result.data["rows"][0][0] or []
                # Merge tags using set to deduplicate, then convert back to list
                merged_tags = list(set(current_tags) | set(tag_list))
                final_tags = merged_tags

        result = asyncio.run(
            tagging_service.update_transaction_tags(transaction_id, final_tags)
        )

        if result.success:
            results.append(
                {
                    "transaction_id": transaction_id_str,
                    "tags": final_tags,
                    "success": True,
                }
            )
        else:
            errors.append(
                {
                    "transaction_id": transaction_id_str,
                    "error": result.error,
                    "success": False,
                }
            )

    if json_output:
        output_json(
            {
                "succeeded": len(results),
                "failed": len(errors),
                "results": results + errors,
            }
        )
    else:
        if results:
            console.print(
                f"\n[{theme.success}]✓ Successfully tagged {len(results)} transaction(s)[/{theme.success}]"
            )
            console.print(
                f"[{theme.muted}]Tags applied: {', '.join(tag_list)}[/{theme.muted}]\n"
            )

        if errors:
            console.print(
                f"[{theme.error}]✗ Failed to tag {len(errors)} transaction(s)[/{theme.error}]"
            )
            for error in errors:
                console.print(
                    f"[{theme.muted}]  {error['transaction_id']}: {error['error']}[/{theme.muted}]"
                )
            console.print()

        if errors:
            raise typer.Exit(1)


@app.command(name="status")
def status_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show account summary and statistics."""
    ensure_treeline_initialized()

    container = get_container()
    status_service = container.status_service()

    result = asyncio.run(status_service.get_status())

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    if json_output:
        # Output concise summary for JSON (exclude full objects, but include account IDs for scripting)
        json_data = {
            "total_accounts": result.data["total_accounts"],
            "total_transactions": result.data["total_transactions"],
            "total_snapshots": result.data["total_snapshots"],
            "total_integrations": result.data["total_integrations"],
            "integration_names": result.data["integration_names"],
            "accounts": [
                {
                    "id": str(acc.id),
                    "name": acc.name,
                    "institution_name": acc.institution_name,
                }
                for acc in result.data["accounts"]
            ],
            "date_range": {
                "earliest": result.data["earliest_date"],
                "latest": result.data["latest_date"],
            },
        }
        output_json(json_data)
    else:
        display_status(result.data)


@app.command(name="query")
def query_command(
    sql: str = typer.Argument(None, help="SQL query to execute (SELECT/WITH only)"),
    file: str = typer.Option(None, "--file", "-f", help="Read SQL from file"),
    format: str = typer.Option(
        "table", "--format", help="Output format (table, json, csv)"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Output as JSON (alias for --format json)"
    ),
) -> None:
    """Execute a SQL query and display results.

    Examples:
      # Inline SQL
      treeline query "SELECT * FROM transactions LIMIT 10"

      # From file
      treeline query --file queries/monthly_spending.sql

      # From stdin (pipe)
      cat queries/analysis.sql | treeline query

      # Output as JSON
      treeline query "SELECT * FROM transactions LIMIT 10" --json

      # Output as CSV
      treeline query "SELECT * FROM transactions LIMIT 10" --format csv

      # Pipe to other commands
      treeline query "SELECT * FROM transactions" --format csv > transactions.csv
    """
    ensure_treeline_initialized()

    import sys

    container = get_container()
    db_service = container.db_service()

    # Determine SQL source (inline, file, or stdin)
    sql_content = None

    if file:
        # Read from file
        try:
            with open(file, "r") as f:
                sql_content = f.read()
        except FileNotFoundError:
            display_error(f"File not found: {file}")
            raise typer.Exit(1)
        except Exception as e:
            display_error(f"Error reading file: {e}")
            raise typer.Exit(1)
    elif sql:
        # Inline SQL provided
        sql_content = sql
    elif not sys.stdin.isatty():
        # Read from stdin (piped input)
        sql_content = sys.stdin.read()
    else:
        display_error(
            "No SQL provided. Use inline argument, --file option, or pipe from stdin."
        )
        console.print(f"[{theme.muted}]Examples:[/{theme.muted}]")
        console.print(f'  treeline query "SELECT * FROM transactions LIMIT 10"')
        console.print(f"  treeline query --file query.sql")
        console.print(f"  cat query.sql | treeline query")
        raise typer.Exit(1)

    sql_stripped = sql_content.strip()

    # Determine output format
    output_format = "json" if json_output else format.lower()
    if output_format not in ["table", "json", "csv"]:
        display_error(f"Invalid format: {format}. Choose: table, json, csv")
        raise typer.Exit(1)

    # Execute query
    if output_format == "table":
        # Show status indicator for table output
        with console.status(f"[{theme.status_loading}]Running query..."):
            result = asyncio.run(db_service.execute_query(sql_stripped))
    else:
        # No spinner for scriptable formats
        result = asyncio.run(db_service.execute_query(sql_stripped))

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    # Format and display results
    query_result = result.data
    rows = query_result.get("rows", [])
    columns = query_result.get("columns", [])

    if len(rows) == 0:
        if output_format == "table":
            console.print(f"[{theme.muted}]No results returned.[/{theme.muted}]\n")
        elif output_format == "json":
            output_json({"columns": columns, "rows": [], "row_count": 0})
        elif output_format == "csv":
            # Just print header for CSV
            import csv
            import sys

            writer = csv.writer(sys.stdout)
            writer.writerow(columns)
        return

    if output_format == "json":
        output_json({"columns": columns, "rows": rows, "row_count": len(rows)})
    elif output_format == "csv":
        import csv
        import sys

        writer = csv.writer(sys.stdout)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(row)
    else:  # table
        display_query_result(columns, rows)


@app.command(name="sync")
def sync_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be synced without making changes"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed tagging information"
    ),
) -> None:
    """Synchronize data from connected integrations.

    Examples:
      # Normal sync
      treeline sync

      # Test taggers without saving changes
      treeline sync --dry-run --verbose

      # See detailed tagging info during real sync
      treeline sync --verbose
    """
    ensure_treeline_initialized()

    container = get_container()
    sync_service = container.sync_service()

    # Sync all integrations with visual feedback
    if not json_output:
        status_msg = (
            "Syncing integrations (dry-run)..."
            if dry_run
            else "Syncing integrations..."
        )
        with console.status(f"[{theme.status_loading}]{status_msg}"):
            result = asyncio.run(
                sync_service.sync_all_integrations(dry_run=dry_run, verbose=verbose)
            )
    else:
        result = asyncio.run(
            sync_service.sync_all_integrations(dry_run=dry_run, verbose=verbose)
        )

    if not result.success:
        display_error(result.error)
        if result.error == "No integrations configured":
            console.print(
                f"[{theme.muted}]Use 'treeline simplefin' to setup an integration first[/{theme.muted}]"
            )
        raise typer.Exit(1)

    if json_output:
        output_json(result.data)
    else:
        display_sync_result(result.data, dry_run=dry_run, verbose=verbose)


@app.command(name="import")
def import_command(
    file_path: str = typer.Argument(
        None, help="Path to CSV file (omit for interactive mode)"
    ),
    account_id: str = typer.Option(
        None, "--account-id", help="Account ID to import into"
    ),
    date_column: str = typer.Option(
        None, "--date-column", help="CSV column name for date"
    ),
    amount_column: str = typer.Option(
        None, "--amount-column", help="CSV column name for amount"
    ),
    description_column: str = typer.Option(
        None, "--description-column", help="CSV column name for description"
    ),
    debit_column: str = typer.Option(
        None, "--debit-column", help="CSV column name for debits"
    ),
    credit_column: str = typer.Option(
        None, "--credit-column", help="CSV column name for credits"
    ),
    flip_signs: bool = typer.Option(
        False, "--flip-signs", help="Flip transaction signs (for credit cards)"
    ),
    preview: bool = typer.Option(False, "--preview", help="Preview only, don't import"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Import transactions from CSV file.

    INTERACTIVE MODE (prompts for all options):
      treeline import

    SCRIPTABLE MODE (all options via flags):
      treeline import file.csv --account-id XXX --date-column "Date" --amount-column "Amount"

    Examples:
      # Interactive mode with prompts
      treeline import

      # Preview import (no changes)
      treeline import transactions.csv --account-id ABC123 --preview

      # Full automated import
      treeline import transactions.csv \\
        --account-id ABC123 \\
        --date-column "Date" \\
        --amount-column "Amount" \\
        --description-column "Description" \\
        --flip-signs
    """
    ensure_treeline_initialized()
    container = get_container()
    import_service = container.import_service()
    account_service = container.account_service()

    # INTERACTIVE MODE: No file path provided
    if file_path is None:
        handle_import_command(
            import_service=import_service,
            account_service=account_service,
        )
        return

    # SCRIPTABLE MODE: Collect parameters and call service
    csv_path = Path(file_path).expanduser()
    if not csv_path.exists():
        display_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    # Validate account_id is provided
    if not account_id:
        display_error("--account-id is required for scriptable import")
        console.print(
            f"[{theme.muted}]Run 'treeline status --json' to see account IDs[/{theme.muted}]"
        )
        raise typer.Exit(1)

    # Build column mapping (if provided)
    column_mapping = None
    if date_column or amount_column or debit_column or credit_column:
        column_mapping = {}
        if date_column:
            column_mapping["date"] = date_column
        if amount_column:
            column_mapping["amount"] = amount_column
        if description_column:
            column_mapping["description"] = description_column
        if debit_column:
            column_mapping["debit"] = debit_column
        if credit_column:
            column_mapping["credit"] = credit_column

    # SINGLE service call - preview mode
    if preview:
        # Auto-detect columns if not provided
        preview_column_mapping = column_mapping
        if not preview_column_mapping:
            if not json_output:
                with console.status(
                    f"[{theme.status_loading}]Detecting CSV columns..."
                ):
                    detect_result = asyncio.run(
                        import_service.detect_columns(
                            source_type="csv", file_path=str(csv_path)
                        )
                    )
            else:
                detect_result = asyncio.run(
                    import_service.detect_columns(
                        source_type="csv", file_path=str(csv_path)
                    )
                )

            if not detect_result.success:
                display_error(f"Column detection failed: {detect_result.error}")
                raise typer.Exit(1)

            preview_column_mapping = detect_result.data

        preview_result = asyncio.run(
            import_service.preview_csv_import(
                file_path=str(csv_path),
                column_mapping=preview_column_mapping,
                date_format="auto",
                limit=10,
                flip_signs=flip_signs,
            )
        )

        if not preview_result.success:
            display_error(f"Preview failed: {preview_result.error}")
            raise typer.Exit(1)

        # Display preview
        if json_output:
            preview_data = {
                "file": str(csv_path),
                "flip_signs": flip_signs,
                "preview": [
                    {
                        "date": str(tx.transaction_date),
                        "description": tx.description,
                        "amount": float(tx.amount),
                    }
                    for tx in preview_result.data
                ],
            }
            output_json(preview_data)
        else:
            console.print(f"\n[{theme.ui_header}]Import Preview[/{theme.ui_header}]\n")
            console.print(f"File: {csv_path}")
            console.print(f"Flip signs: {flip_signs}\n")

            for tx in preview_result.data[:10]:
                amount_style = (
                    theme.negative_amount if tx.amount < 0 else theme.positive_amount
                )
                amount_str = (
                    f"-${abs(tx.amount):,.2f}"
                    if tx.amount < 0
                    else f"${tx.amount:,.2f}"
                )
                console.print(
                    f"  {tx.transaction_date}  [{amount_style}]{amount_str:>12}[/{amount_style}]  {tx.description}"
                )

            console.print(
                f"\n[{theme.muted}]Remove --preview flag to import[/{theme.muted}]\n"
            )
        return

    # SINGLE service call - import mode
    # Auto-detect columns if not provided (CLI responsibility to collect all params)
    import_column_mapping = column_mapping
    if not import_column_mapping:
        if not json_output:
            with console.status(f"[{theme.status_loading}]Detecting CSV columns..."):
                detect_result = asyncio.run(
                    import_service.detect_columns(
                        source_type="csv", file_path=str(csv_path)
                    )
                )
        else:
            detect_result = asyncio.run(
                import_service.detect_columns(
                    source_type="csv", file_path=str(csv_path)
                )
            )

        if not detect_result.success:
            display_error(f"Column detection failed: {detect_result.error}")
            raise typer.Exit(1)

        import_column_mapping = detect_result.data

    source_options = {
        "file_path": str(csv_path),
        "column_mapping": import_column_mapping,
        "date_format": "auto",
        "flip_signs": flip_signs,
    }

    if not json_output:
        with console.status(f"[{theme.status_loading}]Importing transactions..."):
            result = asyncio.run(
                import_service.import_transactions(
                    source_type="csv",
                    account_id=UUID(account_id),
                    source_options=source_options,
                )
            )
    else:
        result = asyncio.run(
            import_service.import_transactions(
                source_type="csv",
                account_id=UUID(account_id),
                source_options=source_options,
            )
        )

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    # Display result
    if json_output:
        output_json(result.data)
    else:
        stats = result.data
        console.print(f"\n[{theme.success}]✓ Import complete![/{theme.success}]")
        console.print(f"  Discovered: {stats['discovered']} transactions")
        console.print(f"  Imported: {stats['imported']} new transactions")
        console.print(f"  Skipped: {stats['skipped']} duplicates\n")


@app.command(name="new")
def new_command(
    resource_type: str = typer.Argument(
        ..., help="Type of resource to create (e.g., 'tagger')"
    ),
    name: str = typer.Argument(..., help="Name for the new resource"),
) -> None:
    """Create a new resource from a template.

    Examples:
      # Create a new tagger
      treeline new tagger groceries

      # Create a tagger for work expenses
      treeline new tagger work_expenses
    """
    if resource_type == "tagger":
        _create_tagger(name)
    else:
        display_error(f"Unknown resource type: {resource_type}")
        console.print(f"[{theme.muted}]Available types: tagger[/{theme.muted}]")
        raise typer.Exit(1)


def _create_tagger(name: str) -> None:
    """Create a new tagger file."""
    import re

    # Validate name - must be a valid Python module name
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        display_error(
            f"Invalid tagger name: '{name}'. "
            "Name must be a valid Python identifier (letters, numbers, underscores only, "
            "cannot start with a number)."
        )
        raise typer.Exit(1)

    # Get taggers directory
    taggers_dir = get_treeline_dir() / "taggers"
    taggers_dir.mkdir(parents=True, exist_ok=True)

    tagger_file = taggers_dir / f"{name}.py"

    if tagger_file.exists():
        display_error(f"Tagger already exists: {tagger_file}")
        raise typer.Exit(1)

    # Write skeleton template
    template = f'''"""
Auto-tagger: {name}

Add your auto-tagging logic here. This function will be called for each
transaction during sync. Return a list of tags to apply.

No imports needed! Transaction fields are passed as parameters.

IMPORTANT: Function must start with "tag_" prefix (like pytest's "test_" convention).
"""


def tag_{name}(description, amount, transaction_date, account_id, **kwargs):
    """
    Auto-tag transactions based on custom rules.

    Args:
        description: Transaction description (str | None)
        amount: Transaction amount (Decimal)
        transaction_date: Date of transaction (date)
        account_id: UUID of the account (UUID)
        **kwargs: Additional fields (posted_date, tags, etc.)

    Returns:
        List of tags to apply to this transaction

    Examples:
        # Tag by description
        if description and 'COFFEE' in description.upper():
            return ['coffee', 'food']

        # Tag by amount
        if amount > 100:
            return ['large-purchase']

        # Tag by account_id
        # if str(account_id) == 'YOUR-ACCOUNT-UUID':
        #     return ['personal']

        # No match
        return []
    """
    # TODO: Add your tagging logic here
    return []
'''

    tagger_file.write_text(template)
    console.print(f"[{theme.success}]✓[/{theme.success}] Created tagger: {tagger_file}")
    console.print(
        f"\n[{theme.muted}]Edit this file to add your tagging logic, then run 'treeline sync --dry-run' or 'treeline backfill tags --dry-run' [/{theme.muted}]\n"
    )


@app.command(name="list")
def list_command(
    resource_type: str = typer.Argument(
        ..., help="Type of resource to list (e.g., 'taggers')"
    ),
) -> None:
    """List installed resources.

    Examples:
      # List all taggers
      treeline list taggers
    """
    if resource_type == "taggers":
        _list_taggers()
    else:
        display_error(f"Unknown resource type: {resource_type}")
        console.print(f"[{theme.muted}]Available types: taggers[/{theme.muted}]")
        raise typer.Exit(1)


def _list_taggers() -> None:
    """List all installed taggers."""
    import importlib.util
    import inspect

    taggers_dir = get_treeline_dir() / "taggers"

    if not taggers_dir.exists():
        console.print(f"\n[{theme.muted}]No taggers directory found.[/{theme.muted}]")
        console.print(
            f"[{theme.muted}]Create a tagger with: treeline new tagger <name>[/{theme.muted}]\n"
        )
        return

    tagger_files = list(taggers_dir.glob("*.py"))

    if not tagger_files:
        console.print(f"\n[{theme.muted}]No taggers found.[/{theme.muted}]")
        console.print(
            f"[{theme.muted}]Create a tagger with: treeline new tagger <name>[/{theme.muted}]\n"
        )
        return

    console.print(f"\n[{theme.ui_header}]Installed Taggers[/{theme.ui_header}]\n")

    for tagger_file in sorted(tagger_files):
        if tagger_file.name.startswith("_"):
            continue

        console.print(f"[{theme.emphasis}]{tagger_file.name}[/{theme.emphasis}]")

        # Try to load and discover functions using auto-discovery (same as service layer)
        try:
            spec = importlib.util.spec_from_file_location(
                f"user_taggers.{tagger_file.stem}", tagger_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Auto-discover all functions (same logic as service layer)
            discovered_functions = []
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # Only include functions that start with "tag_" (like pytest's "test_")
                # Skip imported functions from other modules
                if not name.startswith("tag_") or obj.__module__ != module.__name__:
                    continue
                discovered_functions.append(obj)

            if discovered_functions:
                for func in discovered_functions:
                    # Show signature with explicit parameters
                    sig = inspect.signature(func)
                    params = list(sig.parameters.keys())
                    # Show first 4 params if they match our expected signature
                    if len(params) >= 4 and params[:4] == [
                        "description",
                        "amount",
                        "transaction_date",
                        "account_id",
                    ]:
                        param_display = (
                            "description, amount, transaction_date, account_id, ..."
                        )
                    else:
                        param_display = ", ".join(params[:3]) + (
                            ", ..." if len(params) > 3 else ""
                        )

                    console.print(
                        f"  [{theme.muted}]→ {func.__name__}({param_display})[/{theme.muted}]"
                    )
            else:
                console.print(
                    f"  [{theme.warning}]⚠ No functions found[/{theme.warning}]"
                )

        except Exception as e:
            console.print(f"  [{theme.error}]✗ Failed to load: {e}[/{theme.error}]")

    console.print()


@app.command(name="backfill")
def backfill_command(
    resource_type: str = typer.Argument(
        ...,
        help="Type of resource to backfill (tags, balances)",
    ),
    tagger: List[str] = typer.Option(
        None,
        "--tagger",
        help="[tags] Tagger specification (file.function or file for all taggers in file)",
    ),
    account_id: List[str] = typer.Option(
        None,
        "--account-id",
        help="[balances] Account ID to backfill (can specify multiple)",
    ),
    days: int = typer.Option(
        None,
        "--days",
        help="[balances] Limit to last N days of history",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview changes without saving",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed output",
    ),
):
    """Backfill historical data.

    Examples:
      # Backfill all taggers on all transactions
      treeline backfill tags

      # Backfill specific tagger
      treeline backfill tags --tagger groceries.tag_qfc

      # Backfill all taggers from file
      treeline backfill tags --tagger groceries

      # Preview without saving
      treeline backfill tags --dry-run --verbose

      # Backfill balance snapshots for all accounts
      treeline backfill balances

      # Backfill specific account
      treeline backfill balances --account-id ACCOUNT-UUID

      # Backfill last 90 days only
      treeline backfill balances --days 90 --dry-run
    """
    if resource_type == "tags":
        _backfill_tags(tagger, dry_run, verbose)
    elif resource_type == "balances":
        _backfill_balances(account_id, days, dry_run, verbose)
    else:
        display_error(f"Unknown resource type: {resource_type}")
        console.print(f"[{theme.muted}]Available types: tags, balances[/{theme.muted}]")
        raise typer.Exit(1)


def _backfill_tags(
    tagger_specs: List[str] | None, dry_run: bool, verbose: bool
) -> None:
    """Backfill tags on existing transactions."""
    import asyncio

    container = get_container()
    backfill_service = container.backfill_service()

    # Show dry-run indicator
    if dry_run:
        console.print(
            f"[{theme.warning}]DRY RUN - No changes will be saved[/{theme.warning}]\n"
        )

    # Run backfill
    with console.status("[bold]Backfilling tags..."):
        result = asyncio.run(
            backfill_service.backfill_tags(tagger_specs, dry_run, verbose)
        )

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    data = result.data

    # Display verbose logs
    if verbose and data.get("verbose_logs"):
        console.print(f"\n[{theme.ui_header}]Detailed Logs[/{theme.ui_header}]")
        for log in data["verbose_logs"]:
            if log.startswith("ERROR:"):
                console.print(f"[{theme.error}]{log}[/{theme.error}]")
            else:
                console.print(f"[{theme.muted}]{log}[/{theme.muted}]")

    # Display summary
    console.print(f"\n[{theme.success}]✓[/{theme.success}] Backfill complete")
    console.print(f"  Transactions processed: {data['transactions_processed']}")
    console.print(f"  Transactions updated: {data['transactions_updated']}")
    console.print(f"  Tags added: {data['tags_added']}")

    if data.get("tagger_stats"):
        console.print(f"\n[{theme.ui_header}]Tagger Stats[/{theme.ui_header}]")
        for tagger_name, count in data["tagger_stats"].items():
            console.print(f"  {tagger_name}: {count} tags")

    if dry_run:
        console.print(
            f"\n[{theme.warning}]DRY RUN - No changes were saved[/{theme.warning}]"
        )


def _backfill_balances(
    account_ids_str: List[str] | None, days: int | None, dry_run: bool, verbose: bool
) -> None:
    """Backfill balance snapshots from transaction history."""
    import asyncio

    container = get_container()
    backfill_service = container.backfill_service()

    # Parse account IDs
    account_ids = (
        [UUID(id_str) for id_str in account_ids_str] if account_ids_str else None
    )

    # Show dry-run indicator
    if dry_run:
        console.print(
            f"[{theme.warning}]DRY RUN - No changes will be saved[/{theme.warning}]\n"
        )

    # Run backfill
    with console.status("[bold]Backfilling balance snapshots..."):
        result = asyncio.run(
            backfill_service.backfill_balances(account_ids, days, dry_run, verbose)
        )

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    data = result.data

    # Display warnings
    if data.get("warnings"):
        console.print(f"\n[{theme.warning}]Warnings[/{theme.warning}]")
        for warning in data["warnings"]:
            console.print(f"  {warning}")

    # Display verbose logs
    if verbose and data.get("verbose_logs"):
        console.print(f"\n[{theme.ui_header}]Detailed Logs[/{theme.ui_header}]")
        for log in data["verbose_logs"]:
            console.print(f"[{theme.muted}]{log}[/{theme.muted}]")

    # Display summary
    console.print(f"\n[{theme.success}]✓[/{theme.success}] Backfill complete")
    console.print(f"  Accounts processed: {data['accounts_processed']}")
    console.print(f"  Snapshots created: {data['snapshots_created']}")
    console.print(f"  Snapshots skipped: {data['snapshots_skipped']}")

    if dry_run:
        console.print(
            f"\n[{theme.warning}]DRY RUN - No changes were saved[/{theme.warning}]"
        )


if __name__ == "__main__":
    app()
