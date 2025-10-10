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
