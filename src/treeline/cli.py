"""Treeline CLI - Interactive financial data management."""

import asyncio
import sys
from pathlib import Path
from uuid import UUID
import traceback
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from treeline.app.container import Container

# Load environment variables from .env file
load_dotenv()

app = typer.Typer(
    help="Treeline - AI-native personal finance in your terminal",
    add_completion=False,
    no_args_is_help=False,
)
console = Console()

# Global container instance
_container: Container | None = None


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
        console.print(f"[red]Error initializing database: {result.error}[/red]")
        sys.exit(1)

    return needs_init


def show_welcome_message(first_time: bool = False) -> None:
    """Display welcome message."""
    console.print("\n[bold green]🌲 Welcome to Treeline![/bold green]\n")

    if first_time:
        console.print("[dim]Initialized treeline directory in current folder[/dim]\n")

    # Show authentication status using ConfigService
    container = get_container()
    config_service = container.config_service()

    if config_service.is_authenticated():
        email = config_service.get_current_user_email()
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
    table.add_row("/query <SQL>", "Execute a SQL query directly")
    table.add_row("/simplefin", "Setup SimpleFIN connection")
    table.add_row("/sync", "Run an on-demand data synchronization")
    table.add_row("/import", "Import CSV file of transactions")
    table.add_row("/tag", "Enter tagging power mode")
    table.add_row("/clear", "Clear conversation history and start fresh")

    console.print(table)
    console.print("\n[dim]You can also ask questions about your financial data in natural language[/dim]\n")


def handle_login_command() -> None:
    """Handle /login command."""
    console.print("\n[bold cyan]Login to Treeline[/bold cyan]\n")

    container = get_container()
    config_service = container.config_service()

    try:
        auth_service = container.auth_service()
    except ValueError as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        console.print("[dim]Please set SUPABASE_URL and SUPABASE_KEY in your .env file[/dim]\n")
        return

    # Ask if user wants to sign in or create account
    create_account = Confirm.ask("Create a new account?", default=False)

    email = Prompt.ask("Email")
    password = Prompt.ask("Password", password=True)

    console.print()
    with console.status("[bold green]Authenticating..."):
        if create_account:
            result = asyncio.run(auth_service.sign_up_with_password(email, password))
        else:
            result = asyncio.run(auth_service.sign_in_with_password(email, password))

    if not result.success:
        console.print(f"[red]Authentication failed: {result.error}[/red]\n")
        return

    user = result.data
    console.print(f"[green]✓[/green] Successfully authenticated as [bold]{user.email}[/bold]\n")

    # Save credentials using config service
    config_service.save_user_credentials(str(user.id), user.email)
    console.print("[dim]Credentials saved to system keyring[/dim]\n")


def handle_status_command() -> None:
    """Handle /status command."""
    container = get_container()
    config_service = container.config_service()
    status_service = container.status_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]📊 Financial Data Status[/bold cyan]\n")

    with console.status("[bold green]Loading data..."):
        result = asyncio.run(status_service.get_status(user_id))

        if not result.success:
            console.print(f"[red]Error loading status: {result.error}[/red]\n")
            return

        status = result.data

    # Display summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold white")

    summary_table.add_row("Accounts", str(len(status["accounts"])))
    summary_table.add_row("Transactions", str(status["total_transactions"]))
    summary_table.add_row("Balance Snapshots", str(status["total_snapshots"]))
    summary_table.add_row("Integrations", str(len(status["integrations"])))

    console.print(summary_table)

    # Date range
    if status["earliest_date"] and status["latest_date"]:
        console.print(f"\n[dim]Date range: {status['earliest_date']} to {status['latest_date']}[/dim]")

    # Show integrations
    if status["integrations"]:
        console.print("\n[bold]Connected Integrations:[/bold]")
        for integration in status["integrations"]:
            console.print(f"  • {integration['integrationName']}")

    console.print()


def handle_simplefin_command() -> None:
    """Handle /simplefin command."""
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]SimpleFIN Setup[/bold cyan]\n")
    console.print(
        "[dim]If you don't have a SimpleFIN account, create one at: https://beta-bridge.simplefin.org/[/dim]\n"
    )

    # Prompt for setup token
    setup_token = Prompt.ask("Enter your SimpleFIN setup token")

    if not setup_token or not setup_token.strip():
        console.print("[yellow]Setup cancelled.[/yellow]\n")
        return

    setup_token = setup_token.strip()

    # Use integration service
    integration_service = container.integration_service("simplefin")

    console.print()
    with console.status("[bold green]Verifying token and setting up integration..."):
        # Ensure user database is initialized
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

        # Create integration
        result = asyncio.run(
            integration_service.create_integration(user_id, "simplefin", {"setupToken": setup_token})
        )

        if not result.success:
            console.print(f"[red]Setup failed: {result.error}[/red]\n")
            return

    console.print(f"[green]✓[/green] SimpleFIN integration setup successfully!\n")
    console.print("\n[dim]Use /sync to import your transactions[/dim]\n")


