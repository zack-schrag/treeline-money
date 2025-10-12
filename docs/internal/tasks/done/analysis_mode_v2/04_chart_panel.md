# Task 04: Chart Panel

**Status:** Complete
**Dependencies:** Task 03
**Estimated Time:** 1-2 hours

## Objective

Integrate chart creation and display in top panel when user presses 'c' key.

## Requirements

1. 'c' key opens inline chart wizard
2. Chart appears in top panel (expands layout)
3. 'x' key closes chart (collapses panel)
4. Chart persists until closed or reset
5. Leverage existing chart creation code

## Implementation

**Leveraged existing:**
- Chart wizard from `commands/chart_wizard.py`
- ChartWizardConfig and create_chart_from_config

**Key changes:**
- Created `_create_chart()` function for inline chart wizard
- Store chart in `AnalysisSession.chart`
- Updated `_render_chart_panel()` to render actual chart content
- Wired 'c' keypress to create chart
- Tab key toggles between results and chart view
- 'r' key resets and clears chart

## Acceptance Criteria

- [x] 'c' creates chart from results
- [x] Chart appears in data panel
- [x] Tab toggles between results and chart
- [x] Chart persists during session until reset
- [x] Tests pass (222 passing)
