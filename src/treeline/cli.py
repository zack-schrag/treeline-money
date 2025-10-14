"""Treeline CLI - Interactive financial data management."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
import traceback
import typer
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from treeline.app.container import Container
from treeline.commands.analysis_textual import handle_analysis_command
from treeline.commands.chart import handle_chart_command
from treeline.commands.chat import handle_chat_message
from treeline.commands.help import handle_help_command
from treeline.commands.import_csv import handle_import_command
from treeline.commands.login import handle_login_command
from treeline.commands.query import handle_clear_command, handle_query_command, handle_sql_command
from treeline.commands.saved_queries import handle_queries_command, load_query
from treeline.commands.schema import handle_schema_command
from treeline.commands.simplefin import handle_simplefin_command
from treeline.commands.status import handle_status_command
from treeline.commands.sync import handle_sync_command
from treeline.commands.tag import handle_tag_command
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

# Available slash commands
SLASH_COMMANDS = [
    "/help",
    "/login",
    "/status",
    "/simplefin",
    "/sync",
    "/import",
    "/tag",
    "/query",
    "/sql",
    "/analysis",
    "/schema",
    "/queries",
    "/chart",
    "/clear",
    "/exit",
]


def get_slash_command_completions(text: str) -> list[str]:
    """Get slash command completions for the given text.

    Args:
        text: The current input text

    Returns:
        List of matching slash commands
    """
    if not text.startswith("/"):
        return []

    # Return all commands if just "/" is typed
    if text == "/":
        return SLASH_COMMANDS

    # Return commands that start with the typed text
    return [cmd for cmd in SLASH_COMMANDS if cmd.startswith(text.lower())]


def get_file_path_completions(text: str) -> list[str]:
    """Get file path completions for the given text.

    Args:
        text: The current partial path

    Returns:
        List of matching file/directory paths
    """
    import os
    import glob

    # Expand ~ to home directory
    expanded_text = os.path.expanduser(text)

    # If the text is empty or just ~, return home directory contents
    if not text or text == "~" or text == "~/":
        base_path = os.path.expanduser("~/")
        try:
            items = os.listdir(base_path)
            return [os.path.join("~", item) for item in sorted(items)]
        except (OSError, PermissionError):
            return []

    # Handle partial paths
    try:
        # Get the directory and partial filename
        if os.path.isdir(expanded_text):
            # If it's a directory, list its contents
            base_dir = expanded_text
            pattern = "*"
        else:
            # It's a partial path
            base_dir = os.path.dirname(expanded_text) or "."
            pattern = os.path.basename(expanded_text) + "*"

        # Get matching paths
        search_pattern = os.path.join(base_dir, pattern)
        matches = glob.glob(search_pattern)

        # Convert back to original format (preserve ~ if used)
        if text.startswith("~/"):
            home = os.path.expanduser("~")
            matches = [m.replace(home, "~", 1) if m.startswith(home) else m for m in matches]

        # Sort and return (directories first, then files)
        def sort_key(p):
            is_dir = os.path.isdir(os.path.expanduser(p))
            return (not is_dir, p.lower())

        return sorted(matches, key=sort_key)

    except (OSError, PermissionError):
        return []


class SlashCommandCompleter(Completer):
    """Completer for slash commands in the REPL."""

    def get_completions(self, document, _complete_event):
        """Generate completions for the current document."""
        text = document.text_before_cursor

        # Only provide completions for slash commands
        if not text.startswith("/"):
            return

        # Get matching commands
        matches = get_slash_command_completions(text)

        # Yield each match as a completion
        for match in matches:
            yield Completion(
                match,
                start_position=-len(text),
                display=match,
            )


def prompt_for_file_path(prompt_text: str = "") -> str:
    """Prompt user for a file path with autocomplete.

    Args:
        prompt_text: The prompt text to display (plain text, no Rich markup)

    Returns:
        The file path entered by the user
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import completion_is_selected

    # PathCompleter with expanduser=True handles ~ expansion
    # only_directories=False allows both files and directories
    completer = PathCompleter(expanduser=True, only_directories=False)

    # Create custom key bindings to handle Enter on directory selections
    kb = KeyBindings()

    @kb.add('enter', filter=completion_is_selected)
    def _(event):
        """When Enter is pressed on a selected completion, insert it and continue editing."""
        import os

        # Get the current completion
        completion = event.current_buffer.complete_state.current_completion
        if completion:
            # Insert the completion text
            event.current_buffer.apply_completion(completion)

            # If it's a directory and doesn't end with /, add one
            current_text = event.current_buffer.text
            expanded_path = os.path.expanduser(current_text)
            if os.path.isdir(expanded_path) and not current_text.endswith('/'):
                event.current_buffer.insert_text('/')
        # Don't accept the input - let user continue typing

    session = PromptSession(completer=completer, key_bindings=kb)

    if prompt_text:
        return session.prompt(f"{prompt_text}: ")
    else:
        return session.prompt(">: ")


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the current working directory."""
    return Path.cwd() / "treeline"


# Legacy helper functions for backward compatibility with tests
def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return get_container().config_service().is_authenticated()


def get_current_user_id() -> str | None:
    """Get the current authenticated user ID."""
    return get_container().config_service().get_current_user_id()


def get_current_user_email() -> str | None:
    """Get the current authenticated user email."""
    return get_container().config_service().get_current_user_email()


def get_container() -> Container:
    """Get or create the dependency injection container."""
    global _container
    if _container is None:
        treeline_dir = get_treeline_dir()
        db_path = treeline_dir / "treeline.db"
        _container = Container(str(db_path))
    return _container


# ========================================
# Helper Functions for New CLI Commands
# ========================================

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


def show_welcome_message(first_time: bool = False) -> None:
    """Display welcome message with ASCII art and useful information."""
    from rich.panel import Panel
    from rich.table import Table
    from pathlib import Path

    # Get container and services
    container = get_container()
    config_service = container.config_service()

    # Build info content
    info_parts = []

    # Title
    info_parts.append(f"[{theme.ui_header}]🌲 Treeline[/{theme.ui_header}]")
    info_parts.append("")

    # Authentication status
    if config_service.is_authenticated():
        email = config_service.get_current_user_email()
        info_parts.append(f"[{theme.success}]✓[/{theme.success}] Logged in as [{theme.emphasis}]{email}[/{theme.emphasis}]")

        # Try to get quick stats
        try:
            user_id_str = config_service.get_current_user_id()
            if user_id_str:
                from uuid import UUID
                user_id = UUID(user_id_str)
                status_service = container.status_service()
                result = asyncio.run(status_service.get_status(user_id))

                if result.success:
                    status = result.data
                    info_parts.append("")
                    info_parts.append(f"[{theme.info}]📊 Quick Stats[/{theme.info}]")
                    info_parts.append(f"  Accounts: [{theme.emphasis}]{len(status['accounts'])}[/{theme.emphasis}]")
                    info_parts.append(f"  Transactions: [{theme.emphasis}]{status['total_transactions']}[/{theme.emphasis}]")

                    if status['latest_date']:
                        info_parts.append(f"  Latest data: [{theme.emphasis}]{status['latest_date']}[/{theme.emphasis}]")
        except Exception:
            # If we can't get stats, just skip them
            pass
    else:
        info_parts.append(f"[{theme.warning}]⚠ Not authenticated[/{theme.warning}]")
        info_parts.append(f"Use [{theme.emphasis}]/login[/{theme.emphasis}] to sign in")

    if first_time:
        info_parts.append("")
        info_parts.append(f"[{theme.success}]✓[/{theme.success}] Initialized treeline directory")

    info_parts.append("")
    info_parts.append(f"[{theme.muted}]Type [{theme.emphasis}]/help[/{theme.emphasis}] for commands[/{theme.muted}]")
    info_parts.append(f"[{theme.muted}]Type [{theme.emphasis}]exit[/{theme.emphasis}] or [{theme.emphasis}]Ctrl+C[/{theme.emphasis}] to quit[/{theme.muted}]")

    # Get current directory name for display
    cwd = Path.cwd().name

    # Simple panel with just the info, fit to content
    panel = Panel(
        "\n".join(info_parts),
        border_style=theme.primary,
        padding=(1, 2),
        subtitle=f"[{theme.muted}]{cwd}[/{theme.muted}]",
        expand=False
    )

    console.print()
    console.print(panel)
    console.print()



def process_command(user_input: str) -> bool:
    """Process a user command. Returns True to continue REPL, False to exit."""
    user_input = user_input.strip()

    if not user_input:
        return True

    if user_input.lower() in ("exit", "quit"):
        console.print(f"[{theme.muted}]Goodbye![/{theme.muted}]")
        return False

    # Handle slash commands
    if user_input.startswith("/"):
        command_parts = user_input.split(maxsplit=1)
        command = command_parts[0].lower()

        if command == "/help":
            handle_help_command()
        elif command == "/login":
            handle_login_command()
        elif command == "/status":
            handle_status_command()
        elif command == "/simplefin":
            handle_simplefin_command()
        elif command == "/sync":
            handle_sync_command()
        elif command == "/import":
            handle_import_command()
        elif command == "/tag":
            handle_tag_command()
        elif command == "/clear":
            handle_clear_command()
        elif command == "/exit":
            console.print(f"[{theme.muted}]Goodbye![/{theme.muted}]")
            return False
        elif command == "/query":
            # Extract SQL from command
            if len(command_parts) < 2:
                console.print(f"[{theme.error}]Error: /query requires a SQL statement[/{theme.error}]")
                console.print(f"[{theme.muted}]Usage: /query SELECT * FROM transactions LIMIT 5[/{theme.muted}]\n")
            else:
                sql = command_parts[1]
                handle_query_command(sql)
        elif command.startswith("/query:"):
            # Handle /query:name syntax for saved queries
            query_name = command[7:]  # Remove "/query:" prefix
            if not query_name:
                console.print(f"[{theme.error}]Error: /query: requires a query name[/{theme.error}]")
                console.print(f"[{theme.muted}]Usage: /query:dining_this_month[/{theme.muted}]\n")
            else:
                sql = load_query(query_name)
                if sql is None:
                    console.print(f"[{theme.error}]Query '{query_name}' not found.[/{theme.error}]")
                    console.print(f"[{theme.muted}]Use /queries list to see available queries.[/{theme.muted}]\n")
                else:
                    handle_query_command(sql)
        elif command == "/sql":
            handle_sql_command()
        elif command == "/schema":
            # Extract optional table name
            table_name = command_parts[1] if len(command_parts) > 1 else None
            handle_schema_command(table_name)
        elif command == "/queries":
            # Handle /queries subcommands
            subcommand = command_parts[1] if len(command_parts) > 1 else None
            query_name = command_parts[2] if len(command_parts) > 2 else None
            handle_queries_command(subcommand, query_name)
        elif command == "/chart":
            # Handle /chart [name] - run saved chart or list charts
            chart_name = command_parts[1] if len(command_parts) > 1 else None
            handle_chart_command(chart_name)
        elif command == "/analysis":
            # Handle /analysis - integrated workspace for data exploration
            handle_analysis_command()
        else:
            console.print(f"[{theme.error}]Unknown command: {command}[/{theme.error}]")
            console.print(f"[{theme.muted}]Type /help to see available commands[/{theme.muted}]")
    else:
        # Natural language query - send to AI agent
        handle_chat_message(user_input)

    return True


def run_interactive_mode() -> None:
    """Run the interactive REPL mode."""
    # Initialize treeline directory and database
    first_time = ensure_treeline_initialized()

    # Show welcome message
    show_welcome_message(first_time)

    # Create prompt session with autocomplete
    session = PromptSession(completer=SlashCommandCompleter())

    # Main REPL loop
    try:
        while True:
            try:
                # Print separator line before prompt
                console.print(f"[{theme.separator}]" + "─" * console.width + f"[/{theme.separator}]")

                # Use prompt_toolkit for input with autocomplete
                user_input = session.prompt(">: ")

                # Print separator line after prompt with spacing
                console.print(f"[{theme.separator}]" + "─" * console.width + f"[/{theme.separator}]")
                console.print()  # Add blank line for cushion

                should_continue = process_command(user_input)
                if not should_continue:
                    break
            except KeyboardInterrupt:
                console.print(f"\n[{theme.muted}]Goodbye! =K[/{theme.muted}]")
                break
            except EOFError:
                console.print(f"\n[{theme.muted}]Goodbye! =K[/{theme.muted}]")
                break
    except Exception as e:
        console.print(f"[{theme.error}]Unexpected error:[/{theme.error}]")
        # Don't use markup since error messages may contain square brackets
        console.print(str(e), markup=False)
        console.print(traceback.format_exc(), markup=False)
        sys.exit(1)


@app.command(name="analysis")
def analysis_command() -> None:
    """Launch interactive data analysis workspace."""
    ensure_treeline_initialized()
    require_auth()
    from treeline.commands.analysis_textual import AnalysisApp
    app_instance = AnalysisApp()
    app_instance.run()


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
def query_command(sql: str = typer.Argument(..., help="SQL query to execute (SELECT/WITH only)")) -> None:
    """Execute a SQL query directly."""
    ensure_treeline_initialized()
    handle_query_command(sql)


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
        from treeline.commands.import_csv import handle_import_command
        handle_import_command()
        return

    # SCRIPTABLE MODE: File path provided
    from pathlib import Path as PathLib
    csv_path = PathLib(file_path).expanduser()

    if not csv_path.exists():
        display_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    container = get_container()
    import_service = container.import_service()
    account_service = container.account_service()

    # Build column mapping from flags or auto-detect
    if date_column or amount_column or debit_column or credit_column:
        # User provided explicit mapping
        column_mapping = {}
        if date_column:
            column_mapping["date"] = date_column
        if description_column:
            column_mapping["description"] = description_column
        if amount_column:
            column_mapping["amount"] = amount_column
        if debit_column:
            column_mapping["debit"] = debit_column
        if credit_column:
            column_mapping["credit"] = credit_column
    else:
        # Auto-detect columns
        if not json_output:
            with console.status(f"[{theme.status_loading}]Detecting CSV columns..."):
                detect_result = asyncio.run(import_service.detect_csv_columns(str(csv_path)))
        else:
            detect_result = asyncio.run(import_service.detect_csv_columns(str(csv_path)))

        if not detect_result.success:
            display_error(f"Column detection failed: {detect_result.error}")
            raise typer.Exit(1)

        column_mapping = detect_result.data

    # Get account
    if account_id:
        # Find account by ID
        accounts_result = asyncio.run(account_service.get_accounts(user_id))
        if not accounts_result.success:
            display_error("Failed to fetch accounts")
            raise typer.Exit(1)

        target_account = None
        for acc in accounts_result.data or []:
            if str(acc.id) == account_id:
                target_account = acc
                break

        if not target_account:
            display_error(f"Account not found: {account_id}")
            raise typer.Exit(1)
    else:
        display_error("--account-id is required for scriptable import")
        console.print(f"[{theme.muted}]Run 'treeline status --json' to see account IDs[/{theme.muted}]")
        raise typer.Exit(1)

    # Preview or import
    if preview:
        # Just show preview
        preview_result = asyncio.run(import_service.preview_csv_import(
            file_path=str(csv_path),
            column_mapping=column_mapping,
            date_format="auto",
            limit=10,
            flip_signs=flip_signs
        ))

        if not preview_result.success:
            display_error(f"Preview failed: {preview_result.error}")
            raise typer.Exit(1)

        if json_output:
            # Output preview as JSON
            preview_data = {
                "file": str(csv_path),
                "column_mapping": column_mapping,
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
            console.print(f"Account: {target_account.name}")
            console.print(f"Flip signs: {flip_signs}\n")

            for tx in preview_result.data[:10]:
                amount_style = theme.negative_amount if tx.amount < 0 else theme.positive_amount
                amount_str = f"-${abs(tx.amount):,.2f}" if tx.amount < 0 else f"${tx.amount:,.2f}"
                console.print(f"  {tx.transaction_date}  [{amount_style}]{amount_str:>12}[/{amount_style}]  {tx.description}")

            console.print(f"\n[{theme.muted}]Remove --preview flag to import[/{theme.muted}]\n")
    else:
        # Execute import
        if not json_output:
            with console.status(f"[{theme.status_loading}]Importing transactions..."):
                result = asyncio.run(import_service.import_transactions(
                    user_id=user_id,
                    source_type="csv",
                    account_id=target_account.id,
                    source_options={
                        "file_path": str(csv_path),
                        "column_mapping": column_mapping,
                        "date_format": "auto",
                        "flip_signs": flip_signs,
                    }
                ))
        else:
            result = asyncio.run(import_service.import_transactions(
                user_id=user_id,
                source_type="csv",
                account_id=target_account.id,
                source_options={
                    "file_path": str(csv_path),
                    "column_mapping": column_mapping,
                    "date_format": "auto",
                    "flip_signs": flip_signs,
                }
            ))

        if not result.success:
            display_error(result.error)
            raise typer.Exit(1)

        if json_output:
            output_json(result.data)
        else:
            stats = result.data
            console.print(f"\n[{theme.success}]✓ Import complete![/{theme.success}]")
            console.print(f"  Discovered: {stats['discovered']} transactions")
            console.print(f"  Imported: {stats['imported']} new transactions")
            console.print(f"  Skipped: {stats['skipped']} duplicates\n")


@app.command(name="legacy")
def legacy_command() -> None:
    """Enter legacy REPL mode (temporary during migration)."""
    run_interactive_mode()


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
