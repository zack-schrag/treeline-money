"""Treeline CLI - Interactive financial data management."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from treeline.app.container import Container
from treeline.commands.import_csv import handle_import_command
from treeline.theme import get_theme

# Load environment variables from .env file
load_dotenv()

def version_callback(value: bool):
    """Show version information."""
    if value:
        console.print("treeline version 0.1.0")
        raise typer.Exit()


app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=True,  # Show help by default
)
console = Console()
theme = get_theme()

# Global container instance
_container: Container | None = None


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the current working directory."""
    return Path.cwd() / "treeline"


def get_container() -> Container:
    """Get or create the dependency injection container."""
    global _container
    if _container is None:
        treeline_dir = get_treeline_dir()
        db_path = treeline_dir / "treeline.db"
        _container = Container(str(db_path))
    return _container


def require_auth() -> None:
    """Check if user is authenticated. Exit with error if not."""
    container = get_container()
    config_service = container.config_service()
    if not config_service.is_authenticated():
        console.print(f"[{theme.error}]Error: Not authenticated[/{theme.error}]")
        console.print(f"[{theme.muted}]Run 'treeline login' to sign in[/{theme.muted}]")
        raise typer.Exit(1)


def get_authenticated_user_id() -> UUID:
    """Get authenticated user ID. Exit with error if not authenticated.

    Returns:
        UUID of authenticated user
    """
    require_auth()
    container = get_container()
    config_service = container.config_service()
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: User ID not found[/{theme.error}]")
        raise typer.Exit(1)
    return UUID(user_id_str)


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
    # FIXME: move imports to top
    import json
    from pydantic import BaseModel

    def json_serializer(obj):
        """Custom JSON serializer for Pydantic models and other objects."""
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode='json')
        return str(obj)

    print(json.dumps(data, indent=2, default=json_serializer))


def display_status(status: dict) -> None:
    """Display status using Rich formatting.

    Args:
        status: Status data from StatusService
    """
    console.print(f"\n[{theme.ui_header}]📊 Financial Data Status[/{theme.ui_header}]\n")

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
        console.print(f"\n[{theme.muted}]Date range: {status['earliest_date']} to {status['latest_date']}[/{theme.muted}]")

    # Show integrations
    if status["integrations"]:
        console.print(f"\n[{theme.emphasis}]Connected Integrations:[/{theme.emphasis}]")
        for integration in status["integrations"]:
            console.print(f"  • {integration['integrationName']}")

    console.print()


def display_sync_result(data: dict) -> None:
    """Display sync results using Rich formatting.

    Args:
        data: Sync result data from SyncService
    """
    console.print(f"\n[{theme.ui_header}]Synchronizing Financial Data[/{theme.ui_header}]\n")

    for sync_result in data["results"]:
        integration_name = sync_result["integration"]
        console.print(f"[{theme.emphasis}]Syncing {integration_name}...[/{theme.emphasis}]")

        if "error" in sync_result:
            console.print(f"[{theme.error}]  ✗ {sync_result['error']}[/{theme.error}]")
            continue

        console.print(f"[{theme.success}]  ✓[/{theme.success}] Synced {sync_result['accounts_synced']} account(s)")

        if sync_result["sync_type"] == "incremental":
            console.print(
                f"[{theme.muted}]  Syncing transactions since {sync_result['start_date'].date()} (with 7-day overlap)[/{theme.muted}]"
            )
        else:
            console.print(f"[{theme.muted}]  Initial sync: fetching last 90 days of transactions[/{theme.muted}]")

        # Display transaction breakdown if stats are available
        tx_stats = sync_result.get("transaction_stats", {})
        if tx_stats:
            discovered = tx_stats.get("discovered", 0)
            new = tx_stats.get("new", 0)
            skipped = tx_stats.get("skipped", 0)

            console.print(f"[{theme.success}]  ✓[/{theme.success}] Transaction breakdown:")
            console.print(f"[{theme.muted}]    Discovered: {discovered}[/{theme.muted}]")
            console.print(f"[{theme.muted}]    New: {new}[/{theme.muted}]")
            console.print(f"[{theme.muted}]    Skipped: {skipped} (already exists)[/{theme.muted}]")
        else:
            # Fallback to old display if stats not available
            console.print(f"[{theme.success}]  ✓[/{theme.success}] Synced {sync_result['transactions_synced']} transaction(s)")

        console.print(f"[{theme.muted}]  Balance snapshots created automatically from account data[/{theme.muted}]")

    console.print(f"\n[{theme.success}]✓[/{theme.success}] Sync completed!\n")
    console.print(f"[{theme.muted}]Use 'treeline status' to see your updated data[/{theme.muted}]\n")


