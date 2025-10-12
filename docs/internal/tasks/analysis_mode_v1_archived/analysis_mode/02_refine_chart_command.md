# Refine /chart Command as Chart Browser

## Problem

Current `/chart` command lists charts then exits, requiring users to invoke it again with a chart name. This feels disconnected and requires typing chart names without autocomplete.

Additionally, there's no clear guidance on how to create or edit charts.

## Solution

Make `/chart` an **interactive browser mode** for saved charts, similar to how `/sql` is an interactive editor.

```bash
> /chart

╭────────── Saved Charts ──────────╮
│                                  │
│  📊 Chart Browser                │
│                                  │
│  Type name or Tab to browse:     │
│                                  │
│  • monthly_spending              │
│  • category_breakdown            │
│  • income_vs_expense             │
│                                  │
│  (No charts? Use /sql to create) │
│                                  │
╰──────────────────────────────────╯

Chart name (or [n]ew, [q]uit): _
```

## Implementation Details

### Update `chart.py`

**Current structure:**
```python
def handle_chart_command(chart_name: str | None = None):
    if not chart_name:
        # List charts and exit
        return
    # Run the chart
```

**New structure:**
```python
def handle_chart_command(chart_name: str | None = None):
    if chart_name:
        # Direct invocation: /chart monthly_spending
        _run_chart(chart_name)
        return

    # Interactive browser mode
    _chart_browser_mode()

def _chart_browser_mode():
    """Interactive chart browser with autocomplete."""
    # Show header
    # List charts
    # Loop: prompt for chart name with autocomplete
    # Run chart, then offer: [r]un again, [e]dit, [d]elete, [q]uit
```

### Chart Browser Features

1. **Autocomplete for chart names** (like saved query autocomplete in `/sql`)
2. **Post-run actions menu**:
   ```
   [Chart displayed]

   [r]un again  [e]dit config  [d]elete  [n]ew  [q]uit
   >
   ```

3. **Edit option** shows path and hints:
   ```
   > e

   Chart config: ~/.treeline/charts/monthly_spending.tl

   To modify the chart:
   - Edit the .tl file directly, or
   - Use /sql or /analysis to recreate

   Open in editor? [y/n]: _
   ```

4. **New chart option**:
   ```
   > n

   Creating new charts:

   Use /sql to run a query, then create a chart from the results.
   Or use /analysis for a fluid workspace.

   [Press enter to continue]
   ```

### Autocomplete Implementation

Create `ChartNameCompleter` (similar to `SavedQueryCompleter`):

```python
class ChartNameCompleter(Completer):
    """Completer for chart names."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        store = ChartConfigStore(get_charts_dir())
        charts = store.list()

        for chart_name in charts:
            if chart_name.lower().startswith(text.lower()):
                yield Completion(
                    chart_name,
                    start_position=-len(text),
                    display=f"📊 {chart_name}",
                )
```

### Update CLI Integration

Ensure `/chart` can be invoked both ways:
- `/chart` → interactive browser mode
- `/chart monthly_spending` → direct run (backward compatible)

## Testing

### Unit Tests

Create `tests/unit/commands/test_chart_browser.py`:

```python
def test_chart_command_without_name_enters_browser():
    """Test /chart enters browser mode."""

def test_chart_command_with_name_runs_directly():
    """Test /chart name runs chart immediately."""

def test_chart_browser_autocomplete():
    """Test chart name autocomplete works."""

def test_chart_browser_edit_shows_guidance():
    """Test edit option shows helpful message."""

def test_chart_browser_new_shows_guidance():
    """Test new option explains how to create charts."""
```

### Manual Testing

```bash
> /chart

📊 Chart Browser

Type name or Tab: m[TAB]
> monthly_spending

[Chart runs]

[r]un again [e]dit [d]elete [n]ew [q]uit
> e

Chart config: ~/.treeline/charts/monthly_spending.tl

To modify: use /sql or /analysis
Open in editor? y

[Opens in $EDITOR]

> n

Creating new charts:
Use /sql to run a query, then create chart...

> q
```

## Acceptance Criteria

- [ ] `/chart` without args enters interactive browser mode
- [ ] `/chart name` runs chart directly (backward compatible)
- [ ] Chart name autocomplete works (Tab completion)
- [ ] Post-run menu offers: run again, edit, delete, new, quit
- [ ] Edit option shows config path and helpful guidance
- [ ] New option explains to use `/sql` or `/analysis`
- [ ] Browser mode loops until user quits
- [ ] Empty charts list shows helpful "Use /sql to create" message
- [ ] Unit tests for browser mode
- [ ] Existing chart tests still pass

## Notes

- This makes `/chart` consistent with `/sql` pattern (both are interactive modes)
- Clear separation: `/chart` = browse/run, `/sql` = create/edit
- Sets up for `/analysis` which combines both
