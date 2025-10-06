"""Status command handler."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.table import Table

console = Console()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


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
