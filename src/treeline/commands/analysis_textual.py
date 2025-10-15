"""Analysis mode command - Textual TUI implementation.

This module implements a split-panel TUI using Textual:
- Top panel: Results table
- Bottom panel: SQL editor with syntax highlighting
- Multiple view modes via Textual screens
"""

import asyncio
from uuid import UUID

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)
from textual.reactive import reactive

from rich.console import Console

from treeline.domain import ChartConfig
from treeline.commands.chart_wizard import ChartWizardConfig, create_chart_from_config
from treeline.theme import get_theme
from treeline.tui_theme import ThemedApp

console = Console()
theme = get_theme()


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


class ResultsPanel(Container):
    """Panel for displaying query results or charts."""

    error_message = reactive("")
    view_mode = reactive("results")  # "results", "chart", "help"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.results_data = []
        self.columns_data = []
        self.chart_content = ""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        # Results table
        yield DataTable(id="results_table", zebra_stripes=True)
        # Chart display (hidden by default)
        yield Static("", id="chart_display", classes="hidden")
        # Error display (hidden by default)
        yield Static("", id="error_display", classes="hidden")
        # Help display (hidden by default)
        yield Static("", id="help_display", classes="hidden")

    def on_mount(self) -> None:
        """Configure table when mounted."""
        table = self.query_one("#results_table", DataTable)
        table.cursor_type = "row"
        table.show_cursor = True

    def update_results(self, columns: list[str], rows: list[list]) -> None:
        """Update table with query results."""
        self.columns_data = columns
        self.results_data = rows
        self.error_message = ""
        self.view_mode = "results"

        table = self.query_one("#results_table", DataTable)
        table.clear(columns=True)

        if columns and rows:
            # Add columns
            table.add_columns(*columns)
            # Add rows
            for row in rows:
                # Convert values to strings, handle None
                str_row = [str(val) if val is not None else "NULL" for val in row]
                table.add_row(*str_row)

        self._update_visibility()

    def update_chart(self, chart: str) -> None:
        """Update display with chart content."""
        self.chart_content = chart
        self.view_mode = "chart"
        chart_display = self.query_one("#chart_display", Static)
        chart_display.update(chart)
        self._update_visibility()

    def update_error(self, error: str) -> None:
        """Update display with error message."""
        self.error_message = error
        error_display = self.query_one("#error_display", Static)
        error_display.update(f"[red bold]Error[/red bold]\n\n{error}\n\nFix the SQL below and press Ctrl+Enter to execute again.")
        self._update_visibility()

    def show_help(self) -> None:
        """Show help overlay."""
        self.view_mode = "help"
        help_text = """[bold green]Analysis Mode Shortcuts[/bold green]

[bold]SQL Execution[/bold]
  Alt+Enter   - Execute query
  F5          - Execute query (alternative)

[bold]Navigation[/bold]
  Tab         - Switch focus (SQL ↔ Data panel)
  ↑↓          - Navigate results rows

[bold]Charts[/bold]
  g           - Create chart (wizard)
  v           - Toggle results ↔ chart view
  s           - Save query or chart

[bold]Actions[/bold]
  r           - Reset (clear results/chart)
  ?           - Show this help
  Ctrl+C      - Exit analysis mode

Press any key to close"""
        help_display = self.query_one("#help_display", Static)
        help_display.update(help_text)
        self._update_visibility()

    def toggle_view(self) -> None:
        """Toggle between results and chart view."""
        if self.chart_content:
            self.view_mode = "chart" if self.view_mode == "results" else "results"
            self._update_visibility()

    def _update_visibility(self) -> None:
        """Update which display widget is visible."""
        table = self.query_one("#results_table", DataTable)
        chart_display = self.query_one("#chart_display", Static)
        error_display = self.query_one("#error_display", Static)
        help_display = self.query_one("#help_display", Static)

        # Hide all
        table.add_class("hidden")
        chart_display.add_class("hidden")
        error_display.add_class("hidden")
        help_display.add_class("hidden")

        # Show appropriate widget
        if self.error_message:
            error_display.remove_class("hidden")
        elif self.view_mode == "help":
            help_display.remove_class("hidden")
        elif self.view_mode == "chart" and self.chart_content:
            chart_display.remove_class("hidden")
        else:
            table.remove_class("hidden")


