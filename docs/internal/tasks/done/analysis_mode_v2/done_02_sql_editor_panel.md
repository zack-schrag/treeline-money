# Task 02: SQL Editor Panel

**Status:** Not Started
**Dependencies:** Task 01
**Estimated Time:** 1 hour

## Objective

Integrate multiline SQL editor into the SQL panel, allowing users to edit and execute queries within the modal view.

## Requirements

1. Multiline SQL editor in bottom panel
2. Syntax highlighting (leverage existing SQL editor)
3. F5 executes query and updates results panel
4. SQL persists in session state
5. Cursor position visible

## Implementation

**Leverage existing:** `prompt_toolkit` session from `/sql` command

**Key changes:**
- Extract SQL editor creation into reusable function
- Wire F5 keypress to query execution
- Update `AnalysisSession.sql` on edit
- Clear screen and re-render after execution

## Architecture Notes

- CLI layer handles rendering
- Delegate to `db_service.execute_query()` for execution
- No business logic in command handler

## Acceptance Criteria

- [ ] User can edit SQL in bottom panel
- [ ] F5 executes query
- [ ] Results appear in middle panel
- [ ] SQL state persists between renders
- [ ] Tests pass