def handle_sync_command() -> None:
    """Handle /sync command."""
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()
    sync_service = container.sync_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    console.print("\n[bold cyan]Synchronizing Financial Data[/bold cyan]\n")

    # Ensure user database is initialized
    with console.status("[bold green]Initializing..."):
        db_init_result = asyncio.run(db_service.initialize_user_db(user_id))
        if not db_init_result.success:
            console.print(f"[red]Error initializing database: {db_init_result.error}[/red]\n")
            return

    # Sync all integrations using service
    with console.status("[bold green]Syncing integrations..."):
        result = asyncio.run(sync_service.sync_all_integrations(user_id))

    if not result.success:
        console.print(f"[yellow]{result.error}[/yellow]\n")
        if result.error == "No integrations configured":
            console.print("[dim]Use /simplefin to setup an integration first[/dim]\n")
        return

    # Display results
    for sync_result in result.data["results"]:
        integration_name = sync_result["integration"]
        console.print(f"[bold]Syncing {integration_name}...[/bold]")

        if "error" in sync_result:
            console.print(f"[red]  ✗ {sync_result['error']}[/red]")
            continue

        console.print(f"[green]  ✓[/green] Synced {sync_result['accounts_synced']} account(s)")

        if sync_result["sync_type"] == "incremental":
            console.print(
                f"[dim]  Syncing transactions since {sync_result['start_date'].date()} (with 7-day overlap)[/dim]"
            )
        else:
            console.print(f"[dim]  Initial sync: fetching last 90 days of transactions[/dim]")

        console.print(f"[green]  ✓[/green] Synced {sync_result['transactions_synced']} transaction(s)")
        console.print(f"[dim]  Balance snapshots created automatically from account data[/dim]")

    console.print(f"\n[green]✓[/green] Sync completed!\n")
    console.print("[dim]Use /status to see your updated data[/dim]\n")


def handle_import_command() -> None:
    """Handle /import command."""
    console.print("[yellow]CSV import coming soon...[/yellow]")


def handle_tag_command() -> None:
    """Handle /tag command."""
    console.print("[yellow]Tagging power mode coming soon...[/yellow]")


def handle_clear_command() -> None:
    """Handle /clear command - reset conversation session."""
    container = get_container()
    agent_service = container.agent_service()

    result = asyncio.run(agent_service.clear_session())

    if result.success:
        console.print("[green]✓[/green] Conversation cleared. Starting fresh!\n")
    else:
        console.print(f"[yellow]Note: {result.error}[/yellow]\n")


def handle_query_command(sql: str) -> None:
    """Handle /query command - execute SQL directly."""
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax

    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Validate SQL - only allow SELECT and WITH queries
    sql_stripped = sql.strip()
    sql_upper = sql_stripped.upper()

    if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
        console.print("[red]Error: Only SELECT and WITH queries are allowed.[/red]")
        console.print("[dim]For data modifications, use the AI agent.[/dim]\n")
        return

    # Display the SQL query
    console.print()
    syntax = Syntax(sql_stripped, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(
        syntax,
        title="[bold cyan]Executing Query[/bold cyan]",
        border_style="cyan",
        padding=(0, 1),
    ))

    # Execute query
    with console.status("[dim]Running query...[/dim]"):
        result = asyncio.run(db_service.execute_query(user_id, sql_stripped))

    if not result.success:
        console.print(f"\n[red]Error: {result.error}[/red]\n")
        return

    # Format and display results
    query_result = result.data
    rows = query_result.get("rows", [])
    columns = query_result.get("columns", [])

    console.print()

    if len(rows) == 0:
        console.print("[dim]No results returned.[/dim]\n")
        return

    # Create Rich table
    table = Table(show_header=True, header_style="bold cyan", border_style="dim")

    # Add columns
    for col in columns:
        table.add_column(col)

    # Add rows
    for row in rows:
        # Convert row values to strings
        str_row = [str(val) if val is not None else "[dim]NULL[/dim]" for val in row]
        table.add_row(*str_row)

    console.print(table)
    console.print(f"\n[dim]{len(rows)} row{'s' if len(rows) != 1 else ''} returned[/dim]\n")


