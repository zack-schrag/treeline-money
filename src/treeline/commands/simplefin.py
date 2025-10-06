"""SimpleFIN command handler."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.prompt import Prompt

console = Console()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


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
