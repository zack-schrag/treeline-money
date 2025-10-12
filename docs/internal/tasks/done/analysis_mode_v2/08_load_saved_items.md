# Task 08: Load Saved Queries and Charts

**Status:** ✅ Complete
**Dependencies:** Task 07
**Estimated Time:** 2-3 hours

## Objective

Allow users to load previously saved queries and charts while in analysis mode, maintaining the fluid workflow experience.

## Context

User feedback (message #26):
> "I should be able to load saved queries and/or saved charts while in analysis mode... The goal is for this to be a really fluid experience. I am going to be doing lots of analysis and queries, should be able to fluidly move between them all (which I can now), easily save, load, and edit both queries and charts. We want users to have lots of power here. It may not be as powerful as a jupyter notebook, for example, but it will feel like a close second"

## Requirements

1. In-TUI browser for saved queries (similar to `/sql` command autocomplete)
2. In-TUI browser for saved charts
3. Load query: populate SQL editor, clear results/chart
4. Load chart: populate chart view, keep or clear results (TBD)
5. Keyboard shortcuts for accessing browsers
6. Maintain fluid TUI experience (no exiting)

## Design Considerations

### Option A: Separate Browse Modes
- Press 'l' → show "Load what? [q]uery or [c]hart?"
- Press 'q' → enter browse_query mode (list all .sql files)
- Press 'c' → enter browse_chart mode (list all .tl files)
- Arrow keys to navigate list, Enter to load, Esc to cancel

### Option B: Unified Browser
- Press 'l' → show combined list with type indicators
- Example: "📄 monthly_spending.sql", "📊 expense_trends.tl"
- Arrow keys to navigate, Enter to load (detect type), Esc to cancel

### Option C: Separate Keys
- Press 'q' → browse queries
- Press 'c' → browse charts (conflicts with current chart creation)
- May need to change existing 'g' for chart to something else

## Recommended Approach

**Option A** with separate browse modes:
- Clearer user intent (they know what they want to load)
- Easier to implement (two similar but separate flows)
- No keybinding conflicts
- Follows existing pattern (separate save_query vs save_chart modes)

## Implementation Plan

### 1. New View Modes
Add to AnalysisSession domain model:
```python
view_mode: str  # Add: "browse_query" and "browse_chart"
browse_items: list[str] = []  # List of available items to load
browse_selected_index: int = 0  # Currently selected item in browser
```

### 2. Keybindings
```python
# Press 'l' to initiate load
@kb.add("l", filter=data_focused & ~wizard_mode & ~save_mode)
def load_items(event):
    session.view_mode = "load_menu"  # Show "Load [q]uery or [c]hart?"
    event.app.invalidate()

# In load_menu mode, press 'q' or 'c'
@kb.add("q", filter=load_menu_mode)
def browse_queries(event):
    session.view_mode = "browse_query"
    session.browse_items = list_saved_queries()  # From ~/.treeline/queries/
    session.browse_selected_index = 0
    event.app.invalidate()

@kb.add("c", filter=load_menu_mode)
def browse_charts(event):
    session.view_mode = "browse_chart"
    session.browse_items = list_saved_charts()  # From ~/.treeline/charts/
    session.browse_selected_index = 0
    event.app.invalidate()
```

### 3. Browser UI
Similar to wizard UI pattern, render in data panel:
```python
def _format_browser_ui(session: AnalysisSession, browser_type: str) -> list:
    result = []
    result.append(("bold #44755a", f"Load {browser_type.title()}"))
    result.append(("", "\n\n"))

    if not session.browse_items:
        result.append(("class:muted", f"No saved {browser_type}s found"))
        result.append(("", "\n\n"))
        result.append(("class:muted", "Press Esc to cancel"))
        return result

    for i, item in enumerate(session.browse_items):
        if i == session.browse_selected_index:
            result.append(("bold bg:#44755a fg:white", f"→ {item}"))
        else:
            result.append(("", f"  {item}"))
        result.append(("", "\n"))

    result.append(("", "\n"))
    result.append(("class:muted", "↑↓ to navigate, Enter to load, Esc to cancel"))
    return result
```

### 4. Load Actions
```python
@kb.add("enter", filter=browse_query_mode)
def load_selected_query(event):
    if session.browse_items:
        query_name = session.browse_items[session.browse_selected_index]
        query_path = Path.home() / ".treeline" / "queries" / f"{query_name}.sql"
        session.sql = query_path.read_text()
        session.results = None
        session.columns = None
        session.chart = None
        session.view_mode = "results"
        session.browse_items = []
        # Focus SQL editor so user can edit immediately
        event.app.layout.focus(sql_window)
    event.app.invalidate()

@kb.add("enter", filter=browse_chart_mode)
def load_selected_chart(event):
    if session.browse_items:
        chart_name = session.browse_items[session.browse_selected_index]
        chart_config = load_chart_config(chart_name)
        # Execute the query from the chart config
        asyncio.ensure_future(_load_chart_with_query(session, chart_config))
        session.browse_items = []
        session.view_mode = "chart"
    event.app.invalidate()
```

### 5. Helper Functions
Leverage existing code:
- `list_saved_queries()` - scan `~/.treeline/queries/*.sql`
- `list_saved_charts()` - scan `~/.treeline/charts/*.tl`
- `load_chart_config(name)` - from `chart_config.py`

## Acceptance Criteria

- [x] 'l' key opens load menu
- [x] 'q' and 'c' keys open respective browsers
- [x] Arrow keys navigate browser list
- [x] Enter loads selected item
- [x] Esc cancels browser and returns to previous view
- [x] Loading query populates SQL editor and clears results/chart
- [x] Loading chart executes query and displays chart
- [x] Empty list shows helpful message
- [x] All stays within TUI (no exit)
- [x] Focus management works correctly
- [x] Tests pass - all 198 unit tests passing

## Testing Strategy

### Unit Tests
- Test browser list population
- Test selection index navigation
- Test load query updates session correctly
- Test load chart updates session correctly

### Smoke Tests
- Full workflow: save query → browse → load → edit → save again
- Full workflow: create chart → save → browse → load
- Edge cases: empty lists, invalid files

## Future Enhancements (Out of Scope)

- Search/filter saved items by name
- Delete saved items from browser
- Preview query/chart before loading
- Recent items shortcut (load last 5 used)
- Organize items into folders/tags