def display_query_result(columns: list[str], rows: list[list]) -> None:
    """Display query results as a Rich table.

    Args:
        columns: Column names
        rows: Result rows
    """
    console.print()

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
        console.print(f"[{theme.error}]Error initializing database: {result.error}[/{theme.error}]")
        sys.exit(1)

    return needs_init


@app.command(name="login")
def login_command(
    email: str = typer.Option(None, "--email", help="Email address"),
    password: str = typer.Option(None, "--password", help="Password (not recommended - use prompt)"),
    create_account: bool = typer.Option(False, "--create-account", help="Create a new account instead of signing in"),
) -> None:
    """Authenticate with Treeline.

    Examples:
      # Interactive login (recommended)
      treeline login

      # Login with email (will prompt for password)
      treeline login --email user@example.com

      # Create new account
      treeline login --create-account
    """
    ensure_treeline_initialized()

    console.print(f"\n[{theme.ui_header}]Login to Treeline[/{theme.ui_header}]\n")

    container = get_container()
    config_service = container.config_service()

    try:
        auth_service = container.auth_service()
    except ValueError as e:
        display_error(str(e))
        raise typer.Exit(1)

    # Interactive prompts for missing values
    try:
        if not create_account:
            # Only ask if not specified via flag
            create_account = Confirm.ask("Create a new account?", default=False)

        if not email:
            email = Prompt.ask("Email")

        if not password:
            password = Prompt.ask("Password", password=True)
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.warning}]Login cancelled[/{theme.warning}]\n")
        raise typer.Exit(0)

    # Authenticate
    console.print()
    with console.status(f"[{theme.status_loading}]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_service.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_service.sign_in_with_password(email, password))

    if not result.success:
        display_error(f"Authentication failed: {result.error}")
        raise typer.Exit(1)

    user = result.data
    console.print(f"[{theme.success}]✓[/{theme.success}] Successfully authenticated as [{theme.emphasis}]{user.email}[/{theme.emphasis}]\n")

    # Save credentials
    config_service.save_user_credentials(str(user.id), user.email)
    console.print(f"[{theme.muted}]Credentials saved to system keyring[/{theme.muted}]\n")


@app.command(name="setup")
def setup_command(
    integration: str = typer.Argument(None, help="Integration name (e.g., 'simplefin'). Omit for interactive wizard."),
) -> None:
    """Set up financial data integrations.

    Examples:
      # Interactive wizard
      treeline setup

      # Direct SimpleFIN setup
      treeline setup simplefin
    """
    ensure_treeline_initialized()
    require_auth()

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
        setup_simplefin()
    else:
        display_error(f"Unknown integration: {integration}")
        console.print(f"[{theme.muted}]Supported integrations: simplefin[/{theme.muted}]")
        raise typer.Exit(1)


def setup_simplefin() -> None:
    """Set up SimpleFIN integration (helper function)."""
    user_id = get_authenticated_user_id()

    container = get_container()
    db_service = container.db_service()
    integration_service = container.integration_service("simplefin")

    console.print(f"\n[{theme.ui_header}]SimpleFIN Setup[/{theme.ui_header}]\n")
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
    with console.status(f"[{theme.status_loading}]Verifying token and setting up integration..."):
        # Ensure user database is initialized
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            display_error(f"Error initializing database: {db_init_result.error}")
            raise typer.Exit(1)

        # Create integration
        result = asyncio.run(
            integration_service.create_integration(user_id, "simplefin", {"setupToken": setup_token})
        )

    if not result.success:
        display_error(f"Setup failed: {result.error}")
        raise typer.Exit(1)

    console.print(f"[{theme.success}]✓[/{theme.success}] SimpleFIN integration setup successfully!\n")
    console.print(f"[{theme.muted}]Use 'treeline sync' to import your transactions[/{theme.muted}]\n")


# Tag command group
tag_app = typer.Typer(help="Transaction tagging commands")
app.add_typer(tag_app, name="tag")


@tag_app.callback(invoke_without_command=True)
def tag_callback(
    ctx: typer.Context,
    untagged_only: bool = typer.Option(False, "--untagged", help="Show only untagged transactions"),
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
    user_id = get_authenticated_user_id()

    from treeline.commands.tag_textual import TaggingApp
    app_instance = TaggingApp(user_id=user_id, untagged_only=untagged_only)
    app_instance.run()


@tag_app.command(name="apply")
def tag_apply_command(
    ids: str = typer.Option(None, "--ids", help="Comma-separated transaction IDs (or read from stdin)"),
    tags: str = typer.Argument(..., help="Comma-separated tags to apply"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Apply tags to specific transactions (scriptable).

    Examples:
      # Apply tags to transactions
      treeline tag apply --ids abc123,def456 groceries,food

      # Output result as JSON
      treeline tag apply --ids abc123 dining --json

      # Pipe IDs from query (one ID per line)
      treeline query "SELECT id FROM transactions WHERE description ILIKE '%QFC%'" --json | \\
        jq -r '.[].id' | treeline tag apply groceries

      # Pipe comma-separated IDs
      echo "abc123,def456" | treeline tag apply groceries
    """
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

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
            transaction_ids = [tid.strip() for tid in stdin_input.split("\n") if tid.strip()]
        else:
            transaction_ids = [tid.strip() for tid in stdin_input.split(",") if tid.strip()]

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

    # Apply tags to each transaction
    results = []
    errors = []

    for transaction_id in transaction_ids:
        result = asyncio.run(
            tagging_service.update_transaction_tags(user_id, transaction_id, tag_list)
        )

        if result.success:
            results.append({
                "transaction_id": transaction_id,
                "tags": tag_list,
                "success": True
            })
        else:
            errors.append({
                "transaction_id": transaction_id,
                "error": result.error,
                "success": False
            })

    if json_output:
        output_json({
            "succeeded": len(results),
            "failed": len(errors),
            "results": results + errors
        })
    else:
        if results:
            console.print(f"\n[{theme.success}]✓ Successfully tagged {len(results)} transaction(s)[/{theme.success}]")
            console.print(f"[{theme.muted}]Tags applied: {', '.join(tag_list)}[/{theme.muted}]\n")

        if errors:
            console.print(f"[{theme.error}]✗ Failed to tag {len(errors)} transaction(s)[/{theme.error}]")
            for error in errors:
                console.print(f"[{theme.muted}]  {error['transaction_id']}: {error['error']}[/{theme.muted}]")
            console.print()

        if errors:
            raise typer.Exit(1)


@app.command(name="status")
def status_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Show account summary and statistics."""
    ensure_treeline_initialized()

    user_id = get_authenticated_user_id()

    container = get_container()
    status_service = container.status_service()

    result = asyncio.run(status_service.get_status(user_id))

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
                    "institution_name": acc.institution_name
                }
                for acc in result.data["accounts"]
            ],
            "date_range": {
                "earliest": result.data["earliest_date"],
                "latest": result.data["latest_date"],
            }
        }
        output_json(json_data)
    else:
        display_status(result.data)


@app.command(name="query")
def query_command(
    sql: str = typer.Argument(..., help="SQL query to execute (SELECT/WITH only)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format (table, json, csv)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON (alias for --format json)"),
) -> None:
    """Execute a SQL query and display results.

    Examples:
      # Display as table (default)
      treeline query "SELECT * FROM transactions LIMIT 10"

      # Output as JSON
      treeline query "SELECT * FROM transactions LIMIT 10" --json

      # Output as CSV
      treeline query "SELECT * FROM transactions LIMIT 10" --format csv

      # Pipe to other commands
      treeline query "SELECT * FROM transactions" --format csv > transactions.csv
    """
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

    container = get_container()
    db_service = container.db_service()

    # Validate SQL - only allow SELECT and WITH queries
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        display_error("Only SELECT and WITH queries are allowed")
        console.print(f"[{theme.muted}]For data modifications, use the analysis TUI[/{theme.muted}]")
        raise typer.Exit(1)

    # Determine output format
    output_format = "json" if json_output else format.lower()
    if output_format not in ["table", "json", "csv"]:
        display_error(f"Invalid format: {format}. Choose: table, json, csv")
        raise typer.Exit(1)

    # Execute query
    if output_format == "table":
        # Show status indicator for table output
        with console.status(f"[{theme.status_loading}]Running query..."):
            result = asyncio.run(db_service.execute_query(user_id, sql_stripped))
    else:
        # No spinner for scriptable formats
        result = asyncio.run(db_service.execute_query(user_id, sql_stripped))

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
        output_json({
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        })
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
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Synchronize data from connected integrations."""
    ensure_treeline_initialized()
    user_id = get_authenticated_user_id()

    container = get_container()
    db_service = container.db_service()
    sync_service = container.sync_service()

    # Show visual feedback for non-JSON mode
    if not json_output:
        with console.status(f"[{theme.status_loading}]Initializing..."):
            db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
    else:
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))

    if not db_init_result.success:
        display_error(f"Error initializing database: {db_init_result.error}")
        raise typer.Exit(1)

    # Sync all integrations with visual feedback
    if not json_output:
        with console.status(f"[{theme.status_loading}]Syncing integrations..."):
            result = asyncio.run(sync_service.sync_all_integrations(user_id))
    else:
        result = asyncio.run(sync_service.sync_all_integrations(user_id))

    if not result.success:
        display_error(result.error)
        if result.error == "No integrations configured":
            console.print(f"[{theme.muted}]Use 'treeline simplefin' to setup an integration first[/{theme.muted}]")
        raise typer.Exit(1)

    if json_output:
        output_json(result.data)
    else:
        display_sync_result(result.data)


@app.command(name="import")
def import_command(
    file_path: str = typer.Argument(None, help="Path to CSV file (omit for interactive mode)"),
    account_id: str = typer.Option(None, "--account-id", help="Account ID to import into"),
    date_column: str = typer.Option(None, "--date-column", help="CSV column name for date"),
    amount_column: str = typer.Option(None, "--amount-column", help="CSV column name for amount"),
    description_column: str = typer.Option(None, "--description-column", help="CSV column name for description"),
    debit_column: str = typer.Option(None, "--debit-column", help="CSV column name for debits"),
    credit_column: str = typer.Option(None, "--credit-column", help="CSV column name for credits"),
    flip_signs: bool = typer.Option(False, "--flip-signs", help="Flip transaction signs (for credit cards)"),
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
    user_id = get_authenticated_user_id()

    # INTERACTIVE MODE: No file path provided
    if file_path is None:
        handle_import_command()
        return

    # SCRIPTABLE MODE: Collect parameters and call service

    # Validate file exists
    from pathlib import Path as PathLib
    csv_path = PathLib(file_path).expanduser()
    if not csv_path.exists():
        display_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    # Validate account_id is provided
    if not account_id:
        display_error("--account-id is required for scriptable import")
        console.print(f"[{theme.muted}]Run 'treeline status --json' to see account IDs[/{theme.muted}]")
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

    # Get service
    container = get_container()
    import_service = container.import_service()

    # SINGLE service call - preview mode
    if preview:
        # Auto-detect columns if not provided
        preview_column_mapping = column_mapping
        if not preview_column_mapping:
            if not json_output:
                with console.status(f"[{theme.status_loading}]Detecting CSV columns..."):
                    detect_result = asyncio.run(import_service.detect_columns(source_type="csv", file_path=str(csv_path)))
            else:
                detect_result = asyncio.run(import_service.detect_columns(source_type="csv", file_path=str(csv_path)))

            if not detect_result.success:
                display_error(f"Column detection failed: {detect_result.error}")
                raise typer.Exit(1)

            preview_column_mapping = detect_result.data

        preview_result = asyncio.run(import_service.preview_csv_import(
            file_path=str(csv_path),
            column_mapping=preview_column_mapping,
            date_format="auto",
            limit=10,
            flip_signs=flip_signs
        ))

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
                        "amount": float(tx.amount)
                    }
                    for tx in preview_result.data
                ]
            }
            output_json(preview_data)
        else:
            console.print(f"\n[{theme.ui_header}]Import Preview[/{theme.ui_header}]\n")
            console.print(f"File: {csv_path}")
            console.print(f"Flip signs: {flip_signs}\n")

            for tx in preview_result.data[:10]:
                amount_style = theme.negative_amount if tx.amount < 0 else theme.positive_amount
                amount_str = f"-${abs(tx.amount):,.2f}" if tx.amount < 0 else f"${tx.amount:,.2f}"
                console.print(f"  {tx.transaction_date}  [{amount_style}]{amount_str:>12}[/{amount_style}]  {tx.description}")

            console.print(f"\n[{theme.muted}]Remove --preview flag to import[/{theme.muted}]\n")
        return

    # SINGLE service call - import mode
    # Auto-detect columns if not provided (CLI responsibility to collect all params)
    import_column_mapping = column_mapping
    if not import_column_mapping:
        if not json_output:
            with console.status(f"[{theme.status_loading}]Detecting CSV columns..."):
                detect_result = asyncio.run(import_service.detect_columns(source_type="csv", file_path=str(csv_path)))
        else:
            detect_result = asyncio.run(import_service.detect_columns(source_type="csv", file_path=str(csv_path)))

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
            result = asyncio.run(import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=UUID(account_id),
                source_options=source_options,
            ))
    else:
        result = asyncio.run(import_service.import_transactions(
            user_id=user_id,
            source_type="csv",
            account_id=UUID(account_id),
            source_options=source_options,
        ))

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


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version information",
    )
):
    """Treeline - AI-native personal finance in your terminal."""
    pass


if __name__ == "__main__":
    app()
