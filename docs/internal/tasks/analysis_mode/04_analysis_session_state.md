# Analysis Mode: Session State Management

## Problem

To enable fluid iteration in `/analysis` mode, we need to maintain state across different sub-modes (SQL editing, result viewing, chart creation). Without state management, users lose context when moving between modes.

## Solution

Implement a stateful session that preserves:
- Current SQL query
- Query results (columns + rows)
- Chart configuration (if creating/editing a chart)
- Current mode (sql, results, chart)

## Implementation Details

### Create `analysis_session.py`

```python
"""State management for analysis mode sessions."""

from dataclasses import dataclass, field
from typing import Any, Literal
from treeline.commands.chart_wizard import ChartWizardConfig


@dataclass
class AnalysisSession:
    """Maintains state for an analysis session.

    This allows users to fluidly move between SQL editing,
    result viewing, and chart creation without losing context.
    """

    # SQL state
    sql: str = ""
    sql_modified: bool = False

    # Results state
    columns: list[str] = field(default_factory=list)
    rows: list[list[Any]] = field(default_factory=list)
    has_results: bool = False

    # Chart state
    chart_config: ChartWizardConfig | None = None
    chart_output: str | None = None

    # Navigation state
    mode: Literal["sql", "results", "chart"] = "sql"

    def update_sql(self, sql: str) -> None:
        """Update SQL and mark as modified."""
        self.sql = sql
        self.sql_modified = True

    def update_results(self, columns: list[str], rows: list[list[Any]]) -> None:
        """Update query results."""
        self.columns = columns
        self.rows = rows
        self.has_results = len(rows) > 0
        self.sql_modified = False  # Results match current SQL

    def clear_results(self) -> None:
        """Clear results (e.g., after SQL change)."""
        self.columns = []
        self.rows = []
        self.has_results = False

    def update_chart(self, config: ChartWizardConfig, output: str) -> None:
        """Update chart configuration and output."""
        self.chart_config = config
        self.chart_output = output

    def clear_chart(self) -> None:
        """Clear chart state."""
        self.chart_config = None
        self.chart_output = None

    def reset(self) -> None:
        """Reset entire session to initial state."""
        self.sql = ""
        self.sql_modified = False
        self.clear_results()
        self.clear_chart()
        self.mode = "sql"

    def can_create_chart(self) -> bool:
        """Check if we can create a chart (have results)."""
        return self.has_results and len(self.columns) > 0

    def needs_rerun(self) -> bool:
        """Check if SQL has been modified since last run."""
        return self.sql_modified and len(self.sql) > 0
```

### Session Lifecycle

```python
def handle_analysis_command() -> None:
    """Handle /analysis command - enter analysis mode."""

    # Create new session
    session = AnalysisSession()

    # Show welcome
    _show_analysis_welcome()

    # Main loop
    while True:
        if session.mode == "sql":
            action = _handle_sql_mode(session)
        elif session.mode == "results":
            action = _handle_results_mode(session)
        elif session.mode == "chart":
            action = _handle_chart_mode(session)

        # Handle mode transitions
        if action == "quit":
            break
        elif action == "reset":
            session.reset()
            session.mode = "sql"
```

### Mode Transitions

```
          ┌─────────┐
          │   SQL   │◄─────┐
          └────┬────┘      │
               │           │
         execute query     │
               │       edit sql
               ▼           │
          ┌─────────┐      │
          │ Results │──────┤
          └────┬────┘      │
               │           │
        create chart       │
               │       edit sql
               ▼           │
          ┌─────────┐      │
          │  Chart  │──────┘
          └─────────┘
```

## Testing

### Unit Tests

Create `tests/unit/commands/test_analysis_session.py`:

```python
def test_session_initial_state():
    """Test session starts in SQL mode with empty state."""
    session = AnalysisSession()
    assert session.mode == "sql"
    assert session.sql == ""
    assert not session.has_results
    assert session.chart_config is None

def test_update_sql_marks_modified():
    """Test updating SQL marks it as modified."""
    session = AnalysisSession()
    session.update_sql("SELECT * FROM transactions")
    assert session.sql_modified is True
    assert session.needs_rerun() is True

def test_update_results_clears_modified_flag():
    """Test updating results clears modified flag."""
    session = AnalysisSession()
    session.update_sql("SELECT * FROM transactions")
    session.update_results(["id"], [[1], [2]])
    assert session.sql_modified is False
    assert session.has_results is True

def test_can_create_chart_requires_results():
    """Test chart creation requires results."""
    session = AnalysisSession()
    assert session.can_create_chart() is False

    session.update_results(["col1"], [[1]])
    assert session.can_create_chart() is True

def test_reset_clears_all_state():
    """Test reset returns to initial state."""
    session = AnalysisSession()
    session.update_sql("SELECT 1")
    session.update_results(["x"], [[1]])
    session.update_chart(ChartWizardConfig(...), "chart output")

    session.reset()

    assert session.sql == ""
    assert not session.has_results
    assert session.chart_config is None
    assert session.mode == "sql"

def test_mode_transitions():
    """Test valid mode transitions."""
    session = AnalysisSession()

    # SQL → Results
    session.mode = "results"
    assert session.mode == "results"

    # Results → Chart
    session.mode = "chart"
    assert session.mode == "chart"

    # Chart → SQL
    session.mode = "sql"
    assert session.mode == "sql"
```

## Acceptance Criteria

- [ ] AnalysisSession class created with all state fields
- [ ] Methods for updating SQL, results, and chart
- [ ] Mode tracking (sql, results, chart)
- [ ] `needs_rerun()` detects when SQL has changed
- [ ] `can_create_chart()` validates state for charting
- [ ] `reset()` clears all state back to initial
- [ ] Unit tests for all state transitions
- [ ] Session is isolated (no global state)

## ⚠️ Architecture Checkpoint

**BEFORE IMPLEMENTATION:**
Review `docs/internal/architecture.md` - State management patterns

**Key Questions:**
- Is `AnalysisSession` domain logic or presentation logic?
- Should it live in `app/` or `commands/`?
- Does it need to go through the service layer?

**Decision:** This is **presentation state** (CLI-specific, not domain).
- Lives in `src/treeline/commands/analysis_session.py`
- Simple dataclass, no business rules
- Used only by CLI command handlers
- No service layer interaction needed (just holds UI state)

**Red Flags to Avoid:**
❌ Don't put business logic in session (e.g., transaction deduplication)
❌ Don't make session talk to database/services directly
❌ Don't store domain objects (Transaction, Account) - only primitives/DTOs

**Good Patterns:**
✅ Simple dataclass with clear state transitions
✅ Immutable where possible (use `replace()` for updates)
✅ No dependencies on services/repos
✅ Pure state container

**AFTER IMPLEMENTATION:**
Use architecture-guardian agent to verify:
```
Review src/treeline/commands/analysis_session.py:
- Ensure it's just state (no business logic)
- Verify no service/repository imports
- Check it only stores presentation data
```

## Notes

- Session is NOT persisted between invocations (fresh start each time)
- Could add persistence later if users request it
- State management is foundation for modal navigation (next task)
- Keep session immutable where possible for predictability
- **Architecture:** Presentation state, not domain state
