# Multi-Line SQL Editor

Currently, `/query` only accepts single-line inline SQL. This is extremely limiting for real analysis work. Users need a proper multi-line SQL editor for complex queries.

## User Story
As a power user, I want to write multi-line SQL queries with proper formatting so that I can perform complex analysis without cramming everything into one line.

## Current State
```
> /query SELECT * FROM transactions WHERE amount < 0 AND transaction_date >= '2025-01-01' ORDER BY amount LIMIT 10
```

This is painful for anything non-trivial.

## Desired State
```
> /sql

[Multi-line editor opens]

SELECT
  tags,
  SUM(amount) as total_spending,
  COUNT(*) as transaction_count
FROM transactions
WHERE amount < 0
  AND transaction_date >= '2025-01-01'
  AND transaction_date < '2025-02-01'
GROUP BY tags
ORDER BY total_spending
LIMIT 10;

[Press Ctrl+Enter to execute, Ctrl+C to cancel]
```

## Implementation Details

### New Command
- Add `/sql` command that opens multi-line editor
- Editor should use `prompt_toolkit` for rich input experience
- Keep existing `/query` for quick one-liners

### Features
**Essential:**
- Multi-line input (obviously)
- Execute with Ctrl+Enter
- Cancel with Ctrl+C returns to main prompt
- Basic syntax highlighting using `pygments` (already available)
- Display results as table (reuse existing query display logic)

**Nice to have (if easy):**
- Show line numbers
- Basic history (up arrow for previous queries)

### Technical Approach
1. Create new command handler `handle_sql_command()` in `src/treeline/commands/query.py`
2. Use `prompt_toolkit.PromptSession` with multiline=True
3. Use `pygments.lexers.SqlLexer` for syntax highlighting
4. Reuse existing query execution and display logic from `/query` command
5. Add proper error handling for SQL syntax errors

### Edge Cases
- Empty query (just return to prompt)
- Query with only whitespace (ignore)
- Very long queries (paginate results if needed)
- Syntax errors (display error message, stay in editor? or return to prompt?)

## Acceptance Criteria
- [ ] `/sql` command opens multi-line editor
- [ ] Ctrl+Enter executes the query
- [ ] Ctrl+C cancels and returns to main prompt
- [ ] SQL syntax highlighting works
- [ ] Query results displayed as formatted table
- [ ] Works with SELECT and WITH queries (no mutations)
- [ ] Error messages are clear and helpful
- [ ] Updated `/help` to show `/sql` command
- [ ] Updated docs/external/reference/slash_commands.md
- [ ] Unit tests for the new command handler
- [ ] Smoke test to verify end-to-end workflow

## Notes
- Keep this simple - no need for fancy editor features yet
- Focus on making it functional and reliable
- Can enhance with autocomplete, better error handling, etc. in future tasks
