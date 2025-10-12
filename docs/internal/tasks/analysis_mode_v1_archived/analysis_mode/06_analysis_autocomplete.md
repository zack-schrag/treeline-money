# Analysis Mode: Enhanced Autocomplete

## Problem

To make `/analysis` mode feel truly integrated, we need autocomplete support for:
1. Saved queries in SQL mode
2. Column names when configuring charts
3. Saved charts when referencing them

This creates a smooth, discoverable experience.

## Solution

Implement context-aware autocomplete that adapts to the current mode and input context.

## Implementation Details

### SQL Mode Autocomplete

**Already exists** - leverage `SavedQueryCompleter` from existing `/sql` implementation:

```python
# In _handle_sql_mode()
prompt_session = PromptSession(
    lexer=PygmentsLexer(SqlLexer),
    multiline=True,
    key_bindings=bindings,
    completer=SavedQueryCompleter(),  # Reuse existing
)
```

This gives Tab completion for saved queries.

### Chart Configuration Autocomplete

Create `ChartColumnCompleter` for column name suggestions:

```python
"""Autocomplete for chart configuration."""

from prompt_toolkit.completion import Completer, Completion


class ChartColumnCompleter(Completer):
    """Completer for column names during chart configuration."""

    def __init__(self, columns: list[str]):
        self.columns = columns

    def get_completions(self, document, complete_event):
        """Generate completions for column names."""
        text = document.text_before_cursor.lower()

        for col in self.columns:
            if col.lower().startswith(text):
                yield Completion(
                    col,
                    start_position=-len(text),
                    display=f"📊 {col}",
                )
```

Usage in chart wizard:

```python
def _prompt_chart_configuration(
    columns: list[str],
    rows: list[list],
    sql: str
) -> ChartWizardConfig | None:
    """Prompt for chart configuration with autocomplete."""

    # ... chart type selection ...

    # Column selection with autocomplete
    column_completer = ChartColumnCompleter(columns)
    session = PromptSession(completer=column_completer)

    x_column = session.prompt("X column: ")

    if chart_type != "histogram":
        y_column = session.prompt("Y column: ")
```

### Chart Name Autocomplete

When saving charts, suggest existing chart names:

```python
class ChartNameCompleter(Completer):
    """Completer for chart names when saving."""

    def __init__(self):
        from treeline.commands.chart_config import ChartConfigStore, get_charts_dir
        self.store = ChartConfigStore(get_charts_dir())

    def get_completions(self, document, complete_event):
        """Generate completions for chart names."""
        text = document.text_before_cursor.lower()
        charts = self.store.list()

        for chart_name in charts:
            if chart_name.lower().startswith(text):
                yield Completion(
                    chart_name,
                    start_position=-len(text),
                    display=f"📊 {chart_name}",
                    display_meta="(overwrite)",
                )
```

### Context Help Display

Show available columns prominently when configuring chart:

```python
def _prompt_chart_configuration(...):
    console.print(f"\n[{theme.muted}]Available columns:[/{theme.muted}]")
    for i, col in enumerate(columns, 1):
        console.print(f"  {i}. [{theme.emphasis}]{col}[/{theme.emphasis}]")
    console.print()

    # Then prompt with autocomplete
    column_completer = ChartColumnCompleter(columns)
    session = PromptSession(completer=column_completer)
    x_column = session.prompt("X column (Tab to browse): ")
```

### Keyboard Shortcuts Help

Add a `?` command in each mode to show available shortcuts:

```python
# In SQL mode
SQL> ?

Keyboard Shortcuts:
  F5          - Execute query
  Tab         - Browse saved queries
  Ctrl+C      - Cancel
  q           - Quit analysis mode

# In Results mode
Results> ?

Available Actions:
  c  - Create chart from results
  e  - Edit SQL
  s  - Save query
  q  - Quit
```

## Testing

### Unit Tests

Create `tests/unit/commands/test_analysis_autocomplete.py`:

```python
def test_column_completer_suggests_matching_columns():
    """Test column autocomplete."""
    completer = ChartColumnCompleter(["amount", "date", "category"])

    # Test prefix matching
    suggestions = list(completer.get_completions(..., "am"))
    assert "amount" in [s.text for s in suggestions]

def test_column_completer_case_insensitive():
    """Test case insensitive matching."""
    completer = ChartColumnCompleter(["Amount", "Date"])
    suggestions = list(completer.get_completions(..., "am"))
    assert len(suggestions) > 0

def test_chart_name_completer_suggests_existing():
    """Test chart name suggestions."""
    # Setup: create some test charts
    # Test: type partial name, verify suggestions
```

### Manual Testing

```bash
> /analysis

SQL> sel[Tab]
SQL> SELECT * FROM transactions LIMIT 10
[F5]

Results> c

Available columns:
  1. transaction_id
  2. amount
  3. category

X column (Tab to browse): am[Tab]
X column: amount

Y column: cat[Tab]
Y column: category

Save chart? y
Chart name: my[Tab]
  📊 monthly_spending (overwrite)
  📊 my_old_chart (overwrite)
```

## Acceptance Criteria

- [ ] SQL mode has saved query autocomplete (Tab)
- [ ] Chart column selection has autocomplete for column names
- [ ] Chart name saving suggests existing charts
- [ ] Available columns displayed before prompting
- [ ] `?` command shows keyboard shortcuts in each mode
- [ ] Tab completion works consistently
- [ ] Case-insensitive matching for user convenience
- [ ] Unit tests for all completers
- [ ] Manual testing confirms smooth autocomplete UX

## Notes

- Autocomplete should be helpful, not intrusive
- Tab key is the universal "help me complete this" signal
- Visual feedback (display metadata) helps users understand options
- This is polish, but important polish that makes mode feel professional
