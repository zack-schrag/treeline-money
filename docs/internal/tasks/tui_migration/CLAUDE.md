# TUI Migration Implementation Guidelines

## Architecture Principles

### CLI Layer Responsibilities (ONLY)
- Parse command-line arguments
- Display formatted output (Rich for terminal, JSON for scripts)
- Launch TUI applications (Textual)
- Handle user input/prompts
- **NO business logic whatsoever**

### Service Layer Responsibilities
- All business logic
- Data validation
- Query execution
- Integration coordination
- File operations (via storage abstractions)

### Command Structure
```
cli.py (Typer app)
  ├─ Parses: treeline <command> [args]
  ├─ Calls: service methods from container
  └─ Displays: results using Rich or Textual

commands/ (TUI implementations)
  ├─ Textual apps for complex workflows
  └─ Called by cli.py, uses services via container
```

## Implementation Rules

1. **Service First**: If business logic exists in CLI/commands, move it to service layer FIRST
2. **Single Responsibility**: Each command should be <100 lines if scriptable, focused on display
3. **No Duplication**: Reuse service methods, don't duplicate logic
4. **Container Pattern**: Always use `container.service_name()` for dependencies
5. **Output Formats**: Support both human-readable (Rich) and machine-readable (--json flag)
6. **Testing**: Scriptable commands MUST have unit tests

## Migration Pattern

For each command:
1. ✅ **Audit**: Check if business logic exists in old command handler
2. ✅ **Extract**: Move business logic to service layer if needed
3. ✅ **Implement**: Create new Typer command or Textual TUI
4. ✅ **Test**: Verify functionality matches old behavior
5. ✅ **Document**: Update help text and README
6. ✅ **Remove**: Delete old slash command handler

## Scriptable Command Template

```python
@app.command(name="status")
def status_command(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Show account summary and statistics."""
    container = get_container()
    config_service = container.config_service()

    # Check auth
    if not config_service.is_authenticated():
        if json_output:
            print(json.dumps({"error": "Not authenticated"}))
            raise typer.Exit(1)
        console.print("[red]Error: Not authenticated[/red]")
        raise typer.Exit(1)

    # Get data from service
    user_id = UUID(config_service.get_current_user_id())
    status_service = container.status_service()
    result = asyncio.run(status_service.get_status(user_id))

    # Display
    if json_output:
        print(json.dumps(result.data))
    else:
        # Use Rich to format nicely
        display_status(result.data)
```

## TUI Command Template

```python
@app.command(name="analysis")
def analysis_command() -> None:
    """Launch interactive analysis mode."""
    container = get_container()
    config_service = container.config_service()

    # Check auth
    if not config_service.is_authenticated():
        console.print("[red]Error: Not authenticated[/red]")
        raise typer.Exit(1)

    # Launch Textual app
    from treeline.commands.analysis_textual import AnalysisApp
    app = AnalysisApp()
    app.run()
```

## Verification Checklist

Before marking a command as "migrated":
- [ ] Old slash command removed
- [ ] New Typer command works
- [ ] Service layer has all business logic
- [ ] CLI has only presentation logic
- [ ] Help text is clear
- [ ] Works with `treeline <cmd> --help`
- [ ] If scriptable: supports --json flag
- [ ] Tests updated/added
- [ ] No architectural violations

## Code Organization

```
src/treeline/
├── cli.py                          # Main Typer app, all @app.command()
├── commands/                       # TUI implementations only
│   ├── analysis_textual.py        # Textual TUI
│   └── tag_textual.py             # Textual TUI
├── app/
│   ├── service.py                 # All business logic
│   └── container.py               # DI container
└── infra/                         # Infrastructure implementations
```

## Common Pitfalls to Avoid

❌ **Don't**: Put business logic in CLI handlers
✅ **Do**: Call service methods from CLI handlers

❌ **Don't**: Mix TUI code with service logic
✅ **Do**: TUIs call services via container

❌ **Don't**: Have commands directly import from infra/
✅ **Do**: Use container to get service instances

❌ **Don't**: Duplicate logic between old and new commands
✅ **Do**: Remove old code immediately after migration

## Post-Migration

Once all commands are migrated:
1. Remove old REPL loop from cli.py
2. Remove slash command parsing
3. Remove all old command handlers
4. Update all documentation
5. Run full test suite
6. Verify architecture with architecture-guardian agent
