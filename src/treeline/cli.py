"""Treeline CLI - Interactive financial data management."""

import sys
from pathlib import Path

from dotenv import load_dotenv
import typer

# Load environment variables from .env file
load_dotenv()
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()


def get_treeline_dir() -> Path:
    """Get the treeline data directory in the current working directory."""
    return Path.cwd() / "treeline"


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    import keyring

    try:
        user_id = keyring.get_password("treeline", "user_id")
        return user_id is not None
    except Exception:
        return False


def get_current_user_id() -> str | None:
    """Get the current authenticated user ID."""
    import keyring

    try:
        return keyring.get_password("treeline", "user_id")
    except Exception:
        return None


def get_current_user_email() -> str | None:
    """Get the current authenticated user email."""
    import keyring

    try:
        return keyring.get_password("treeline", "user_email")
    except Exception:
        return None


def ensure_treeline_initialized() -> bool:
    """Ensure treeline directory and database exist. Returns True if initialization was needed."""
    treeline_dir = get_treeline_dir()
    db_path = treeline_dir / "treeline.db"

    needs_init = not (treeline_dir.exists() and db_path.exists())

    # Create directory if it doesn't exist
    treeline_dir.mkdir(exist_ok=True)

    # Initialize database with schema
    # Note: We don't need user_id for schema initialization
    # The repository will create the tables when we first connect
    from treeline.infra.duckdb import DuckDBRepository

    repository = DuckDBRepository(str(db_path))

    # Ensure schema is created - using a dummy UUID since schema is user-independent
    import asyncio
    from uuid import UUID

    dummy_user_id = UUID("00000000-0000-0000-0000-000000000000")
    result = asyncio.run(repository.ensure_db_exists(dummy_user_id))

    if not result.success:
        console.print(f"[red]Error initializing database: {result.error}[/red]")
        sys.exit(1)

    result = asyncio.run(repository.ensure_schema_upgraded(dummy_user_id))

    if not result.success:
        console.print(f"[red]Error initializing schema: {result.error}[/red]")
        sys.exit(1)

    return needs_init


def show_welcome_message(first_time: bool = False) -> None:
    """Display welcome message."""
    console.print("\n[bold green]🌲 Welcome to Treeline![/bold green]\n")

    if first_time:
        console.print("[dim]Initialized treeline directory in current folder[/dim]\n")

    # Show authentication status
    if is_authenticated():
        email = get_current_user_email()
        console.print(f"[dim]Logged in as {email}[/dim]\n")
    else:
        console.print("[yellow]⚠ Not authenticated. Please use [bold]/login[/bold] to sign in.[/yellow]\n")

    console.print("Type [bold]/help[/bold] to see available commands")
    console.print("Type [bold]exit[/bold] or press [bold]Ctrl+C[/bold] to quit\n")


def handle_help_command() -> None:
    """Display help information about available commands."""
    table = Table(title="Available Slash Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    table.add_row("/help", "Show all available commands")
    table.add_row("/login", "Login or create your Treeline account")
    table.add_row("/status", "Shows summary of current state of your financial data")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")

    console.print(table)
    console.print("\n[dim]You can also ask questions about your financial data in natural language[/dim]\n")


def handle_login_command() -> None:
    """Handle /login command."""
    import asyncio
    from rich.prompt import Prompt, Confirm

    console.print("\n[bold cyan]Login to Treeline[/bold cyan]\n")

    # Ask if user wants to sign in or create account
    create_account = Confirm.ask("Create a new account?", default=False)

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    # Initialize Supabase auth provider
    import os
    from treeline.infra.supabase import SupabaseAuthProvider
    from supabase import create_client

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        console.print("\n[red]Error: SUPABASE_URL and SUPABASE_KEY environment variables must be set[/red]")
        console.print("[dim]Please set these in your environment or .env file[/dim]\n")
        return

    supabase_client = create_client(supabase_url, supabase_key)
    auth_provider = SupabaseAuthProvider(supabase_client)

    # Sign in or sign up
    console.print()
    with console.status("[bold green]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_provider.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_provider.sign_in_with_password(email, password))

    if not result.success:
        console.print(f"[red]Authentication failed: {result.error}[/red]\n")
        return

    user = result.data
    console.print(f"[green]✓[/green] Successfully authenticated as [bold]{user.email}[/bold]\n")

    # Store credentials in keyring
    import keyring

    keyring.set_password("treeline", "supabase_access_token", "TODO_access_token")
    keyring.set_password("treeline", "user_id", str(user.id))
    keyring.set_password("treeline", "user_email", user.email)

    console.print("[dim]Credentials saved to system keyring[/dim]\n")


def handle_status_command() -> None:
    """Handle /status command."""
    console.print("[yellow]Status functionality coming soon...[/yellow]")
    # TODO: Implement status


def handle_simplefin_command() -> None:
    """Handle /simplefin command."""
    console.print("[yellow]SimpleFIN setup coming soon...[/yellow]")
    # TODO: Implement simplefin


def handle_sync_command() -> None:
    """Handle /sync command."""
    console.print("[yellow]Sync functionality coming soon...[/yellow]")
    # TODO: Implement sync


def handle_import_command() -> None:
    """Handle /import command."""
    console.print("[yellow]CSV import coming soon...[/yellow]")
    # TODO: Implement import


def handle_tag_command() -> None:
    """Handle /tag command."""
    console.print("[yellow]Tagging power mode coming soon...[/yellow]")
    # TODO: Implement tag


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
        command = user_input.lower().split()[0]

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
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help to see available commands[/dim]")
    else:
        # Natural language query - TODO: implement AI integration
        console.print("[yellow]AI integration coming soon...[/yellow]")

    return True


def run_interactive_mode() -> None:
    """Run the interactive REPL mode."""
    # Initialize treeline directory and database
    first_time = ensure_treeline_initialized()

    # Show welcome message
    show_welcome_message(first_time)

    # TODO: Check authentication status and prompt for /login if needed

    # Main REPL loop
    try:
        while True:
            try:
                user_input = Prompt.ask("[bold cyan]>[/bold cyan]")
                should_continue = process_command(user_input)
                if not should_continue:
                    break
            except KeyboardInterrupt:
                console.print("\n[dim]Goodbye! =K[/dim]")
                break
            except EOFError:
                console.print("\n[dim]Goodbye! =K[/dim]")
                break
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        sys.exit(1)


@app.command()
def main() -> None:
    """Start Treeline interactive mode."""
    run_interactive_mode()


if __name__ == "__main__":
    app()
