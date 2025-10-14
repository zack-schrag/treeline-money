"""Textual TUI for browsing and managing saved charts."""

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Static

from treeline.tui_theme import ThemedApp


def get_container():
    """Import get_container to avoid circular import."""
    from treeline.cli import get_container as _get_container
    return _get_container()


def is_authenticated():
    """Check if user is authenticated."""
    from treeline.cli import is_authenticated as _is_authenticated
    return _is_authenticated()


class RenameModal(ModalScreen[str | None]):
    """Modal screen for renaming a chart."""

    DEFAULT_CSS = """
    RenameModal {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        background: $panel;
        border: solid $primary;
        padding: 2;
    }

    #rename_input {
        width: 100%;
        margin: 1 0;
    }

    #buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, current_name: str):
        super().__init__()
        self.current_name = current_name

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"Rename chart: {self.current_name}")
            yield Input(
                value=self.current_name,
                placeholder="new_chart_name",
                id="rename_input",
            )
            with Horizontal(id="buttons"):
                yield Button("Rename", variant="primary", id="rename_button")
                yield Button("Cancel", id="cancel_button")

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#rename_input", Input).focus()

    @on(Button.Pressed, "#rename_button")
    def handle_rename(self) -> None:
        """Return the new name."""
        input_widget = self.query_one("#rename_input", Input)
        new_name = input_widget.value.strip()

        if not new_name:
            self.notify("Name cannot be empty", severity="warning")
            return

        # Validate name
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', new_name):
            self.notify("Invalid name. Use only letters, numbers, and underscores", severity="error")
            return

        self.dismiss(new_name)

    @on(Button.Pressed, "#cancel_button")
    def handle_cancel(self) -> None:
        """Cancel rename."""
        self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel with escape key."""
        self.dismiss(None)

    @on(Input.Submitted)
    def handle_input_submit(self, event: Input.Submitted) -> None:
        """Handle Enter key in input."""
        self.handle_rename()


