# Code Style
- Use ruff for code formatting, and automatic formatting on file save
- ALWAYS use Python type hints

# Implementation Guidelines
- ALWAYS use Test Driven Development unless explicitly told otherwise. All new features should begin with **simple** unit tests that verify the logic and are **failing**. Only then should you begin implementation.
- ALWAYS follow Hexagonal architecture principles. All business logic should be completely independent of underlying technology choices. For example, there should NEVER be code written in the service layer that has specific knowledge of DuckDB or Supabase or OpenAI. ALWAYS review [architecture.md](./docs/internal/architecture.md) for more details about Hexagonal.
- ALWAYS run unit tests (see below) before doing a git commit, unless explicity asked not to.

# CLI Architecture Rules
- The CLI (`src/treeline/cli.py`) MUST be a thin presentation layer
- The CLI MUST ONLY interact with services from `src/treeline/app/service.py`
- The CLI MUST NEVER directly call repositories, providers, or any other abstractions
- The CLI MUST NEVER perform direct file I/O operations (use storage abstractions via container)
- All business logic MUST live in the service layer, NOT in the CLI
- The CLI should only:
  1. Parse user input
  2. Call the appropriate service method
  3. Display the results to the user

# Storage and Persistence Rules
- ALL file operations MUST go through storage abstractions defined in `src/treeline/abstractions/storage.py`
- Commands and CLI layers MUST access storage via container: `container.query_storage()`, `container.chart_storage()`
- NEVER use `Path.read_text()`, `Path.write_text()`, `open()`, or other file operations directly in commands/CLI
- Storage implementations (e.g., FileQueryStorage) belong in `src/treeline/infra/file_storage.py`
- ALL domain models (Account, Transaction, ChartConfig, etc.) MUST be defined in `src/treeline/domain.py`

# TUI Development Guidelines

## Textual TUI Architecture
- TUI applications are implemented using Textual framework in `src/treeline/commands/`
- TUIs MUST be thin presentation layers, like the CLI
- All business logic MUST be delegated to services via container
- TUIs should NOT perform direct database operations or file I/O

## TUI Structure Pattern

```python
from textual.app import App
from treeline.app.container import get_container

class MyTuiApp(App):
    """TUI application for [specific task]."""

    def on_mount(self) -> None:
        """Initialize TUI - get services from container."""
        self.container = get_container()
        self.some_service = self.container.some_service()

    @work
    async def some_action(self) -> None:
        """Handle user action - delegate to service."""
        result = await self.some_service.do_something()
        if result.success:
            self.display_result(result.data)
        else:
            self.show_error(result.error)
```

## TUI Best Practices
1. **Keyboard-Driven** - All actions should have keyboard shortcuts
2. **Discoverable** - Use `?` for help, show shortcuts in status bars
3. **Consistent** - Follow patterns from existing TUIs (analysis, tag, queries, charts)
4. **Vim-Inspired** - Use j/k for navigation where appropriate
5. **Mnemonic Shortcuts** - `g` for chart/graph, `s` for save, `r` for reset
6. **No Modal Prompts** - Avoid blocking modal dialogs, use inline forms
7. **Async Operations** - Use `@work` decorator for long-running operations
8. **Error Handling** - Display errors inline, don't crash the TUI

## Launching TUIs from CLI

```python
@app.command(name="mytui")
def mytui_command() -> None:
    """Launch my TUI application."""
    container = get_container()
    config_service = container.config_service()

    # Check auth first
    if not config_service.is_authenticated():
        console.print("[red]Error: Not authenticated[/red]")
        console.print("Run 'treeline login' first")
        raise typer.Exit(1)

    # Launch TUI
    from treeline.commands.mytui_textual import MyTuiApp
    app = MyTuiApp()
    app.run()
```

## TUI vs Scriptable Commands

**Use TUI when:**
- Complex interactive workflow (analysis, tagging)
- Real-time feedback needed
- Multiple steps with navigation
- Visual data browsing required

**Use Scriptable Command when:**
- Simple one-shot operations
- Needs JSON/CSV output
- Should work in scripts
- No interaction required

Examples:
- ✅ TUI: `treeline tag` (interactive tagging workflow)
- ✅ Scriptable: `treeline sync` (one-shot with JSON output)
- ✅ TUI: `treeline analysis` (complex SQL workspace)
- ✅ Scriptable: `treeline query "SELECT..."` (one-shot query)

# Testing Instructions
## Unit Tests
These have mocked dependencies and verify core logic. For example, a unit test to verify transaction deduplication works during synchronization, with data provider mocked.

Run unit tests: `uv run pytest tests/unit`

## Smoke Tests
These are end-to-end tests intended to test the same functionality a user will itneract with. These should be very basic and not duplicate unit tests, but rather test high-level commands and flows.

Run smoke tests: `uv run pytest tests/smoke`