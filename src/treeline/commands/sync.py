"""Sync command handler."""

import asyncio
from uuid import UUID

from rich.console import Console
from treeline.theme import get_theme

console = Console()
theme = get_theme()


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
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    console.print(f"\n[{theme.ui_header}]Synchronizing Financial Data[/{theme.ui_header}]\n")

    # Ensure user database is initialized
    with console.status(f"[{theme.status_loading}]Initializing..."):
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[{theme.error}]Error initializing database: {db_init_result.error}[/{theme.error}]\n")
            return

    # Sync all integrations using service
    with console.status(f"[{theme.status_loading}]Syncing integrations..."):
        result = asyncio.run(sync_service.sync_all_integrations(user_id))

    if not result.success:
        console.print(f"[{theme.warning}]{result.error}[/{theme.warning}]\n")
        if result.error == "No integrations configured":
            console.print(f"[{theme.muted}]Use /simplefin to setup an integration first[/{theme.muted}]\n")
        return

    # Display results
    for sync_result in result.data["results"]:
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
    console.print(f"[{theme.muted}]Use /status to see your updated data[/{theme.muted}]\n")
