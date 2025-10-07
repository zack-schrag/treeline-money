"""Treeline CLI - Interactive financial data management."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
import traceback
import typer
from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from treeline.app.container import Container
from treeline.commands.chat import handle_chat_message
from treeline.commands.help import handle_help_command
from treeline.commands.import_csv import handle_import_command
from treeline.commands.login import handle_login_command
from treeline.commands.query import handle_clear_command, handle_query_command
from treeline.commands.simplefin import handle_simplefin_command
from treeline.commands.status import handle_status_command
from treeline.commands.sync import handle_sync_command
from treeline.commands.tag import handle_tag_command
from treeline.theme import get_theme

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()
theme = get_theme()

# Global container instance
_container: Container | None = None

# Available slash commands
SLASH_COMMANDS = [
    "/help",
    "/login",
    "/status",
    "/simplefin",
    "/sync",
    "/import",
    "/tag",
    "/query",
    "/clear",
]


def get_slash_command_completions(text: str) -> list[str]:
    """Get slash command completions for the given text.

    Args:
        text: The current input text

    Returns:
        List of matching slash commands
    """
    if not text.startswith("/"):
        return []

    # Return all commands if just "/" is typed
    if text == "/":
        return SLASH_COMMANDS

    # Return commands that start with the typed text
    return [cmd for cmd in SLASH_COMMANDS if cmd.startswith(text.lower())]


def get_file_path_completions(text: str) -> list[str]:
    """Get file path completions for the given text.

    Args:
        text: The current partial path

    Returns:
        List of matching file/directory paths
    """
    import os
    import glob

    # Expand ~ to home directory
    expanded_text = os.path.expanduser(text)

    # If the text is empty or just ~, return home directory contents
    if not text or text == "~" or text == "~/":
        base_path = os.path.expanduser("~/")
        try:
            items = os.listdir(base_path)
            return [os.path.join("~", item) for item in sorted(items)]
        except (OSError, PermissionError):
            return []

    # Handle partial paths
    try:
        # Get the directory and partial filename
        if os.path.isdir(expanded_text):
            # If it's a directory, list its contents
            base_dir = expanded_text
            pattern = "*"
        else:
            # It's a partial path
            base_dir = os.path.dirname(expanded_text) or "."
            pattern = os.path.basename(expanded_text) + "*"

        # Get matching paths
        search_pattern = os.path.join(base_dir, pattern)
        matches = glob.glob(search_pattern)

        # Convert back to original format (preserve ~ if used)
        if text.startswith("~/"):
            home = os.path.expanduser("~")
            matches = [m.replace(home, "~", 1) if m.startswith(home) else m for m in matches]

        # Sort and return (directories first, then files)
        def sort_key(p):
            is_dir = os.path.isdir(os.path.expanduser(p))
            return (not is_dir, p.lower())

        return sorted(matches, key=sort_key)

    except (OSError, PermissionError):
        return []


class SlashCommandCompleter(Completer):
    """Completer for slash commands in the REPL."""

    def get_completions(self, document, _complete_event):
        """Generate completions for the current document."""
        text = document.text_before_cursor

        # Only provide completions for slash commands
        if not text.startswith("/"):
            return

        # Get matching commands
        matches = get_slash_command_completions(text)

        # Yield each match as a completion
        for match in matches:
            yield Completion(
                match,
                start_position=-len(text),
                display=match,
            )


def prompt_for_file_path(prompt_text: str = "") -> str:
    """Prompt user for a file path with autocomplete.

    Args:
        prompt_text: The prompt text to display (plain text, no Rich markup)

    Returns:
        The file path entered by the user
    """
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.filters import completion_is_selected

    # PathCompleter with expanduser=True handles ~ expansion
    # only_directories=False allows both files and directories
    completer = PathCompleter(expanduser=True, only_directories=False)

    # Create custom key bindings to handle Enter on directory selections
    kb = KeyBindings()

    @kb.add('enter', filter=completion_is_selected)
    def _(event):
        """When Enter is pressed on a selected completion, insert it and continue editing."""
        import os

        # Get the current completion
        completion = event.current_buffer.complete_state.current_completion
        if completion:
            # Insert the completion text
            event.current_buffer.apply_completion(completion)

            # If it's a directory and doesn't end with /, add one
            current_text = event.current_buffer.text
            expanded_path = os.path.expanduser(current_text)
            if os.path.isdir(expanded_path) and not current_text.endswith('/'):
                event.current_buffer.insert_text('/')
        # Don't accept the input - let user continue typing

    session = PromptSession(completer=completer, key_bindings=kb)

    if prompt_text:
        return session.prompt(f"{prompt_text}: ")
    else:
        return session.prompt(">: ")


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the current working directory."""
    return Path.cwd() / "treeline"


