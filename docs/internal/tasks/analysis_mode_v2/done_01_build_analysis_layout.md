# Task 01: Build Analysis Modal View Layout

**Status:** Not Started
**Dependencies:** None
**Estimated Time:** 1-2 hours

## Objective

Create the core full-screen modal view structure for analysis mode using Rich Layout, similar to `/tag` mode.

## Requirements

### Functional
1. Enter `/analysis` command to open full-screen modal view
2. Display header with context-aware keyboard shortcuts
3. Display 3 panels: SQL (bottom), Results (middle), Chart (top, conditional)
4. Chart panel only visible when chart exists
5. Clean exit on 'q' keypress

### Technical
1. Create `src/treeline/commands/analysis.py`
2. Register command in CLI
3. Use Rich Layout for panel composition
4. Create `AnalysisSession` dataclass in `src/treeline/domain/analysis.py`
5. Basic event loop structure

## Implementation Details

### 1. Domain Model

**File:** `src/treeline/domain/analysis.py`

```python
"""Domain models for analysis mode."""

from dataclasses import dataclass
from typing import Any


@dataclass
class AnalysisSession:
    """State for an analysis mode session."""

    sql: str = ""
    results: list[list[Any]] | None = None
    columns: list[str] | None = None
    chart: Any | None = None  # Will be ChartDisplay later
    view_mode: str = "results"  # "results" or "chart"

    def has_results(self) -> bool:
        """Check if session has query results."""
        return self.results is not None and self.columns is not None

    def has_chart(self) -> bool:
        """Check if session has a chart."""
        return self.chart is not None

    def toggle_view(self) -> None:
        """Toggle between results and chart view."""
        if self.view_mode == "results":
            self.view_mode = "chart"
        else:
            self.view_mode = "results"

    def reset(self) -> None:
        """Reset results and chart, keep SQL."""
        self.results = None
        self.columns = None
        self.chart = None
        self.view_mode = "results"

    def clear(self) -> None:
        """Clear everything."""
        self.sql = ""
        self.results = None
        self.columns = None
        self.chart = None
        self.view_mode = "results"
```

### 2. Layout Structure

**File:** `src/treeline/commands/analysis.py`

```python
"""Analysis mode command - integrated workspace for data exploration."""

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from treeline.domain.analysis import AnalysisSession
from treeline.theme import get_theme

console = Console()
theme = get_theme()


def _render_shortcuts(session: AnalysisSession) -> str:
    """Render context-aware keyboard shortcuts."""
    base = "[F5] execute  [q]uit"

    if session.has_results():
        base = f"[c]hart  [s]ave  [r]eset  {base}"

    if session.has_chart():
        base = f"[x] close chart  {base}"

    return f"[{theme.info}]Analysis Mode[/{theme.info}]    {base}"


def _render_sql_panel(session: AnalysisSession) -> Panel:
    """Render SQL editor panel."""
    content = session.sql if session.sql else "[dim]Enter SQL query...[/dim]"

    return Panel(
        content,
        title="SQL",
        subtitle="[F5] execute",
        border_style=theme.info,
    )


def _render_results_panel(session: AnalysisSession) -> Panel:
    """Render results table panel."""
    if not session.has_results():
        return Panel(
            "[dim]No results yet. Press F5 to execute query.[/dim]",
            title="Results",
            border_style=theme.muted,
        )

    # TODO: Render actual table (Task 03)
    row_count = len(session.results)
    return Panel(
        f"[{theme.success}]{row_count} rows returned[/{theme.success}]",
        title=f"Results ({row_count} rows)",
        border_style=theme.success,
    )


def _render_chart_panel(session: AnalysisSession) -> Panel:
    """Render chart panel."""
    # TODO: Render actual chart (Task 04)
    return Panel(
        "[dim]Chart will appear here[/dim]",
        title="Chart",
        subtitle="[x] close",
        border_style=theme.primary,
    )


def _render_analysis_view(session: AnalysisSession) -> Layout:
    """Render the complete analysis modal view."""
    layout = Layout()

    # Two-panel layout: Header + Data panel (top) + SQL (bottom)
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="data", ratio=2),
        Layout(name="sql", size=10),
    )

    layout["header"].update(Panel(_render_shortcuts(session), style=theme.ui_header))

    # Data panel shows either results or chart based on view_mode
    if session.view_mode == "chart" and session.has_chart():
        layout["data"].update(_render_chart_panel(session))
    else:
        layout["data"].update(_render_results_panel(session))

    layout["sql"].update(_render_sql_panel(session))

    return layout


def handle_analysis_command() -> None:
    """Main analysis mode entry point."""
    session = AnalysisSession()

    try:
        console.clear()

        while True:
            # Render current state
            console.print(_render_analysis_view(session))

            # TODO: Handle keyboard input (Task 05)
            # For now, just show layout and exit
            console.print("\n[dim]Press enter to exit (keyboard nav coming in Task 05)...[/dim]")
            input()
            break

    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{theme.muted}]Exiting analysis mode[/{theme.muted}]\n")
```

