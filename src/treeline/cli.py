"""Treeline CLI - Interactive financial data management."""

import sys
from pathlib import Path

from dotenv import load_dotenv
import typer

# Load environment variables from .env file
load_dotenv()
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the current working directory."""
    return Path.cwd() / "treeline"


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    import keyring

    try:
        user_id = keyring.get_password("treeline", "user_id")
        return user_id is not None
    except Exception:
        return False


def get_current_user_id() -> str | None:
    """Get the current authenticated user ID."""
    import keyring

    try:
        return keyring.get_password("treeline", "user_id")
    except Exception:
        return None


def get_current_user_email() -> str | None:
    """Get the current authenticated user email."""
    import keyring

    try:
        return keyring.get_password("treeline", "user_email")
    except Exception:
        return None


def ensure_treeline_initialized() -> bool:
    """Ensure treeline directory and database exist. Returns True if initialization was needed."""
    treeline_dir = get_treeline_dir()
    db_path = treeline_dir / "treeline.db"

    needs_init = not (treeline_dir.exists() and db_path.exists())

    # Create directory if it doesn't exist
    treeline_dir.mkdir(exist_ok=True)

    # Initialize database with schema
    # Note: We don't need user_id for schema initialization
    # The repository will create the tables when we first connect
    from treeline.infra.duckdb import DuckDBRepository

    repository = DuckDBRepository(str(db_path))

    # Ensure schema is created - using a dummy UUID since schema is user-independent
    import asyncio
    from uuid import UUID

    dummy_user_id = UUID("00000000-0000-0000-0000-000000000000")
    result = asyncio.run(repository.ensure_db_exists(dummy_user_id))

    if not result.success:
        console.print(f"[red]Error initializing database: {result.error}[/red]")
        sys.exit(1)

    result = asyncio.run(repository.ensure_schema_upgraded(dummy_user_id))

    if not result.success:
        console.print(f"[red]Error initializing schema: {result.error}[/red]")
        sys.exit(1)

    return needs_init


def show_welcome_message(first_time: bool = False) -> None:
    """Display welcome message."""
    console.print("\n[bold green]🌲 Welcome to Treeline![/bold green]\n")

    if first_time:
        console.print("[dim]Initialized treeline directory in current folder[/dim]\n")

    # Show authentication status
    if is_authenticated():
        email = get_current_user_email()
        console.print(f"[dim]Logged in as {email}[/dim]\n")
    else:
        console.print("[yellow]⚠ Not authenticated. Please use [bold]/login[/bold] to sign in.[/yellow]\n")

    console.print("Type [bold]/help[/bold] to see available commands")
    console.print("Type [bold]exit[/bold] or press [bold]Ctrl+C[/bold] to quit\n")


def handle_help_command() -> None:
    """Display help information about available commands."""
    table = Table(title="Available Slash Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/help", "Show all available commands")
    table.add_row("/login", "Login or create your Treeline account")
    table.add_row("/status", "Shows summary of current state of your financial data")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")

    console.print(table)
    console.print("\n[dim]You can also ask questions about your financial data in natural language[/dim]\n")


def handle_login_command() -> None:
    """Handle /login command."""
    import asyncio
    from rich.prompt import Prompt, Confirm

    console.print("\n[bold cyan]Login to Treeline[/bold cyan]\n")

    # Ask if user wants to sign in or create account
    create_account = Confirm.ask("Create a new account?", default=False)

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    # Initialize Supabase auth provider
    import os
    from treeline.infra.supabase import SupabaseAuthProvider
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        console.print("\n[red]Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set[/red]")
        console.print("[dim]Please set these in your environment or .env file[/dim]\n")
        return

    supabase_client = create_client(supabase_url, supabase_key)
    auth_provider = SupabaseAuthProvider(supabase_client)

    # Sign in or sign up
    console.print()
    with console.status("[bold green]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_provider.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_provider.sign_in_with_password(email, password))

    if not result.success:
        console.print(f"[red]Authentication failed: {result.error}[/red]\n")
        return

    user = result.data
    console.print(f"[green]✓[/green] Successfully authenticated as [bold]{user.email}[/bold]\n")

    # Store credentials in keyring
    import keyring

    keyring.set_password("treeline", "supabase_access_token", "TODO_access_token")
    keyring.set_password("treeline", "user_id", str(user.id))
    keyring.set_password("treeline", "user_email", user.email)

    console.print("[dim]Credentials saved to system keyring[/dim]\n")


def handle_status_command() -> None:
    """Handle /status command."""
    import asyncio
    from uuid import UUID
    from rich.table import Table

    # Check authentication
    user_id_str = get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Get database path
    treeline_dir = get_treeline_dir()
    db_path = treeline_dir / "treeline.db"

    if not db_path.exists():
        console.print("[yellow]No database found. Add some data first.[/yellow]\n")
        return

    # Initialize repository
    from treeline.infra.duckdb import DuckDBRepository

    repository = DuckDBRepository(str(db_path))

    console.print("\n[bold cyan]📊 Financial Data Status[/bold cyan]\n")

    with console.status("[bold green]Loading data..."):
        # Ensure database exists for this user
        db_init_result = asyncio.run(repository.ensure_db_exists(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

        schema_result = asyncio.run(repository.ensure_schema_upgraded(user_id))
        if not schema_result.success:
            console.print(f"[red]Error initializing schema: {schema_result.error}[/red]\n")
            return

        # Get accounts
        accounts_result = asyncio.run(repository.get_accounts(user_id))
        if not accounts_result.success:
            console.print(f"[red]Error loading accounts: {accounts_result.error}[/red]\n")
            return

        accounts = accounts_result.data or []

        # Get integrations
        integrations_result = asyncio.run(repository.list_integrations(user_id))
        if not integrations_result.success:
            console.print(f"[red]Error loading integrations: {integrations_result.error}[/red]\n")
            return

        integrations = integrations_result.data or []

        # Query for transaction stats
        transaction_stats_query = """
            SELECT
                COUNT(*) as total_transactions,
                MIN(transaction_date) as earliest_date,
                MAX(transaction_date) as latest_date
            FROM transactions
        """
        stats_result = asyncio.run(repository.execute_query(user_id, transaction_stats_query))

        if not stats_result.success:
            console.print(f"[red]Error loading transaction stats: {stats_result.error}[/red]\n")
            return

        transaction_stats = stats_result.data
        rows = transaction_stats.get("rows", [])
        if rows and len(rows) > 0:
            total_transactions = rows[0].get("total_transactions", 0)
            earliest_date = rows[0].get("earliest_date")
            latest_date = rows[0].get("latest_date")
        else:
            total_transactions = 0
            earliest_date = None
            latest_date = None

        # Query for balance snapshots
        balance_query = "SELECT COUNT(*) as total_snapshots FROM balance_snapshots"
        balance_result = asyncio.run(repository.execute_query(user_id, balance_query))

        if not balance_result.success:
            total_snapshots = 0
        else:
            balance_data = balance_result.data
            balance_rows = balance_data.get("rows", [])
            total_snapshots = balance_rows[0].get("total_snapshots", 0) if balance_rows and len(balance_rows) > 0 else 0

    # Display summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold white")

    summary_table.add_row("Accounts", str(len(accounts)))
    summary_table.add_row("Transactions", str(total_transactions))
    summary_table.add_row("Balance Snapshots", str(total_snapshots))
    summary_table.add_row("Integrations", str(len(integrations)))

    console.print(summary_table)

    # Date range
    if earliest_date and latest_date:
        console.print(f"\n[dim]Date range: {earliest_date} to {latest_date}[/dim]")

    # Show integrations
    if integrations:
        console.print("\n[bold]Connected Integrations:[/bold]")
        for integration in integrations:
            console.print(f"  • {integration['integrationName']}")

    console.print()


def handle_simplefin_command() -> None:
    """Handle /simplefin command."""
    import asyncio
    from uuid import UUID
    from rich.prompt import Prompt

    # Check authentication
    user_id_str = get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]SimpleFIN Setup[/bold cyan]\n")
    console.print("[dim]If you don't have a SimpleFIN account, create one at: https://beta-bridge.simplefin.org/[/dim]\n")

    # Prompt for setup token
    setup_token = Prompt.ask("Enter your SimpleFIN setup token")

    if not setup_token or not setup_token.strip():
        console.print("[yellow]Setup cancelled.[/yellow]\n")
        return

    setup_token = setup_token.strip()

    # Get database path
    treeline_dir = get_treeline_dir()
    db_path = treeline_dir / "treeline.db"

    # Initialize repository and provider
    from treeline.infra.duckdb import DuckDBRepository
    from treeline.infra.simplefin import SimpleFINProvider

    repository = DuckDBRepository(str(db_path))
    simplefin_provider = SimpleFINProvider()

    console.print()
    with console.status("[bold green]Verifying token and setting up integration..."):
        # Ensure database exists
        db_init_result = asyncio.run(repository.ensure_db_exists(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

        schema_result = asyncio.run(repository.ensure_schema_upgraded(user_id))
        if not schema_result.success:
            console.print(f"[red]Error initializing schema: {schema_result.error}[/red]\n")
            return

        # Create integration (exchange token for access URL)
        integration_result = asyncio.run(
            simplefin_provider.create_integration(
                user_id, "simplefin", {"setupToken": setup_token}
            )
        )

        if not integration_result.success:
            console.print(f"[red]Setup failed: {integration_result.error}[/red]\n")
            return

        integration_settings = integration_result.data

        # Store integration in database
        upsert_result = asyncio.run(
            repository.upsert_integration(user_id, "simplefin", integration_settings)
        )

        if not upsert_result.success:
            console.print(f"[red]Failed to save integration: {upsert_result.error}[/red]\n")
            return

        # Fetch accounts to show preview
        accounts_result = asyncio.run(
            simplefin_provider.get_accounts(
                user_id, provider_account_ids=[], provider_settings=integration_settings
            )
        )

        if not accounts_result.success:
            console.print(f"[red]Failed to fetch accounts: {accounts_result.error}[/red]\n")
            return

        accounts = accounts_result.data or []

    console.print(f"[green]✓[/green] SimpleFIN integration setup successfully!\n")
    console.print(f"[bold]Found {len(accounts)} account(s):[/bold]")

    for account in accounts:
        institution = account.institution_name or "Unknown Institution"
        console.print(f"  • {account.name} ({institution})")

    console.print("\n[dim]Use /sync to import your transactions[/dim]\n")


def handle_sync_command() -> None:
    """Handle /sync command."""
    import asyncio
    from uuid import UUID

    # Check authentication
    user_id_str = get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Get database path
    treeline_dir = get_treeline_dir()
    db_path = treeline_dir / "treeline.db"

    # Initialize repository
    from treeline.infra.duckdb import DuckDBRepository
    from treeline.infra.simplefin import SimpleFINProvider
    from treeline.app.service import SyncService

    repository = DuckDBRepository(str(db_path))

    console.print("\n[bold cyan]Synchronizing Financial Data[/bold cyan]\n")

    with console.status("[bold green]Loading integrations..."):
        # Ensure database exists
        db_init_result = asyncio.run(repository.ensure_db_exists(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

        schema_result = asyncio.run(repository.ensure_schema_upgraded(user_id))
        if not schema_result.success:
            console.print(f"[red]Error initializing schema: {schema_result.error}[/red]\n")
            return

        # Get list of integrations
        integrations_result = asyncio.run(repository.list_integrations(user_id))
        if not integrations_result.success:
            console.print(f"[red]Failed to load integrations: {integrations_result.error}[/red]\n")
            return

        integrations = integrations_result.data or []

    if not integrations:
        console.print("[yellow]No integrations configured. Use /simplefin to setup an integration first.[/yellow]\n")
        return

    # Create provider registry
    provider_registry = {"simplefin": SimpleFINProvider()}

    # Initialize sync service
    sync_service = SyncService(provider_registry, repository)

    # Sync each integration
    for integration in integrations:
        integration_name = integration["integrationName"]
        integration_options = integration["integrationOptions"]

        console.print(f"[bold]Syncing {integration_name}...[/bold]")

        # Sync accounts
        with console.status(f"  Fetching accounts from {integration_name}..."):
            accounts_result = asyncio.run(
                sync_service.sync_accounts(user_id, integration_name, integration_options)
            )

            if not accounts_result.success:
                console.print(f"[red]  ✗ Failed to sync accounts: {accounts_result.error}[/red]")
                continue

            accounts_data = accounts_result.data
            num_accounts = len(accounts_data.get("accounts", []))
            console.print(f"[green]  ✓[/green] Synced {num_accounts} account(s)")

        # Sync transactions
        with console.status(f"  Fetching transactions from {integration_name}..."):
            transactions_result = asyncio.run(
                sync_service.sync_transactions(user_id, integration_name, integration_options)
            )

            if not transactions_result.success:
                console.print(f"[red]  ✗ Failed to sync transactions: {transactions_result.error}[/red]")
                continue

            transactions_data = transactions_result.data
            num_transactions = len(transactions_data.get("transactions", []))
            console.print(f"[green]  ✓[/green] Synced {num_transactions} transaction(s)")

        # Sync balances
        with console.status(f"  Fetching balance snapshots from {integration_name}..."):
            balances_result = asyncio.run(
                sync_service.sync_balances(user_id, integration_name, integration_options)
            )

            if not balances_result.success:
                console.print(f"[red]  ✗ Failed to sync balances: {balances_result.error}[/red]")
                continue

            balances_data = balances_result.data
            num_balances = len(balances_data.get("balances", []))
            console.print(f"[green]  ✓[/green] Synced {num_balances} balance snapshot(s)")

    console.print(f"\n[green]✓[/green] Sync completed!\n")
    console.print("[dim]Use /status to see your updated data[/dim]\n")


def handle_import_command() -> None:
    """Handle /import command."""
    console.print("[yellow]CSV import coming soon...[/yellow]")
    # TODO: Implement import


def handle_tag_command() -> None:
    """Handle /tag command."""
    console.print("[yellow]Tagging power mode coming soon...[/yellow]")
    # TODO: Implement tag


def process_command(user_input: str) -> bool:
    """Process a user command. Returns True to continue REPL, False to exit."""
    user_input = user_input.strip()

    if not user_input:
        return True

    if user_input.lower() in ("exit", "quit"):
        console.print("[dim]Goodbye! =K[/dim]")
        return False

    # Handle slash commands
    if user_input.startswith("/"):
        command = user_input.lower().split()[0]

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
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help to see available commands[/dim]")
    else:
        # Natural language query - TODO: implement AI integration
        console.print("[yellow]AI integration coming soon...[/yellow]")

    return True


def run_interactive_mode() -> None:
    """Run the interactive REPL mode."""
    # Initialize treeline directory and database
    first_time = ensure_treeline_initialized()

    # Show welcome message
    show_welcome_message(first_time)

    # TODO: Check authentication status and prompt for /login if needed

    # Main REPL loop
    try:
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]>[/bold cyan]")
                should_continue = process_command(user_input)
                if not should_continue:
                    break
            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye! =K[/dim]")
                break
            except EOFError:
                console.print("\n[dim]Goodbye! =K[/dim]")
                break
    except Exception as e:
        import traceback
        console.print("[red]Unexpected error:[/red]")
        # Don't use markup since error messages may contain square brackets
        console.print(str(e), markup=False)
        console.print(traceback.format_exc(), markup=False)
        sys.exit(1)


@app.command()
def main() -> None:
    """Start Treeline interactive mode."""
    run_interactive_mode()


if __name__ == "__main__":
    app()