class ChartsBrowserScreen(Screen):
    """Browse saved charts."""

    BINDINGS = [
        Binding("enter", "load_chart", "Load Chart", show=True),
        Binding("d", "delete_chart", "Delete", show=True),
        Binding("r", "rename_chart", "Rename", show=True),
        Binding("q,escape", "quit", "Quit", show=True),
    ]

    DEFAULT_CSS = """
    ChartsBrowserScreen {
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

    #chart_list_container {
        width: 1fr;
        border-right: solid $primary;
    }

    #preview_panel {
        width: 2fr;
        background: $panel;
        padding: 1;
    }

    #help_bar {
        dock: bottom;
        height: 2;
        background: $panel;
        color: $text-muted;
        padding: 0 1;
    }

    ListView {
        height: 100%;
    }
    """

    def __init__(self):
        super().__init__()
        self.charts: list[str] = []
        self.current_chart_name: str | None = None
        self.current_chart_config = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading charts...", id="status_bar")

        with Horizontal(id="main_container"):
            with Vertical(id="chart_list_container"):
                yield ListView(id="chart_list")
            with VerticalScroll(id="preview_panel"):
                yield Static("Select a chart to preview", id="preview_content")

        yield Static(
            "Enter: Load Chart | D: Delete | R: Rename | Q: Quit",
            id="help_bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load charts when mounted."""
        self.load_charts()

    def load_charts(self) -> None:
        """Load all saved charts."""
        container = get_container()
        chart_storage = container.chart_storage()
        self.charts = sorted(chart_storage.list())

        # Populate list
        list_view = self.query_one("#chart_list", ListView)
        list_view.clear()

        if not self.charts:
            list_view.append(ListItem(Label("(no saved charts)")))
            self.update_status("No saved charts")
        else:
            for chart_name in self.charts:
                list_view.append(ListItem(Label(chart_name)))
            self.update_status(f"{len(self.charts)} saved charts")

    def update_status(self, message: str) -> None:
        """Update status bar."""
        status = self.query_one("#status_bar", Static)
        status.update(message)

    @on(ListView.Selected)
    def on_chart_selected(self, event: ListView.Selected) -> None:
        """Handle chart selection."""
        if not self.charts:
            return

        # Get selected index
        list_view = self.query_one("#chart_list", ListView)
        selected_index = list_view.index

        if selected_index is None or selected_index >= len(self.charts):
            return

        # Load chart config
        chart_name = self.charts[selected_index]
        self.current_chart_name = chart_name

        container = get_container()
        chart_storage = container.chart_storage()
        config = chart_storage.load(chart_name)

        if config:
            self.current_chart_config = config
            preview = self.query_one("#preview_content", Static)

            # Format chart config for display
            preview_text = f"[bold cyan]Chart: {chart_name}[/bold cyan]\n\n"
            preview_text += f"[dim]Type:[/dim] {config.chart_type}\n"
            preview_text += f"[dim]X Column:[/dim] {config.x_column}\n"
            preview_text += f"[dim]Y Column:[/dim] {config.y_column or '(none)'}\n"
            if config.title:
                preview_text += f"[dim]Title:[/dim] {config.title}\n"
            if config.description:
                preview_text += f"[dim]Description:[/dim] {config.description}\n"
            preview_text += f"\n[dim]SQL Query:[/dim]\n{config.query}"

            preview.update(preview_text)
        else:
            self.current_chart_config = None
            self.notify(f"Failed to load chart '{chart_name}'", severity="error")

    def action_load_chart(self) -> None:
        """Load selected chart into analysis mode."""
        if not self.current_chart_name or not self.current_chart_config:
            self.notify("Select a chart first", severity="warning")
            return

        # Launch analysis mode with this chart
        from treeline.commands.analysis_textual import AnalysisApp, AnalysisScreen
        from treeline.commands.chart_wizard import ChartWizardConfig, create_chart_from_config
        import asyncio
        from uuid import UUID

        # Exit this browser
        self.app.exit()

        # Launch analysis mode with pre-loaded SQL and chart
        config = self.current_chart_config
        analysis_app = AnalysisApp()

        # Create a custom mount that pre-loads SQL and executes query
        original_on_mount = AnalysisApp.on_mount

        def custom_on_mount(self_app):
            screen = AnalysisScreen()
            self_app.push_screen(screen)

            # Set SQL and execute query after screen is mounted
            def load_and_execute():
                from treeline.cli import get_current_user_id

                # Set SQL in editor
                sql_editor = screen.query_one("#sql_editor")
                sql_editor.text = config.query

                # Execute query to get data
                container = get_container()
                db_service = container.db_service()
                user_id = UUID(get_current_user_id())

                result = asyncio.run(db_service.execute_query(user_id, config.query))

                if result.success:
                    rows = result.data["rows"]
                    columns = result.data["columns"]

                    # Store results in screen
                    screen.current_rows = rows
                    screen.current_columns = columns
                    screen.sql_text = config.query

                    # Create chart
                    chart_config = ChartWizardConfig(
                        chart_type=config.chart_type,
                        x_column=config.x_column,
                        y_column=config.y_column,
                        title=config.title or f"{config.y_column} by {config.x_column}",
                        width=100,
                        height=20,
                    )

                    chart_result = create_chart_from_config(chart_config, columns, rows)

                    if chart_result.success:
                        # Store chart data in screen
                        screen.current_chart = chart_result.data
                        screen.wizard_chart_type = config.chart_type
                        screen.wizard_x_column = config.x_column
                        screen.wizard_y_column = config.y_column

                        # Update results panel
                        results_panel = screen.query_one("ResultsPanel")
                        results_panel.update_results(columns, rows)
                        results_panel.update_chart(chart_result.data)
                    else:
                        # Just show results if chart fails
                        results_panel = screen.query_one("ResultsPanel")
                        results_panel.update_results(columns, rows)
                else:
                    # Show error
                    results_panel = screen.query_one("ResultsPanel")
                    results_panel.update_error(f"Query failed: {result.error}")

            self_app.call_later(load_and_execute)

        analysis_app.on_mount = lambda: custom_on_mount(analysis_app)
        analysis_app.run()

    def action_delete_chart(self) -> None:
        """Delete selected chart."""
        if not self.current_chart_name:
            self.notify("Select a chart first", severity="warning")
            return

        chart_name = self.current_chart_name
        container = get_container()
        chart_storage = container.chart_storage()

        if chart_storage.delete(chart_name):
            self.notify(f"✓ Deleted chart '{chart_name}'", severity="information")
            self.current_chart_name = None
            self.current_chart_config = None

            # Clear preview
            preview = self.query_one("#preview_content", Static)
            preview.update("Select a chart to preview")

            # Reload list
            self.load_charts()
        else:
            self.notify(f"Failed to delete chart '{chart_name}'", severity="error")

    def action_rename_chart(self) -> None:
        """Rename selected chart."""
        if not self.current_chart_name or not self.current_chart_config:
            self.notify("Select a chart first", severity="warning")
            return

        # Show rename modal
        modal = RenameModal(self.current_chart_name)
        self.app.push_screen(modal, self.handle_rename_result)

    def handle_rename_result(self, new_name: str | None) -> None:
        """Handle rename modal result."""
        if not new_name or new_name == self.current_chart_name:
            return

        container = get_container()
        chart_storage = container.chart_storage()

        # Check if new name already exists
        if chart_storage.exists(new_name):
            self.notify(f"Chart '{new_name}' already exists", severity="error")
            return

        # Create new config with updated name
        from treeline.domain import ChartConfig

        old_config = self.current_chart_config
        new_config = ChartConfig(
            name=new_name,
            query=old_config.query,
            chart_type=old_config.chart_type,
            x_column=old_config.x_column,
            y_column=old_config.y_column,
            title=old_config.title,
            xlabel=old_config.xlabel,
            ylabel=old_config.ylabel,
            color=old_config.color,
            description=old_config.description,
        )

        # Save with new name and delete old
        if chart_storage.save(new_name, new_config):
            if chart_storage.delete(self.current_chart_name):
                self.notify(f"✓ Renamed to '{new_name}'", severity="information")
                self.current_chart_name = new_name
                self.current_chart_config = new_config

                # Reload list
                self.load_charts()

                # Update preview
                preview = self.query_one("#preview_content", Static)
                preview_text = f"[bold cyan]Chart: {new_name}[/bold cyan]\n\n"
                preview_text += f"[dim]Type:[/dim] {new_config.chart_type}\n"
                preview_text += f"[dim]X Column:[/dim] {new_config.x_column}\n"
                preview_text += f"[dim]Y Column:[/dim] {new_config.y_column or '(none)'}\n"
                if new_config.title:
                    preview_text += f"[dim]Title:[/dim] {new_config.title}\n"
                if new_config.description:
                    preview_text += f"[dim]Description:[/dim] {new_config.description}\n"
                preview_text += f"\n[dim]SQL Query:[/dim]\n{new_config.query}"
                preview.update(preview_text)
            else:
                # Rollback: delete the new one
                chart_storage.delete(new_name)
                self.notify("Failed to rename chart", severity="error")
        else:
            self.notify("Failed to rename chart", severity="error")

    def action_quit(self) -> None:
        """Quit the browser."""
        self.app.exit()


class ChartsBrowserApp(ThemedApp):
    """Textual application for browsing charts."""

    TITLE = "Saved Charts Browser"

    def on_mount(self) -> None:
        """Initialize the app."""
        self.push_screen(ChartsBrowserScreen())
