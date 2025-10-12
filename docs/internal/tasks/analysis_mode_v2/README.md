# Analysis Mode - Modal View Implementation

**Approach:** Full-screen modal view (like `/tag` mode)
**Proposal:** [analysis_mode_v2.md](../../proposals/analysis_mode_v2.md)

## Overview

Building an integrated workspace for fluid data exploration with:
- SQL editor (bottom panel, always visible)
- Results table (middle panel, scrollable)
- Chart display (top panel, conditional)
- Keyboard shortcuts (header, context-aware)

## Task Breakdown

1. **[01_build_analysis_layout.md](01_build_analysis_layout.md)** - Core modal view structure
2. **[02_sql_editor_panel.md](02_sql_editor_panel.md)** - Multiline SQL editor integration
3. **[03_results_panel.md](03_results_panel.md)** - Results table display and scrolling
4. **[04_chart_panel.md](04_chart_panel.md)** - Chart integration in top panel
5. **[05_keyboard_navigation.md](05_keyboard_navigation.md)** - Event loop and shortcuts
6. **[06_histogram_helper.md](06_histogram_helper.md)** - Smart histogram bucketing
7. **[07_polish_and_docs.md](07_polish_and_docs.md)** - Final touches and documentation

## ⚠️ Architecture Guidelines

**CRITICAL:** This feature touches core CLI flows and adds a new modal view.

### Before Starting Each Task:
1. Review [docs/internal/architecture.md](../../architecture.md)
2. Identify which layer each component belongs to:
   - **CLI Layer**: `src/treeline/commands/analysis.py` - thin presentation, renders views
   - **Service Layer**: Use existing services (db_service, etc.)
   - **Domain Layer**: `AnalysisSession` dataclass for state
   - **Infrastructure**: No new infra needed, reuse existing

### After Completing Each Task:
**MANDATORY:** Use `architecture-guardian` agent to review architectural compliance

### Red Flags to Avoid:
❌ Business logic in `commands/analysis.py`
❌ Direct database calls from CLI
❌ Modal view code in service layer
❌ Global state or singletons

### Good Patterns:
✅ Thin command handler that delegates to services
✅ State as simple dataclass
✅ Rich Layout for UI (similar to tag mode)
✅ Dependency injection for services

## Dependencies

**Existing code to leverage:**
- `/tag` mode implementation - similar modal view patterns
- Multiline SQL editor - already exists in `/sql` command
- Chart wizard - already exists
- Query execution service - already exists

**New code needed:**
- `AnalysisSession` dataclass
- Layout composition with 3-4 panels
- Event loop for keyboard navigation
- Chart panel rendering

## Testing Strategy

**Unit Tests:**
- AnalysisSession state management
- Keyboard event routing logic
- Panel visibility based on state

**Smoke Tests:**
- Full analysis workflow: enter → type SQL → execute → chart → exit
- State persistence during session
- Reset functionality

## Success Criteria

- [ ] User can enter `/analysis` and see full-screen modal view
- [ ] SQL editor is always visible at bottom
- [ ] F5 executes query and displays results
- [ ] 'c' creates chart in top panel
- [ ] 'q' exits cleanly
- [ ] All context remains visible (no disappearing SQL/results)
- [ ] 190+ tests still passing
- [ ] Architecture review passes

## Timeline Estimate

- Task 01-02: 1-2 hours (layout + SQL editor)
- Task 03: 1 hour (results panel)
- Task 04: 1-2 hours (chart integration)
- Task 05: 1 hour (keyboard nav)
- Task 06: 2 hours (histogram helper)
- Task 07: 1 hour (polish)

**Total: ~8-10 hours**