def handle_chat_message(message: str) -> None:
    """Handle natural language chat message."""
    container = get_container()
    config_service = container.config_service()
    agent_service = container.agent_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print("[red]Error: Not authenticated. Please use /login first.[/red]\n")
        return

    user_id = UUID(user_id_str)

    # Get database path for this specific user
    treeline_dir = get_treeline_dir()
    db_path = str(treeline_dir / "treeline.db" / f"{user_id}.duckdb")

    # Send message to agent
    with console.status("[dim]Thinking...[/dim]"):
        result = asyncio.run(agent_service.chat(user_id, db_path, message))

    if not result.success:
        console.print(f"[red]Error: {result.error}[/red]\n")
        return

    # Stream the response
    response_data = result.data
    stream = response_data["stream"]

    console.print()  # Blank line before response

    try:
        # Consume the async stream
        async def consume_stream():
            from rich.panel import Panel
            from rich.syntax import Syntax

            current_content = []
            in_sql_block = False
            sql_content = []

            async for chunk in stream:
                # Check if this is a tool indicator (starts with special marker)
                if chunk.startswith("__TOOL_USE__:"):
                    tool_name = chunk.replace("__TOOL_USE__:", "").strip()

                    # Flush any pending content
                    if current_content:
                        console.print("".join(current_content), end="", markup=False)
                        current_content = []

                    # Display tool usage in a panel
                    console.print(Panel(
                        f"[cyan]Using tool:[/cyan] [bold]{tool_name}[/bold]",
                        border_style="dim",
                        padding=(0, 1),
                    ))

                elif chunk.startswith("Visualization:"):
                    # Flush any pending content
                    if current_content:
                        console.print("".join(current_content), end="", markup=False)
                        current_content = []

                    # Charts contain ANSI escape codes - use raw print
                    console.print()  # Blank line before chart
                    print(chunk, end="", flush=True)
                    console.print()  # Blank line after chart

                else:
                    # Check for SQL code blocks
                    if "```sql" in chunk:
                        in_sql_block = True
                        # Print content before SQL
                        before_sql = chunk.split("```sql")[0]
                        if before_sql:
                            current_content.append(before_sql)

                        # Flush content before SQL
                        if current_content:
                            console.print("".join(current_content), end="", markup=False)
                            current_content = []

                        # Start collecting SQL
                        sql_content = []
                        after_marker = chunk.split("```sql", 1)[1]
                        if after_marker:
                            sql_content.append(after_marker)

                    elif "```" in chunk and in_sql_block:
                        # End of SQL block
                        before_end = chunk.split("```")[0]
                        if before_end:
                            sql_content.append(before_end)

                        # Display SQL in a panel with syntax highlighting
                        sql_text = "".join(sql_content).strip()
                        if sql_text:
                            syntax = Syntax(sql_text, "sql", theme="monokai", line_numbers=False)
                            console.print(Panel(
                                syntax,
                                title="[bold cyan]SQL Query[/bold cyan]",
                                border_style="cyan",
                                padding=(0, 1),
                            ))

                        sql_content = []
                        in_sql_block = False

                        # Continue with content after closing ```
                        after_end = chunk.split("```", 1)[1]
                        if after_end:
                            current_content.append(after_end)

                    elif in_sql_block:
                        # Accumulate SQL content
                        sql_content.append(chunk)
                    else:
                        # Regular content - accumulate for printing
                        current_content.append(chunk)

                        # Print in larger chunks for better performance
                        if len(current_content) > 10:
                            console.print("".join(current_content), end="", markup=False)
                            current_content = []

            # Flush any remaining content
            if current_content:
                console.print("".join(current_content), end="", markup=False)
            if sql_content:
                # Handle case where SQL block wasn't closed
                sql_text = "".join(sql_content).strip()
                if sql_text:
                    syntax = Syntax(sql_text, "sql", theme="monokai", line_numbers=False)
                    console.print(Panel(
                        syntax,
                        title="[bold cyan]SQL Query[/bold cyan]",
                        border_style="cyan",
                        padding=(0, 1),
                    ))

        asyncio.run(consume_stream())

    except Exception as e:
        console.print(f"[red]Error streaming response: {str(e)}[/red]")

    console.print()  # Blank line after response


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
                console.print("[red]Error: /query requires a SQL statement[/red]")
                console.print("[dim]Usage: /query SELECT * FROM transactions LIMIT 5[/dim]\n")
            else:
                sql = command_parts[1]
                handle_query_command(sql)
        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("[dim]Type /help to see available commands[/dim]")
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
        console.print("[red]Unexpected error:[/red]")
        # Don't use markup since error messages may contain square brackets
        console.print(str(e), markup=False)
        console.print(traceback.format_exc(), markup=False)
        sys.exit(1)


@app.command()
def main() -> None:
    """Start Treeline interactive mode."""
    run_interactive_mode()


if __name__ == "__main__":
    app()
