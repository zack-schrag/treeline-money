# Task 03: Results Panel

**Status:** Not Started
**Dependencies:** Task 02
**Estimated Time:** 1 hour

## Objective

Display query results as scrollable table in middle panel, similar to `/tag` mode transaction display.

## Requirements

1. Render results as formatted table
2. Scrollable for large result sets
3. Column headers visible
4. Row count indicator
5. Handle empty results gracefully

## Implementation

**Leverage existing:** Rich Table rendering from other commands

**Key additions:**
- Format columns based on type (amounts, dates, etc.)
- Limit visible rows, indicate total count
- Pagination or scrolling controls

## Acceptance Criteria

- [ ] Results render as table
- [ ] Up to 100 rows visible (configurable)
- [ ] Column headers shown
- [ ] Empty results show helpful message
- [ ] Tests pass