# Legacy helper functions for backward compatibility with tests
def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return get_container().config_service().is_authenticated()


def get_current_user_id() -> str | None:
    """Get the current authenticated user ID."""
    return get_container().config_service().get_current_user_id()


def get_current_user_email() -> str | None:
    """Get the current authenticated user email."""
    return get_container().config_service().get_current_user_email()


def get_container() -> Container:
    """Get or create the dependency injection container."""
    global _container
    if _container is None:
        treeline_dir = get_treeline_dir()
        db_path = treeline_dir / "treeline.db"
        _container = Container(str(db_path))
    return _container


def ensure_treeline_initialized() -> bool:
    """Ensure treeline directory and database exist. Returns True if initialization was needed."""
    treeline_dir = get_treeline_dir()
    needs_init = not treeline_dir.exists()

    # Create directory if it doesn't exist
    treeline_dir.mkdir(exist_ok=True)

    # Initialize database using DbService
    container = get_container()
    db_service = container.db_service()

    result = asyncio.run(db_service.initialize_db())
    if not result.success:
        console.print(f"[{theme.error}]Error initializing database: {result.error}[/{theme.error}]")
        sys.exit(1)

    return needs_init


def show_welcome_message(first_time: bool = False) -> None:
    """Display welcome message with ASCII art and useful information."""
    from rich.panel import Panel
    from rich.table import Table
    from pathlib import Path

    # Get container and services
    container = get_container()
    config_service = container.config_service()

    # Build info content
    info_parts = []

    # Title
    info_parts.append(f"[{theme.ui_header}]🌲 Treeline[/{theme.ui_header}]")
    info_parts.append("")

    # Authentication status
    if config_service.is_authenticated():
        email = config_service.get_current_user_email()
        info_parts.append(f"[{theme.success}]✓[/{theme.success}] Logged in as [{theme.emphasis}]{email}[/{theme.emphasis}]")

        # Try to get quick stats
        try:
            user_id_str = config_service.get_current_user_id()
            if user_id_str:
                from uuid import UUID
                user_id = UUID(user_id_str)
                status_service = container.status_service()
                result = asyncio.run(status_service.get_status(user_id))

                if result.success:
                    status = result.data
                    info_parts.append("")
                    info_parts.append(f"[{theme.info}]📊 Quick Stats[/{theme.info}]")
                    info_parts.append(f"  Accounts: [{theme.emphasis}]{len(status['accounts'])}[/{theme.emphasis}]")
                    info_parts.append(f"  Transactions: [{theme.emphasis}]{status['total_transactions']}[/{theme.emphasis}]")

                    if status['latest_date']:
                        info_parts.append(f"  Latest data: [{theme.emphasis}]{status['latest_date']}[/{theme.emphasis}]")
        except Exception:
            # If we can't get stats, just skip them
            pass
    else:
        info_parts.append(f"[{theme.warning}]⚠ Not authenticated[/{theme.warning}]")
        info_parts.append(f"Use [{theme.emphasis}]/login[/{theme.emphasis}] to sign in")

    if first_time:
        info_parts.append("")
        info_parts.append(f"[{theme.success}]✓[/{theme.success}] Initialized treeline directory")

    info_parts.append("")
    info_parts.append(f"[{theme.muted}]Type [{theme.emphasis}]/help[/{theme.emphasis}] for commands[/{theme.muted}]")
    info_parts.append(f"[{theme.muted}]Type [{theme.emphasis}]exit[/{theme.emphasis}] or [{theme.emphasis}]Ctrl+C[/{theme.emphasis}] to quit[/{theme.muted}]")

    # Get current directory name for display
    cwd = Path.cwd().name

    # Simple panel with just the info, fit to content
    panel = Panel(
        "\n".join(info_parts),
        border_style="green",
        padding=(1, 2),
        subtitle=f"[dim]{cwd}[/dim]",
        expand=False
    )

    console.print()
    console.print(panel)
    console.print()



