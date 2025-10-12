# Analysis Mode v2 - Next Session Guide

## Status Summary

**Current Status**: Analysis mode core functionality is **COMPLETE** and committed. All 194 tests passing.

**What's Working**:
- Full-screen dual-panel TUI (SQL editor + data panel)
- Tab-based focus management (prevents keybinding conflicts)
- Ctrl+Enter executes queries asynchronously
- Results table with column windowing and scrolling
- In-TUI chart wizard (no exit required)
- In-TUI save functionality for queries and charts
- Context-aware keyboard shortcuts using prompt_toolkit Conditions
- Selection highlighting matching /tag mode theme (sage green #44755a)

**Last Commit**: "Complete analysis mode with in-TUI chart wizard and save functionality"

## Remaining Work

### Task 07: Polish and Documentation (1-2 hours)
**File**: [07_polish_and_docs.md](07_polish_and_docs.md)

**Subtasks**:
1. **Help overlay** ('?' key) - Show all keybindings in a formatted overlay
2. **Update `/help` command** - Add analysis mode section to [src/treeline/commands/help.py](../../../src/treeline/commands/help.py)
3. **Update slash commands docs** - Add `/analysis` to [docs/external/reference/slash_commands.md](../../external/reference/slash_commands.md)
4. **Update landing page** - Add analysis mode example to [docs/external/landing_page.md](../../external/landing_page.md)
5. **Review error messages** - Ensure query failures and chart errors are user-friendly

**Current Keybindings to Document**:
```
Ctrl+Enter  - Execute SQL query
Tab         - Switch focus (SQL editor ↔ data panel)
↑↓←→        - Context-aware (edit SQL or scroll results/chart)
Shift+←→    - Scroll columns horizontally (in results view)
v           - Toggle results ↔ chart view
g           - Create/edit chart (in-TUI wizard)
s           - Save query or chart (in-TUI prompt)
r           - Reset (clear results/chart, keep SQL)
Ctrl+C      - Exit analysis mode
?           - Show help overlay (TO BE IMPLEMENTED)
```

### Task 08: Load Saved Items (2-3 hours) - NEW
**File**: [08_load_saved_items.md](08_load_saved_items.md)

**Goal**: Allow loading saved queries/charts while in analysis mode (user request: "fluid experience, close to jupyter notebook")

**Design**:
- Press 'l' → Load menu: "[q]uery or [c]hart?"
- Press 'q' → Browse queries list (from ~/.treeline/queries/)
- Press 'c' → Browse charts list (from ~/.treeline/charts/)
- Arrow keys navigate, Enter loads, Esc cancels
- All stays within TUI (no exit)

**Implementation**: Add `browse_query` and `browse_chart` view modes to AnalysisSession domain model

## Key Files

### Main Implementation
- [src/treeline/commands/analysis.py](../../../src/treeline/commands/analysis.py) - Main analysis mode (810 lines)
- [src/treeline/domain.py](../../../src/treeline/domain.py) - AnalysisSession domain model

### Tests
- [tests/unit/commands/test_analysis_sql_editor.py](../../../../tests/unit/commands/test_analysis_sql_editor.py)
- [tests/smoke/test_analysis_workflow.py](../../../../tests/smoke/test_analysis_workflow.py) (if exists)

### Documentation
- [src/treeline/commands/help.py](../../../src/treeline/commands/help.py)
- [docs/external/reference/slash_commands.md](../../external/reference/slash_commands.md)
- [docs/external/landing_page.md](../../external/landing_page.md)

### Reference Implementation
- [src/treeline/commands/tag.py](../../../src/treeline/commands/tag.py) - Similar modal view pattern
- [src/treeline/commands/sql.py](../../../src/treeline/commands/sql.py) - Saved query autocomplete pattern
- [src/treeline/commands/chart_wizard.py](../../../src/treeline/commands/chart_wizard.py) - Chart creation logic

## Architecture Patterns Used

**Domain Model**: `AnalysisSession` (dataclass) tracks all state
- `sql`: Current SQL text
- `results`, `columns`: Query results
- `chart`: Created chart
- `view_mode`: Current view (results/chart/wizard/save_query/save_chart)
- `scroll_offset`, `column_offset`, `selected_row`: Scrolling state
- `wizard_*`: Chart wizard state
- `chart_scroll_offset`: Chart vertical scrolling
- `save_input_buffer`: Save prompt buffer

**CLI Layer**: Thin presentation using prompt_toolkit
- `HSplit` layout for panels
- `BufferControl` for SQL editor (with PygmentsLexer for syntax highlighting)
- `FormattedTextControl` for data panel (focusable=True)
- `KeyBindings` with `Condition` filters for context-aware shortcuts
- `has_focus()` filters to prevent keybinding conflicts

**Service Layer**: Delegates to existing services
- `db_service.execute_query()` for SQL execution
- `save_query()`, `load_chart_config()` helper functions

## Critical Design Decisions

### Focus Management (Solved keybinding conflicts)
**Problem**: Arrow keys needed for both SQL editing AND results scrolling

**Solution**: Tab switches focus between panels
- SQL editor focused: arrows work for text navigation
- Data panel focused: arrows work for scrolling
- Uses `has_focus(window)` Condition filters

### In-TUI Wizards (Maintains fluid experience)
**Problem**: User rejected exiting TUI for chart creation or saving

**Solution**: View modes for wizards/prompts that render in data panel
- Chart wizard: Step-by-step selections (chart type → X column → Y column)
- Save prompt: Type name, Enter saves, shows brief success message

### Column Windowing (Fixed "smushed" results)
**Problem**: Wide tables with many columns looked unreadable

**Solution**: Calculate which columns fit terminal width, show indicators (◀ ▶)
- `column_offset` tracks horizontal scroll position
- Dynamically calculates visible columns based on terminal width
- Shift+←→ for horizontal scrolling

## User Feedback Context

**User's Vision**: "Jupyter-like experience", "lots of power", "fluid workflow"

**Key Requirements**:
- Everything stays in TUI (no context switching)
- SQL and results always visible
- Easy to iterate: query → results → chart → edit → repeat
- Save/load should be seamless

**Rejected Approaches**:
- Auto-chart detection (too fragile)
- Exiting TUI for wizard/save (breaks fluid experience)
- Various keybinding attempts (Ctrl+arrows don't work, vim keys conflict)

## Quick Start Commands

```bash
# Run analysis mode
uv run python -m treeline.cli.main analysis

# Run unit tests
uv run pytest tests/unit -v

# Run smoke tests
uv run pytest tests/smoke -v

# Run all tests
uv run pytest

# Check architecture compliance
# (Use architecture-guardian agent if making structural changes)
```

## Suggested Next Session Prompt

```
Continue implementing analysis_mode_v2 Task 07 (polish and documentation).

Current status: Core analysis mode is complete with dual-panel TUI, chart wizard,
and save functionality. All 194 tests passing. Last commit: "Complete analysis mode
with in-TUI chart wizard and save functionality"

Next steps:
1. Implement '?' help overlay showing all keybindings (see Task 07 for detailed layout)
2. Update /help command with analysis mode section
3. Update docs/external/reference/slash_commands.md with /analysis command
4. Update docs/external/landing_page.md with analysis mode example

Key files to review:
- docs/internal/tasks/analysis_mode_v2/07_polish_and_docs.md (detailed requirements)
- docs/internal/tasks/analysis_mode_v2/README.md (overview)
- src/treeline/commands/analysis.py (main implementation, 810 lines)
- src/treeline/commands/help.py (to update)

Follow TDD: write tests first, then implement. Use TodoWrite to track progress.
```

## Additional Notes

- **Task 06 (histogram helper)** was explicitly skipped - use DuckDB's histogram function instead
- **Smoke test** for full chart workflow was in progress but not completed (see todo list)
- All code follows hexagonal architecture principles (thin CLI, business logic in services)
- Sage green theme color (#44755a) matches /tag mode for consistency
