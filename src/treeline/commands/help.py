"""Help command handler."""

from rich.console import Console
from rich.table import Table
from treeline.theme import get_theme

console = Console()
theme = get_theme()


def handle_help_command() -> None:
    """Display help information about available commands."""
    table = Table(title="Available Slash Commands", show_header=True)
    table.add_column("Command", style=theme.info, no_wrap=True)
    table.add_column("Description", style=theme.neutral)

    table.add_row("/help", "Show all available commands")
    table.add_row("/login", "Login or create your Treeline account")
    table.add_row("/status", "Shows summary of current state of your financial data")
    table.add_row("/query <SQL>", "Execute a SQL query directly")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")
    table.add_row("/clear", "Clear conversation history and start fresh")

    console.print(table)
    console.print(f"\n[{theme.muted}]You can also ask questions about your financial data in natural language[/{theme.muted}]\n")
