# Task 05: Keyboard Navigation

**Status:** Complete
**Dependencies:** Task 04
**Estimated Time:** 1 hour

## Objective

Implement complete keyboard navigation and event handling for analysis mode.

## Requirements

1. Ctrl+Enter - Execute SQL query
2. g - Create/edit chart (when results exist)
3. Tab - Switch focus between SQL editor and data panel
4. v - Toggle between results view and chart view
5. s - Save query/chart (in-TUI prompt)
6. r - Reset (clear results/chart, keep SQL)
7. Ctrl+C - Quit analysis mode
8. Context-aware shortcuts (only show valid options)
9. Arrow keys for scrolling (context-aware based on focus)

## Implementation

**Used:** `prompt_toolkit` Application with `KeyBindings` and `Condition` filters

**Key Design Decisions:**

1. **Focus-based navigation**: Tab switches focus between SQL editor and data panel. Arrow keys behave differently based on which panel is focused:
   - SQL editor focused: arrows navigate/edit SQL text
   - Data panel focused: arrows scroll results/chart

2. **In-TUI wizards**: Chart creation and save use in-TUI prompts in the data panel (no context switching)

3. **View modes**:
   - `results`: Show query results
   - `chart`: Show created chart
   - `wizard`: Show chart wizard UI
   - `save_query`: Show query save prompt
   - `save_chart`: Show chart save prompt

4. **Auto-focus**: After query execution, focus automatically switches to data panel for immediate scrolling

## Acceptance Criteria

- [x] All keyboard shortcuts work
- [x] Context-aware (invalid shortcuts ignored using Condition filters)
- [x] Clean exit on Ctrl+C
- [x] Tests cover query execution logic
- [x] Tab-based focus switching prevents keybinding conflicts
- [x] In-TUI save functionality (no exit required)
- [x] 194 tests passing
