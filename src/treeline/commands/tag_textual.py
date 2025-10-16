"""Textual TUI for transaction tagging."""

import asyncio
from uuid import UUID
from typing import List, Dict

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, DataTable, Footer, Header, Input, Label, Static

from treeline.domain import Transaction
from treeline.tui_theme import ThemedApp


class TagEditModal(ModalScreen[bool]):
    """Modal screen for editing transaction tags."""

    DEFAULT_CSS = """
    TagEditModal {
        align: center middle;
    }

    #dialog {
        width: 70;
        height: auto;
        background: $panel;
        border: solid $primary;
        padding: 1;
    }

    #tag_input {
        width: 100%;
        margin: 1 0;
    }

    #suggestions {
        color: $text-muted;
        margin: 1 0;
    }

    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss(False)", "Cancel", show=False),
    ]

    def __init__(
        self,
        transaction: Transaction,
        current_tags: List[str],
        suggestions: List[str],
    ):
        super().__init__()
        self.transaction = transaction
        self.current_tags = current_tags
        self.suggestions = suggestions

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Edit tags for: {self.transaction.description[:50]}")
            yield Input(
                value=", ".join(self.current_tags),
                placeholder="tag1, tag2, tag3",
                id="tag_input",
            )

            if self.suggestions:
                suggestions_text = "Suggestions: " + ", ".join(self.suggestions[:5])
                yield Static(suggestions_text, id="suggestions")

            with Horizontal(id="buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Clear All", id="clear")
                yield Button("Cancel", id="cancel")

    @on(Button.Pressed, "#save")
    def handle_save(self) -> None:
        """Save the tags."""
        self.dismiss(True)

    @on(Button.Pressed, "#clear")
    def handle_clear(self) -> None:
        """Clear all tags."""
        tag_input = self.query_one("#tag_input", Input)
        tag_input.value = ""

    @on(Button.Pressed, "#cancel")
    def handle_cancel(self) -> None:
        """Cancel editing."""
        self.dismiss(False)

    def get_tags(self) -> List[str]:
        """Get the current tags from the input."""
        tag_input = self.query_one("#tag_input", Input)
        tags_text = tag_input.value.strip()
        if not tags_text:
            return []
        return [tag.strip() for tag in tags_text.split(",") if tag.strip()]


class TaggingScreen(Screen):
    """Main tagging interface screen."""

    BINDINGS = [
        Binding("t", "type_tags", "Type Tags", show=False),
        Binding("c", "clear_tags", "Clear Tags", show=False),
        Binding("1", "quick_tag(0)", "Tag 1", show=False),
        Binding("2", "quick_tag(1)", "Tag 2", show=False),
        Binding("3", "quick_tag(2)", "Tag 3", show=False),
        Binding("4", "quick_tag(3)", "Tag 4", show=False),
        Binding("5", "quick_tag(4)", "Tag 5", show=False),
        Binding("u", "toggle_filter", "Toggle Filter", show=False),
        Binding("]", "next_page", "Next Page", show=False),
        Binding("[", "prev_page", "Prev Page", show=False),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("q", "quit", "Quit", show=False),
    ]

    DEFAULT_CSS = """
    TaggingScreen {
        background: $background;
    }

    #status_bar {
        dock: top;
        height: 3;
        background: $panel;
        color: $text;
        padding: 1;
    }

    #main_container {
        height: 1fr;
    }

    #transaction_table {
        width: 3fr;
    }

    #details_panel {
        width: 2fr;
        background: $panel;
        border-left: solid $primary;
        padding: 1;
    }

    #help_bar {
        dock: bottom;
        height: 2;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        user_id: UUID,
        untagged_only: bool = False,
    ):
        super().__init__()
        self.user_id = user_id
        self.untagged_only = untagged_only
        self.transactions: List[Transaction] = []
        self.account_map: Dict[UUID, str] = {}
        self.current_offset = 0
        self.batch_size = 100
        self.current_suggestions: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading...", id="status_bar")

        with Horizontal(id="main_container"):
            yield DataTable(id="transaction_table", zebra_stripes=True, cursor_type="row")
            with VerticalScroll(id="details_panel"):
                yield Static("Select a transaction to see details", id="details_content")

        yield Static(
            "↑/↓: Navigate | 1-5: Quick Tag | T: Type Tags | C: Clear Tags | U: Toggle Untagged | [/]: Page | Q: Quit",
            id="help_bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the screen when mounted."""
        table = self.query_one(DataTable)

        # Add columns
        table.add_column("Date", width=12)
        table.add_column("Account", width=18)
        table.add_column("Description", width=30)
        table.add_column("Amount", width=12)
        table.add_column("Tags", width=20)

        # Load data
        self.load_data()

    @work(exclusive=True, thread=True)
    def load_data(self) -> None:
        """Load accounts and transactions in background."""
        from treeline.cli import get_container

        container = get_container()
        account_service = container.account_service()
        tagging_service = container.tagging_service()

        # Load accounts
        accounts_result = asyncio.run(account_service.get_accounts(self.user_id))
        if accounts_result.success:
            self.account_map = {
                acc.id: acc.nickname or acc.name for acc in accounts_result.data
            }

        # Load transactions
        filters = {"has_tags": False} if self.untagged_only else {}
        result = asyncio.run(
            tagging_service.get_transactions_for_tagging(
                self.user_id,
                filters=filters,
                limit=self.batch_size,
                offset=self.current_offset,
            )
        )

        if result.success:
            self.transactions = result.data or []
            self.app.call_from_thread(self.populate_table)
            self.app.call_from_thread(self.update_status)
            self.app.call_from_thread(self.update_details)

    def populate_table(self) -> None:
        """Populate the data table with transactions."""
        table = self.query_one(DataTable)
        table.clear()

        for tx in self.transactions:
            date_str = tx.transaction_date.strftime("%Y-%m-%d")
            account_name = self.account_map.get(tx.account_id, "Unknown")[:16]
            desc = (tx.description or "")[:28]

            # Format amount with color
            if tx.amount < 0:
                amount_str = f"[red]-${abs(tx.amount):,.2f}[/red]"
            else:
                amount_str = f"[green]${tx.amount:,.2f}[/green]"

            # Format tags with badge-like styling
            if tx.tags:
                badge_tags = [f"[cyan][[/cyan]{tag}[cyan]][/cyan]" for tag in tx.tags[:2]]
                tags_str = " ".join(badge_tags)
                if len(tx.tags) > 2:
                    tags_str += f" [dim]+{len(tx.tags) - 2}[/dim]"
            else:
                tags_str = "[dim](none)[/dim]"

            table.add_row(date_str, account_name, desc, amount_str, tags_str)

    def update_status(self) -> None:
        """Update the status bar."""
        status = self.query_one("#status_bar", Static)
        filter_text = "Untagged Only" if self.untagged_only else "All Transactions"
        tagged_count = sum(1 for tx in self.transactions if tx.tags)
        page_num = (self.current_offset // self.batch_size) + 1
        status.update(
            f"{filter_text} | Page {page_num} | Showing: {len(self.transactions)} | "
            f"Tagged: {tagged_count} | Untagged: {len(self.transactions) - tagged_count}"
        )

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the table."""
        self.update_details()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Handle row highlight changes (keyboard navigation)."""
        self.update_details()

    @work(exclusive=True, thread=True)
    async def update_details(self) -> None:
        """Update the details panel for the selected transaction."""
        table = self.query_one(DataTable)

        if table.cursor_row is None or table.cursor_row < 0 or table.cursor_row >= len(self.transactions):
            return

        transaction = self.transactions[table.cursor_row]

        # Get suggested tags
        from treeline.cli import get_container
        container = get_container()
        tagging_service = container.tagging_service()

        suggestions_result = await tagging_service.get_suggested_tags(
            self.user_id, transaction, limit=5
        )
        self.current_suggestions = suggestions_result.data if suggestions_result.success else []

        # Build details text
        details_lines = []
        details_lines.append(f"[bold]Selected Transaction ({table.cursor_row + 1}/{len(self.transactions)})[/bold]\n")
        details_lines.append(f"[dim]Account:[/dim] {self.account_map.get(transaction.account_id, 'Unknown')}")
        details_lines.append(f"[dim]Date:[/dim] {transaction.transaction_date}")
        details_lines.append(f"[dim]Description:[/dim] {transaction.description or '(none)'}")

        # Format amount with color
        if transaction.amount < 0:
            amount_display = f"[red]-${abs(transaction.amount):,.2f}[/red]"
        else:
            amount_display = f"[green]${transaction.amount:,.2f}[/green]"
        details_lines.append(f"[dim]Amount:[/dim] {amount_display}")

        # Current tags
        if transaction.tags:
            tags_display = ", ".join(transaction.tags)
            details_lines.append(f"\n[dim]Current Tags:[/dim] {tags_display}")
        else:
            details_lines.append(f"\n[dim]Current Tags:[/dim] [yellow](none)[/yellow]")

        # Suggested tags
        if self.current_suggestions:
            details_lines.append(f"\n[bold cyan]Suggested Tags:[/bold cyan]")
            for i, tag in enumerate(self.current_suggestions[:5]):
                details_lines.append(f"  [bold][{i+1}][/bold] {tag}")

        details_text = "\n".join(details_lines)

        def update_ui():
            details_content = self.query_one("#details_content", Static)
            details_content.update(details_text)

        self.app.call_from_thread(update_ui)

    def action_toggle_filter(self) -> None:
        """Toggle between all transactions and untagged only."""
        self.untagged_only = not self.untagged_only
        self.current_offset = 0
        self.load_data()

    def action_next_page(self) -> None:
        """Load next page of transactions."""
        if len(self.transactions) == self.batch_size:
            self.current_offset += self.batch_size
            self.load_data()

    def action_prev_page(self) -> None:
        """Load previous page of transactions."""
        if self.current_offset > 0:
            self.current_offset = max(0, self.current_offset - self.batch_size)
            self.load_data()

    def action_refresh(self) -> None:
        """Refresh the transaction list."""
        self.load_data()

    def action_quit(self) -> None:
        """Quit the tagging interface."""
        self.app.exit()

    def action_quick_tag(self, index: int) -> None:
        """Quickly apply a suggested tag by index (0-4)."""
        table = self.query_one(DataTable)

        if table.cursor_row is None or table.cursor_row < 0 or table.cursor_row >= len(self.transactions):
            return

        if index >= len(self.current_suggestions):
            return

        transaction = self.transactions[table.cursor_row]
        tag = self.current_suggestions[index]
        current_tags = list(transaction.tags) if transaction.tags else []

        # Add tag if not already present
        if tag not in current_tags:
            current_tags.append(tag)
            self.save_tags(transaction, current_tags)

    def action_clear_tags(self) -> None:
        """Clear all tags from the selected transaction."""
        table = self.query_one(DataTable)

        if table.cursor_row is None or table.cursor_row < 0 or table.cursor_row >= len(self.transactions):
            return

        transaction = self.transactions[table.cursor_row]

        # Only clear if there are tags
        if transaction.tags:
            self.save_tags(transaction, [])

    def action_type_tags(self) -> None:
        """Open modal to type tags manually."""
        self.action_edit_tags()

    @work(exclusive=True, thread=True)
    async def action_edit_tags(self) -> None:
        """Edit tags for the selected transaction."""
        table = self.query_one(DataTable)

        if table.cursor_row is None or table.cursor_row < 0:
            return

        row_idx = table.cursor_row
        if row_idx >= len(self.transactions):
            return

        transaction = self.transactions[row_idx]
        current_tags = list(transaction.tags) if transaction.tags else []

        # Show modal
        def show_modal():
            self.app.push_screen(
                TagEditModal(transaction, current_tags, self.current_suggestions),
                self.handle_tag_edit_result,
            )

        self.app.call_from_thread(show_modal)

    def handle_tag_edit_result(self, save: bool) -> None:
        """Handle the result from the tag edit modal."""
        if not save:
            return

        # Get the modal and extract tags
        modal = self.app.screen_stack[-1]
        if not isinstance(modal, TagEditModal):
            return

        tags = modal.get_tags()
        transaction = modal.transaction

        # Save the tags
        self.save_tags(transaction, tags)

    @work(exclusive=True, thread=True)
    def save_tags(self, transaction: Transaction, tags: List[str]) -> None:
        """Save tags for a transaction."""
        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        result = asyncio.run(
            tagging_service.update_transaction_tags(self.user_id, str(transaction.id), tags)
        )

        if result.success:
            # Update local transaction list
            for i, tx in enumerate(self.transactions):
                if tx.id == transaction.id:
                    self.transactions[i] = result.data
                    break

            # Refresh the table and details
            self.app.call_from_thread(self.populate_table)
            self.app.call_from_thread(self.update_status)
            self.app.call_from_thread(self.update_details)


class TaggingApp(ThemedApp):
    """Textual application for transaction tagging."""

    TITLE = "Transaction Tagging"

    def __init__(self, user_id: UUID, untagged_only: bool = False):
        super().__init__()
        self.user_id = user_id
        self.untagged_only = untagged_only

    def on_mount(self) -> None:
        """Initialize the app."""
        self.push_screen(TaggingScreen(self.user_id, self.untagged_only))
