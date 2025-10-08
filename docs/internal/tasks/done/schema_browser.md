# Schema Browser

Users need to see what tables and columns are available when writing SQL queries. Currently, they have to remember or look at external documentation.

## User Story
As a user, I want to see what tables and columns exist in my database so that I can write SQL queries without guessing or checking documentation.

## Current State
Users must:
- Remember table/column names
- Check external documentation
- Run `SELECT * FROM table LIMIT 1` to see columns
- Make errors and iterate

## Desired State
```
> /schema

Available tables:
  - accounts
  - transactions
  - balance_snapshots
  - integrations

> /schema transactions

Table: transactions
┌──────────────────────┬──────────┬──────────┐
│ Column               │ Type     │ Nullable │
├──────────────────────┼──────────┼──────────┤
│ id                   │ UUID     │ NO       │
│ account_id           │ UUID     │ NO       │
│ amount               │ DECIMAL  │ NO       │
│ transaction_date     │ DATE     │ NO       │
│ posted_date          │ DATE     │ YES      │
│ description          │ VARCHAR  │ YES      │
│ tags                 │ VARCHAR[]│ YES      │
│ external_ids         │ JSON     │ NO       │
│ created_at           │ TIMESTAMP│ NO       │
│ updated_at           │ TIMESTAMP│ NO       │
└──────────────────────┴──────────┴──────────┘

Sample query:
SELECT * FROM transactions
WHERE amount < 0
  AND transaction_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY transaction_date DESC
LIMIT 10;
```

## Implementation Details

### Commands

**List all tables:**
- `/schema` - shows all tables in the database

**Show table schema:**
- `/schema table_name` - shows columns, types, nullability
- Include example query for that table

### Technical Approach
1. Add new command `/schema` in `src/treeline/commands/`
2. Use DuckDB's `INFORMATION_SCHEMA` or `DESCRIBE` to get metadata
3. Format output using `rich.table.Table` for clean display
4. Add example queries for each table (hardcoded templates)
5. Reuse existing database connection from container

### Query to Get Schema
```sql
-- List tables
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'main';

-- Get columns for a table
SELECT
  column_name,
  data_type,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'transactions'
ORDER BY ordinal_position;
```

### Example Queries (Templates)
Provide helpful examples for each table:

**transactions:**
```sql
SELECT * FROM transactions
WHERE amount < 0
  AND transaction_date >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY transaction_date DESC
LIMIT 10;
```

**accounts:**
```sql
SELECT
  name,
  institution_name,
  (SELECT SUM(amount) FROM transactions WHERE account_id = accounts.id) as total_flow
FROM accounts;
```

**balance_snapshots:**
```sql
SELECT
  snapshot_date,
  balance
FROM balance_snapshots
WHERE account_id = 'your-account-id'
ORDER BY snapshot_date DESC
LIMIT 30;
```

### Edge Cases
- No tables (new installation) - show friendly message
- Invalid table name - show error and list valid tables
- Table with no columns (shouldn't happen, but handle gracefully)

## Acceptance Criteria
- [ ] `/schema` lists all tables
- [ ] `/schema table_name` shows columns with types and nullability
- [ ] Output formatted as a clean table using rich
- [ ] Include example query for each table
- [ ] Graceful error handling for invalid table names
- [ ] Updated `/help` to show `/schema` command
- [ ] Updated docs/external/reference/slash_commands.md
- [ ] Unit tests for schema fetching logic
- [ ] Smoke test to verify commands work

## Notes
- This is pure read-only introspection
- Keep example queries simple and practical
- Focus on the main tables users will query
- Can add more features later (search columns, show indexes, etc.)
