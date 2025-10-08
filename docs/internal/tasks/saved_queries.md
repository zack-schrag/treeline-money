# Saved Queries

Users need to save frequently-used queries for reuse. Writing the same query repeatedly is tedious and error-prone.

## User Story
As a user, I want to save SQL queries I use frequently so that I can quickly run them again without rewriting.

## Current State
Users must retype or copy-paste queries every time. No way to organize or reuse queries.

## Desired State
```
> /sql
SELECT SUM(amount) FROM transactions
WHERE 'dining' = ANY(tags)
  AND transaction_date >= date_trunc('month', CURRENT_DATE)

[Results displayed]

Save this query? (y/n): y
Name: dining_this_month

✓ Saved as ~/.treeline/queries/dining_this_month.sql

> /query:dining_this_month
[Query executes and shows results]

> /queries list
Saved queries:
  - dining_this_month
  - net_worth_trend
  - monthly_summary

> /queries show dining_this_month
[Displays the SQL]
```

## Implementation Details

### File Structure
Queries stored as plain `.sql` files in `~/.treeline/queries/`:
```
~/.treeline/
└── queries/
    ├── dining_this_month.sql
    ├── net_worth_trend.sql
    └── monthly_summary.sql
```

### Commands

**Save a query:**
After running `/sql` or `/query`, prompt user: "Save this query? (y/n)"
- If yes, ask for name
- Validate name (alphanumeric + underscores only)
- Save to `~/.treeline/queries/{name}.sql`
- Confirm with file path

**Run saved query:**
- `/query:query_name` - runs the saved query
- Example: `/query:dining_this_month`

**List queries:**
- `/queries list` - shows all saved queries

**Show query:**
- `/queries show query_name` - displays the SQL

**Delete query:**
- `/queries delete query_name` - removes the file

### Technical Approach
1. Create queries directory on first use (in `~/.treeline/queries/`)
2. Add save prompt after query execution in `/sql` and `/query` commands
3. Add new `/queries` command with subcommands (list, show, delete)
4. Add support for `/query:name` syntax to run saved queries
5. Use simple file I/O - no database needed
6. Files are just `.sql` text files (easy to edit externally)

### Edge Cases
- Query name already exists (prompt to overwrite)
- Invalid query name characters (show error, ask again)
- Queries directory doesn't exist (create it)
- Empty query (don't offer to save)
- Query file deleted externally (handle gracefully)

## Acceptance Criteria
- [ ] After running query, user is prompted to save
- [ ] Saved queries stored as `.sql` files in `~/.treeline/queries/`
- [ ] `/query:name` syntax runs saved query
- [ ] `/queries list` shows all saved queries
- [ ] `/queries show name` displays the SQL
- [ ] `/queries delete name` removes the query
- [ ] Query names validated (alphanumeric + underscore only)
- [ ] Graceful error handling for missing/invalid queries
- [ ] Updated `/help` to show `/queries` command
- [ ] Updated docs/external/reference/slash_commands.md
- [ ] Unit tests for query saving/loading logic
- [ ] Smoke test for full workflow

## Notes
- Keep it simple - just plain text files
- Users can edit `.sql` files directly (intentional design)
- No fancy query organization (folders, tags) yet - just flat list
- File-based approach aligns with "local-first" philosophy
