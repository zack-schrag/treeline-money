"""Chat message handler."""

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


def get_treeline_dir():
    """Import get_treeline_dir to avoid circular import."""
    from treeline.cli import get_treeline_dir as _get_treeline_dir
    return _get_treeline_dir()


def handle_chat_message(message: str) -> None:
    """Handle natural language chat message."""
    container = get_container()
    config_service = container.config_service()
    agent_service = container.agent_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    # Get database path for this specific user
    treeline_dir = get_treeline_dir()
    db_path = str(treeline_dir / "treeline.db" / f"{user_id}.duckdb")

    # Send message to agent
    with console.status(f"[{theme.muted}]Thinking...[/{theme.muted}]"):
        result = asyncio.run(agent_service.chat(user_id, db_path, message))

    if not result.success:
        console.print(f"[{theme.error}]Error: {result.error}[/{theme.error}]\n")
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
                        f"[{theme.muted}]Using tool:[/{theme.muted}] [{theme.emphasis}]{tool_name}[/{theme.emphasis}]",
                        border_style=theme.muted,
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
                                title=f"[{theme.ui_header}]SQL Query[/{theme.ui_header}]",
                                border_style=theme.primary,
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
                        title=f"[{theme.ui_header}]SQL Query[/{theme.ui_header}]",
                        border_style=theme.primary,
                        padding=(0, 1),
                    ))

        asyncio.run(consume_stream())

    except Exception as e:
        console.print(f"[{theme.error}]Error streaming response: {str(e)}[/{theme.error}]")

    console.print()  # Blank line after response
