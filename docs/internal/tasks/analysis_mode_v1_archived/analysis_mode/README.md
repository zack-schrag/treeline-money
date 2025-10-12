# Analysis Mode Implementation

This folder contains all tasks related to implementing the fluid `/analysis` mode for Treeline.

## Overview

See the full proposal: [docs/internal/proposals/analysis_mode.md](../../proposals/analysis_mode.md)

## Goal

Create a fluid, iterative workspace for data exploration that maintains state and allows users to move seamlessly between SQL editing, result viewing, and chart creation.

## Implementation Order

The tasks should be completed in this order to minimize risk and maximize value:

1. **01_simplify_sql_prompts.md** - Quick win, reduces friction immediately
2. **02_refine_chart_command.md** - Clarify `/chart` purpose as browser/runner
3. **03_histogram_bucketing_helper.md** - Smart helper for common use case
4. **04_analysis_session_state.md** - Core state management for analysis mode
5. **05_analysis_modal_navigation.md** - Build the modal UI for analysis mode
6. **06_analysis_autocomplete.md** - Polish: autocomplete within mode
7. **07_update_documentation.md** - Update docs and landing page

## Acceptance Criteria (Overall)

- `/sql` has streamlined chart creation (single action menu instead of 3 prompts)
- `/chart` is clearly a browser for saved charts
- `/analysis` mode provides fluid SQL → Results → Chart workflow
- Histogram bucketing has smart helper (no manual SQL required)
- Documentation reflects new mental model
- All existing tests pass
- New smoke test for full `/analysis` workflow

## Testing Strategy

Each task should include unit tests where applicable. The final task (07) should include a comprehensive smoke test that exercises the full `/analysis` workflow.

## ⚠️ Architecture Guidelines

**CRITICAL:** This is a large feature that touches core CLI flows. We must maintain hexagonal architecture principles throughout.

### Before Starting Each Task:
1. Review `docs/internal/architecture.md` for hexagonal principles
2. Identify which layer each new module belongs to:
   - **CLI layer** (`src/treeline/cli.py`, `commands/*.py`) - thin presentation, NO business logic
   - **Service layer** (`src/treeline/app/service.py`) - business logic, independent of tech choices
   - **Abstractions** (`src/treeline/abstractions.py`) - ports/interfaces
   - **Infrastructure** (`src/treeline/infra/`) - adapters for specific technologies

### After Completing Each Task:
**MANDATORY:** Use the `architecture-guardian` agent to review your changes:

```
Use the architecture-guardian agent to review the implementation in:
- src/treeline/commands/analysis.py (or relevant files)
- Ensure no business logic leaked into CLI layer
- Verify abstractions are technology-agnostic
- Check that state management follows clean patterns
```

### Red Flags to Avoid:
❌ **Business logic in CLI commands** - Commands should only parse input, call services, display output
❌ **Direct database/API calls from commands** - Always go through service layer
❌ **Technology-specific details in abstractions** - Keep interfaces generic
❌ **Global state or singletons** - Pass dependencies explicitly
❌ **Mixing concerns** - State management ≠ UI rendering ≠ business logic

### Good Patterns to Follow:
✅ **Thin command handlers** - Parse → Call service → Display
✅ **State as data class** - Simple, immutable where possible
✅ **Services coordinate logic** - But defer to domain/repository for operations
✅ **Dependency injection** - Use container, no hardcoded imports
✅ **Testable units** - Each module independently testable

## Architecture Review Checkpoints

**Task 01 (Simplify SQL prompts):**
- Review: UI refactoring only, no new business logic

**Task 03 (Histogram bucketing):**
- Review: SQL transformation logic - should this be a service? An abstraction?

**Task 04 (Session state):**
- Review: State management structure - is it properly isolated?

**Task 05 (Modal navigation):**
- Review: CLI command structure - are handlers thin enough?

**FINAL REVIEW** (After Task 07):
- Comprehensive architecture-guardian review of entire feature
- Verify no hexagonal violations
- Check for code smells or architectural drift
