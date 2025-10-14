# Task 01: Create New CLI Structure

## Priority
**CRITICAL** - Foundation for all other tasks

## Objective
Restructure `cli.py` to support both old slash commands (temporarily) and new Typer commands, allowing gradual migration.

## Changes Required

### 1. Restructure cli.py
- Keep existing REPL loop (for now)
- Add new Typer command structure
- Make `treeline` with no args show help (or enter chat later)
- Ensure both systems can coexist during migration

### 2. Update Entry Points
```python
# pyproject.toml
[project.scripts]
treeline = "treeline.cli:app"  # Points to Typer app
tl = "treeline.cli:app"        # Alias

# cli.py structure
app = typer.Typer(...)

@app.command(name="legacy")
def legacy_command():
    """Enter legacy REPL mode (temporary during migration)."""
    run_interactive_mode()  # Old REPL

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Show help by default."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
```

### 3. Helper Functions
Create reusable patterns:
- `require_auth()` - Check authentication, exit if not
- `get_authenticated_user_id()` - Get user ID or exit
- `display_error()` - Consistent error display
- `output_json()` - JSON output helper

### 4. Architecture Validation
- Verify `cli.py` only imports from `app/` (services)
- No imports from `infra/` directly
- All business logic in service layer

## Implementation Notes

**Keep it simple:** This is just scaffolding. Don't migrate commands yet.

**Backward compatibility:** `treeline legacy` temporarily enters old REPL.

**Testing:** Verify `treeline --help` shows command list.

## Success Criteria
- [ ] `treeline --help` shows command list
- [ ] `treeline --version` shows version
- [ ] `treeline legacy` enters old REPL
- [ ] New command structure ready for migration
- [ ] No architectural violations
- [ ] Tests still pass

## Files to Modify
- `src/treeline/cli.py` - Restructure
- `pyproject.toml` - Verify entry points

## Files to Create
None (just restructuring)
