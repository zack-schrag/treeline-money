# Task 04: Migrate Query and Schema (Scriptable)

## Priority
**MEDIUM** - Useful scriptable commands

## Objective
Migrate `/query`, `/sql`, and `/schema` to standard CLI.

## Part A: `treeline query`

### Implementation
```python
@app.command(name="query")
def query_command(
    sql: str = typer.Argument(..., help="SQL query to execute"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    format: str = typer.Option("table", "--format", help="Output format: table, json, csv")
) -> None:
    """Execute a SQL query (SELECT/WITH only)."""
    user_id = get_authenticated_user_id()

    # Validate SELECT/WITH only
    sql_upper = sql.strip().upper()
    if not sql_upper.startswith(("SELECT", "WITH")):
        display_error("Only SELECT and WITH queries allowed")
        raise typer.Exit(1)

    container = get_container()
    db_service = container.db_service()
    result = asyncio.run(db_service.execute_query(user_id, sql))

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    # Output based on format
    if format == "json" or json_output:
        output_json(result.data)
    elif format == "csv":
        output_csv(result.data)
    else:
        display_query_results(result.data)
```

### Testing
- `treeline query "SELECT * FROM accounts"`
- `treeline query "SELECT * FROM accounts" --json`
- `treeline query "SELECT * FROM accounts" --format csv > accounts.csv`

## Part B: `treeline schema`

### Implementation
```python
@app.command(name="schema")
def schema_command(
    table: str = typer.Argument(None, help="Table name (optional)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Show database schema for all tables or a specific table."""
    user_id = get_authenticated_user_id()

    container = get_container()
    db_service = container.db_service()

    if table:
        result = asyncio.run(db_service.get_table_schema(user_id, table))
    else:
        result = asyncio.run(db_service.get_all_schemas(user_id))

    if json_output:
        output_json(result.data)
    else:
        display_schema(result.data)
```

### Testing
- `treeline schema`
- `treeline schema accounts`
- `treeline schema --json | jq .`

## Note: SQL Editor

The `/sql` multiline editor is REPLACED by `treeline analysis` TUI.

Users who want multiline SQL should use:
```bash
treeline analysis   # Full TUI with editor
# OR
treeline query "$(cat query.sql)"  # From file
```

## Success Criteria
- [ ] `treeline query` outputs to stdout cleanly
- [ ] Multiple format options work
- [ ] Can pipe to other commands
- [ ] `treeline schema` shows useful info
- [ ] JSON output is well-structured

## Files to Modify
- `src/treeline/cli.py` - Add commands
- `src/treeline/app/service.py` - Add schema methods if needed

## Files to Mark for Deletion (later)
- Old `/query`, `/sql`, `/schema` handlers (task 10)
- `commands/query.py` - Multiline editor (replaced by analysis TUI)
