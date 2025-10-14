# Task 02: Migrate Analysis (TUI) and Status (Scriptable)

## Priority
**CRITICAL** - First real migrations, establishes patterns

## Objective
Migrate one TUI command (`/analysis`) and one scriptable command (`/status`) to validate the new architecture and get user feedback.

## Part A: Migrate /analysis to `treeline analysis`

### Changes
1. **Add Typer command:**
```python
@app.command(name="analysis")
def analysis_command() -> None:
    """Launch interactive data analysis workspace."""
    require_auth()
    from treeline.commands.analysis_textual import AnalysisApp
    app = AnalysisApp()
    app.run()
```

2. **Keep** `analysis_textual.py` as-is (already done)

3. **Test:**
   - `treeline analysis --help`
   - Launch and verify all functionality works
   - Compare with old `/analysis` behavior

## Part B: Migrate /status to `treeline status`

### Changes
1. **Audit current implementation:**
   - Check `commands/status.py` for business logic
   - If found, move to `StatusService` in `app/service.py`

2. **Create StatusService (if needed):**
```python
class StatusService:
    def __init__(self, repository: Repository):
        self.repository = repository

    async def get_status(self, user_id: UUID) -> Result[dict]:
        """Get account summary and statistics."""
        # All logic here, return structured data
```

3. **Add Typer command:**
```python
@app.command(name="status")
def status_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Show account summary and statistics."""
    user_id = get_authenticated_user_id()

    container = get_container()
    status_service = container.status_service()
    result = asyncio.run(status_service.get_status(user_id))

    if not result.success:
        display_error(result.error)
        raise typer.Exit(1)

    if json_output:
        output_json(result.data)
    else:
        display_status(result.data)  # Rich formatting
```

4. **Display function:**
```python
def display_status(data: dict) -> None:
    """Display status using Rich (keep in cli.py)."""
    # Rich Table, Panel, etc. - presentation only
```

5. **Test:**
   - `treeline status`
   - `treeline status --json`
   - `treeline status --json | jq .`

## Validation Checklist

### Architecture
- [ ] StatusService has all business logic
- [ ] CLI command only displays data
- [ ] No direct imports from `infra/` in CLI
- [ ] Container pattern used correctly

### Functionality
- [ ] `treeline analysis` works identically to `/analysis`
- [ ] `treeline status` shows same info as `/status`
- [ ] `treeline status --json` outputs valid JSON
- [ ] Help text is clear and useful

### Testing
- [ ] Manual testing complete
- [ ] JSON output can be piped to jq
- [ ] Error handling works (not authenticated, etc.)

## User Review

After this task, STOP and get feedback:
1. Does `treeline status` feel right?
2. Is the JSON output useful?
3. Does `treeline analysis` work as expected?
4. Any UX improvements needed?

**Don't proceed to task 03 until approved.**

## Files to Modify
- `src/treeline/cli.py` - Add commands
- `src/treeline/app/service.py` - Add/update StatusService
- `src/treeline/app/container.py` - Add status_service() if needed

## Files to Create
None (reusing existing)

## Files to Mark for Deletion (later)
- Old `/status` handler in REPL (task 10)
- Old `/analysis` handler in REPL (task 10)
