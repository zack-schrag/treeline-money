"""SimpleFIN command handler."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.prompt import Prompt
from treeline.theme import get_theme

console = Console()
theme = get_theme()


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
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

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
        return

    if not setup_token or not setup_token.strip():
        console.print(f"[{theme.warning}]Setup cancelled[/{theme.warning}]\n")
        return

    setup_token = setup_token.strip()

    # Use integration service
    integration_service = container.integration_service("simplefin")

    console.print()
    with console.status(f"[{theme.status_loading}]Verifying token and setting up integration..."):
        # Ensure user database is initialized
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[{theme.error}]Error initializing database: {db_init_result.error}[/{theme.error}]\n")
            return

        # Create integration
        result = asyncio.run(
            integration_service.create_integration(user_id, "simplefin", {"setupToken": setup_token})
        )

        if not result.success:
            console.print(f"[{theme.error}]Setup failed: {result.error}[/{theme.error}]\n")
            return

    console.print(f"[{theme.success}]✓[/{theme.success}] SimpleFIN integration setup successfully!\n")
    console.print(f"\n[{theme.muted}]Use /sync to import your transactions[/{theme.muted}]\n")
