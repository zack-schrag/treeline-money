"""Login command handler."""

import asyncio

from rich.console import Console
from rich.prompt import Prompt, Confirm

console = Console()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


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
