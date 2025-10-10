"""Chart command for running saved chart configurations."""

import asyncio
from uuid import UUID
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from treeline.theme import get_theme
from treeline.commands.chart_config import ChartConfigStore, get_charts_dir
from treeline.commands.chart_wizard import ChartWizardConfig, create_chart_from_config

console = Console()
theme = get_theme()


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def handle_chart_command(chart_name: str | None = None) -> None:
    """Handle /chart command - run saved chart or list charts.

    Args:
        chart_name: Name of the chart to run (None to list all charts)
    """
    container = get_container()
    config_service = container.config_service()
    db_service = container.db_service()

    # Check authentication
    user_id_str = config_service.get_current_user_id()
    if not user_id_str:
        console.print(f"[{theme.error}]Error: Not authenticated. Please use /login first.[/{theme.error}]\n")
        return

    user_id = UUID(user_id_str)

    # Load chart config store
    store = ChartConfigStore(get_charts_dir())

    # If no chart name provided, list all charts
    if not chart_name:
        charts = store.list()

        console.print()
        if not charts:
            console.print(f"[{theme.muted}]No saved charts yet.[/{theme.muted}]")
            console.print(f"[{theme.muted}]After running a query, you'll be prompted to create and save a chart.[/{theme.muted}]\n")
            return

        console.print(f"[{theme.ui_header}]Saved Charts[/{theme.ui_header}]\n")
        for chart in charts:
            console.print(f"  • [{theme.emphasis}]{chart}[/{theme.emphasis}]")

        console.print()
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/chart chart_name[/{theme.emphasis}] to run a saved chart[/{theme.muted}]\n")
        return

    # Load the chart configuration
    chart_config = store.load(chart_name)

    if chart_config is None:
        console.print(f"\n[{theme.error}]Chart '{chart_name}' not found.[/{theme.error}]")
        console.print(f"[{theme.muted}]Use [{theme.emphasis}]/chart[/{theme.emphasis}] to see available charts.[/{theme.muted}]\n")
        return

    # Display the SQL query that will be executed
    console.print()
    syntax = Syntax(chart_config.query, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(
        syntax,
        title=f"[{theme.ui_header}]Executing Query[/{theme.ui_header}]",
        border_style=theme.primary,
        padding=(0, 1),
    ))

    # Execute the query
    with console.status(f"[{theme.muted}]Running query...[/{theme.muted}]"):
        result = asyncio.run(db_service.execute_query(user_id, chart_config.query))

    if not result.success:
        console.print(f"\n[{theme.error}]Error: {result.error}[/{theme.error}]\n")
        return

    # Get query results
    query_result = result.data
    rows = query_result.get("rows", [])
    columns = query_result.get("columns", [])

    console.print()

    if len(rows) == 0:
        console.print(f"[{theme.muted}]Query returned no results. Cannot generate chart.[/{theme.muted}]\n")
        return

    # Create chart wizard config from saved config
    wizard_config = ChartWizardConfig(
        chart_type=chart_config.chart_type,
        x_column=chart_config.x_column,
        y_column=chart_config.y_column,
        title=chart_config.title,
        xlabel=chart_config.xlabel,
        ylabel=chart_config.ylabel,
        color=chart_config.color,
    )

    # Generate and display chart
    with console.status(f"[{theme.muted}]Generating chart...[/{theme.muted}]"):
        chart_result = create_chart_from_config(wizard_config, columns, rows)

    if not chart_result.success:
        console.print(f"[{theme.error}]Error creating chart: {chart_result.error}[/{theme.error}]\n")
        return

    console.print(chart_result.data)
