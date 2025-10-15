# Task 07: Create Charts and Queries Browser TUIs

## Priority
**LOW** - Nice-to-have TUIs for managing saved items

## Objective
Create Textual TUIs for browsing, loading, and managing saved charts and queries.

## Part A: `treeline queries`

### TUI Design
- List all saved queries
- Preview SQL on selection
- Load query (opens in analysis mode)
- Delete query
- Rename query

### Implementation
```python
class QueriesBrowserScreen(Screen):
    """Browse saved queries."""

    BINDINGS = [
        Binding("enter", "load_query", "Load"),
        Binding("d", "delete_query", "Delete"),
        Binding("r", "rename_query", "Rename"),
    ]

    def compose(self):
        yield Header()
        yield ListView(id="query_list")  # List of queries
        yield Static(id="preview")        # SQL preview
        yield Footer()

@app.command(name="queries")
def queries_command() -> None:
    """Browse and manage saved queries."""
    require_auth()
    from treeline.commands.queries_textual import QueriesBrowserApp
    app = QueriesBrowserApp()
    app.run()
```

## Part B: `treeline charts`

### TUI Design
- List all saved charts
- Preview chart config on selection
- Load chart (opens in analysis mode with chart)
- Delete chart
- Rename chart

### Implementation
```python
class ChartsBrowserScreen(Screen):
    """Browse saved charts."""

    BINDINGS = [
        Binding("enter", "load_chart", "Load"),
        Binding("d", "delete_chart", "Delete"),
        Binding("r", "rename_chart", "Rename"),
    ]

    def compose(self):
        yield Header()
        yield ListView(id="chart_list")
        yield Static(id="preview")  # Config preview
        yield Footer()

@app.command(name="charts")
def charts_command() -> None:
    """Browse and manage saved charts."""
    require_auth()
    from treeline.commands.charts_textual import ChartsBrowserApp
    app = ChartsBrowserApp()
    app.run()
```

## Service Layer

Use existing storage abstractions:
- `container.query_storage()`
- `container.chart_storage()`

No new service methods needed.

## Success Criteria
- [ ] Can browse saved queries/charts
- [ ] Can preview before loading
- [ ] Can delete items
- [ ] Can load into analysis mode
- [ ] Consistent UX with other TUIs

## Files to Create
- `src/treeline/commands/queries_textual.py`
- `src/treeline/commands/charts_textual.py`

## Files to Modify
- `src/treeline/cli.py` - Add commands

## Files to Mark for Deletion (later)
- Old `/queries` and `/chart` handlers (task 10)
- `commands/saved_queries.py` - Keep only helper functions
- `commands/chart.py` - Old implementation