### 3. CLI Registration

**File:** `src/treeline/cli.py`

Add to command handlers:
```python
from treeline.commands.analysis import handle_analysis_command

# In main CLI loop
elif command == "analysis":
    handle_analysis_command()
```

Add to help text in `src/treeline/commands/help.py`:
```python
commands.append(("analysis", "Integrated workspace for data exploration"))
```

## Testing

### Unit Tests

**File:** `tests/unit/commands/test_analysis_layout.py`

```python
"""Tests for analysis mode layout."""

import pytest
from treeline.domain.analysis import AnalysisSession
from treeline.commands.analysis import _render_analysis_view


class TestAnalysisSession:
    """Tests for AnalysisSession state."""

    def test_empty_session_has_no_results(self):
        session = AnalysisSession()
        assert not session.has_results()
        assert not session.has_chart()

    def test_session_with_results(self):
        session = AnalysisSession(
            sql="SELECT * FROM test",
            columns=["id", "name"],
            results=[[1, "test"]],
        )
        assert session.has_results()
        assert not session.has_chart()

    def test_session_reset_keeps_sql(self):
        session = AnalysisSession(
            sql="SELECT * FROM test",
            columns=["id"],
            results=[[1]],
        )
        session.reset()
        assert session.sql == "SELECT * FROM test"
        assert not session.has_results()

    def test_session_clear_removes_everything(self):
        session = AnalysisSession(sql="SELECT * FROM test")
        session.clear()
        assert session.sql == ""


class TestAnalysisLayout:
    """Tests for layout rendering."""

    def test_layout_renders_without_results(self):
        session = AnalysisSession()
        layout = _render_analysis_view(session)
        assert layout is not None

    def test_layout_includes_chart_when_chart_exists(self):
        session = AnalysisSession(chart="mock_chart")
        layout = _render_analysis_view(session)
        assert layout is not None
        # Chart panel should have non-zero size
```

### Smoke Test

**File:** `tests/smoke/test_analysis_mode.py`

```python
"""Smoke tests for analysis mode."""

import pytest
from unittest.mock import patch
from treeline.commands.analysis import handle_analysis_command


def test_analysis_mode_opens_and_exits():
    """Test that analysis mode can open and exit cleanly."""
    with patch("treeline.commands.analysis.console") as mock_console:
        with patch("builtins.input", return_value=""):
            handle_analysis_command()

    assert mock_console.clear.called
    assert mock_console.print.called
```

## Architecture Review Checklist

- [ ] `AnalysisSession` is in domain layer (pure data)
- [ ] `handle_analysis_command` is thin CLI handler
- [ ] No business logic in command file
- [ ] No direct database calls
- [ ] Uses existing theme system
- [ ] No global state

## Acceptance Criteria

- [ ] `/analysis` command opens full-screen modal view
- [ ] Header shows keyboard shortcuts
- [ ] Three panels render correctly (SQL, Results placeholder, no Chart initially)
- [ ] Can exit with enter key (keyboard nav in Task 05)
- [ ] Unit tests pass (4+ tests)
- [ ] Smoke test passes
- [ ] Architecture guardian review passes

## Notes

- This task establishes the foundation but doesn't implement full functionality
- SQL editing, query execution, and chart creation come in later tasks
- Focus on layout structure and state management
- Keep it simple - just render the view correctly