class AnalysisScreen(Screen):
    """Main analysis mode screen with SQL editor and results."""

    BINDINGS = [
        Binding("escape,enter", "execute_query", "Execute", key_display="Alt+Enter"),
        Binding("f5", "execute_query", "Execute", key_display="F5", show=False),
        Binding("tab", "focus_next", "Switch Focus"),
        Binding("g", "create_chart", "Create Chart", show=False),
        Binding("v", "toggle_view", "Toggle View", show=False),
        Binding("s", "save", "Save", show=False),
        Binding("r", "reset", "Reset", show=False),
        Binding("?", "show_help", "Help"),
        Binding("escape", "dismiss_help", "Close Help", show=False),
    ]

    CSS = """
    AnalysisScreen {
        layout: vertical;
    }

    #results_panel {
        height: 2fr;
        border: solid $accent;
    }

    #sql_panel {
        height: 1fr;
        border: solid $primary;
    }

    .hidden {
        display: none;
    }

    #results_table {
        height: 100%;
    }

    #chart_display {
        height: 100%;
        overflow-y: auto;
    }

    #error_display {
        height: 100%;
        padding: 1 2;
    }

    #help_display {
        height: 100%;
        padding: 2 4;
    }

    TextArea {
        height: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.sql_text = ""
        self.current_columns = []
        self.current_rows = []
        self.current_chart = None
        self.wizard_chart_type = ""
        self.wizard_x_column = ""
        self.wizard_y_column = ""

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with Container(id="results_panel"):
            yield ResultsPanel()
        with Container(id="sql_panel"):
            yield TextArea(
                text="",
                language="sql",
                theme="monokai",
                show_line_numbers=True,
                id="sql_editor"
            )
        yield Footer()

    def on_mount(self) -> None:
        """Set initial focus."""
        sql_editor = self.query_one("#sql_editor", TextArea)
        sql_editor.focus()

    def action_execute_query(self) -> None:
        """Execute SQL query (Ctrl+Enter)."""
        sql_editor = self.query_one("#sql_editor", TextArea)
        sql = sql_editor.text.strip()

        if not sql:
            return

        # Validate SELECT only
        sql_upper = sql.upper()
        if not sql_upper.startswith("SELECT") and not sql_upper.startswith("WITH"):
            results_panel = self.query_one(ResultsPanel)
            results_panel.update_error("Only SELECT and WITH queries are allowed in analysis mode")
            return

        # Store SQL for later use
        self.sql_text = sql

        # Execute query asynchronously
        self._execute_query(sql)

    @work(exclusive=True, thread=True)
    def _execute_query(self, sql: str) -> None:
        """Execute query in background thread."""
        # Get container and execute
        container = get_container()
        db_service = container.db_service()

        # Get user_id
        user_id_str = get_current_user_id()
        user_id = UUID(user_id_str)

        # Execute query (run async in thread)
        result = asyncio.run(db_service.execute_query(user_id, sql))

        # Update UI on main thread
        self.app.call_from_thread(self._handle_query_result, result)

    def _handle_query_result(self, result) -> None:
        """Handle query result on main thread."""
        results_panel = self.query_one(ResultsPanel)

        if result.success:
            rows = result.data["rows"]
            columns = result.data["columns"]
            self.current_rows = rows
            self.current_columns = columns
            results_panel.update_results(columns, rows)
        else:
            results_panel.update_error(f"Query failed: {result.error}")

    def action_focus_next(self) -> None:
        """Switch focus between SQL editor and results table."""
        self.screen.focus_next()

    def action_toggle_view(self) -> None:
        """Toggle between results and chart view."""
        results_panel = self.query_one(ResultsPanel)
        results_panel.toggle_view()

    def action_create_chart(self) -> None:
        """Open chart wizard."""
        if not self.current_rows or not self.current_columns:
            self.notify("No results to chart. Execute a query first.")
            return

        # Push chart wizard screen
        wizard_screen = ChartWizardScreen(
            columns=self.current_columns,
            rows=self.current_rows,
            sql=self.sql_text
        )
        self.app.push_screen(wizard_screen, self._handle_chart_created)

    def _handle_chart_created(self, chart_data: dict | None) -> None:
        """Handle chart creation callback."""
        if chart_data:
            # Update the current screen with the chart
            self.current_chart = chart_data["chart"]
            self.wizard_chart_type = chart_data["chart_type"]
            self.wizard_x_column = chart_data["x_column"]
            self.wizard_y_column = chart_data["y_column"]

            results_panel = self.query_one(ResultsPanel)
            results_panel.update_chart(chart_data["chart"])

    def action_save(self) -> None:
        """Save current query or chart."""
        results_panel = self.query_one(ResultsPanel)

        # Determine what to save
        if results_panel.view_mode == "chart" and self.current_chart:
            # Save chart
            save_screen = SaveScreen(
                save_type="chart",
                sql=self.sql_text,
                chart_type=self.wizard_chart_type,
                x_column=self.wizard_x_column,
                y_column=self.wizard_y_column
            )
            self.app.push_screen(save_screen)
        elif self.sql_text.strip():
            # Save query
            save_screen = SaveScreen(save_type="query", sql=self.sql_text)
            self.app.push_screen(save_screen)

    def action_reset(self) -> None:
        """Reset results and chart."""
        self.current_rows = []
        self.current_columns = []
        self.current_chart = None
        results_panel = self.query_one(ResultsPanel)
        results_panel.update_results([], [])

    def action_show_help(self) -> None:
        """Show help overlay."""
        results_panel = self.query_one(ResultsPanel)
        results_panel.show_help()

    def action_dismiss_help(self) -> None:
        """Dismiss help overlay."""
        results_panel = self.query_one(ResultsPanel)
        if results_panel.view_mode == "help":
            results_panel.view_mode = "results"
            results_panel._update_visibility()


class ChartWizardScreen(Screen):
    """Screen for creating charts with step-by-step wizard."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("1", "select_1", "Select 1", show=False),
        Binding("2", "select_2", "Select 2", show=False),
        Binding("3", "select_3", "Select 3", show=False),
        Binding("4", "select_4", "Select 4", show=False),
        Binding("5", "select_5", "Select 5", show=False),
        Binding("6", "select_6", "Select 6", show=False),
        Binding("7", "select_7", "Select 7", show=False),
        Binding("8", "select_8", "Select 8", show=False),
        Binding("9", "select_9", "Select 9", show=False),
    ]

    CSS = """
    ChartWizardScreen {
        align: center middle;
    }

    #wizard_container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2 4;
    }

    #wizard_title {
        text-align: center;
        color: $accent;
        text-style: bold;
    }

    #wizard_content {
        margin-top: 2;
    }

    .wizard_option {
        margin: 1 0;
    }

    #wizard_footer {
        margin-top: 2;
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, columns: list[str], rows: list[list], sql: str):
        super().__init__()
        self.columns = columns
        self.rows = rows
        self.sql = sql
        self.step = "chart_type"  # chart_type, x_column, y_column
        self.chart_type = ""
        self.x_column = ""
        self.y_column = ""

    def compose(self) -> ComposeResult:
        """Create wizard UI."""
        with Container(id="wizard_container"):
            yield Static("Chart Wizard", id="wizard_title")
            yield Container(id="wizard_content")
            yield Static("Press 1-9 to select, Esc to cancel", id="wizard_footer")

    def on_mount(self) -> None:
        """Show initial wizard step."""
        self._update_wizard_content()

    def _update_wizard_content(self) -> None:
        """Update wizard content based on current step."""
        content = self.query_one("#wizard_content", Container)
        content.remove_children()

        if self.step == "chart_type":
            content.mount(Static("Select chart type:\n", classes="wizard_option"))
            content.mount(Static("  [1] Bar chart", classes="wizard_option"))
            content.mount(Static("  [2] Line chart", classes="wizard_option"))
            content.mount(Static("  [3] Scatter plot", classes="wizard_option"))
            content.mount(Static("  [4] Histogram", classes="wizard_option"))

        elif self.step == "x_column":
            content.mount(Static(f"Chart type: {self.chart_type}\n", classes="wizard_option"))
            content.mount(Static("Select X-axis column:\n", classes="wizard_option"))
            for i, col in enumerate(self.columns[:9], 1):
                content.mount(Static(f"  [{i}] {col}", classes="wizard_option"))

        elif self.step == "y_column":
            content.mount(Static(f"Chart type: {self.chart_type}", classes="wizard_option"))
            content.mount(Static(f"X-axis: {self.x_column}\n", classes="wizard_option"))
            content.mount(Static("Select Y-axis column:\n", classes="wizard_option"))
            for i, col in enumerate(self.columns[:9], 1):
                content.mount(Static(f"  [{i}] {col}", classes="wizard_option"))

    def action_cancel(self) -> None:
        """Cancel wizard and return to main screen."""
        self.dismiss(None)

    def action_select_1(self) -> None:
        self._handle_selection(1)

    def action_select_2(self) -> None:
        self._handle_selection(2)

    def action_select_3(self) -> None:
        self._handle_selection(3)

    def action_select_4(self) -> None:
        self._handle_selection(4)

    def action_select_5(self) -> None:
        self._handle_selection(5)

    def action_select_6(self) -> None:
        self._handle_selection(6)

    def action_select_7(self) -> None:
        self._handle_selection(7)

    def action_select_8(self) -> None:
        self._handle_selection(8)

    def action_select_9(self) -> None:
        self._handle_selection(9)

    def _handle_selection(self, choice: int) -> None:
        """Handle wizard step selection."""
        if self.step == "chart_type":
            chart_types = {1: "bar", 2: "line", 3: "scatter", 4: "histogram"}
            if choice in chart_types:
                self.chart_type = chart_types[choice]
                if self.chart_type == "histogram":
                    # Histogram only needs X column
                    self.step = "x_column"
                else:
                    self.step = "x_column"
                self._update_wizard_content()

        elif self.step == "x_column":
            if 1 <= choice <= len(self.columns):
                self.x_column = self.columns[choice - 1]
                if self.chart_type == "histogram":
                    # Create histogram immediately
                    self._create_chart()
                else:
                    self.step = "y_column"
                    self._update_wizard_content()

        elif self.step == "y_column":
            if 1 <= choice <= len(self.columns):
                self.y_column = self.columns[choice - 1]
                self._create_chart()

    def _create_chart(self) -> None:
        """Create the chart and dismiss wizard."""
        config = ChartWizardConfig(
            chart_type=self.chart_type,
            x_column=self.x_column,
            y_column=self.y_column if self.y_column else "",
            title=f"{self.y_column} by {self.x_column}" if self.y_column else self.x_column,
            width=100,
            height=20,
        )

        result = create_chart_from_config(config, self.columns, self.rows)

        if result.success:
            chart_data = {
                "chart": result.data,
                "chart_type": self.chart_type,
                "x_column": self.x_column,
                "y_column": self.y_column
            }
            self.dismiss(chart_data)
        else:
            self.notify(f"Error: {result.error}", severity="error")
            self.dismiss(None)


class SaveScreen(Screen):
    """Screen for saving queries or charts."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    CSS = """
    SaveScreen {
        align: center middle;
    }

    #save_container {
        width: 60;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2 4;
    }

    #save_title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin-bottom: 2;
    }

    #save_input {
        margin: 2 0;
    }

    #save_footer {
        margin-top: 2;
        text-align: center;
        color: $text-muted;
    }

    Button {
        margin: 1 2;
    }
    """

    def __init__(self, save_type: str, sql: str, chart_type: str = "", x_column: str = "", y_column: str = ""):
        super().__init__()
        self.save_type = save_type  # "query" or "chart"
        self.sql = sql
        self.chart_type = chart_type
        self.x_column = x_column
        self.y_column = y_column

    def compose(self) -> ComposeResult:
        """Create save UI."""
        with Container(id="save_container"):
            yield Static(f"Save {self.save_type.title()}", id="save_title")
            yield Label(f"Enter {self.save_type} name:")
            yield Input(placeholder="my_query_name", id="save_input")
            with Horizontal():
                yield Button("Save", variant="primary", id="save_button")
                yield Button("Cancel", id="cancel_button")
            yield Static("Name must use only letters, numbers, and underscores", id="save_footer")

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#save_input", Input).focus()

    @on(Button.Pressed, "#save_button")
    def handle_save(self) -> None:
        """Save the query or chart."""
        name_input = self.query_one("#save_input", Input)
        name = name_input.value.strip()

        if not name:
            self.notify("Name cannot be empty", severity="warning")
            return

        # Validate name
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            self.notify("Invalid name. Use only letters, numbers, and underscores", severity="error")
            return

        # Save based on type
        if self.save_type == "query":
            from treeline.commands.saved_queries import save_query
            if save_query(name, self.sql):
                self.notify(f"✓ Saved query '{name}'", severity="information")
                self.dismiss()
            else:
                self.notify("Failed to save query", severity="error")

        elif self.save_type == "chart":
            chart_config = ChartConfig(
                name=name,
                query=self.sql,
                chart_type=self.chart_type,
                x_column=self.x_column,
                y_column=self.y_column,
                title=f"{self.y_column} by {self.x_column}" if self.y_column else self.x_column,
            )
            container = get_container()
            chart_storage = container.chart_storage()
            if chart_storage.save(name, chart_config):
                self.notify(f"✓ Saved chart '{name}'", severity="information")
                self.dismiss()
            else:
                self.notify("Failed to save chart", severity="error")

    @on(Button.Pressed, "#cancel_button")
    def handle_cancel(self) -> None:
        """Cancel save."""
        self.dismiss()

    def action_cancel(self) -> None:
        """Cancel save with escape key."""
        self.dismiss()

    @on(Input.Submitted)
    def handle_input_submit(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self.handle_save()


class AnalysisApp(ThemedApp):
    """Textual application for analysis mode."""

    TITLE = "Analysis Mode"

    def on_mount(self) -> None:
        """Push the main screen when app starts."""
        self.push_screen(AnalysisScreen())


def handle_analysis_command() -> None:
    """Main analysis mode entry point using Textual."""
    if not is_authenticated():
        console.print(
            f"[{theme.error}]Error: You must be logged in to use analysis mode.[/{theme.error}]"
        )
        console.print(f"[{theme.muted}]Run 'treeline login' to authenticate[/{theme.muted}]\n")
        return

    app = AnalysisApp()
    app.run()

    console.print(f"\n[{theme.muted}]Exiting analysis mode[/{theme.muted}]\n")
