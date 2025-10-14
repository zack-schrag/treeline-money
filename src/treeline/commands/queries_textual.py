"""Textual TUI for browsing and managing saved queries."""

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
    """Modal screen for renaming a query."""

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
            yield Label(f"Rename query: {self.current_name}")
            yield Input(
                value=self.current_name,
                placeholder="new_query_name",
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


class QueriesBrowserScreen(Screen):
    """Browse saved queries."""

    BINDINGS = [
        Binding("enter", "load_query", "Load Query", show=True),
        Binding("d", "delete_query", "Delete", show=True),
        Binding("r", "rename_query", "Rename", show=True),
        Binding("q,escape", "quit", "Quit", show=True),
    ]

    DEFAULT_CSS = """
    QueriesBrowserScreen {
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

    #query_list_container {
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
        self.queries: list[str] = []
        self.current_query_name: str | None = None
        self.current_query_sql: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Loading queries...", id="status_bar")

        with Horizontal(id="main_container"):
            with Vertical(id="query_list_container"):
                yield ListView(id="query_list")
            with VerticalScroll(id="preview_panel"):
                yield Static("Select a query to preview", id="preview_content")

        yield Static(
            "Enter: Load Query | D: Delete | R: Rename | Q: Quit",
            id="help_bar",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Load queries when mounted."""
        self.load_queries()

    def load_queries(self) -> None:
        """Load all saved queries."""
        container = get_container()
        query_storage = container.query_storage()
        self.queries = sorted(query_storage.list())

        # Populate list
        list_view = self.query_one("#query_list", ListView)
        list_view.clear()

        if not self.queries:
            list_view.append(ListItem(Label("(no saved queries)")))
            self.update_status("No saved queries")
        else:
            for query_name in self.queries:
                list_view.append(ListItem(Label(query_name)))
            self.update_status(f"{len(self.queries)} saved queries")

    def update_status(self, message: str) -> None:
        """Update status bar."""
        status = self.query_one("#status_bar", Static)
        status.update(message)

    @on(ListView.Selected)
    def on_query_selected(self, event: ListView.Selected) -> None:
        """Handle query selection."""
        if not self.queries:
            return

        # Get selected index
        list_view = self.query_one("#query_list", ListView)
        selected_index = list_view.index

        if selected_index is None or selected_index >= len(self.queries):
            return

        # Load query SQL
        query_name = self.queries[selected_index]
        self.current_query_name = query_name

        container = get_container()
        query_storage = container.query_storage()
        sql = query_storage.load(query_name)

        if sql:
            self.current_query_sql = sql
            preview = self.query_one("#preview_content", Static)
            preview.update(f"[bold cyan]Query: {query_name}[/bold cyan]\n\n[dim]SQL:[/dim]\n{sql}")
        else:
            self.current_query_sql = None
            self.notify(f"Failed to load query '{query_name}'", severity="error")

    def action_load_query(self) -> None:
        """Load selected query into analysis mode."""
        if not self.current_query_name or not self.current_query_sql:
            self.notify("Select a query first", severity="warning")
            return

        # Launch analysis mode with this query
        from treeline.commands.analysis_textual import AnalysisApp, AnalysisScreen

        # Exit this browser
        self.app.exit()

        # Launch analysis mode with pre-loaded SQL
        # We need to create a custom screen with pre-loaded SQL
        analysis_app = AnalysisApp()

        # Create a custom mount that pre-loads SQL
        original_on_mount = AnalysisApp.on_mount

        def custom_on_mount(self_app):
            screen = AnalysisScreen()
            self_app.push_screen(screen)
            # Set SQL after screen is mounted
            def set_sql():
                sql_editor = screen.query_one("#sql_editor")
                sql_editor.text = self.current_query_sql
            self_app.call_later(set_sql)

        analysis_app.on_mount = lambda: custom_on_mount(analysis_app)
        analysis_app.run()

    def action_delete_query(self) -> None:
        """Delete selected query."""
        if not self.current_query_name:
            self.notify("Select a query first", severity="warning")
            return

        query_name = self.current_query_name
        container = get_container()
        query_storage = container.query_storage()

        if query_storage.delete(query_name):
            self.notify(f"✓ Deleted query '{query_name}'", severity="information")
            self.current_query_name = None
            self.current_query_sql = None

            # Clear preview
            preview = self.query_one("#preview_content", Static)
            preview.update("Select a query to preview")

            # Reload list
            self.load_queries()
        else:
            self.notify(f"Failed to delete query '{query_name}'", severity="error")

    def action_rename_query(self) -> None:
        """Rename selected query."""
        if not self.current_query_name or not self.current_query_sql:
            self.notify("Select a query first", severity="warning")
            return

        # Show rename modal
        modal = RenameModal(self.current_query_name)
        self.app.push_screen(modal, self.handle_rename_result)

    def handle_rename_result(self, new_name: str | None) -> None:
        """Handle rename modal result."""
        if not new_name or new_name == self.current_query_name:
            return

        container = get_container()
        query_storage = container.query_storage()

        # Check if new name already exists
        if query_storage.exists(new_name):
            self.notify(f"Query '{new_name}' already exists", severity="error")
            return

        # Save with new name and delete old
        if query_storage.save(new_name, self.current_query_sql):
            if query_storage.delete(self.current_query_name):
                self.notify(f"✓ Renamed to '{new_name}'", severity="information")
                self.current_query_name = new_name

                # Reload list
                self.load_queries()

                # Update preview
                preview = self.query_one("#preview_content", Static)
                preview.update(f"[bold cyan]Query: {new_name}[/bold cyan]\n\n[dim]SQL:[/dim]\n{self.current_query_sql}")
            else:
                # Rollback: delete the new one
                query_storage.delete(new_name)
                self.notify("Failed to rename query", severity="error")
        else:
            self.notify("Failed to rename query", severity="error")

    def action_quit(self) -> None:
        """Quit the browser."""
        self.app.exit()


class QueriesBrowserApp(ThemedApp):
    """Textual application for browsing queries."""

    TITLE = "Saved Queries Browser"

    def on_mount(self) -> None:
        """Initialize the app."""
        self.push_screen(QueriesBrowserScreen())
