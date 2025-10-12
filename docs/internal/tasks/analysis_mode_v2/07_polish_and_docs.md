# Task 07: Polish and Documentation

**Status:** Not Started
**Dependencies:** Task 05 (Task 06 histogram helper was skipped)
**Estimated Time:** 1-2 hours

## Objective

Final polish, help overlay, and documentation updates.

## Requirements

### Polish
1. ✅ Help overlay ('?' key shows all shortcuts)
2. Loading indicators for query execution (optional)
3. Better error messages (query failures, invalid chart configs)
4. Smooth panel transitions (already good)
5. Terminal size validation (optional)

### Documentation
1. Update `/help` command with analysis mode
2. Update `docs/external/landing_page.md` with analysis mode examples
3. Update `docs/external/reference/slash_commands.md`
4. Migration guide (how to use analysis vs sql vs chart)

## Implementation

### Help Overlay
Press '?' to show:
```
╭─ Analysis Mode Shortcuts ──────────────────────────╮
│ SQL Execution                                       │
│   Ctrl+Enter  - Execute query                       │
│                                                     │
│ Navigation                                          │
│   Tab         - Switch focus (SQL ↔ Data panel)    │
│   ↑↓←→        - Context-aware (edit SQL or scroll)  │
│                                                     │
│ Data Panel (when focused)                           │
│   ↑↓          - Scroll results vertically           │
│   Shift+←→    - Scroll columns horizontally         │
│   v           - Toggle results ↔ chart view         │
│                                                     │
│ Charts                                              │
│   g           - Create/edit chart (wizard)          │
│   s           - Save query or chart                 │
│                                                     │
│ Actions                                             │
│   r           - Reset (clear results/chart)         │
│   Ctrl+C      - Exit analysis mode                  │
│   ?           - Show this help                      │
╰─────────────────────────────────────────────────────╯
```

### Current Keybindings (as implemented)
- **Ctrl+Enter**: Execute SQL query (async, auto-focus to data panel)
- **Tab**: Switch focus between SQL editor and data panel
- **v**: Toggle between results and chart view (when data panel focused)
- **g**: Create/edit chart via in-TUI wizard
- **s**: Save query (in-TUI prompt)
- **r**: Reset (clear results/chart, keep SQL)
- **Arrows**: Context-aware scrolling
  - SQL editor focused: navigate/edit text
  - Data panel focused, results view: ↑↓ scroll rows, Shift+←→ scroll columns
  - Data panel focused, chart view: ↑↓ scroll chart content
- **Wizard mode** (when creating chart):
  - 1-4: Select chart type or column
  - Esc: Cancel wizard
- **Save mode** (when saving):
  - Letters/numbers/_/-: Type name
  - Enter: Confirm save
  - Esc: Cancel save
- **Ctrl+C**: Exit analysis mode

### Documentation Updates

1. **`src/treeline/commands/help.py`**: Add analysis mode section
2. **`docs/external/reference/slash_commands.md`**: Add `/analysis` command with full keybinding reference
3. **`docs/external/landing_page.md`**: Add analysis mode showcase example

### Migration Guide

**When to use each command:**
- `/sql` - Quick one-off queries, saved queries with autocomplete
- `/chart` - Create standalone charts from command line
- `/analysis` - **Interactive workspace** for exploration: write SQL, view results, create charts, iterate

Analysis mode provides a Jupyter-like experience where everything stays visible and you can fluidly move between SQL editing, results viewing, and chart creation.

## Acceptance Criteria

- [ ] '?' help overlay implemented
- [ ] Help command updated with analysis mode
- [ ] slash_commands.md fully documented
- [ ] landing_page.md has analysis mode example
- [ ] Error messages reviewed (already decent)
- [ ] All 194+ tests passing

## Notes

**Chart wizard implementation**: Uses in-TUI prompts in data panel, step-by-step:
1. Select chart type (1=bar, 2=line, 3=scatter, 4=histogram)
2. Select X column (number keys)
3. Select Y column (number keys)

**Save implementation**: In-TUI prompt shows in data panel, user types name, Enter saves to `~/.treeline/queries/` or `~/.treeline/charts/`

**Focus management**: Critical design - Tab switches focus, arrow keys work differently based on focus. This prevents keybinding conflicts with SQL editing.
