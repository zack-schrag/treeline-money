"""Tag mode command handler."""

import asyncio
from uuid import UUID

from rich.console import Console
from rich.table import Table
from readchar import readkey, key as readkey_keys

console = Console()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def is_authenticated():
    """Check if user is authenticated."""
    from treeline.cli import is_authenticated as _is_authenticated
    return _is_authenticated()


def get_current_user_id():
    """Get current user ID."""
    from treeline.cli import get_current_user_id as _get_current_user_id
    return _get_current_user_id()


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
    account_map = {}  # Map of account_id -> account name

    def load_accounts():
        """Load accounts and create mapping."""
        nonlocal account_map
        accounts_result = asyncio.run(repository.get_accounts(UUID(user_id)))
        if accounts_result.success:
            account_map = {acc.id: acc.nickname or acc.name for acc in accounts_result.data}
            return True
        console.print(f"[red]Error loading accounts: {accounts_result.error}[/red]\n")
        return False

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

    # Load accounts and initial transactions
    console.print("[dim]Loading accounts and transactions...[/dim]")
    if not load_accounts():
        console.print(f"[red]Error loading accounts[/red]\n")
        return

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
        list_table.add_column("Account", width=20)
        list_table.add_column("Description", width=30)
        list_table.add_column("Amount", justify="right", width=12)
        list_table.add_column("Tags", width=20)

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
            account_name = account_map.get(txn.account_id, "Unknown")[:18]
            desc = (txn.description or "")[:28]

            # Format amount with proper sign placement and color
            if txn.amount < 0:
                amount_str = f"[red]-${abs(txn.amount):.2f}[/red]"
            else:
                amount_str = f"[green]${txn.amount:.2f}[/green]"

            tags_str = ", ".join(txn.tags[:2]) if txn.tags else ""
            if len(txn.tags) > 2:
                tags_str += "..."

            style = "bold cyan" if i == current_index else ""
            list_table.add_row(marker, date_str, account_name, desc, amount_str, tags_str, style=style)

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

        detail_table.add_row("Account", account_map.get(txn.account_id, "Unknown"))
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


