"""Login command handler."""

import asyncio

from rich.console import Console
from rich.prompt import Prompt, Confirm
from treeline.theme import get_theme

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def handle_login_command() -> None:
    """Handle /login command."""
    console.print(f"\n[{theme.ui_header}]Login to Treeline[/{theme.ui_header}]\n")

    container = get_container()
    config_service = container.config_service()

    try:
        auth_service = container.auth_service()
    except ValueError as e:
        console.print(f"\n[{theme.error}]Error: {str(e)}[/{theme.error}]")
        console.print(f"[{theme.muted}]Please set SUPABASE_URL and SUPABASE_KEY in your .env file[/{theme.muted}]\n")
        return

    # Ask if user wants to sign in or create account
    create_account = Confirm.ask("Create a new account?", default=False)

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    console.print()
    with console.status(f"[{theme.status_loading}]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_service.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_service.sign_in_with_password(email, password))

    if not result.success:
        console.print(f"[{theme.error}]Authentication failed: {result.error}[/{theme.error}]\n")
        return

    user = result.data
    console.print(f"[{theme.success}]✓[/{theme.success}] Successfully authenticated as [{theme.emphasis}]{user.email}[/{theme.emphasis}]\n")

    # Save credentials using config service
    config_service.save_user_credentials(str(user.id), user.email)
    console.print(f"[{theme.muted}]Credentials saved to system keyring[/{theme.muted}]\n")
