"""Treeline CLI - Interactive financial data management."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
import traceback
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from treeline.app.container import Container

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()

# Global container instance
_container: Container | None = None


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
        console.print(f"[red]Error initializing database: {result.error}[/red]")
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
    info_parts.append("[bold green]🌲 Treeline[/bold green]")
    info_parts.append("")

    # Authentication status
    if config_service.is_authenticated():
        email = config_service.get_current_user_email()
        info_parts.append(f"[green]✓[/green] Logged in as [bold]{email}[/bold]")

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
                    info_parts.append(f"[cyan]📊 Quick Stats[/cyan]")
                    info_parts.append(f"  Accounts: [bold]{len(status['accounts'])}[/bold]")
                    info_parts.append(f"  Transactions: [bold]{status['total_transactions']}[/bold]")

                    if status['latest_date']:
                        info_parts.append(f"  Latest data: [bold]{status['latest_date']}[/bold]")
        except Exception:
            # If we can't get stats, just skip them
            pass
    else:
        info_parts.append("[yellow]⚠ Not authenticated[/yellow]")
        info_parts.append("Use [bold]/login[/bold] to sign in")

    if first_time:
        info_parts.append("")
        info_parts.append("[green]✓[/green] Initialized treeline directory")

    info_parts.append("")
    info_parts.append("[dim]Type [bold]/help[/bold] for commands[/dim]")
    info_parts.append("[dim]Type [bold]exit[/bold] or [bold]Ctrl+C[/bold] to quit[/dim]")

    # Get current directory name for display
    cwd = Path.cwd().name

    # Simple panel with just the info, fit to content
    panel = Panel(
        "\n".join(info_parts),
        border_style="green",
        padding=(1, 2),
        subtitle=f"[dim]{cwd}[/dim]",
        expand=False
    )

    console.print()
    console.print(panel)
    console.print()


def handle_help_command() -> None:
    """Display help information about available commands."""
    table = Table(title="Available Slash Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/help", "Show all available commands")
    table.add_row("/login", "Login or create your Treeline account")
    table.add_row("/status", "Shows summary of current state of your financial data")
    table.add_row("/query <SQL>", "Execute a SQL query directly")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")
    table.add_row("/clear", "Clear conversation history and start fresh")

    console.print(table)
    console.print("\n[dim]You can also ask questions about your financial data in natural language[/dim]\n")


def handle_login_command() -> None:
    """Handle /login command."""
    console.print("\n[bold cyan]Login to Treeline[/bold cyan]\n")

    container = get_container()
    config_service = container.config_service()

    try:
        auth_service = container.auth_service()
    except ValueError as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        console.print("[dim]Please set SUPABASE_URL and SUPABASE_KEY in your .env file[/dim]\n")
        return

    # Ask if user wants to sign in or create account
    create_account = Confirm.ask("Create a new account?", default=False)

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    console.print()
    with console.status("[bold green]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_service.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_service.sign_in_with_password(email, password))

    if not result.success:
        console.print(f"[red]Authentication failed: {result.error}[/red]\n")
        return

    user = result.data
    console.print(f"[green]✓[/green] Successfully authenticated as [bold]{user.email}[/bold]\n")

    # Save credentials using config service
    config_service.save_user_credentials(str(user.id), user.email)
    console.print("[dim]Credentials saved to system keyring[/dim]\n")


def handle_status_command() -> None:
    """Handle /status command."""
    container = get_container()
    config_service = container.config_service()
    status_service = container.status_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]📊 Financial Data Status[/bold cyan]\n")

    with console.status("[bold green]Loading data..."):
        result = asyncio.run(status_service.get_status(user_id))

        if not result.success:
            console.print(f"[red]Error loading status: {result.error}[/red]\n")
            return

        status = result.data

    # Display summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold white")

    summary_table.add_row("Accounts", str(len(status["accounts"])))
    summary_table.add_row("Transactions", str(status["total_transactions"]))
    summary_table.add_row("Balance Snapshots", str(status["total_snapshots"]))
    summary_table.add_row("Integrations", str(len(status["integrations"])))

    console.print(summary_table)

    # Date range
    if status["earliest_date"] and status["latest_date"]:
        console.print(f"\n[dim]Date range: {status['earliest_date']} to {status['latest_date']}[/dim]")

    # Show integrations
    if status["integrations"]:
        console.print("\n[bold]Connected Integrations:[/bold]")
        for integration in status["integrations"]:
            console.print(f"  • {integration['integrationName']}")

    console.print()


def handle_simplefin_command() -> None:
    """Handle /simplefin command."""
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]SimpleFIN Setup[/bold cyan]\n")
    console.print(
        "[dim]If you don't have a SimpleFIN account, create one at: https://beta-bridge.simplefin.org/[/dim]\n"
    )

    # Prompt for setup token
    setup_token = Prompt.ask("Enter your SimpleFIN setup token")

    if not setup_token or not setup_token.strip():
        console.print("[yellow]Setup cancelled.[/yellow]\n")
        return

    setup_token = setup_token.strip()

    # Use integration service
    integration_service = container.integration_service("simplefin")

    console.print()
    with console.status("[bold green]Verifying token and setting up integration..."):
        # Ensure user database is initialized
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

        # Create integration
        result = asyncio.run(
            integration_service.create_integration(user_id, "simplefin", {"setupToken": setup_token})
        )

        if not result.success:
            console.print(f"[red]Setup failed: {result.error}[/red]\n")
            return

    console.print(f"[green]✓[/green] SimpleFIN integration setup successfully!\n")
    console.print("\n[dim]Use /sync to import your transactions[/dim]\n")


def handle_sync_command() -> None:
    """Handle /sync command."""
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()
    sync_service = container.sync_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]Synchronizing Financial Data[/bold cyan]\n")

    # Ensure user database is initialized
    with console.status("[bold green]Initializing..."):
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

    # Sync all integrations using service
    with console.status("[bold green]Syncing integrations..."):
        result = asyncio.run(sync_service.sync_all_integrations(user_id))

    if not result.success:
        console.print(f"[yellow]{result.error}[/yellow]\n")
        if result.error == "No integrations configured":
            console.print("[dim]Use /simplefin to setup an integration first[/dim]\n")
        return

    # Display results
    for sync_result in result.data["results"]:
        integration_name = sync_result["integration"]
        console.print(f"[bold]Syncing {integration_name}...[/bold]")

        if "error" in sync_result:
            console.print(f"[red]  ✗ {sync_result['error']}[/red]")
            continue

        console.print(f"[green]  ✓[/green] Synced {sync_result['accounts_synced']} account(s)")

        if sync_result["sync_type"] == "incremental":
            console.print(
                f"[dim]  Syncing transactions since {sync_result['start_date'].date()} (with 7-day overlap)[/dim]"
            )
        else:
            console.print(f"[dim]  Initial sync: fetching last 90 days of transactions[/dim]")

        console.print(f"[green]  ✓[/green] Synced {sync_result['transactions_synced']} transaction(s)")
        console.print(f"[dim]  Balance snapshots created automatically from account data[/dim]")

    console.print(f"\n[green]✓[/green] Sync completed!\n")
    console.print("[dim]Use /status to see your updated data[/dim]\n")


def handle_import_command() -> None:
    """Handle /import command - import transactions from CSV."""
    import os
    from pathlib import Path

    if not is_authenticated():
        console.print("[red]Error: You must be logged in to import data.[/red]")
        console.print("[dim]Run /login to authenticate[/dim]\n")
        return

    user_id = get_current_user_id()
    if not user_id:
        console.print("[red]Error: Could not get user ID[/red]\n")
        return

    container = get_container()
    import_service = container.import_service()
    repository = container.repository()

    # Step 1: Get CSV file path
    console.print("\n[bold cyan]CSV Import[/bold cyan]\n")
    file_path = Prompt.ask("[cyan]Enter path to CSV file[/cyan]")

    if not file_path:
        console.print("[yellow]Import cancelled[/yellow]\n")
        return

    # Check if file exists - expand ~ manually using os.path
    expanded_path = os.path.expanduser(file_path)
    csv_path = Path(expanded_path)
    if not csv_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]\n")
        return

    # Step 2: Get or select account to import into
    console.print("\n[dim]Fetching accounts...[/dim]")
    accounts_result = asyncio.run(repository.get_accounts(UUID(user_id)))

    if not accounts_result.success or not accounts_result.data:
        console.print("[red]No accounts found. Please sync with SimpleFIN first.[/red]\n")
        return

    accounts = accounts_result.data

    # Display accounts for selection
    console.print("\n[cyan]Select account to import into:[/cyan]")
    for i, account in enumerate(accounts, 1):
        console.print(f"  [{i}] {account.name}" + (f" - {account.institution_name}" if account.institution_name else ""))

    account_choice = Prompt.ask("\n[cyan]Account number[/cyan]", default="1")

    try:
        account_idx = int(account_choice) - 1
        if account_idx < 0 or account_idx >= len(accounts):
            console.print("[red]Invalid account selection[/red]\n")
            return
        target_account = accounts[account_idx]
    except ValueError:
        console.print("[red]Invalid account selection[/red]\n")
        return

    # Step 3: Auto-detect columns and show preview
    csv_provider = container.provider_registry()["csv"]

    console.print("\n[dim]Detecting CSV columns...[/dim]")
    detect_result = csv_provider.detect_columns(str(csv_path))

    if not detect_result.success:
        console.print(f"[red]Error detecting columns: {detect_result.error}[/red]\n")
        return

    column_mapping = detect_result.data
    flip_signs = False

    if not column_mapping.get("date") or not (column_mapping.get("amount") or (column_mapping.get("debit") and column_mapping.get("credit"))):
        console.print("[yellow]Warning: Could not auto-detect all required columns[/yellow]")
        console.print("[dim]You'll need to manually specify column mapping[/dim]\n")
        # TODO: Fallback to manual mapping
        return

    # Show detected columns
    console.print("\n[green]✓ Detected columns:[/green]")
    for key, value in column_mapping.items():
        if value:
            console.print(f"  {key}: {value}")

    # Preview first 5 transactions
    console.print("\n[dim]Loading preview...[/dim]")

    preview_result = csv_provider.preview_transactions(
        str(csv_path),
        column_mapping,
        date_format="auto",
        limit=5,
        flip_signs=flip_signs
    )

    if not preview_result.success:
        console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
        return

    preview_txs = preview_result.data

    if not preview_txs:
        console.print("[yellow]No transactions found in CSV[/yellow]\n")
        return

    # Display preview table
    console.print("\n[bold cyan]Preview - First 5 Transactions:[/bold cyan]\n")

    preview_table = Table(show_header=True, box=None, padding=(0, 1))
    preview_table.add_column("Date", width=12)
    preview_table.add_column("Description", width=40)
    preview_table.add_column("Amount", justify="right", width=15)

    for tx in preview_txs:
        date_str = tx.transaction_date.strftime("%Y-%m-%d")
        desc = (tx.description or "")[:38]

        # Use proper sign placement: -$XX.XX not $-XX.XX
        if tx.amount < 0:
            amount_str = f"-${abs(tx.amount):,.2f}"
        else:
            amount_str = f"${tx.amount:,.2f}"

        # Color code: negative = red, positive = green
        amount_style = "red" if tx.amount < 0 else "green"
        preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

    console.print(preview_table)

    # Step 4: Validate preview with combined options
    console.print("\n[bold cyan]Preview Check[/bold cyan]")
    console.print("[dim]Spending should appear as NEGATIVE (red), income/refunds as POSITIVE (green)[/dim]\n")

    # Main preview validation loop
    while True:
        console.print("[cyan]What would you like to do?[/cyan]")
        console.print("  [1] Proceed with import")
        console.print("  [2] View more transactions (next 10)")
        console.print("  [3] Flip all signs (if spending shows positive)")
        console.print("  [4] Try different column mapping")
        console.print("  [5] Cancel import")

        choice = Prompt.ask("\n[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            # Proceed with import
            break

        elif choice == "2":
            # Show more transactions
            console.print("\n[dim]Loading more transactions...[/dim]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=15,  # Show 15 total (5 already shown + 10 more)
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
                continue

            preview_txs = preview_result.data

            # Display extended preview
            console.print("\n[bold cyan]Extended Preview - First 15 Transactions:[/bold cyan]\n")

            preview_table = Table(show_header=True, box=None, padding=(0, 1))
            preview_table.add_column("Date", width=12)
            preview_table.add_column("Description", width=40)
            preview_table.add_column("Amount", justify="right", width=15)

            for tx in preview_txs:
                date_str = tx.transaction_date.strftime("%Y-%m-%d")
                desc = (tx.description or "")[:38]
                # Use proper sign placement
                if tx.amount < 0:
                    amount_str = f"-${abs(tx.amount):,.2f}"
                else:
                    amount_str = f"${tx.amount:,.2f}"
                amount_style = "red" if tx.amount < 0 else "green"
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "3":
            # Flip signs
            flip_signs = True

            # Show preview with flipped signs
            console.print("\n[dim]Regenerating preview with flipped signs...[/dim]")

            preview_result = csv_provider.preview_transactions(
                str(csv_path),
                column_mapping,
                date_format="auto",
                limit=5,
                flip_signs=flip_signs
            )

            if not preview_result.success:
                console.print(f"[red]Error generating preview: {preview_result.error}[/red]\n")
                continue

            preview_txs = preview_result.data

            # Display updated preview
            console.print("\n[bold cyan]Updated Preview - First 5 Transactions:[/bold cyan]\n")

            preview_table = Table(show_header=True, box=None, padding=(0, 1))
            preview_table.add_column("Date", width=12)
            preview_table.add_column("Description", width=40)
            preview_table.add_column("Amount", justify="right", width=15)

            for tx in preview_txs:
                date_str = tx.transaction_date.strftime("%Y-%m-%d")
                desc = (tx.description or "")[:38]
                # Use proper sign placement
                if tx.amount < 0:
                    amount_str = f"-${abs(tx.amount):,.2f}"
                else:
                    amount_str = f"${tx.amount:,.2f}"
                amount_style = "red" if tx.amount < 0 else "green"
                preview_table.add_row(date_str, desc, f"[{amount_style}]{amount_str}[/{amount_style}]")

            console.print(preview_table)
            console.print()  # Blank line before next menu

        elif choice == "4":
            # Manual column mapping not implemented
            console.print("[yellow]Manual column mapping not yet implemented[/yellow]\n")
            continue

        else:  # choice == "5"
            # Cancel
            console.print("[yellow]Import cancelled[/yellow]\n")
            return

    # Step 4.5: Check for potential duplicates
    console.print("\n[dim]Checking for potential duplicates...[/dim]")

    # First, get the transactions that would be imported (need to map to target account)
    preview_with_account = []
    for tx in preview_txs:
        tx_dict = tx.model_dump()
        tx_dict["account_id"] = target_account.id
        # Remove fingerprint to force recalculation
        ext_ids = dict(tx_dict.get("external_ids", {}))
        ext_ids.pop("fingerprint", None)
        tx_dict["external_ids"] = ext_ids
        from treeline.domain import Transaction
        preview_with_account.append(Transaction(**tx_dict))

    potential_dupes_result = asyncio.run(import_service.find_potential_duplicates(
        user_id=UUID(user_id),
        account_id=target_account.id,
        transactions=preview_with_account
    ))

    if potential_dupes_result.success and potential_dupes_result.data:
        potential_dupes = potential_dupes_result.data

        console.print(f"\n[yellow]⚠ Found {len(potential_dupes)} potential duplicate(s)[/yellow]")
        console.print("[dim]These transactions have the same date and amount but different descriptions.[/dim]\n")

        # Show each potential duplicate
        for i, dupe_info in enumerate(potential_dupes, 1):
            csv_tx = dupe_info["csv_transaction"]
            existing_tx = dupe_info["existing_transaction"]

            console.print(f"[bold cyan]Potential Duplicate {i}/{len(potential_dupes)}:[/bold cyan]")

            comparison_table = Table(show_header=True, box=None, padding=(0, 2))
            comparison_table.add_column("", style="dim")
            comparison_table.add_column("CSV (New)", style="yellow")
            comparison_table.add_column("Existing", style="green")

            comparison_table.add_row(
                "Date",
                csv_tx.transaction_date.strftime("%Y-%m-%d"),
                existing_tx.transaction_date.strftime("%Y-%m-%d")
            )
            comparison_table.add_row(
                "Amount",
                f"${csv_tx.amount:.2f}",
                f"${existing_tx.amount:.2f}"
            )
            comparison_table.add_row(
                "Description",
                csv_tx.description or "",
                existing_tx.description or ""
            )

            console.print(comparison_table)

            # Ask user if they want to import this transaction
            import_anyway = Confirm.ask(
                f"\n[cyan]Import this transaction anyway?[/cyan]",
                default=False
            )

            if not import_anyway:
                # Mark this transaction to skip
                dupe_info["skip"] = True
                console.print("[dim]Will skip this transaction[/dim]\n")
            else:
                dupe_info["skip"] = False
                console.print("[dim]Will import this transaction[/dim]\n")

        # Filter out transactions user chose to skip
        skip_ids = {dupe["csv_transaction"].id for dupe in potential_dupes if dupe.get("skip")}
        if skip_ids:
            console.print(f"\n[dim]Skipping {len(skip_ids)} potential duplicate(s) as requested[/dim]")
            # Note: We'll need to modify the import flow to respect this
            # For now, we'll just warn the user
            console.print("[yellow]Note: The import will proceed with all transactions.[/yellow]")
            console.print("[yellow]Manual duplicate skipping will be implemented in a future update.[/yellow]\n")

    # Step 5: Execute import
    console.print("\n[dim]Importing transactions...[/dim]")

    import_result = asyncio.run(import_service.import_transactions(
        user_id=UUID(user_id),
        source_type="csv",
        account_id=target_account.id,
        source_options={
            "file_path": str(csv_path),
            "column_mapping": column_mapping,
            "date_format": "auto",
            "flip_signs": flip_signs,
        }
    ))

    if import_result.success:
        stats = import_result.data
        console.print(f"\n[bold green]✓ Import complete![/bold green]")
        console.print(f"  Discovered: {stats['discovered']} transactions")
        console.print(f"  Imported: {stats['imported']} new transactions")
        console.print(f"  Skipped: {stats['skipped']} duplicates\n")

        # Write debug CSV
        import csv as csv_module
        from datetime import datetime as dt

        debug_file = Path.cwd() / f"import_debug_{dt.now().strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(debug_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv_module.writer(f)
                writer.writerow(["Status", "Date", "Description", "Amount", "Fingerprint", "Existing Count"])

                # Write imported transactions
                for tx in stats.get('imported_transactions', []):
                    writer.writerow([
                        "IMPORTED",
                        tx.transaction_date.strftime("%Y-%m-%d"),
                        tx.description or "",
                        f"{tx.amount:.2f}",
                        tx.external_ids.get("fingerprint", ""),
                        "0"
                    ])

                # Write skipped transactions
                for skip_info in stats.get('skipped_transactions', []):
                    tx = skip_info['transaction']
                    writer.writerow([
                        "SKIPPED",
                        tx.transaction_date.strftime("%Y-%m-%d"),
                        tx.description or "",
                        f"{tx.amount:.2f}",
                        skip_info['fingerprint'],
                        str(skip_info['existing_count'])
                    ])

            console.print(f"[dim]Debug report written to: {debug_file}[/dim]\n")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not write debug file: {e}[/yellow]\n")
    else:
        console.print(f"\n[red]Error: {import_result.error}[/red]\n")


def handle_tag_command() -> None:
    """Handle /tag command - launch interactive tagging mode."""
    import readchar
    from rich.table import Table
    from rich.panel import Panel
    from treeline.infra.tag_suggesters import FrequencyTagSuggester, CommonTagSuggester, CombinedTagSuggester

    if not is_authenticated():
        console.print("[red]Error: You must be logged in to use tagging mode.[/red]")
        console.print("[dim]Run /login to authenticate[/dim]\n")
        return

    user_id = get_current_user_id()
    if not user_id:
        console.print("[red]Error: Could not get user ID[/red]\n")
        return

    container = get_container()
    repository = container.repository()

    # Create tagging service with combined suggester (frequency + common tags)
    frequency_suggester = FrequencyTagSuggester(repository)
    common_suggester = CommonTagSuggester()
    tag_suggester = CombinedTagSuggester(frequency_suggester, common_suggester)
    tagging_service = container.tagging_service(tag_suggester)

    # Pagination and filtering state
    current_index = 0
    page_size = 10
    batch_size = 100
    current_offset = 0
    show_untagged_only = False
    transactions = []

    def load_transactions():
        """Load transactions with current filter and offset."""
        nonlocal transactions
        filters = {"has_tags": False} if show_untagged_only else {}
        result = asyncio.run(tagging_service.get_transactions_for_tagging(
            UUID(user_id),
            filters=filters,
            limit=batch_size,
            offset=current_offset
        ))
        if result.success:
            transactions = result.data
            return True
        console.print(result.error)
        return False

    # Load initial transactions
    console.print("[dim]Loading transactions...[/dim]")
    if not load_transactions():
        console.print(f"[red]Error loading transactions[/red]\n")
        return

    if not transactions:
        console.print("[yellow]No transactions found![/yellow]\n")
        return

    def render_view():
        """Render transaction list and selected transaction details."""
        console.clear()
        filter_text = "untagged only" if show_untagged_only else "all transactions"
        page_info = f"(showing {current_offset + 1}-{current_offset + len(transactions)})"
        console.print(f"\n[green]Tagging Power Mode[/green] - {filter_text} {page_info}")
        console.print("[dim]↑/↓: navigate | 1-5: quick tag | t: type tags | c: clear | u: toggle untagged | n/p: next/prev page | q: quit[/dim]\n")

        # Transaction list
        list_table = Table(show_header=True, box=None, padding=(0, 1))
        list_table.add_column("", width=2)
        list_table.add_column("Date", width=12)
        list_table.add_column("Description", width=40)
        list_table.add_column("Amount", justify="right", width=12)
        list_table.add_column("Tags", width=30)

        # Show page of transactions around current index
        start_idx = max(0, current_index - page_size // 2)
        end_idx = min(len(transactions), start_idx + page_size)

        # Adjust start if we're near the end
        if end_idx - start_idx < page_size and start_idx > 0:
            start_idx = max(0, end_idx - page_size)

        for i in range(start_idx, end_idx):
            txn = transactions[i]
            marker = "→" if i == current_index else " "
            date_str = txn.transaction_date.strftime("%Y-%m-%d")
            desc = (txn.description or "")[:38]

            # Format amount with proper sign placement and color
            if txn.amount < 0:
                amount_str = f"[red]-${abs(txn.amount):.2f}[/red]"
            else:
                amount_str = f"[green]${txn.amount:.2f}[/green]"

            tags_str = ", ".join(txn.tags[:3]) if txn.tags else ""
            if len(txn.tags) > 3:
                tags_str += "..."

            style = "bold cyan" if i == current_index else ""
            list_table.add_row(marker, date_str, desc, amount_str, tags_str, style=style)

        console.print(list_table)

        # Selected transaction details
        txn = transactions[current_index]
        console.print(f"\n[bold cyan]Selected Transaction ({current_index + 1}/{len(transactions)})[/bold cyan]")

        detail_table = Table(show_header=False, box=None, padding=(0, 1))
        detail_table.add_column(style="dim", width=15)
        detail_table.add_column()

        # Format amount with proper sign placement and color
        if txn.amount < 0:
            amount_display = f"[red]-${abs(txn.amount):.2f}[/red]"
        else:
            amount_display = f"[green]${txn.amount:.2f}[/green]"

        detail_table.add_row("Description", txn.description or "")
        detail_table.add_row("Amount", amount_display)
        detail_table.add_row("Current tags", ", ".join(txn.tags) if txn.tags else "[dim](none)[/dim]")

        # Get suggested tags
        suggestions_result = asyncio.run(tagging_service.get_suggested_tags(UUID(user_id), txn, limit=5))
        suggested_tags = suggestions_result.data if suggestions_result.success else []

        if suggested_tags:
            suggestions_str = "  ".join([f"[bold][{i+1}][/bold] {tag}" for i, tag in enumerate(suggested_tags)])
            detail_table.add_row("Suggested", suggestions_str)

        console.print(detail_table)
        console.print()

        return suggested_tags

    while True:
        suggested_tags = render_view()

        try:
            key = readchar.readkey()

            if key == readchar.key.UP:
                if current_index > 0:
                    current_index -= 1

            elif key == readchar.key.DOWN:
                if current_index < len(transactions) - 1:
                    current_index += 1

            elif key in ['1', '2', '3', '4', '5']:
                tag_index = int(key) - 1
                if tag_index < len(suggested_tags):
                    tag = suggested_tags[tag_index]
                    txn = transactions[current_index]
                    current_tags = list(txn.tags) if txn.tags else []

                    if tag not in current_tags:
                        current_tags.append(tag)
                        result = asyncio.run(tagging_service.update_transaction_tags(
                            UUID(user_id), str(txn.id), current_tags
                        ))

                        if result.success:
                            transactions[current_index] = result.data

            elif key == 't':
                console.print("[cyan]Enter tags (comma-separated):[/cyan] ", end="")
                tags_input = input()

                if tags_input.strip():
                    tags = [t.strip() for t in tags_input.split(",") if t.strip()]
                    txn = transactions[current_index]
                    current_tags = list(txn.tags) if txn.tags else []

                    for tag in tags:
                        if tag not in current_tags:
                            current_tags.append(tag)

                    result = asyncio.run(tagging_service.update_transaction_tags(
                        UUID(user_id), str(txn.id), current_tags
                    ))

                    if result.success:
                        transactions[current_index] = result.data

            elif key == 'c':
                txn = transactions[current_index]
                if txn.tags:
                    result = asyncio.run(tagging_service.update_transaction_tags(
                        UUID(user_id), str(txn.id), []
                    ))

                    if result.success:
                        transactions[current_index] = result.data

            elif key == 'u':
                # Toggle untagged filter
                show_untagged_only = not show_untagged_only
                current_offset = 0
                current_index = 0
                load_transactions()

            elif key == 'n':
                # Next page
                if len(transactions) == batch_size:  # Might be more results
                    current_offset += batch_size
                    current_index = 0
                    if not load_transactions() or not transactions:
                        # No more results, go back
                        current_offset -= batch_size
                        load_transactions()

            elif key == 'p':
                # Previous page
                if current_offset > 0:
                    current_offset = max(0, current_offset - batch_size)
                    current_index = 0
                    load_transactions()

            elif key == 'q':
                console.clear()
                console.print("\n[green]✓[/green] Exited tagging mode\n")
                return

        except KeyboardInterrupt:
            console.clear()
            console.print("\n[green]✓[/green] Exited tagging mode\n")
            return


def handle_clear_command() -> None:
    """Handle /clear command - reset conversation session."""
    container = get_container()
    agent_service = container.agent_service()

    result = asyncio.run(agent_service.clear_session())

    if result.success:
        console.print("[green]✓[/green] Conversation cleared. Starting fresh!\n")
    else:
        console.print(f"[yellow]Note: {result.error}[/yellow]\n")


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
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Validate SQL - only allow SELECT and WITH queries
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        console.print("[red]Error: Only SELECT and WITH queries are allowed.[/red]")
        console.print("[dim]For data modifications, use the AI agent.[/dim]\n")
        return

    # Display the SQL query
    console.print()
    syntax = Syntax(sql_stripped, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(
        syntax,
        title="[bold cyan]Executing Query[/bold cyan]",
        border_style="cyan",
        padding=(0, 1),
    ))

    # Execute query
    with console.status("[dim]Running query...[/dim]"):
        result = asyncio.run(db_service.execute_query(user_id, sql_stripped))

    if not result.success:
        console.print(f"\n[red]Error: {result.error}[/red]\n")
        return

    # Format and display results
    query_result = result.data
    rows = query_result.get("rows", [])
    columns = query_result.get("columns", [])

    console.print()

    if len(rows) == 0:
        console.print("[dim]No results returned.[/dim]\n")
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold cyan", border_style="dim")

    # Add columns
    for col in columns:
        table.add_column(col)

    # Add rows
    for row in rows:
        # Convert row values to strings
        str_row = [str(val) if val is not None else "[dim]NULL[/dim]" for val in row]
        table.add_row(*str_row)

    console.print(table)
    console.print(f"\n[dim]{len(rows)} row{'s' if len(rows) != 1 else ''} returned[/dim]\n")


def handle_chat_message(message: str) -> None:
    """Handle natural language chat message."""
    container = get_container()
    config_service = container.config_service()
    agent_service = container.agent_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Get database path for this specific user
    treeline_dir = get_treeline_dir()
    db_path = str(treeline_dir / "treeline.db" / f"{user_id}.duckdb")

    # Send message to agent
    with console.status("[dim]Thinking...[/dim]"):
        result = asyncio.run(agent_service.chat(user_id, db_path, message))

    if not result.success:
        console.print(f"[red]Error: {result.error}[/red]\n")
        return

    # Stream the response
    response_data = result.data
    stream = response_data["stream"]

    console.print()  # Blank line before response

    try:
        # Consume the async stream
        async def consume_stream():
            from rich.panel import Panel
            from rich.syntax import Syntax

            current_content = []
            in_sql_block = False
            sql_content = []

            async for chunk in stream:
                # Check if this is a tool indicator (starts with special marker)
                if chunk.startswith("__TOOL_USE__:"):
                    tool_name = chunk.replace("__TOOL_USE__:", "").strip()

                    # Flush any pending content
                    if current_content:
                        console.print("".join(current_content), end="", markup=False)
                        current_content = []

                    # Display tool usage in a panel
                    console.print(Panel(
                        f"[cyan]Using tool:[/cyan] [bold]{tool_name}[/bold]",
                        border_style="dim",
                        padding=(0, 1),
                    ))

                elif chunk.startswith("Visualization:"):
                    # Flush any pending content
                    if current_content:
                        console.print("".join(current_content), end="", markup=False)
                        current_content = []

                    # Charts contain ANSI escape codes - use raw print
                    console.print()  # Blank line before chart
                    print(chunk, end="", flush=True)
                    console.print()  # Blank line after chart

                else:
                    # Check for SQL code blocks
                    if "```sql" in chunk:
                        in_sql_block = True
                        # Print content before SQL
                        before_sql = chunk.split("```sql")[0]
                        if before_sql:
                            current_content.append(before_sql)

                        # Flush content before SQL
                        if current_content:
                            console.print("".join(current_content), end="", markup=False)
                            current_content = []

                        # Start collecting SQL
                        sql_content = []
                        after_marker = chunk.split("```sql", 1)[1]
                        if after_marker:
                            sql_content.append(after_marker)

                    elif "```" in chunk and in_sql_block:
                        # End of SQL block
                        before_end = chunk.split("```")[0]
                        if before_end:
                            sql_content.append(before_end)

                        # Display SQL in a panel with syntax highlighting
                        sql_text = "".join(sql_content).strip()
                        if sql_text:
                            syntax = Syntax(sql_text, "sql", theme="monokai", line_numbers=False)
                            console.print(Panel(
                                syntax,
                                title="[bold cyan]SQL Query[/bold cyan]",
                                border_style="cyan",
                                padding=(0, 1),
                            ))

                        sql_content = []
                        in_sql_block = False

                        # Continue with content after closing ```
                        after_end = chunk.split("```", 1)[1]
                        if after_end:
                            current_content.append(after_end)

                    elif in_sql_block:
                        # Accumulate SQL content
                        sql_content.append(chunk)
                    else:
                        # Regular content - accumulate for printing
                        current_content.append(chunk)

                        # Print in larger chunks for better performance
                        if len(current_content) > 10:
                            console.print("".join(current_content), end="", markup=False)
                            current_content = []

            # Flush any remaining content
            if current_content:
                console.print("".join(current_content), end="", markup=False)
            if sql_content:
                # Handle case where SQL block wasn't closed
                sql_text = "".join(sql_content).strip()
                if sql_text:
                    syntax = Syntax(sql_text, "sql", theme="monokai", line_numbers=False)
                    console.print(Panel(
                        syntax,
                        title="[bold cyan]SQL Query[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1),
                    ))

        asyncio.run(consume_stream())

    except Exception as e:
        console.print(f"[red]Error streaming response: {str(e)}[/red]")

    console.print()  # Blank line after response


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
        elif command == "/query":
            # Extract SQL from command
            if len(command_parts) < 2:
                console.print("[red]Error: /query requires a SQL statement[/red]")
                console.print("[dim]Usage: /query SELECT * FROM transactions LIMIT 5[/dim]\n")
            else:
                sql = command_parts[1]
                handle_query_command(sql)
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help to see available commands[/dim]")
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

    # Main REPL loop
    try:
        while True:
            try:
                # Print separator line before prompt
                console.print("[dim]" + "─" * console.width + "[/dim]")
                # Use input() with console cursor control for better spacing
                console.print(">: ", end="")
                user_input = input()
                # Print separator line after prompt with spacing
                console.print("[dim]" + "─" * console.width + "[/dim]")
                console.print()  # Add blank line for cushion

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
        console.print("[red]Unexpected error:[/red]")
        # Don't use markup since error messages may contain square brackets
        console.print(str(e), markup=False)
        console.print(traceback.format_exc(), markup=False)
        sys.exit(1)


@app.command(name="status")
def status_command() -> None:
    """Shows summary of current state of your financial data."""
    ensure_treeline_initialized()
    handle_status_command()


@app.command(name="query")
def query_command(sql: str = typer.Argument(..., help="SQL query to execute (SELECT/WITH only)")) -> None:
    """Execute a SQL query directly."""
    ensure_treeline_initialized()
    handle_query_command(sql)


@app.command(name="sync")
def sync_command() -> None:
    """Run an on-demand data synchronization."""
    ensure_treeline_initialized()
    handle_sync_command()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Treeline - AI-native personal finance in your terminal.

    Run without arguments to enter interactive mode, or use a specific command.
    """
    if ctx.invoked_subcommand is None:
        # No command specified - enter interactive mode
        run_interactive_mode()


if __name__ == "__main__":
    app()
