# Task 03: Migrate Sync and Import (Scriptable)

## Priority
**HIGH** - Core scriptable commands

## Objective
Migrate `/sync` and `/import` to standard CLI commands with JSON output support.

## Part A: `treeline sync`

### Service Layer Check
- Verify `SyncService` has all logic
- No business logic in old command handler

### Implementation
```python
@app.command(name="sync")
def sync_command(
    integration: str = typer.Option(None, "--integration", help="Sync specific integration"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Synchronize data from connected integrations."""
    user_id = get_authenticated_user_id()

    container = get_container()
    sync_service = container.sync_service()

    result = asyncio.run(
        sync_service.sync_integration(user_id, integration) if integration
        else sync_service.sync_all_integrations(user_id)
    )

    if json_output:
        output_json(result.data)
    else:
        display_sync_result(result.data)
```

### Testing
- `treeline sync`
- `treeline sync --integration simplefin`
- `treeline sync --json`

## Part B: `treeline import`

### Service Layer Check
- Verify `ImportService` has all CSV logic
- Move any display logic out of service

### Implementation
```python
@app.command(name="import")
def import_command(
    file_path: Path = typer.Argument(..., help="Path to CSV file"),
    account: str = typer.Option(None, "--account", help="Account name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Import transactions from CSV file."""
    user_id = get_authenticated_user_id()

    if not file_path.exists():
        display_error(f"File not found: {file_path}")
        raise typer.Exit(1)

    container = get_container()
    import_service = container.import_service()

    # Interactive column mapping if not --json
    if not json_output:
        # Use Rich prompts for column mapping
        column_mapping = prompt_for_column_mapping(file_path)
    else:
        # Auto-detect or error
        column_mapping = auto_detect_columns(file_path)

    result = asyncio.run(
        import_service.import_from_csv(user_id, file_path, column_mapping, account)
    )

    if json_output:
        output_json(result.data)
    else:
        display_import_result(result.data)
```

### Testing
- `treeline import transactions.csv`
- `treeline import transactions.csv --account "Chase Checking"`
- `treeline import transactions.csv --json`

## Success Criteria
- [ ] Both commands work with and without --json
- [ ] Service layer has all business logic
- [ ] CLI has only display logic
- [ ] Error handling is consistent
- [ ] Help text is clear
- [ ] Can be used in bash scripts

## Files to Modify
- `src/treeline/cli.py` - Add commands
- `src/treeline/app/service.py` - Verify/update services
- `src/treeline/commands/import_csv.py` - Extract display helpers

## Files to Mark for Deletion (later)
- Old `/sync` handler (task 10)
- Old `/import` handler (task 10)
