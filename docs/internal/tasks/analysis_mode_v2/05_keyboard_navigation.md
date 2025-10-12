# Task 05: Keyboard Navigation

**Status:** Not Started
**Dependencies:** Task 04
**Estimated Time:** 1 hour

## Objective

Implement complete keyboard navigation and event handling for analysis mode.

## Requirements

1. F5 - Execute SQL query
2. c - Create chart (when results exist)
3. Tab - Toggle between results view and chart view
4. s - Save query (or save chart when viewing chart)
5. r - Reset (clear results/chart, keep SQL)
6. q - Quit analysis mode
7. Context-aware shortcuts (only show valid options)

## Implementation

**Use:** `readkey()` or `prompt_toolkit` key bindings

**Event loop:**
```python
while True:
    render_view(session)
    key = get_keypress()

    if key == "F5":
        execute_query()
        session.view_mode = "results"  # Show results after execution
    elif key == "c" and session.has_results():
        create_chart()
        session.view_mode = "chart"  # Show chart after creation
    elif key == "Tab" and session.has_chart():
        session.toggle_view()  # Switch between results and chart
    elif key == "s":
        if session.view_mode == "chart":
            save_chart()
        else:
            save_query()
    elif key == "r":
        session.reset()
    elif key == "q":
        break
    # ... etc
```

## Acceptance Criteria

- [ ] All keyboard shortcuts work
- [ ] Context-aware (invalid shortcuts ignored)
- [ ] Clean exit on 'q'
- [ ] Tests cover each key action
