# Analysis Mode: Pivot to Modal View Approach

**Date:** 2025-10-11
**Decision:** Pivot from REPL-based to modal view approach

## Context

After implementing Task 01 (simplified SQL prompts), we discovered issues with the REPL approach:
1. **Visibility problems**: Prompt text colors not showing in terminal
2. **Context loss**: Results disappear between modes
3. **Complexity**: State machine navigation harder to implement
4. **Poor fit**: REPL doesn't match "IDE-like workspace" vision

## Decision

**Pivot to full-screen modal view** (like `/tag` mode):
- All context visible simultaneously (SQL + Results + Chart)
- Proven UI pattern users already understand
- Simpler implementation (less state management)
- Better alignment with vision

## What Changed

### Archived (REPL Approach)
- `docs/internal/proposals/analysis_mode.md` → `analysis_mode_v1_archived.md`
- `docs/internal/tasks/analysis_mode/` → `analysis_mode_v1_archived/`

### New (Modal View Approach)
- `docs/internal/proposals/analysis_mode_v2.md` - New proposal
- `docs/internal/tasks/analysis_mode_v2/` - New task breakdown (7 tasks)

### Preserved
- **Task 01 work is still valuable**: Simplified `/sql` prompts improve UX regardless of analysis mode implementation
- All tests still passing (190 unit + 6 smoke)
- Chart feature fully functional

## New Task Breakdown

1. **Task 01**: Build analysis layout (Rich Layout, 3 panels)
2. **Task 02**: SQL editor panel (multiline, F5 to execute)
3. **Task 03**: Results panel (table display, scrollable)
4. **Task 04**: Chart panel (appears when created, 'x' to close)
5. **Task 05**: Keyboard navigation (F5, c, s, r, x, q)
6. **Task 06**: Histogram helper (smart bucketing)
7. **Task 07**: Polish and documentation

## Timeline

**Original estimate:** 10-12 hours (REPL approach)
**New estimate:** 8-10 hours (Modal view approach)

Simpler implementation = faster delivery.

## Next Steps

1. ✅ Proposal updated (analysis_mode_v2.md)
2. ✅ Task breakdown created
3. ✅ Old files archived
4. ⏭️ Ready to start Task 01: Build Analysis Layout

## Lessons Learned

- Test UI patterns early in actual terminal environment
- Leverage existing proven patterns (tag mode) rather than inventing new ones
- Visual continuity matters for "IDE-like" feel
- Sometimes pivoting early saves time vs. pushing through issues
