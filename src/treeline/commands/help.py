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
    table.add_row("/query <SQL>", "Execute a single-line SQL query")
    table.add_row("/query:name", "Run a saved query")
    table.add_row("/sql", "Open multi-line SQL editor")
    table.add_row("/analysis", "Integrated workspace for data exploration")
    table.add_row("/schema [table]", "Browse database schema and tables")
    table.add_row("/queries [list|show|delete]", "Manage saved queries")
    table.add_row("/chart [name]", "Run saved chart or list all charts")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")
    table.add_row("/clear", "Clear conversation history and start fresh")
    table.add_row("/exit", "Exit the Treeline REPL")

    console.print(table)

    # Add analysis mode details
    console.print(f"\n[bold {theme.info}]Analysis Mode Shortcuts[/bold {theme.info}]")
    console.print(f"[{theme.muted}]When in /analysis mode, use these keyboard shortcuts:[/{theme.muted}]\n")

    shortcuts_table = Table(show_header=False, box=None, padding=(0, 2))
    shortcuts_table.add_column("Key", style=theme.info)
    shortcuts_table.add_column("Action", style=theme.neutral)

    shortcuts_table.add_row("Ctrl+Enter", "Execute SQL query")
    shortcuts_table.add_row("Tab", "Switch focus (SQL ↔ Data panel)")
    shortcuts_table.add_row("↑↓←→", "Context-aware (edit SQL or scroll results)")
    shortcuts_table.add_row("Shift+←→", "Scroll columns horizontally")
    shortcuts_table.add_row("v", "Toggle between results and chart view")
    shortcuts_table.add_row("g", "Create/edit chart (wizard)")
    shortcuts_table.add_row("s", "Save query or chart")
    shortcuts_table.add_row("l", "Load saved query or chart")
    shortcuts_table.add_row("r", "Reset (clear results/chart)")
    shortcuts_table.add_row("?", "Show help overlay")
    shortcuts_table.add_row("Ctrl+C", "Exit analysis mode")

    console.print(shortcuts_table)
    console.print(f"\n[{theme.muted}]You can also ask questions about your financial data in natural language[/{theme.muted}]\n")
