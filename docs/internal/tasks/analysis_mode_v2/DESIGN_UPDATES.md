# Design Updates: Two-Panel Toggle Approach

**Date:** 2025-10-11
**Change:** Simplified from 3-panel layout to 2-panel toggle layout

## User Feedback

> "you have the chart config appearing in addition to the results. This may be odd, perhaps a simpler way to just toggle between the results view and the chart view."

## Updated Design

### Layout Structure

**Before:** 3 panels (Header + Chart + Results + SQL)
- Chart and Results both visible
- Cluttered when chart present
- More complex rendering logic

**After:** 2 panels with toggle (Header + Data + SQL)
- Data panel shows EITHER results OR chart
- Clean, uncluttered view
- Simple toggle with Tab key

### Visual Change

```
Before:                          After:
┌─────────────────────┐         ┌─────────────────────┐
│ Header              │         │ Header              │
├─────────────────────┤         ├─────────────────────┤
│ Chart (if exists)   │         │ Data Panel:         │
├─────────────────────┤         │  - Results view OR  │
│ Results             │         │  - Chart view       │
├─────────────────────┤         │ [Tab to toggle]     │
│ SQL Editor          │         ├─────────────────────┤
└─────────────────────┘         │ SQL Editor          │
                                └─────────────────────┘
```

## Implementation Changes

### 1. AnalysisSession State
Added `view_mode` field:
```python
view_mode: str = "results"  # "results" or "chart"

def toggle_view(self) -> None:
    """Toggle between results and chart view."""
    if self.view_mode == "results":
        self.view_mode = "chart"
    else:
        self.view_mode = "results"
```

### 2. Keyboard Navigation
- **Tab** - Toggle between results and chart (when chart exists)
- **F5** - Execute query → auto-switch to results view
- **c** - Create chart → auto-switch to chart view
- **s** - Context-aware: save query OR save chart depending on view

### 3. Rendering Logic
```python
# Data panel shows either results or chart
if session.view_mode == "chart" and session.has_chart():
    layout["data"].update(_render_chart_panel(session))
else:
    layout["data"].update(_render_results_panel(session))
```

## User Answers to Open Questions

1. **Chart auto-update?** ✅ Yes - chart automatically updates when SQL is re-executed
2. **Result set limit?** ✅ None - no artificial limits, user can load as many rows as they want
3. **Session auto-save?** ✅ No - keep it simple for v1, no unnecessary complexity

## Benefits

1. **Cleaner UX**: No visual clutter, focus on one data view at a time
2. **Simpler implementation**: Less complex layout logic
3. **Clear state**: User knows exactly what they're viewing
4. **Natural workflow**: Execute → view results → chart → toggle back to verify data

## Updated Files

- [x] `docs/internal/proposals/analysis_mode_v2.md` - Updated layout diagrams and workflow
- [x] `docs/internal/tasks/analysis_mode_v2/01_build_analysis_layout.md` - Updated domain model and rendering
- [x] `docs/internal/tasks/analysis_mode_v2/05_keyboard_navigation.md` - Added Tab key handling
- [x] This document created to track changes

## Ready to Implement

All design decisions finalized. Ready to start Task 01 implementation.
