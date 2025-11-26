"""Rich-based TUI for transaction tagging."""

import asyncio
import sys
from typing import List, Dict, Optional
from uuid import UUID

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout as RichLayout
from rich.panel import Panel
from rich.text import Text
import readchar

from treeline.domain import Transaction
from treeline.theme import get_theme


class TaggingInterface:
    """Interactive tagging interface using Rich live display."""

    def __init__(self, untagged_only: bool = False):
        self.untagged_only = untagged_only
        self.initial_untagged_only = untagged_only  # Remember initial state for reset
        self.transactions: List[Transaction] = []  # All loaded transactions
        self.account_map: Dict[UUID, str] = {}
        self.current_cursor = 0
        self.search_query: str = ""
        self.current_suggestions: List[str] = []
        self.all_tags: List[str] = []
        self.console = Console()
        self.theme = get_theme()
        self.running = True
        self.search_mode: bool = False  # Track if we're in search mode
        self.search_input_buffer: str = ""  # Buffer for search input
        self.bulk_tag_mode: bool = False  # Track if we're in bulk tag mode
        self.bulk_tag_input_buffer: str = ""  # Buffer for bulk tag input
        self.bulk_tag_confirm_mode: bool = False  # Track if we're confirming bulk tag
        self.manual_tag_mode: bool = False  # Track if we're in manual tag mode
        self.manual_tag_input_buffer: str = ""  # Buffer for manual tag input

        # Display window for scrolling
        self.display_window_start: int = 0  # Start index of visible transactions
        self.display_window_size: int = 20  # Number of transactions to show at once

    async def load_accounts(self) -> None:
        """Load accounts for display."""
        from treeline.cli import get_container

        container = get_container()
        account_service = container.account_service()

        accounts_result = await account_service.get_accounts()
        if accounts_result.success:
            self.account_map = {
                acc.id: acc.nickname or acc.name for acc in accounts_result.data
            }

    async def load_transactions(self) -> None:
        """Load ALL transactions based on current filters (no pagination)."""
        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        filters = {"has_tags": False} if self.untagged_only else {}
        if self.search_query:
            filters["search"] = self.search_query

        # Load all filtered transactions (no limit/offset)
        result = await tagging_service.get_transactions_for_tagging(
            filters=filters,
            limit=100000,  # Large limit to get all results
            offset=0,
        )

        if result.success:
            self.transactions = result.data or []
            # Reset cursor and window when loading new data
            self.current_cursor = 0
            self.display_window_start = 0

    async def load_suggestions(self) -> None:
        """Load tag suggestions for the current transaction."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            self.current_suggestions = []
            return

        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        transaction = self.transactions[self.current_cursor]
        result = await tagging_service.get_suggested_tags(transaction, limit=5)
        self.current_suggestions = result.data if result.success else []

    async def load_all_tags(self) -> None:
        """Load all existing tags for autocomplete."""
        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        result = await tagging_service.get_tag_statistics()
        if result.success:
            # Sort by frequency
            self.all_tags = sorted(
                result.data.keys(), key=lambda t: result.data[t], reverse=True
            )

    def adjust_display_window(self) -> None:
        """Adjust the display window to keep the cursor visible.

        Maintains a margin of 3 rows from the top/bottom of the window.
        """
        margin = 3

        # If cursor is above the window, scroll up
        if self.current_cursor < self.display_window_start:
            self.display_window_start = max(0, self.current_cursor - margin)

        # If cursor is below the window, scroll down
        elif (
            self.current_cursor >= self.display_window_start + self.display_window_size
        ):
            self.display_window_start = min(
                len(self.transactions) - self.display_window_size,
                self.current_cursor - self.display_window_size + margin + 1,
            )

        # If cursor is near the bottom edge of window, scroll down
        elif (
            self.current_cursor
            >= self.display_window_start + self.display_window_size - margin
        ):
            self.display_window_start = min(
                len(self.transactions) - self.display_window_size,
                self.display_window_start + 1,
            )

        # If cursor is near the top edge of window, scroll up
        elif self.current_cursor <= self.display_window_start + margin:
            self.display_window_start = max(0, self.display_window_start - 1)

        # Ensure window start is within bounds
        self.display_window_start = max(
            0, min(self.display_window_start, len(self.transactions) - 1)
        )

    def create_display(self) -> RichLayout:
        """Create the Rich layout for display."""
        layout = RichLayout()
        layout.split_column(
            RichLayout(name="header", size=3),
            RichLayout(name="summary", size=3),
            RichLayout(name="main"),
            RichLayout(name="suggestions", size=5),
            RichLayout(name="footer", size=3),
        )

        # Header - status bar
        header_text = self._create_header_text()
        layout["header"].update(Panel(header_text, style=f"bold {self.theme.primary}"))

        # Summary - financial statistics
        summary_panel = self._create_summary_panel()
        layout["summary"].update(summary_panel)

        # Main - transaction table
        main_table = self._create_transaction_table()
        layout["main"].update(main_table)

        # Suggestions panel - show current transaction's tag suggestions
        suggestions_panel = self._create_suggestions_panel()
        layout["suggestions"].update(suggestions_panel)

        # Footer - help text, search input, bulk tag input, or manual tag input
        if self.manual_tag_mode:
            footer_text = self._create_manual_tag_input()
        elif self.bulk_tag_mode:
            footer_text = self._create_bulk_tag_input()
        elif self.search_mode:
            footer_text = self._create_search_input()
        else:
            footer_text = self._create_footer_text()
        layout["footer"].update(Panel(footer_text, style=self.theme.muted))

        return layout

    def _create_header_text(self) -> Text:
        """Create header status text."""
        filter_text = "Untagged Only" if self.untagged_only else "All Transactions"
        if self.search_query:
            filter_text += f" | Search: '{self.search_query}'"

        total_count = len(self.transactions)
        tagged_count = sum(1 for tx in self.transactions if tx.tags)

        # Calculate visible range based on display window
        if self.transactions:
            start = self.display_window_start + 1
            end = min(self.display_window_start + self.display_window_size, total_count)
        else:
            start = 0
            end = 0

        text = Text()
        text.append(f"{filter_text} | ", style=self.theme.info)
        text.append(
            f"Viewing {start}-{end} of {total_count} | ", style=self.theme.neutral
        )
        text.append(f"Tagged: {tagged_count}", style=self.theme.success)

        return text

    def _create_summary_panel(self) -> Panel:
        """Create summary panel with financial statistics for all loaded transactions."""
        if not self.transactions:
            text = Text("No transactions to summarize", style=self.theme.muted)
            return Panel(text, title="Summary", style=self.theme.info)

        # Calculate statistics from all loaded transactions
        amounts = [float(tx.amount) for tx in self.transactions]
        dates = [tx.transaction_date for tx in self.transactions]

        # Income vs Expenses
        income_amounts = [amt for amt in amounts if amt > 0]
        expense_amounts = [amt for amt in amounts if amt < 0]

        income_total = sum(income_amounts) if income_amounts else 0
        expense_total = sum(expense_amounts) if expense_amounts else 0
        net_total = income_total + expense_total

        income_count = len(income_amounts)
        expense_count = len(expense_amounts)

        # Average
        avg_amount = sum(amounts) / len(amounts) if amounts else 0

        # Date range
        min_date = min(dates)
        max_date = max(dates)

        # Build summary text - all on one line
        text = Text()

        # Income vs Expenses
        text.append("Income: ", style=self.theme.muted)
        text.append(f"${income_total:,.2f}", style=self.theme.positive_amount)
        text.append(f" ({income_count})", style=self.theme.muted)
        text.append(" | ", style=self.theme.muted)
        text.append("Expenses: ", style=self.theme.muted)
        text.append(f"-${abs(expense_total):,.2f}", style=self.theme.negative_amount)
        text.append(f" ({expense_count})", style=self.theme.muted)
        text.append(" | ", style=self.theme.muted)
        text.append("Net: ", style=self.theme.muted)
        if net_total >= 0:
            text.append(f"${net_total:,.2f}", style=self.theme.positive_amount)
        else:
            text.append(f"-${abs(net_total):,.2f}", style=self.theme.negative_amount)
        text.append(" | ", style=self.theme.muted)
        text.append("Avg: ", style=self.theme.muted)
        if avg_amount >= 0:
            text.append(f"${avg_amount:,.2f}", style=self.theme.neutral)
        else:
            text.append(f"-${abs(avg_amount):,.2f}", style=self.theme.neutral)
        text.append(" | ", style=self.theme.muted)
        text.append(
            f"{min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')}",
            style=self.theme.info,
        )

        return Panel(text, title="Summary", style=self.theme.info)

    def _create_transaction_table(self) -> Table:
        """Create the main transaction table."""
        table = Table(
            show_header=True,
            header_style=f"bold {self.theme.primary}",
            box=None,
            padding=(0, 1),
        )

        table.add_column("", width=2)  # Cursor indicator
        table.add_column("Date", width=12)
        table.add_column("Account", width=18)
        table.add_column("Description", width=40)
        table.add_column("Amount", width=15, justify="right")
        table.add_column("Tags", width=25)

        # Calculate window bounds
        window_end = min(
            self.display_window_start + self.display_window_size, len(self.transactions)
        )
        visible_transactions = self.transactions[self.display_window_start : window_end]

        # Display only transactions within the visible window
        for i, tx in enumerate(visible_transactions):
            # Calculate the actual index in the full transaction list
            actual_index = self.display_window_start + i

            # Cursor indicator
            cursor = "→" if actual_index == self.current_cursor else ""

            # Date
            date_str = tx.transaction_date.strftime("%Y-%m-%d")

            # Account
            account_name = self.account_map.get(tx.account_id, "Unknown")[:16]

            # Description
            desc = (tx.description or "")[:38]

            # Amount with color
            if tx.amount < 0:
                amount_str = f"-${abs(tx.amount):,.2f}"
                amount_style = self.theme.negative_amount
            else:
                amount_str = f"${tx.amount:,.2f}"
                amount_style = self.theme.positive_amount

            # Tags with badge styling
            if tx.tags:
                tags_display = ", ".join(tx.tags[:3])
                if len(tx.tags) > 3:
                    tags_display += f" +{len(tx.tags) - 3}"
                tags_style = self.theme.info
            else:
                tags_display = "(none)"
                tags_style = self.theme.muted

            # Highlight current row
            row_style = (
                self.theme.highlight if actual_index == self.current_cursor else None
            )

            table.add_row(
                cursor,
                date_str,
                account_name,
                desc,
                f"[{amount_style}]{amount_str}[/{amount_style}]",
                f"[{tags_style}]{tags_display}[/{tags_style}]",
                style=row_style,
            )

        return table

    def _create_suggestions_panel(self) -> Panel:
        """Create the tag suggestions panel."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            return Panel(
                Text("No transaction selected", style=self.theme.muted),
                title="Quick Tags",
                style=self.theme.muted,
            )

        transaction = self.transactions[self.current_cursor]

        # Build suggestions display
        text = Text()

        # Current tags
        if transaction.tags:
            text.append("Current: ", style=self.theme.muted)
            text.append(", ".join(transaction.tags[:5]), style=self.theme.info)
            if len(transaction.tags) > 5:
                text.append(f" +{len(transaction.tags) - 5}", style=self.theme.muted)
            text.append("\n")

        # Suggestions with key numbers (show all 5)
        if self.current_suggestions:
            text.append("Press key to tag: ", style=self.theme.muted)
            text.append("\n")
            for i, tag in enumerate(self.current_suggestions, 1):
                text.append(f"  [{i}] ", style=f"bold {self.theme.primary}")
                text.append(f"{tag}    ", style=self.theme.success)
        else:
            text.append("No suggestions available", style=self.theme.muted)

        return Panel(text, title="Quick Tags", style=self.theme.primary)

    def _create_search_input(self) -> Text:
        """Create search input display."""
        text = Text()
        text.append("🔍 Search: ", style=f"bold {self.theme.primary}")
        text.append(self.search_input_buffer, style=self.theme.neutral)
        text.append("█", style=self.theme.primary)  # Cursor
        text.append("  (Enter to apply, Ctrl+X to cancel)", style=self.theme.muted)
        return text

    def _create_bulk_tag_input(self) -> Text:
        """Create bulk tag input display."""
        text = Text()

        if self.bulk_tag_confirm_mode:
            # Confirmation mode
            tags = [
                tag.strip()
                for tag in self.bulk_tag_input_buffer.split(",")
                if tag.strip()
            ]
            text.append("⚠ Apply ", style=f"bold {self.theme.warning}")
            text.append(f"{', '.join(tags)}", style=self.theme.info)
            text.append(
                f" to {len(self.transactions)} transaction(s)? ",
                style=f"bold {self.theme.warning}",
            )
            text.append("(Enter=Yes, Ctrl+X=Cancel)", style=self.theme.muted)
        else:
            # Input mode
            text.append(
                f"🏷️  Bulk Tag ({len(self.transactions)} txns): ",
                style=f"bold {self.theme.primary}",
            )
            text.append(self.bulk_tag_input_buffer, style=self.theme.neutral)

            # Show autocomplete suggestion in gray
            autocomplete = self.get_bulk_tag_autocomplete()
            if autocomplete:
                text.append(autocomplete, style=self.theme.muted)

            text.append("█", style=self.theme.primary)  # Cursor
            text.append(
                "  (Tab to autocomplete, Enter to confirm, Ctrl+X to cancel)",
                style=self.theme.muted,
            )

        return text

    def _create_manual_tag_input(self) -> Text:
        """Create manual tag input display."""
        text = Text()
        text.append("🏷️  Tag: ", style=f"bold {self.theme.primary}")
        text.append(self.manual_tag_input_buffer, style=self.theme.neutral)

        # Show autocomplete suggestion in gray
        autocomplete = self.get_manual_tag_autocomplete()
        if autocomplete:
            text.append(autocomplete, style=self.theme.muted)

        text.append("█", style=self.theme.primary)  # Cursor
        text.append(
            "  (Tab to autocomplete, Enter to apply, Ctrl+X to cancel)",
            style=self.theme.muted,
        )
        return text

    def _create_footer_text(self) -> Text:
        """Create footer help text."""
        text = Text()
        text.append("↑/↓: Navigate | ", style=self.theme.muted)
        text.append("Enter: Tag | ", style=self.theme.muted)
        text.append("1-5: Quick Tag | ", style=self.theme.muted)
        text.append("C: Clear | ", style=self.theme.muted)
        text.append("S: Search | ", style=self.theme.muted)
        text.append("A: Bulk Tag | ", style=self.theme.muted)
        text.append("U: Toggle Filter | ", style=self.theme.muted)
        text.append("R: Reset Filters | ", style=self.theme.muted)
        text.append("[/]: Page | ", style=self.theme.muted)
        text.append("Q: Quit", style=self.theme.muted)
        return text

    async def handle_quick_tag(self, index: int) -> None:
        """Apply a suggested tag by index."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            return

        if index >= len(self.current_suggestions):
            return

        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        transaction = self.transactions[self.current_cursor]
        tag = self.current_suggestions[index]
        current_tags = list(transaction.tags) if transaction.tags else []

        # Add tag if not already present
        if tag not in current_tags:
            current_tags.append(tag)
            result = await tagging_service.update_transaction_tags(
                transaction.id, current_tags
            )
            if result.success:
                self.transactions[self.current_cursor] = result.data
                # Move to next transaction
                if self.current_cursor < len(self.transactions) - 1:
                    self.current_cursor += 1
                    await self.load_suggestions()

    async def handle_search(self) -> None:
        """Enter search mode for live filtering."""
        self.search_mode = True
        self.search_input_buffer = self.search_query  # Start with current search

    async def apply_search_live(self) -> None:
        """Apply the search filter in real-time on every keystroke."""
        # Update search query and execute immediately
        self.search_query = self.search_input_buffer.strip()
        await self.load_transactions()
        # Skip loading suggestions during search typing - only load when navigating
        # This reduces DB calls and makes typing feel more responsive

    async def exit_search(self) -> None:
        """Exit search mode."""
        self.search_mode = False

    async def handle_bulk_tag_start(self) -> None:
        """Enter bulk tag mode for live input."""
        self.bulk_tag_mode = True
        self.bulk_tag_confirm_mode = False
        self.bulk_tag_input_buffer = ""

    async def exit_bulk_tag(self) -> None:
        """Exit bulk tag mode."""
        self.bulk_tag_mode = False
        self.bulk_tag_confirm_mode = False
        self.bulk_tag_input_buffer = ""

    def get_bulk_tag_autocomplete(self) -> str:
        """Get autocomplete suggestion for current partial tag.

        Returns the remainder of the suggested tag, or empty string if no match.
        """
        if not self.bulk_tag_input_buffer or not self.all_tags:
            return ""

        # Get the current partial tag (after last comma)
        if "," in self.bulk_tag_input_buffer:
            partial = self.bulk_tag_input_buffer.rsplit(",", 1)[-1].strip()
        else:
            partial = self.bulk_tag_input_buffer.strip()

        if not partial:
            return ""

        # Find first matching tag (case-insensitive)
        partial_lower = partial.lower()
        for tag in self.all_tags:
            if tag.lower().startswith(partial_lower) and tag.lower() != partial_lower:
                # Return only the remainder of the tag
                return tag[len(partial) :]

        return ""

    async def handle_manual_tag_start(self) -> None:
        """Enter manual tag mode for live input."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            return

        self.manual_tag_mode = True
        # Pre-populate with current tags
        transaction = self.transactions[self.current_cursor]
        if transaction.tags:
            self.manual_tag_input_buffer = ", ".join(transaction.tags)
        else:
            self.manual_tag_input_buffer = ""

    async def exit_manual_tag(self) -> None:
        """Exit manual tag mode."""
        self.manual_tag_mode = False
        self.manual_tag_input_buffer = ""

    def get_manual_tag_autocomplete(self) -> str:
        """Get autocomplete suggestion for current partial tag.

        Returns the remainder of the suggested tag, or empty string if no match.
        """
        if not self.manual_tag_input_buffer or not self.all_tags:
            return ""

        # Get the current partial tag (after last comma)
        if "," in self.manual_tag_input_buffer:
            partial = self.manual_tag_input_buffer.rsplit(",", 1)[-1].strip()
        else:
            partial = self.manual_tag_input_buffer.strip()

        if not partial:
            return ""

        # Find first matching tag (case-insensitive)
        partial_lower = partial.lower()
        for tag in self.all_tags:
            if tag.lower().startswith(partial_lower) and tag.lower() != partial_lower:
                # Return only the remainder of the tag
                return tag[len(partial) :]

        return ""

    async def apply_manual_tags(self) -> None:
        """Apply the manually entered tags to the current transaction."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            await self.exit_manual_tag()
            return

        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        transaction = self.transactions[self.current_cursor]

        # Parse tags
        if self.manual_tag_input_buffer.strip():
            tags = [
                tag.strip()
                for tag in self.manual_tag_input_buffer.split(",")
                if tag.strip()
            ]
        else:
            tags = []

        # Save tags
        result = await tagging_service.update_transaction_tags(transaction.id, tags)
        if result.success:
            self.transactions[self.current_cursor] = result.data
            # Move to next transaction
            if self.current_cursor < len(self.transactions) - 1:
                self.current_cursor += 1
                self.adjust_display_window()
                await self.load_suggestions()

        # Exit manual tag mode
        await self.exit_manual_tag()

    async def apply_bulk_tags_inline(self) -> None:
        """Apply the bulk tags to all filtered transactions."""
        if not self.transactions or not self.bulk_tag_input_buffer.strip():
            await self.exit_bulk_tag()
            return

        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        # Parse tags
        new_tags = [
            tag.strip() for tag in self.bulk_tag_input_buffer.split(",") if tag.strip()
        ]

        # Apply tags to all filtered transactions
        for i, transaction in enumerate(self.transactions):
            # Merge with existing tags (deduplicate)
            current_tags = list(transaction.tags) if transaction.tags else []
            merged_tags = current_tags.copy()

            for tag in new_tags:
                if tag not in merged_tags:
                    merged_tags.append(tag)

            # Only update if tags changed
            if merged_tags != current_tags:
                result = await tagging_service.update_transaction_tags(
                    transaction.id, merged_tags
                )
                if result.success:
                    self.transactions[i] = result.data

        # Exit bulk tag mode and reload
        await self.exit_bulk_tag()
        await self.load_suggestions()

    async def handle_clear_tags(self) -> None:
        """Clear tags from the current transaction."""
        if not self.transactions or self.current_cursor >= len(self.transactions):
            return

        from treeline.cli import get_container

        container = get_container()
        tagging_service = container.tagging_service()

        transaction = self.transactions[self.current_cursor]

        if transaction.tags:
            result = await tagging_service.update_transaction_tags(transaction.id, [])
            if result.success:
                self.transactions[self.current_cursor] = result.data
                # Move to next transaction
                if self.current_cursor < len(self.transactions) - 1:
                    self.current_cursor += 1
                    await self.load_suggestions()

    async def handle_toggle_filter(self) -> None:
        """Toggle between all and untagged transactions."""
        self.untagged_only = not self.untagged_only
        await self.load_transactions()
        await self.load_suggestions()

    async def handle_next_page(self) -> None:
        """Jump display window forward by 20 transactions."""
        max_start = max(0, len(self.transactions) - self.display_window_size)
        new_start = min(self.display_window_start + self.display_window_size, max_start)

        if new_start != self.display_window_start:
            self.display_window_start = new_start
            # Move cursor to the first transaction in the new window
            self.current_cursor = self.display_window_start
            await self.load_suggestions()

    async def handle_prev_page(self) -> None:
        """Jump display window backward by 20 transactions."""
        new_start = max(0, self.display_window_start - self.display_window_size)

        if new_start != self.display_window_start:
            self.display_window_start = new_start
            # Move cursor to the first transaction in the new window
            self.current_cursor = self.display_window_start
            await self.load_suggestions()

    async def handle_reset_filters(self) -> None:
        """Reset all filters to initial state."""
        # Clear search
        self.search_query = ""
        self.search_input_buffer = ""
        # Reset to initial untagged_only state
        self.untagged_only = self.initial_untagged_only
        # Reload
        await self.load_transactions()
        await self.load_suggestions()

    async def run(self) -> None:
        """Run the interactive tagging interface."""
        # Load initial data
        await self.load_accounts()
        await self.load_transactions()
        await self.load_suggestions()
        await self.load_all_tags()

        # Create the Live display
        with Live(
            self.create_display(),
            console=self.console,
            refresh_per_second=20,  # Increased from 4 for snappier typing
            screen=True,
        ) as live:
            while self.running:
                # Update display
                live.update(self.create_display())

                # Wait for a key press (non-blocking with timeout)
                try:
                    # Use readchar to get a single character
                    key = await asyncio.get_event_loop().run_in_executor(
                        None, readchar.readkey
                    )

                    # Handle key press
                    needs_update = await self.handle_key(key, live)

                    # Update display if needed
                    if needs_update:
                        live.update(self.create_display())

                except KeyboardInterrupt:
                    # Ctrl+C always exits the application
                    self.running = False
                    break

    async def handle_key(self, key: str, live: Live) -> bool:
        """Handle a key press and return True if display needs update.

        Args:
            key: The key that was pressed
            live: The Live display object

        Returns:
            True if the display needs to be updated
        """
        # Handle Ctrl+X (character code '\x18') for cancellation
        if key == "\x18":
            if self.manual_tag_mode:
                # Exit manual tag mode
                await self.exit_manual_tag()
                return True
            elif self.bulk_tag_mode:
                # Exit bulk tag mode
                await self.exit_bulk_tag()
                return True
            elif self.search_mode:
                # Exit search mode
                await self.exit_search()
                await self.load_suggestions()
                return True
            # In normal mode, Ctrl+X does nothing (Ctrl+C exits the app)
            return False

        # If in search mode, handle search input
        if self.search_mode:
            # Arrow keys exit search mode and do navigation
            if key == readchar.key.UP:
                await self.exit_search()
                if self.current_cursor > 0:
                    self.current_cursor -= 1
                    self.adjust_display_window()
                    await self.load_suggestions()
                return True
            elif key == readchar.key.DOWN:
                await self.exit_search()
                if self.current_cursor < len(self.transactions) - 1:
                    self.current_cursor += 1
                    self.adjust_display_window()
                    await self.load_suggestions()
                return True
            # Enter exits search mode, keeping the filter
            elif key == readchar.key.ENTER:
                await self.exit_search()
                # Load suggestions now that we're exiting search mode
                await self.load_suggestions()
                return True
            # Backspace removes last character
            elif key == readchar.key.BACKSPACE:
                if self.search_input_buffer:
                    self.search_input_buffer = self.search_input_buffer[:-1]
                    # Apply filter immediately
                    await self.apply_search_live()
                return True
            # Regular typing adds to search
            elif len(key) == 1 and key.isprintable():
                self.search_input_buffer += key
                # Apply filter immediately
                await self.apply_search_live()
                return True
            return False

        # If in manual tag mode, handle manual tag input
        if self.manual_tag_mode:
            if key == readchar.key.ENTER:
                # Apply the tags
                await self.apply_manual_tags()
                return True
            elif key == readchar.key.TAB:
                # Autocomplete the current partial tag
                autocomplete = self.get_manual_tag_autocomplete()
                if autocomplete:
                    self.manual_tag_input_buffer += autocomplete
                return True
            elif key == readchar.key.BACKSPACE:
                if self.manual_tag_input_buffer:
                    self.manual_tag_input_buffer = self.manual_tag_input_buffer[:-1]
                return True
            elif len(key) == 1 and key.isprintable():
                self.manual_tag_input_buffer += key
                return True
            return False

        # If in bulk tag mode, handle bulk tag input
        if self.bulk_tag_mode:
            if self.bulk_tag_confirm_mode:
                # In confirmation mode
                if key == readchar.key.ENTER:
                    # Apply the tags
                    await self.apply_bulk_tags_inline()
                    return True
                return False
            else:
                # In input mode
                if key == readchar.key.ENTER:
                    # Move to confirmation mode if tags entered
                    if self.bulk_tag_input_buffer.strip():
                        self.bulk_tag_confirm_mode = True
                        return True
                    else:
                        # No tags, just exit
                        await self.exit_bulk_tag()
                        return True
                elif key == readchar.key.TAB:
                    # Autocomplete the current partial tag
                    autocomplete = self.get_bulk_tag_autocomplete()
                    if autocomplete:
                        self.bulk_tag_input_buffer += autocomplete
                    return True
                elif key == readchar.key.BACKSPACE:
                    if self.bulk_tag_input_buffer:
                        self.bulk_tag_input_buffer = self.bulk_tag_input_buffer[:-1]
                    return True
                elif len(key) == 1 and key.isprintable():
                    self.bulk_tag_input_buffer += key
                    return True
                return False

        # Normal mode key handling
        # Navigation
        if key == readchar.key.UP:
            if self.current_cursor > 0:
                self.current_cursor -= 1
                self.adjust_display_window()
                await self.load_suggestions()
                return True

        elif key == readchar.key.DOWN:
            if self.current_cursor < len(self.transactions) - 1:
                self.current_cursor += 1
                self.adjust_display_window()
                await self.load_suggestions()
                return True

        # Quick tagging
        elif key in ["1", "2", "3", "4", "5"]:
            index = int(key) - 1
            await self.handle_quick_tag(index)
            return True

        # Manual tag entry
        elif key == readchar.key.ENTER:
            await self.handle_manual_tag_start()
            return True

        # Clear tags
        elif key.lower() == "c":
            await self.handle_clear_tags()
            return True

        # Search - enter search mode instead of modal
        elif key.lower() == "s":
            await self.handle_search()
            return True

        # Bulk tag - enter bulk tag mode
        elif key.lower() == "a":
            if self.transactions:
                await self.handle_bulk_tag_start()
            return True

        # Toggle filter
        elif key.lower() == "u":
            await self.handle_toggle_filter()
            return True

        # Pagination
        elif key == "]":
            await self.handle_next_page()
            return True

        elif key == "[":
            await self.handle_prev_page()
            return True

        # Reset all filters
        elif key.lower() == "r":
            await self.handle_reset_filters()
            return True

        # Quit
        elif key.lower() == "q":
            self.running = False
            return False

        return False


def run_tagging_interface(untagged_only: bool = False) -> None:
    """Entry point for the tagging interface."""
    interface = TaggingInterface(untagged_only=untagged_only)
    asyncio.run(interface.run())
