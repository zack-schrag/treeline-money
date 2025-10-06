"""Sync command handler."""

import asyncio
from uuid import UUID

from rich.console import Console

console = Console()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


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
