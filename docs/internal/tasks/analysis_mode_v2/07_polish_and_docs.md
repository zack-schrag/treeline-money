# Task 07: Polish and Documentation

**Status:** Not Started
**Dependencies:** Task 06
**Estimated Time:** 1 hour

## Objective

Final polish, help overlay, and documentation updates.

## Requirements

### Polish
1. Help overlay ('?' key shows all shortcuts)
2. Loading indicators for query execution
3. Better error messages (query failures, invalid chart configs)
4. Smooth panel transitions
5. Terminal size validation

### Documentation
1. Update `/help` command with analysis mode
2. Update `docs/external/landing_page.md` with analysis mode examples
3. Update `docs/external/reference/slash_commands.md`
4. Add GIF/screenshots to README (if applicable)
5. Migration guide (how to use analysis vs sql vs chart)

## Implementation

### Help Overlay
```python
Press '?' to show:
╭─ Analysis Mode Shortcuts ─╮
│ F5  - Execute query        │
│ c   - Create chart         │
│ s   - Save query           │
│ r   - Reset results        │
│ x   - Close chart          │
│ q   - Quit                 │
│ ?   - Show this help       │
╰────────────────────────────╯
```

### Landing Page Example
Add analysis mode showcase to landing page with example workflow.

## Acceptance Criteria

- [ ] Help overlay implemented
- [ ] Error handling improved
- [ ] All documentation updated
- [ ] Migration guide clear
- [ ] Manual testing complete
- [ ] All 190+ tests passing
