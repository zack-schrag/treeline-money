# CLI Command Patterns

This document describes reusable patterns for implementing Treeline CLI commands.

## Pattern 1: Visual Feedback for Long Operations

Show a spinner/status indicator for long-running operations in **human-readable mode only**. Skip it for `--json` mode to keep output clean.

### Implementation

```python
@app.command()
def my_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """My command that takes time to execute."""
    user_id = get_authenticated_user_id()

    container = get_container()
    my_service = container.my_service()

    # Pattern: Show status for human mode, silent for JSON mode
    if not json_output:
        with console.status(f"[{theme.status_loading}]Processing..."):
            result = asyncio.run(my_service.do_work(user_id))
    else:
        result = asyncio.run(my_service.do_work(user_id))

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    if json_output:
        output_json(result.data)
    else:
        display_my_result(result.data)
```

### Why This Pattern?

- **Human mode**: Users see feedback that something is happening
- **JSON mode**: Clean output for piping/scripting (no status text)
- **Consistency**: All long operations feel the same

### Examples

```bash
# Human mode - shows "Syncing integrations..." spinner
$ treeline sync
Syncing integrations...
✓ Sync completed!

# JSON mode - no spinner, just JSON
$ treeline sync --json
{"results": [...]}
```

## Pattern 2: Dual-Mode Commands (Interactive + Scriptable)

Commands should support **both** interactive prompts and full automation via flags.

### Use Case

User downloads CSV from bank every week. They want to:
1. **First time (interactive)**: Run `treeline import` to figure out column mapping
2. **Automated (scriptable)**: Save command in script for weekly runs

### Implementation

```python
@app.command()
def import_command(
    file_path: str = typer.Argument(None, help="Path to file (omit for interactive)"),
    # Add flags for EVERY interactive option
    account_id: str = typer.Option(None, "--account-id", help="..."),
    date_column: str = typer.Option(None, "--date-column", help="..."),
    # ... more flags
    preview: bool = typer.Option(False, "--preview", help="Preview only"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Dual-mode command."""

    # INTERACTIVE MODE: No file path provided
    if file_path is None:
        from treeline.commands.import_csv import handle_import_command
        handle_import_command()  # Full interactive flow
        return

    # SCRIPTABLE MODE: File path + flags provided
    # Validate required flags
    if not account_id:
        display_error("--account-id is required for scriptable import")
        console.print(f"[{theme.muted}]Hint: Run 'treeline status --json' for account IDs[/{theme.muted}]")
        raise typer.Exit(1)

    # ... execute with provided flags
```

### Benefits

1. **First-time users**: Interactive mode guides them
2. **Power users**: Can automate everything
3. **Preview mode**: Test import before committing
4. **Scriptability**: Weekly cron job example:

```bash
#!/bin/bash
# download_and_import.sh - runs every Monday

# Download CSV from bank (user's script)
./download_transactions.sh > /tmp/transactions.csv

# Import to Treeline (fully automated)
treeline import /tmp/transactions.csv \
  --account-id "dfcd0adb-ed6e-4143-9462-d299eb877873" \
  --date-column "Date" \
  --amount-column "Amount" \
  --description-column "Description" \
  --flip-signs \
  --json > /tmp/import_result.json

# Check results
if jq -e '.imported > 0' /tmp/import_result.json; then
  echo "✓ Imported $(jq '.imported' /tmp/import_result.json) new transactions"
fi
```

## Pattern 3: JSON Output Design

### Principle: **Concise for Scriptability**

JSON output should include:
- ✅ Summary statistics
- ✅ IDs needed for scripting (account IDs, transaction IDs)
- ✅ Simple key-value pairs
- ❌ Full object dumps (verbose, hard to parse)

### Example: Status Command

```python
# BAD - Too verbose (full objects)
{
  "accounts": [
    "id=UUID(...) name='Checking' nickname=None account_type=None ...",
    "id=UUID(...) name='Savings' ..."
  ]
}

# GOOD - Concise summary + IDs
{
  "total_accounts": 2,
  "total_transactions": 665,
  "accounts": [
    {"id": "dfcd0adb-...", "name": "Checking"},
    {"id": "1bd11365-...", "name": "Savings"}
  ],
  "date_range": {
    "earliest": "2025-06-20",
    "latest": "2025-10-10"
  }
}
```

### Scriptability Example

```bash
# Get first checking account ID
ACCOUNT_ID=$(treeline status --json | jq -r '.accounts[] | select(.name | contains("Checking")) | .id')

# Use it in import
treeline import transactions.csv --account-id "$ACCOUNT_ID"
```

## Pattern 4: Error Handling

### Standard Error Pattern

```python
if not result.success:
    display_error(result.error)

    # Optional: Add helpful hint
    if result.error == "No integrations configured":
        console.print(f"[{theme.muted}]Hint: Run 'treeline simplefin' to setup[/{theme.muted}]")

    raise typer.Exit(1)
```

### Benefits
- **Consistent formatting**: All errors look the same
- **Helpful hints**: Guide users to next step
- **Non-zero exit code**: Scripts can detect failures

### JSON Mode Error Handling

```python
if json_output:
    output_json({"error": result.error})
    raise typer.Exit(1)
else:
    display_error(result.error)
    console.print(f"[{theme.muted}]Hint: ...[/{theme.muted}]")
    raise typer.Exit(1)
```

## Pattern Checklist

When implementing a new command:

- [ ] **Visual feedback**: Use `console.status()` for long operations (non-JSON only)
- [ ] **Dual mode**: Support both interactive and fully scriptable modes
- [ ] **JSON output**: Add `--json` flag with concise, script-friendly output
- [ ] **Preview mode**: For destructive operations, add `--preview` flag
- [ ] **Help text**: Include examples showing both modes
- [ ] **Error hints**: Guide users to next step on errors
- [ ] **IDs in JSON**: Include all IDs needed for scripting follow-up commands
- [ ] **Exit codes**: Always `raise typer.Exit(1)` on errors

## Summary

These patterns ensure:
1. **Consistency**: All commands feel the same
2. **Usability**: Interactive mode for learning, scriptable mode for automation
3. **Feedback**: Users always know what's happening
4. **Scriptability**: Every command can be automated