def process_command(user_input: str) -> bool:
    """Process a user command. Returns True to continue REPL, False to exit."""
    user_input = user_input.strip()

    if not user_input:
        return True

    if user_input.lower() in ("exit", "quit"):
        console.print("[dim]Goodbye! =K[/dim]")
        return False

    # Handle slash commands
    if user_input.startswith("/"):
        command_parts = user_input.split(maxsplit=1)
        command = command_parts[0].lower()

        if command == "/help":
            handle_help_command()
        elif command == "/login":
            handle_login_command()
        elif command == "/status":
            handle_status_command()
        elif command == "/simplefin":
            handle_simplefin_command()
        elif command == "/sync":
            handle_sync_command()
        elif command == "/import":
            handle_import_command()
        elif command == "/tag":
            handle_tag_command()
        elif command == "/clear":
            handle_clear_command()
        elif command == "/query":
            # Extract SQL from command
            if len(command_parts) < 2:
                console.print(f"[{theme.error}]Error: /query requires a SQL statement[/{theme.error}]")
                console.print(f"[{theme.muted}]Usage: /query SELECT * FROM transactions LIMIT 5[/{theme.muted}]\n")
            else:
                sql = command_parts[1]
                handle_query_command(sql)
        else:
            console.print(f"[{theme.error}]Unknown command: {command}[/{theme.error}]")
            console.print(f"[{theme.muted}]Type /help to see available commands[/{theme.muted}]")
    else:
        # Natural language query - send to AI agent
        handle_chat_message(user_input)

    return True


def run_interactive_mode() -> None:
    """Run the interactive REPL mode."""
    # Initialize treeline directory and database
    first_time = ensure_treeline_initialized()

    # Show welcome message
    show_welcome_message(first_time)

    # Create prompt session with autocomplete
    session = PromptSession(completer=SlashCommandCompleter())

    # Main REPL loop
    try:
        while True:
            try:
                # Print separator line before prompt
                console.print(f"[{theme.separator}]" + "─" * console.width + f"[/{theme.separator}]")

                # Use prompt_toolkit for input with autocomplete
                user_input = session.prompt(">: ")

                # Print separator line after prompt with spacing
                console.print(f"[{theme.separator}]" + "─" * console.width + f"[/{theme.separator}]")
                console.print()  # Add blank line for cushion

                should_continue = process_command(user_input)
                if not should_continue:
                    break
            except KeyboardInterrupt:
                console.print(f"\n[{theme.muted}]Goodbye! =K[/{theme.muted}]")
                break
            except EOFError:
                console.print(f"\n[{theme.muted}]Goodbye! =K[/{theme.muted}]")
                break
    except Exception as e:
        console.print(f"[{theme.error}]Unexpected error:[/{theme.error}]")
        # Don't use markup since error messages may contain square brackets
        console.print(str(e), markup=False)
        console.print(traceback.format_exc(), markup=False)
        sys.exit(1)


@app.command(name="status")
def status_command() -> None:
    """Shows summary of current state of your financial data."""
    ensure_treeline_initialized()
    handle_status_command()


@app.command(name="query")
def query_command(sql: str = typer.Argument(..., help="SQL query to execute (SELECT/WITH only)")) -> None:
    """Execute a SQL query directly."""
    ensure_treeline_initialized()
    handle_query_command(sql)


@app.command(name="sync")
def sync_command() -> None:
    """Run an on-demand data synchronization."""
    ensure_treeline_initialized()
    handle_sync_command()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Treeline - AI-native personal finance in your terminal.

    Run without arguments to enter interactive mode, or use a specific command.
    """
    if ctx.invoked_subcommand is None:
        # No command specified - enter interactive mode
        run_interactive_mode()


if __name__ == "__main__":
    app()
